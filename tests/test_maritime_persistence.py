"""Persistance et préconditions des modules maritimes autrefois en mémoire."""
from __future__ import annotations


def test_conteneur_persiste_et_preconditions_terminal(client_factory):
    with client_factory() as client:
        rep = client.post("/api/conteneurs", json={"dossier_id": "dos_test", "numero_conteneur": "CONT-1"})
        assert rep.status_code == 200, rep.text
        url = "/api/conteneurs/" + rep.json()["id"]
        assert client.put(url, json={"poids": -1}).status_code == 422
        assert client.put(url, json={"statut": "inconnu"}).status_code == 422
        assert client.put(url, json={"position_actuelle": "Quai 3"}).status_code == 200
        terminal = client.post("/api/terminal", json={
            "dossier_id": "dos_test", "numero_bl": "BL-1", "numero_conteneur": "CONT-1"})
        assert terminal.status_code == 200
        assert client.delete(url).status_code == 409
        assert client.put(url, json={"dossier_id": "dos_autre"}).status_code == 409
    with client_factory() as client:
        assert client.get(url).json()["position_actuelle"] == "Quai 3"


def test_connaissement_bad_liens_et_aliases(client_factory):
    with client_factory() as client:
        assert client.post("/api/connaissements/bad", json={
            "dossier_id": "dos_test", "numero_bl": "BL-1", "numero_bad": "BAD-1"}).status_code == 422
        bl = client.post("/api/connaissements/bl", json={"dossier_id": "dos_test", "numero_bl": "BL-1"})
        assert bl.status_code == 200, bl.text
        bl_url = "/api/connaissements/bl/" + bl.json()["id"]
        bad = client.post("/api/connaissements/bad", json={
            "dossier_id": "dos_test", "numero_bl": "BL-1", "numero_bad": "BAD-1"})
        assert bad.status_code == 200, bad.text
        bad_url = "/api/connaissements/bad/" + bad.json()["id"]
        assert client.delete(bl_url).status_code == 409
        assert client.put(bl_url, json={"numero_bl": "BL-2"}).status_code == 409
        rep = client.put(bl_url, json={"frais_payes": 12.5, "bad_recu": True, "originals_count": 3, "originals_received": 2})
        assert rep.status_code == 200, rep.text
        assert rep.json()["frais_payés"] == 12.5
        assert rep.json()["bad_reçu"] is True
        assert client.put(bl_url, json={"originals_received": 4}).status_code == 422
    with client_factory() as client:
        assert client.get(bl_url).json()["frais_payés"] == 12.5
        assert client.get(bad_url).json()["numero_bad"] == "BAD-1"
        assert client.delete(bad_url).status_code == 200
        assert client.delete(bl_url).status_code == 200
    with client_factory() as client:
        assert client.get(bl_url).status_code == 404
        assert client.get(bad_url).status_code == 404


def test_livraison_workflow_persistant_et_preuves(client_factory):
    with client_factory() as client:
        rep = client.post("/api/transport/livraisons", json={"dossier_id": "dos_test", "lieu_livraison": "Entrepôt"})
        assert rep.status_code == 200, rep.text
        url = "/api/transport/livraisons/" + rep.json()["id"]
        assert client.put(url, json={"statut": "en_route"}).status_code == 409
        assert client.post(url + "/arriver", params={"date_reelle": "2026-11-14"}).status_code == 409
        assert client.post(url + "/demarrer", params={"date_depart": "2026-11-13"}).status_code == 200
    with client_factory() as client:
        assert client.get(url).json()["statut"] == "en_route"
        assert client.post(url + "/arriver", params={"date_reelle": "2026-11-14", "reserves": "Colis abîmé"}).status_code == 200
    with client_factory() as client:
        assert client.get(url).json()["statut"] == "reponse"
        assert client.post(url + "/confirmer", params={"preuve_signee": False, "date_signature": "2026-11-14"}).status_code == 400
        assert client.post(url + "/confirmer", params={"preuve_signee": True, "date_signature": "2026-11-14"}).status_code == 200
    with client_factory() as client:
        avant = client.get(url).json()
        assert avant["statut"] == "confirme"
        assert client.put(url, json={"lieu_livraison": "Autre"}).status_code == 409
        assert client.put(url, json={"observations": "Note après confirmation"}).status_code == 200
        assert client.get(url).json()["statut"] == "confirme"


def test_transporteur_camion_liens_et_suppression_refusee(client_factory):
    with client_factory() as client:
        assert client.post("/api/transport/camions", json={
            "transporteur_id": "transp_absent", "immatriculation": "AA-123"}).status_code == 422
        transporteur = client.post("/api/transport/transporteurs", json={"nom": "Transports Test"})
        assert transporteur.status_code == 200
        transp_url = "/api/transport/transporteurs/" + transporteur.json()["id"]
        camion = client.post("/api/transport/camions", json={
            "transporteur_id": transporteur.json()["id"], "immatriculation": "AA-123"})
        assert camion.status_code == 200
        camion_url = "/api/transport/camions/" + camion.json()["id"]
        assert client.delete(transp_url).status_code == 409
        livraison = client.post("/api/transport/livraisons", json={
            "dossier_id": "dos_test", "transporteur_id": transporteur.json()["id"],
            "camion_id": camion.json()["id"]})
        assert livraison.status_code == 200, livraison.text
        assert client.delete(camion_url).status_code == 409
        assert client.put(camion_url, json={"transporteur_id": "transp_absent"}).status_code == 422
    with client_factory() as client:
        assert client.get(camion_url).json()["immatriculation"] == "AA-123"
        assert client.get(transp_url).json()["nom"] == "Transports Test"


def test_suppression_dossier_refusee_si_liens_maritimes_ou_banque(client_factory, tmp_path):
    import pytest
    from fastapi import HTTPException

    from unocr.business_links import exiger_dossier_sans_liens
    from unocr.business_store import BusinessStore
    from unocr.finance import OperationBancaire
    from unocr.models import BonADelivrer, Connaissement, Conteneur, DeclarationDouaniere, Livraison

    liens = [
        ("conteneur", Conteneur, {"numero_conteneur": "CONT-X"}),
        ("connaissement", Connaissement, {"numero_bl": "BL-X"}),
        ("bon_a_delivrer", BonADelivrer, {"numero_bl": "BL-X", "numero_bad": "BAD-X"}),
        ("livraison", Livraison, {}),
        ("operation_bancaire", OperationBancaire, {"date": "2026-11-11", "montant": 10}),
    ]
    for collection, modele, champs in liens:
        magasin = BusinessStore(tmp_path / f"{collection}.sqlite3", "declaration", DeclarationDouaniere)
        with magasin.transaction() as transaction:
            objet = modele(id="objet_test", dossier_id="dos_test", **champs)
            transaction.related(collection, modele)[objet.id] = objet
            with pytest.raises(HTTPException) as refus:
                exiger_dossier_sans_liens(transaction, "dos_test")
            assert refus.value.status_code == 409
            assert "référence encore" in refus.value.detail
            assert transaction.related(collection, modele).get("objet_test") is not None
