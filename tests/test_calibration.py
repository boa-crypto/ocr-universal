"""Tests A2 : calibration des scores de confiance."""

import pytest
from fastapi.testclient import TestClient

from unocr import api
from unocr.api import app
from unocr.calibration import Calibration, fit_isotonic, fit_platt


@pytest.fixture()
def client(tmp_cfg, fixtures_dir):
    api._watch.stop()
    api._watch.reset()
    yield TestClient(app)
    api._watch.stop()
    api._watch.reset()


# ───────────────────────── mathématique ─────────────────────────

def test_platt_separates_correct_and_wrong():
    """Platt donne une probabilité forte aux bons scores, faible aux mauvais."""
    A, B = fit_platt([(0.95, True)] * 10 + [(0.2, False)] * 10)
    cal = Calibration(method="platt", a=A, b=B, active=True)
    assert cal.apply(0.95) > 0.8
    assert cal.apply(0.2) < 0.2
    assert cal.apply(0.95) > cal.apply(0.5) > cal.apply(0.2)   # monotone


def test_platt_is_deterministic():
    """Même entrée → même sortie (pas d'aléa, donc testable)."""
    pairs = [(i / 20, i > 10) for i in range(20)]
    assert fit_platt(pairs) == fit_platt(pairs)


def test_isotonic_is_monotonic():
    pairs = [(i / 30, i > 15) for i in range(30)]
    steps = fit_isotonic(pairs)
    probs = [p for _, p in steps]
    assert probs == sorted(probs)                     # non décroissant
    assert all(0.0 <= p <= 1.0 for p in probs)


def test_identity_calibration_changes_nothing():
    cal = Calibration()
    assert cal.active is False
    for s in (0.0, 0.3, 0.62, 1.0):
        assert cal.apply(s) == s


def test_apply_is_always_bounded():
    cal = Calibration(method="platt", a=50.0, b=-25.0, active=True)
    for s in (0.0, 0.5, 1.0, 0.99):
        assert 0.0 <= cal.apply(s) <= 1.0


# ───────────────────────── garde-fous ─────────────────────────

def test_too_few_samples_keeps_identity():
    cal = Calibration()
    diag = cal.fit([(0.9, True)] * 3)
    assert diag["method"] == "identity"
    assert diag["active"] is False
    assert "insuffisant" in diag["note"]
    assert cal.apply(0.9) == 0.9


def test_synthetic_fit_is_fitted_but_inactive():
    """Le cœur du garde-fou : ajusté sur du synthétique ⇒ jamais actif d'office."""
    cal = Calibration()
    diag = cal.fit([(0.9, True)] * 10 + [(0.2, False)] * 10)
    assert diag["method"] == "platt"
    assert diag["active"] is False
    assert diag["synthetic"] is True
    assert "SYNTHÉTIQUES" in diag["note"]
    assert cal.apply(0.9) == 0.9          # pas d'effet tant que inactif


def test_force_activates_and_real_data_activates():
    cal = Calibration()
    cal.fit([(0.9, True)] * 10 + [(0.2, False)] * 10, force=True)
    assert cal.active is True

    cal2 = Calibration()
    cal2.fit([(0.9, True)] * 10 + [(0.2, False)] * 10, synthetic=False)
    assert cal2.active is True


def test_isotonic_chosen_when_enough_samples():
    cal = Calibration()
    pairs = [(i / 250, i > 125) for i in range(250)]
    diag = cal.fit(pairs, synthetic=False)
    assert diag["method"] == "isotonic"
    assert diag["n_samples"] == 250


# ───────────────────────── persistance ─────────────────────────

def test_save_load_roundtrip(tmp_path):
    cal = Calibration(method="platt", a=2.0, b=-1.0, active=True,
                      n_samples=40, n_positive=20, synthetic=False)
    path = cal.save(tmp_path / "calibration.json")
    loaded = Calibration.load(path)
    assert loaded.a == 2.0 and loaded.b == -1.0
    assert loaded.active is True and loaded.method == "platt"
    assert loaded.n_samples == 40


def test_load_missing_file_is_identity(tmp_path):
    cal = Calibration.load(tmp_path / "absent.json")
    assert cal.method == "identity" and cal.active is False


def test_load_corrupt_file_is_identity(tmp_path):
    bad = tmp_path / "calibration.json"
    bad.write_text("{ceci n'est pas du json", encoding="utf-8")
    assert Calibration.load(bad).method == "identity"


# ───────────────────────── intégration pipeline ─────────────────────────

def test_pipeline_sets_calibrated_confidence(client, fixtures_dir):
    """Le champ calibré existe et reste cohérent avec la confiance (identité)."""
    r = client.post("/api/documents", files={"file": (
        "carte_grise.png", (fixtures_dir / "photo_carte_grise.png").read_bytes(),
        "image/png")})
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    for _ in range(60):
        st = client.get(f"/api/jobs/{job_id}").json()
        if st.get("status") in ("done", "error"):
            break
    doc = client.get(f"/api/jobs/{job_id}/result").json()
    fields = doc.get("fields") or {}
    assert fields, "aucun champ extrait — test non concluant"
    for name, fv in fields.items():
        if fv.get("confidence"):
            # calibration inactive par défaut : identité
            assert fv.get("calibrated_confidence") == fv["confidence"]


# ───────────────────────── API ─────────────────────────

def test_calibration_endpoint_reports_provenance(client):
    body = client.get("/api/calibration").json()
    assert body["method"] in ("identity", "platt", "isotonic")
    assert body["active"] is False        # aucune calibration validée à ce jour
    assert body["synthetic"] is True


def test_calibration_fit_endpoint(client):
    """Le réajustement réel tourne sur les échantillons étiquetés."""
    r = client.post("/api/calibration/fit", json={"force": False})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["suite"] in ("synthétique", "réelle")
    assert body["n_samples"] >= 8, "trop peu de paires étiquetées"
    assert body["active"] is False        # synthétique ⇒ inactif
    assert "note" in body


def test_calibration_fit_force_activates(client):
    r = client.post("/api/calibration/fit", json={"force": True})
    assert r.status_code == 200
    body = r.json()
    assert body["method"] in ("platt", "isotonic")
    assert body["active"] is True
    # l'état exposé reflète l'activation
    state = client.get("/api/calibration").json()
    assert state["active"] is True and state["method"] == body["method"]
