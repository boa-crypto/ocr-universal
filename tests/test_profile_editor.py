"""Tests de l'éditeur de profils (B5) : CRUD, sécurité, essai à blanc."""
import pytest
from fastapi.testclient import TestClient

from unocr import api
from unocr.api import app


@pytest.fixture()
def client(tmp_cfg, fixtures_dir):
    api._watch.stop()
    api._watch.reset()
    yield TestClient(app)
    api._watch.stop()
    api._watch.reset()


def _wait_done(client, job_id, timeout=180):
    import time

    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "error"):
            return j
        time.sleep(0.5)
    raise TimeoutError("job non terminé")


def _upload(client, path, name, **data):
    with open(path, "rb") as f:
        base = {"profile": "invoice", "quality_mode": "fast"}
        base.update(data)
        return client.post("/api/documents",
                           files={"file": (name, f, "application/octet-stream")},
                           data=base)


# ─────────────────────────── lecture ───────────────────────────

def test_catalog_lists_vocabulary(client):
    d = client.get("/api/profiles/catalog").json()
    assert "vin_check" in d["validators"]
    assert "iso6346" in d["validators"]
    assert "date" in d["normalizations"]
    assert d["aux_validators"] == ["vin_check"]


def test_get_builtin_profile(client):
    r = client.get("/api/profiles/invoice")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "builtin"
    assert body["fields"], "le profil facture doit avoir des champs"
    assert all("key" in f and "patterns" in f for f in body["fields"])


def test_get_unknown_profile(client):
    assert client.get("/api/profiles/nexiste_pas").status_code == 404


def test_user_profile_appears_in_list(client):
    body = {"label": "Mon profil", "fields": [
        {"key": "numero", "label": "Numéro", "patterns": [r"N°\s*(\d+)"]}]}
    assert client.put("/api/profiles/essai", json=body).status_code == 200
    names = [p["name"] for p in client.get("/api/profiles").json()]
    assert "essai" in names


# ─────────────────────────── écriture ───────────────────────────

def test_create_user_profile(client):
    body = {"label": "Bon de livraison interne",
            "description": "test",
            "fields": [{"key": "ref", "label": "Référence",
                        "patterns": [r"REF[:\s]+([A-Z0-9-]+)"],
                        "normalize": "upper"}]}
    r = client.put("/api/profiles/bl_interne", json=body)
    assert r.status_code == 200
    assert r.json()["fields"] == 1
    assert r.json()["overrides_builtin"] is False

    got = client.get("/api/profiles/bl_interne").json()
    assert got["source"] == "user"
    assert got["fields"][0]["key"] == "ref"


def test_user_profile_does_not_touch_builtin_dir(client):
    """Le profil écrit va dans data/profiles/, jamais dans profiles/."""
    from unocr.config import get_config

    cfg = get_config()
    body = {"label": "X", "fields": [{"key": "a", "patterns": [r"(\w+)"]}]}
    client.put("/api/profiles/securite", json=body)
    assert not (cfg.profiles_dir / "securite.json").exists()
    assert (cfg.user_profiles_dir / "securite.json").is_file()


def test_reject_bad_regex(client):
    body = {"fields": [{"key": "a", "patterns": ["(unclosed"]}]}
    r = client.put("/api/profiles/mauvais", json=body)
    assert r.status_code == 400
    assert "motif invalide" in r.json()["detail"]


def test_reject_unknown_validator(client):
    body = {"fields": [{"key": "a", "patterns": [r"(\d+)"],
                        "validators": ["validateur_fantaisiste"]}]}
    r = client.put("/api/profiles/mauvais2", json=body)
    assert r.status_code == 400
    assert "validateur inconnu" in r.json()["detail"]


def test_reject_too_many_fields(client):
    body = {"fields": [{"key": f"c{i}", "patterns": [r"(\w+)"]} for i in range(61)]}
    assert client.put("/api/profiles/trop", json=body).status_code == 400


def test_reject_path_traversal(client):
    r = client.put("/api/profiles/..%2F..%2Fetc%2Fpasswd",
                   json={"fields": []})
    assert r.status_code in (400, 404, 405)


def test_delete_user_profile(client):
    body = {"fields": [{"key": "a", "patterns": [r"(\w+)"]}]}
    client.put("/api/profiles/supprimable", json=body)
    assert client.delete("/api/profiles/supprimable").status_code == 200
    assert client.get("/api/profiles/supprimable").status_code == 404


