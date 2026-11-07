"""Scénario de référence — le parcours complet, de bout en bout.

**Ce que ce test prouve.** Une facture, un connaissement et une liste de
colisage sont importés, classés, extraits, rapprochés ; les incohérences sont
détectées ; une valeur est corrigée et validée par un humain ; un dossier
structuré est constitué ; un paquet Excel est généré. Puis on simule une panne
OCR et on vérifie que la reprise ne perd ni l'original ni la correction
humaine.

Aucune étape n'est simulée : les documents passent par le pipeline réel.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from parcours_fixtures import creer_fixtures

pytestmark = pytest.mark.usefixtures("tmp_cfg")


@pytest.fixture()
def client(tmp_cfg, fixtures_dir, tmp_path):
    """Client d'API avec magasins isolés (même méthode que test_connector_api)."""
    from fastapi.testclient import TestClient

    from unocr import api
    from unocr.dossier import DossierStore

    api._watch.stop()
    api._watch.reset()
    api._dossiers = DossierStore(tmp_path / "dossiers", log_dir=tmp_path / "logs")
    with TestClient(api.app) as c:
        yield c
    api._watch.stop()
    api._watch.reset()


def _attend_termine(client, job_id: str, timeout: int = 300):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/api/jobs/{job_id}")
        if r.status_code == 200:
            etat = r.json().get("status")
            if etat in ("done", "failed"):
                return r.json()
        time.sleep(0.5)
    raise AssertionError(f"le job {job_id} n'a pas fini en {timeout} s")


def _importer(client, chemin: Path, nom: str) -> str:
    with chemin.open("rb") as f:
        r = client.post("/api/documents", files={"file": (nom, f, "application/pdf")})
    assert r.status_code in (200, 201), f"import refusé : {r.text}"
    return r.json()["job_id"]


# ─────────────────────────── le parcours complet ───────────────────────────

def test_parcours_complet_reference(client, fixtures_dir, tmp_path) -> None:
    docs = creer_fixtures(tmp_path / "documents-parcours")

    # 01 · réception — trois documents, chacun avec son identifiant
    ids = {}
    for role, chemin in docs.items():
        ids[role] = _importer(client, chemin, f"{role}.pdf")
        assert ids[role].startswith("job_")
    assert len(set(ids.values())) == 3, "chaque document doit avoir son identifiant"

    # 02-07 · traitement réel par le pipeline existant
    for role, job_id in ids.items():
        job = _attend_termine(client, job_id)
        assert job["status"] == "done", f"{role} n'a pas été traité : {job.get('error')}"

    # 04 · classification
    classifications = {}
    for role, job_id in ids.items():
        r = client.post(f"/api/jobs/{job_id}/classify")
        assert r.status_code == 200, r.text
        classifications[role] = r.json()["classification"]
    assert classifications["facture"]["category"] == "invoice"
    assert classifications["bl"]["category"] == "bill_of_lading"
    assert classifications["colisage"]["category"] == "packing_list"
    for role, c in classifications.items():
        assert c["confidence"] > 0, f"{role} : confiance nulle"
        assert c["evidence"] or c["manual"], f"{role} : aucune preuve"

    # 11 · constitution du dossier
    r = client.post("/api/dossiers", json={"label": "Import 2024-118",
                                           "profile": "importation"})
    assert r.status_code == 200, r.text
    dossier_id = r.json()["id"]

    for role, job_id in ids.items():
        r = client.post(f"/api/dossiers/{dossier_id}/pieces", json={
            "job_id": job_id, "filename": f"{role}.pdf",
            "category": classifications[role]["category"]})
        assert r.status_code == 200, r.text

    synthese = client.get(f"/api/dossiers/{dossier_id}").json()
    assert len(synthese["pieces"]) == 3
    assert synthese["state"] in ("en_validation", "valide", "revision_requise")

    # 08 · cohérence interdocumentaire — les incohérences réelles doivent sortir
    r = client.get(f"/api/dossiers/{dossier_id}/coherence")
    assert r.status_code == 200, r.text
    constats = r.json()["constats"]
    regles = {c["rule"] for c in constats}
    # le BL annonce 12 000 kg, la liste de colisage 13 500 kg
    assert any("poids_divergent" in regle for regle in regles), (
        f"divergence de poids non détectée : {regles}"
    )
    # TGHU7654321 est dans le BL mais pas dans la liste de colisage
    assert any("conteneur_absent" in regle for regle in regles), (
        f"conteneur manquant non détecté : {regles}"
    )
    # aucun constat ne doit être bloquant par défaut
    assert all(c["severity"] != "blocage" for c in constats), (
        "une règle non configurée ne doit pas bloquer"
    )

    # 10 · correction et validation humaines
    job_id = ids["facture"]
    r = client.patch(f"/api/jobs/{job_id}/fields/invoice_number",
                     json={"confirmed_value": "INV-2024-118"})
    assert r.status_code == 200, f"correction refusée : {r.text}"

    # 13 · génération du paquet de données
    r = client.post(f"/api/dossiers/{dossier_id}/package", json={"format": "xlsx"})
    assert r.status_code == 200, r.text
    paquet = r.json()
    assert paquet["documents"] == 3
    chemin = Path(paquet["chemin"])
    assert chemin.is_file() and chemin.stat().st_size > 1000

    # le paquet sépare vraiment les champs validés des autres
    from openpyxl import load_workbook
    wb = load_workbook(chemin)
    assert "Champs validés" in wb.sheetnames
    assert "Champs en attente" in wb.sheetnames
    assert "Anomalies" in wb.sheetnames
    valides = wb["Champs validés"]
    cles = {str(row[2].value) for row in valides.iter_rows(min_row=2) if row[2].value}
    assert "invoice_number" in cles, "la valeur corrigée doit être dans les validés"

    # 14 · l'export ZIP contient un manifeste
    r = client.post(f"/api/dossiers/{dossier_id}/package", json={"format": "zip"})
    assert r.status_code == 200, r.text
    import zipfile
    with zipfile.ZipFile(Path(r.json()["chemin"])) as zf:
        assert "manifeste.json" in zf.namelist()
        assert "facture.pdf" not in zf.namelist(), (
            "les originaux ne doivent pas être embarqués sans demande"
        )
        manifeste = json.loads(zf.read("manifeste.json").decode("utf-8"))
    assert manifeste["schema_version"]
    assert len(manifeste["documents_inclus"]) == 3

    # 15 · traçabilité
    r = client.get("/api/audit", params={"event": "document_classified"})
    assert r.status_code == 200
    assert r.json()["events"], "aucune classification tracée"
    r = client.get("/api/audit", params={"event": "data_package_generated"})
    assert r.json()["events"], "aucune génération de paquet tracée"


