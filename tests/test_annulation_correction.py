"""Annulation d'une correction humaine : restaurer sans effacer la trace.

Une annulation qui écraserait la correction ferait disparaître l'historique —
c'est exactement ce que la traçabilité interdit. Ces tests vérifient qu'annuler
restaure l'état d'avant, que l'annulation est elle-même tracée, et qu'on ne
peut pas annuler ce qui n'a jamais été corrigé.
"""
import json

import pytest
from fastapi.testclient import TestClient

from unocr import api


@pytest.fixture()
def client(tmp_cfg):
    (tmp_cfg.log_dir / "audit.log").write_text("", encoding="utf-8")
    with TestClient(api.app) as c:
        yield c


def _job(client, job_id="job1", champs=None):
    api.store.job_dir(job_id).mkdir(parents=True, exist_ok=True)
    api.store.save_result(job_id, {
        "job_id": job_id,
        "status": "done",
        "fields": champs or {"invoice_number": {"value": "FA-1", "raw_value": "FA-1",
                                                "normalized_value": "FA-1",
                                                "value_origin": "raw",
                                                "status": "detected"}},
    })


def test_annulation_restaure_letat_davant(client):
    _job(client)
    r = client.patch("/api/jobs/job1/fields/invoice_number",
                     json={"corrected_value": "FA-CORRIGEE"})
    assert r.status_code == 200
    r = client.post("/api/jobs/job1/fields/invoice_number/undo", json={})
    assert r.status_code == 200
    f = r.json()["field"]
    # la correction doit disparaître de l'état courant…
    assert f["corrected_value"] is None and f["confirmed_value"] is None
    # …et l'état d'avant être restitué, y compris l'origine « raw »
    assert f["value_origin"] == "raw" and f["status"] == "detected"
    assert r.json()["restaure"]["valeur"] == "FA-1"


def test_annulation_est_tracee_et_garde_la_correction(client):
    _job(client)
    client.patch("/api/jobs/job1/fields/invoice_number",
                 json={"corrected_value": "FA-CORRIGEE", "user": "marie",
                       "reason": "lu sur le document papier"})
    client.post("/api/jobs/job1/fields/invoice_number/undo",
                json={"user": "marie", "motif": "erreur de ma part"})
    lignes = (api.cfg.log_dir / "audit.log").read_text(encoding="utf-8").splitlines()
    annulees = [json.loads(ligne) for ligne in lignes if "field_correction_annulee" in ligne]
    assert len(annulees) == 1
    e = annulees[0]
    assert e["acteur"] == "marie" and e["motif"] == "erreur de ma part"
    # la valeur supprimée reste connue : l'audit ne perd rien
    assert e["valeur_annulee"] == "FA-CORRIGEE" and e["valeur_restauree"] == "FA-1"
    # la correction d'origine est toujours là, pas écrasée par l'annulation
    validees = [json.loads(ligne) for ligne in lignes if "field_validated" in ligne]
    assert validees and validees[0]["corrected"] == "FA-CORRIGEE"


def test_annuler_une_valeur_normalisee_restaure_la_normalisation(client):
    """Annuler ne doit pas faire perdre le travail du moteur.

    Si le champ était normalisé, la valeur affichée avant correction était la
    version normalisée : la restaurer la remet, plutôt que la valeur brute.
    """
    _job(client, champs={"amount": {"value": "1200.00", "raw_value": "1 200,00",
                                    "normalized_value": "1200.00",
                                    "value_origin": "normalized",
                                    "status": "detected"}})
    client.patch("/api/jobs/job1/fields/amount", json={"corrected_value": "1500"})
    r = client.post("/api/jobs/job1/fields/amount/undo", json={})
    f = r.json()["field"]
    assert f["value_origin"] == "normalized" and f["status"] == "detected"
    assert r.json()["restaure"]["valeur"] == "1200.00"


def test_annuler_sans_correction_est_refuse(client):
    _job(client)
    r = client.post("/api/jobs/job1/fields/invoice_number/undo", json={})
    assert r.status_code == 409
    assert "aucune correction" in r.json()["detail"]


def test_annuler_deux_fois_ne_restaure_quune_fois(client):
    """La deuxième annulation n'a plus rien à annuler."""
    _job(client)
    client.patch("/api/jobs/job1/fields/invoice_number", json={"corrected_value": "A"})
    client.patch("/api/jobs/job1/fields/invoice_number", json={"confirmed_value": "B"})
    client.post("/api/jobs/job1/fields/invoice_number/undo", json={})
    r = client.post("/api/jobs/job1/fields/invoice_number/undo", json={})
    assert r.status_code == 409


def test_etat_precedent_trace_dans_field_validated(client):
    """L'audit doit dire ce qui a été remplacé, pas seulement ce qui l'a été."""
    _job(client)
    client.patch("/api/jobs/job1/fields/invoice_number",
                 json={"confirmed_value": "FA-VALIDEE"})
    e = [json.loads(ligne) for ligne in
         (api.cfg.log_dir / "audit.log").read_text(encoding="utf-8").splitlines()
         if "field_validated" in ligne][0]
    assert e["ancienne_valeur"] == "FA-1"
    assert e["ancienne_origine"] == "raw" and e["ancien_statut"] == "detected"


def test_annulation_peut_reprendre_apres_coup(client):
    """L'état redevient cohérent : un champ annulé peut être re-corrigé."""
    _job(client)
    client.patch("/api/jobs/job1/fields/invoice_number", json={"corrected_value": "A"})
    client.post("/api/jobs/job1/fields/invoice_number/undo", json={})
    r = client.patch("/api/jobs/job1/fields/invoice_number", json={"corrected_value": "B"})
    assert r.status_code == 200
    f = client.get("/api/jobs/job1/result").json()["fields"]["invoice_number"]
    assert f["corrected_value"] == "B" and f["value_origin"] == "corrected"