def test_cannot_delete_builtin(client):
    assert client.delete("/api/profiles/invoice").status_code == 404


def test_user_profile_overrides_builtin(client):
    """Un profil utilisateur du même nom prime sur le profil livré."""
    body = {"label": "Facture personnalisée",
            "fields": [{"key": "mon_champ", "patterns": [r"MON[:\s]+(\w+)"]}]}
    r = client.put("/api/profiles/invoice", json=body)
    assert r.status_code == 200
    assert r.json()["overrides_builtin"] is True

    got = client.get("/api/profiles/invoice").json()
    assert got["source"] == "user"
    assert [f["key"] for f in got["fields"]] == ["mon_champ"]

    # et il est bien utilisé par le moteur
    names = [p["name"] for p in client.get("/api/profiles").json()]
    assert names.count("invoice") == 1


# ─────────────────────────── essai à blanc ───────────────────────────

def test_test_profile_against_real_document(client, fixtures_dir):
    r = _upload(client, fixtures_dir / "text_pdf.pdf", "test_prof.pdf")
    jid = r.json()["job_id"]
    assert _wait_done(client, jid)["status"] == "done"

    res = client.get(f"/api/jobs/{jid}/result").json()
    valeur = res["fields"]["invoice_number"]["raw_value"]
    assert valeur

    body = {"profile": {"name": "essai", "label": "Essai",
                        "fields": [{"key": "num", "label": "Numéro",
                                    "patterns": [r"(?:facture|invoice)\s*(?:num[ée]ro|n[°o\s]|no\.?)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/_]{2,30})"],
                                    "normalize": "upper"}]},
            "job_id": jid}
    r = client.post("/api/profiles/test", json=body)
    assert r.status_code == 200
    out = r.json()
    assert out["total"] == 1
    assert out["detected"] == 1
    assert out["fields"]["num"]["raw_value"] == valeur


def test_test_profile_with_plain_text(client):
    body = {"profile": {"name": "t", "fields": [
        {"key": "code", "patterns": [r"CODE[:\s]+([A-Z]{3}\d{3})"]}]},
        "text": "Bon de livraison\nCODE: ABC123\nfin"}
    r = client.post("/api/profiles/test", json=body)
    assert r.status_code == 200
    assert r.json()["fields"]["code"]["raw_value"] == "ABC123"


def test_test_profile_absent_field_is_not_detected(client):
    body = {"profile": {"name": "t", "fields": [
        {"key": "absent", "patterns": [r"INEXISTANT[:\s]+(\w+)"], "required": True}]},
        "text": "rien à voir ici"}
    out = client.post("/api/profiles/test", json=body).json()
    assert out["detected"] == 0
    assert out["fields"]["absent"]["raw_value"] is None


def test_test_profile_requires_input(client):
    r = client.post("/api/profiles/test", json={"profile": {"name": "t", "fields": []}})
    assert r.status_code == 400


def test_test_profile_rejects_invalid(client):
    r = client.post("/api/profiles/test", json={"profile": {"fields": "pas-un-liste"}})
    assert r.status_code == 400


def test_profile_test_accepts_saved_profile_name(client, tmp_cfg):
    """Un profil enregistré peut être testé par son nom (régression : 500)."""
    body = {"label": "Essai nom", "fields": [
        {"key": "ref", "label": "Référence",
         "patterns": ["(?:REF|Réf)\\s*[:#]\\s*([A-Z0-9-]{4,})"]}]}
    r = client.put("/api/profiles/essai_nom", json=body)
    assert r.status_code == 200, r.text

    r = client.post("/api/profiles/test", json={
        "profile": "essai_nom", "text": "Facture REF : AB-123-CD"})
    assert r.status_code == 200, r.text
    assert r.json()["detected"] == 1
    assert r.json()["total"] == 1


def test_profile_test_unknown_name_is_404(client):
    """Un nom inconnu renvoie 404, jamais 500."""
    r = client.post("/api/profiles/test",
                    json={"profile": "profil_inexistant_xyz", "text": "x"})
    assert r.status_code == 404, r.text


def test_profile_test_builtin_by_name(client):
    """Un profil livré est aussi testable par son nom."""
    r = client.post("/api/profiles/test",
                    json={"profile": "invoice", "text": "Facture n° 2024-001"})
    assert r.status_code == 200, r.text
    assert "total" in r.json()
