"""Contrats financiers complémentaires, données et API temporaires."""
from unocr.business_store import BusinessStore
from unocr.models import Facture, Frais


def test_documents_joints_conserves(client_factory):
    with client_factory() as client:
        creation = client.post("/api/frais/facture", json={
            "dossier_id": "dos_test", "documents_joints": ["piece_test"], "montant_ttc": 42})
        assert creation.status_code == 200, creation.text
        url = "/api/frais/facture/" + creation.json()["id"]
    with client_factory() as client:
        assert client.get(url).json()["documents_joints"] == ["piece_test"]
    ancien = Facture.model_validate({"documents_joint": ["ancienne_piece"]})
    assert ancien.documents_joints == ["ancienne_piece"]


def test_rapprochement_sans_import_ne_plante_pas(client_factory):
    with client_factory() as client:
        creation = client.post("/api/frais/facture", json={"dossier_id": "dos_test", "montant_ttc": 42})
        assert creation.status_code == 200
        rep = client.post("/api/frais/rapprochement/auto", json={
            "dossier_id": "dos_test", "date_debut": "2026-11-01", "date_fin": "2026-11-30"})
        assert rep.status_code == 200, rep.text
        assert rep.json()["total_factures"] == 1
        assert rep.json()["rapprochees"] == []
        assert rep.json()["non_rapprochees"][0]["raison"] == "aucune_correspondance"
        assert client.get("/api/frais/facture/" + creation.json()["id"]).json()["rapprochee"] is False


def test_montant_null_refuse_sans_perte(client_factory):
    with client_factory() as client:
        creation = client.post("/api/frais", json={"dossier_id": "dos_test", "montant": 42})
        avant = creation.json()
        url = "/api/frais/" + avant["id"]
        assert client.put(url, json={"montant": None}).status_code == 422
    with client_factory() as client:
        assert client.get(url).json() == avant


def test_frais_avec_justificatifs_non_supprime(client_factory, tmp_path):
    magasin = BusinessStore(tmp_path / "metier.sqlite3", "frais", Frais)
    magasin["frais_test"] = Frais(id="frais_test", dossier_id="dos_test", justificatifs=["just_test"])
    with client_factory() as client:
        assert client.delete("/api/frais/frais_test").status_code == 409
        assert client.get("/api/frais/frais_test").json()["justificatifs"] == ["just_test"]