# ─────────────────── reprise après panne, sans rien perdre ───────────────────

def test_reprise_apres_panne_conserve_originaux_et_corrections(client, tmp_path) -> None:
    """Une panne puis une reprise ne doivent rien effacer.

    On casse volontairement le pipeline (moteur OCR absent), on fait échouer un
    document, puis on le relance après remise en état. L'original et la
    correction humaine déjà portée doivent survivre.
    """
    from unocr import api

    docs = creer_fixtures(tmp_path / "documents-parcours")
    job_id = _importer(client, docs["facture"], "facture.pdf")
    _attend_termine(client, job_id)

    # correction humaine
    r = client.patch(f"/api/jobs/{job_id}/fields/invoice_number",
                     json={"confirmed_value": "INV-2024-118"})
    assert r.status_code == 200
    original = api.store.original_dir(job_id)
    assert original.is_dir() and any(original.iterdir()), "l'original doit être conservé"

    # panne : on fait échouer le job puis on le remet en file
    from unocr.models import JobStatus
    job = api.store.get(job_id)
    job.status = JobStatus.ERROR
    job.error = "panne simulée du moteur OCR"
    api.store.update(job)

    r = client.post(f"/api/jobs/{job_id}/retry")
    assert r.status_code == 200, r.text
    job = _attend_termine(client, job_id)
    assert job["status"] == "done", f"reprise échouée : {job.get('error')}"

    # l'original est toujours là, et la correction humaine aussi
    assert any(original.iterdir()), "l'original a disparu après la reprise"
    champs = client.get(f"/api/jobs/{job_id}/fields").json()["fields"]
    correction = champs.get("invoice_number")
    assert correction, "le champ corrigé a disparu après la reprise"
    assert correction.get("confirmed_value") == "INV-2024-118", (
        "la correction humaine a été perdue par la reprise"
    )


def test_job_bloque_est_detectable(client, tmp_cfg) -> None:
    """Un traitement tué net doit apparaître dans la file des bloqués."""
    from unocr import api
    from unocr.models import JobStatus

    store = api.store
    bloque = store.create_job("bloque.pdf", b"%PDF-1.4 faux\n")
    bloque.status = JobStatus.PROCESSING
    store.update(bloque)
    import json as _json
    chemin = store._job_path(bloque.id)
    data = _json.loads(chemin.read_text(encoding="utf-8"))
    data["updated_at"] = time.time() - 3600
    chemin.write_text(_json.dumps(data), encoding="utf-8")

    r = client.get("/api/jobs/stale")
    assert r.status_code == 200
    assert any(j["id"] == bloque.id for j in r.json()["jobs"]), (
        "un job figé depuis 1 h doit être proposé à la reprise"
    )
