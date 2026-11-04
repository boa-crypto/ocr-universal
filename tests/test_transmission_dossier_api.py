"""Étape 14 — transmission d'un dossier, vue par l'API.

**Pourquoi ce fichier.** Le module `unocr.transmission_dossier` est testé en
direct (`tests/test_transmission_dossier.py`). Reste à prouver que les
**routes** le servent sans le dénaturer : qu'un aperçu n'envoie rien, qu'un
envoi réel aboutisse, qu'un envoi sans confirmation soit refusé, et que
**chaque** réponse porte le rappel « envoyé n'est pas accepté ».
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("tmp_cfg")

FORM_CIBLE = "demo_declaration"
REGLES = [
    {"source_field": "containerNo", "target_field": "containerNo",
     "transform": "none"},
    {"source_field": "bl_reference", "target_field": "bl_reference",
     "transform": "none"},
    {"source_field": "grossWeight", "target_field": "grossWeight",
     "transform": "none"},
]


@pytest.fixture()
def client(tmp_cfg, tmp_path):
    """Client d'API avec magasins de dossiers et de connecteurs isolés."""
    from unocr import api
    from unocr.connectors.forms import FormStore
    from unocr.connectors.hub import ConnectorHub
    from unocr.connectors.simulated import SIMULATED
    from unocr.connectors.transmission import TransmissionEngine
    from unocr.dossier import DossierStore
    from unocr.formulaire import FormulaireStore

    SIMULATED.healthy = True
    api._watch.stop()
    api._watch.reset()
    api._dossiers = DossierStore(tmp_path / "dossiers", log_dir=tmp_path / "logs")
    api.connector_hub = ConnectorHub(tmp_path / "connectors", tmp_path / "logs")
    api.transmissions = TransmissionEngine(tmp_path / "connectors",
                                           tmp_path / "logs")
    api.form_store = FormStore(tmp_path / "connectors" / "forms")
    api._formulaires = FormulaireStore(tmp_path / "formulaires",
                                       log_dir=tmp_path / "logs")
    with TestClient(api.app) as c:
        yield c
    api._watch.stop()
    api._watch.reset()
    SIMULATED.healthy = True


def _job_factice(job_id: str, filename: str = "facture.pdf") -> None:
    """Crée un enregistrement de document **avec ses champs extraits**.

    L'ajout d'une pièce à un dossier exige que le document existe. On n'a pas
    besoin du pipeline OCR ici — un enregistrement suffit, et évite de
    dépendre d'un moteur absent. Les champs sont posés pour que le form
    builder ait de quoi construire un formulaire : sans eux, le dossier
    n'aurait rien à transmettre, ce qui est un autre test.
    """
    from unocr import api
    from unocr.models import Job, JobStatus

    api.store.job_dir(job_id).mkdir(parents=True, exist_ok=True)
    api.store.update(Job(id=job_id, filename=filename, status=JobStatus.DONE))
    api.store.save_result(job_id, {"fields": {
        "containerNo": {"raw_value": "TGHU1234567", "status": "validated",
                        "label": "N° de conteneur"},
        "bl_reference": {"raw_value": "BL-2024-0456", "status": "validated",
                         "label": "Référence BL"},
        "grossWeight": {"raw_value": "12000", "status": "validated",
                        "label": "Poids brut"},
    }})


def _dossier_complet(client, label="Import 2024-118") -> str:
    r = client.post("/api/dossiers", json={"label": label,
                                          "profile": "importation"})
    assert r.status_code == 200, r.text
    did = r.json()["id"]
    for job_id, nom, cat in (("job_f", "facture.pdf", "invoice"),
                             ("job_b", "bl.pdf", "bill_of_lading")):
        _job_factice(job_id, nom)
        r = client.post(f"/api/dossiers/{did}/pieces", json={
            "job_id": job_id, "filename": nom, "category": cat})
        assert r.status_code == 200, r.text
    return did


def _formulaire(client, did):
    r = client.post(f"/api/dossiers/{did}/formulaire")
    assert r.status_code == 200, r.text
    return r.json()


# ─────────────────────────── l'aperçu n'envoie rien ───────────────────────────

def test_apercu_ne_transmet_rien(client):
    """Un GET d'aperçu ne doit créer aucune transmission."""
    did = _dossier_complet(client)
    _formulaire(client, did)
    r = client.get(f"/api/dossiers/{did}/transmission")
    assert r.status_code == 200, r.text
    corps = r.json()
    assert corps["transmissible"] is False, (
        "sans règles de correspondance, rien ne doit partir")
    assert any(i["kind"] == "unknown_field" for i in corps["issues"]), (
        "l'aperçu doit signaler les champs sans correspondance")
    # et surtout : aucune transmission créée
    assert client.get(f"/api/dossiers/{did}/transmissions").json()[
        "transmissions"] == []


def test_apercu_d_un_dossier_inconnu_renvoie_404(client):
    assert client.get("/api/dossiers/absent/transmission").status_code == 404


