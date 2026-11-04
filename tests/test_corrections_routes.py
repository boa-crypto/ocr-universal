"""Non-régression des corrections issues du nettoyage (ruff / routes cassées).

Chaque test couvre un bug réel corrigé : routes clients sans `Request`,
module transit branché sur un store inexistant, store de justificatifs lu
avant d'être créé, calcul des droits sur un code SH non normalisé.
"""
import pytest
from fastapi.testclient import TestClient

from unocr.api import app


@pytest.fixture()
def client(tmp_cfg):
    return TestClient(app, raise_server_exceptions=False)


def test_clients_crud(client):
    creation = client.post("/api/clients", json={"name": "ACME", "legal_name": "ACME SARL"})
    assert creation.status_code == 200, creation.text
    client_id = creation.json()["id"]
    assert creation.json()["status"] == "active"

    liste = client.get("/api/clients")
    assert liste.status_code == 200
    assert [c["id"] for c in liste.json()] == [client_id]

    detail = client.get(f"/api/clients/{client_id}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "ACME"

    modification = client.put(f"/api/clients/{client_id}", json={"status": "inactive", "city": "Oran"})
    assert modification.status_code == 200, modification.text
    assert modification.json()["status"] == "inactive"
    assert modification.json()["city"] == "Oran"

    recherche = client.get("/api/clients", params={"search": "acme", "status": "inactive"})
    assert [c["id"] for c in recherche.json()] == [client_id]

    suppression = client.delete(f"/api/clients/{client_id}")
    assert suppression.status_code == 200
    assert client.get(f"/api/clients/{client_id}").status_code == 404


def test_client_pays_invalide_renvoie_422_pas_500(client):
    """Un code pays trop long doit être refusé proprement (422).

    Le modèle `Client` limite `country` à deux caractères (ISO 3166-1). Le
    corps de requête, lui, ne le vérifiait pas : la construction du modèle
    levait une ValidationError et l'API répondait 500 sans explication.
    """
    trop_long = client.post(
        "/api/clients", json={"name": "ACME", "legal_name": "ACME SARL",
                              "country": "Algérie"},
    )
    assert trop_long.status_code == 422, trop_long.text
    assert "country" in trop_long.text

    valide = client.post(
        "/api/clients", json={"name": "ACME", "legal_name": "ACME SARL", "country": "DZ"},
    )
    assert valide.status_code == 200, valide.text
    assert valide.json()["country"] == "DZ"


def test_client_dossiers_filtre_par_client(client):
    client_id = client.post(
        "/api/clients", json={"name": "Client maritime", "legal_name": "CM SARL"}
    ).json()["id"]

    dossier = client.post("/api/dossiers", json={
        "label": "Import ACME", "profile": "importation", "client_importateur": "Client maritime",
    })
    assert dossier.status_code in (200, 201), dossier.text
    dossier_id = dossier.json()["id"]

    rattaches = client.get(f"/api/clients/{client_id}/dossiers")
    assert rattaches.status_code == 200
    assert [d["id"] for d in rattaches.json()] == [dossier_id]

    assert client.get("/api/clients/client_inconnu/dossiers").status_code == 404

    autre = client.post(
        "/api/clients", json={"name": "Autre", "legal_name": "Autre SARL"}
    ).json()["id"]
    assert client.get(f"/api/clients/{autre}/dossiers").json() == []


def test_transit_lit_les_dossiers_reels(client):
    dossier = client.post("/api/dossiers", json={"label": "Transit test", "profile": "transport"})
    assert dossier.status_code in (200, 201)
    dossier_id = dossier.json()["id"]

    liste = client.get("/transit/dossiers")
    assert liste.status_code == 200, liste.text
    assert dossier_id in [d["id"] for d in liste.json()]

    detail = client.get(f"/transit/dossiers/{dossier_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["label"] == "Transit test"

    assert client.get("/transit/dossiers/dos_inconnu").status_code == 404
    assert client.get("/transit/security").status_code == 200


def test_transit_met_a_jour_les_champs_connus(client):
    dossier_id = client.post(
        "/api/dossiers", json={"label": "ETA test", "profile": "importation"}
    ).json()["id"]

    reponse = client.post(f"/transit/dossiers/{dossier_id}/eta", json={"eta": "2026-12-01"})
    assert reponse.status_code == 200, reponse.text
    assert client.get(f"/transit/dossiers/{dossier_id}").json()["eta"] == "2026-12-01"


def test_justificatif_absent_renvoie_404(client):
    reponse = client.get("/api/frais/justificatif/inexistant/download")
    assert reponse.status_code == 404
    assert client.delete("/api/frais/justificatif/inexistant").status_code == 404


def test_droits_complets_normalise_le_code_sh():
    from unocr.reglementation import obtenir_droits_complets

    resultat = obtenir_droits_complets("0901.21", 1000)
    assert resultat["code_sh"] == "090121"
    assert resultat["validation_sh"]["valide"] is True
    assert resultat["total_douane"] > 0

    inconnu = obtenir_droits_complets("99999999", 100)
    assert inconnu["validation_sh"]["valide"] is False