def test_apercu_porte_le_rappel_permanent(client):
    did = _dossier_complet(client)
    _formulaire(client, did)
    corps = client.get(f"/api/dossiers/{did}/transmission").json()
    assert corps["ne_garantit_pas"]
    assert any("accepté" in g for g in corps["ne_garantit_pas"])


def test_apercu_indique_que_les_fichiers_ne_partent_pas(client):
    did = _dossier_complet(client)
    _formulaire(client, did)
    corps = client.get(f"/api/dossiers/{did}/transmission").json()
    assert corps["contenu"]["fichiers_joints"] is False


# ─────────────────────────── transmission réelle ───────────────────────────

def _connecteur_operationnel(client):
    client.post("/api/connectors/demo_simulated", json={"settings": {}})
    r = client.post("/api/connectors/demo_simulated/test")
    assert r.status_code == 200, r.text


def test_transmission_reelle_aboutit(client):
    did = _dossier_complet(client)
    _formulaire(client, did)
    _connecteur_operationnel(client)
    r = client.post(f"/api/dossiers/{did}/transmission", json={
        "form_id": FORM_CIBLE, "rules": REGLES,
        "risk": "low", "confirmed": True, "confirmed_by": "test"})
    assert r.status_code == 200, r.text
    corps = r.json()
    assert corps["transmission"]["dossier_id"] == did
    assert corps["transmission"]["status"] in ("sent", "accepted")
    assert corps["renvoye_evite"] is False
    # le dossier est bien complet : aucune pièce requise manquante
    assert not any(i["kind"] == "missing_required"
                   for i in corps["apercu"]["issues"])


def test_sans_confirmation_l_envoi_est_refuse(client):
    """Le verrou est côté serveur, pas dans l'interface."""
    did = _dossier_complet(client)
    _formulaire(client, did)
    _connecteur_operationnel(client)
    r = client.post(f"/api/dossiers/{did}/transmission", json={
        "form_id": FORM_CIBLE, "rules": REGLES, "risk": "high"})
    assert r.status_code == 409
    assert "confirmation" in r.json()["detail"]


def test_sans_connecteur_operationnel_l_envoi_est_refuse(client):
    did = _dossier_complet(client)
    _formulaire(client, did)
    r = client.post(f"/api/dossiers/{did}/transmission", json={
        "form_id": FORM_CIBLE, "rules": REGLES, "risk": "low",
        "confirmed": True})
    assert r.status_code == 409
    assert "opérationnel" in r.json()["detail"]


def test_second_envoi_du_meme_contenu_n_est_pas_renvoye(client):
    did = _dossier_complet(client)
    _formulaire(client, did)
    _connecteur_operationnel(client)
    corps = {"form_id": FORM_CIBLE, "rules": REGLES, "risk": "low",
             "confirmed": True, "confirmed_by": "test"}
    r1 = client.post(f"/api/dossiers/{did}/transmission", json=corps)
    assert r1.status_code == 200, r1.text
    assert r1.json()["renvoye_evite"] is False
    r2 = client.post(f"/api/dossiers/{did}/transmission", json=corps)
    assert r2.status_code == 200, r2.text
    assert r2.json()["renvoye_evite"] is True
    assert (r1.json()["transmission"]["transmission_id"]
            == r2.json()["transmission"]["transmission_id"])


def test_transmission_est_tracee_dans_le_dossier(client):
    did = _dossier_complet(client)
    _formulaire(client, did)
    _connecteur_operationnel(client)
    client.post(f"/api/dossiers/{did}/transmission", json={
        "form_id": FORM_CIBLE, "rules": REGLES, "risk": "low",
        "confirmed": True})
    trace = client.get(f"/api/dossiers/{did}/trace").json()
    evenements = [e["event"] for e in trace["entrees"]]
    assert "dossier_transmitted" in evenements


def test_historique_des_transmissions_du_dossier(client):
    did = _dossier_complet(client)
    _formulaire(client, did)
    _connecteur_operationnel(client)
    r = client.get(f"/api/dossiers/{did}/transmissions")
    assert r.status_code == 200
    corps = r.json()
    assert corps["transmissions"] == []
    assert corps["ne_garantit_pas"]

    client.post(f"/api/dossiers/{did}/transmission", json={
        "form_id": FORM_CIBLE, "rules": REGLES, "risk": "low",
        "confirmed": True})
    corps = client.get(f"/api/dossiers/{did}/transmissions").json()
    assert len(corps["transmissions"]) == 1
    assert corps["transmissions"][0]["dossier_id"] == did


def test_transmission_d_un_dossier_inconnu_renvoie_404(client):
    r = client.post("/api/dossiers/absent/transmission",
                    json={"form_id": FORM_CIBLE, "rules": REGLES})
    assert r.status_code == 404


def test_sans_regles_l_envoi_est_refuse(client):
    """Sans correspondance, les champs du dossier seraient perdus en silence."""
    did = _dossier_complet(client)
    _formulaire(client, did)
    _connecteur_operationnel(client)
    r = client.post(f"/api/dossiers/{did}/transmission", json={
        "form_id": FORM_CIBLE, "rules": [], "risk": "low", "confirmed": True})
    assert r.status_code == 409
    assert "correspondance" in r.json()["detail"]
