"""Liens liquidation/déclaration : contrôlés dans la même transaction SQLite."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from unocr.business_store import BusinessStore
from unocr.models import DeclarationDouaniere, Liquidation


def parent(client, dossier="dos_test"):
    rep = client.post("/api/declarations", json={"dossier_id": dossier})
    assert rep.status_code == 200
    return rep.json()["id"]


def enfant(client, declaration_id, dossier="dos_test"):
    return client.post("/api/declarations/liquidation", json={
        "dossier_id": dossier, "declaration_id": declaration_id, "tva": 12.5})


@pytest.mark.parametrize("identifiant", ["decl_absente", "", "  "])
def test_parent_inexistant_refuse(client_factory, identifiant):
    with client_factory() as client:
        assert enfant(client, identifiant).status_code == 422
    with client_factory() as client:
        assert client.get("/api/declarations/liquidation").json() == []


def test_mauvais_dossier_refuse(client_factory):
    with client_factory() as client:
        identifiant = parent(client)
        assert enfant(client, identifiant, "dos_autre").status_code == 409
        assert client.get("/api/declarations/liquidation").json() == []


@pytest.mark.parametrize("modification,code", [
    ({"declaration_id": "inconnue"}, 422), ({"dossier_id": "dos_autre"}, 409),
    ({"declaration_id": None}, 422), ({"tva": None}, 422),
])
def test_modification_invalide_ne_persiste_rien(client_factory, modification, code):
    with client_factory() as client:
        identifiant = parent(client)
        rep = enfant(client, identifiant)
        assert rep.status_code == 200
        avant = rep.json()
        url = "/api/declarations/liquidation/" + avant["id"]
        assert client.put(url, json=modification).status_code == code
    with client_factory() as client:
        assert client.get(url).json() == avant


def test_parent_utilise_protege_puis_suppression_liberee(client_factory):
    with client_factory() as client:
        identifiant = parent(client)
        liquidation = enfant(client, identifiant).json()
        url = "/api/declarations/" + identifiant
        assert client.delete(url).status_code == 409
        assert client.put(url, json={"dossier_id": "dos_autre"}).status_code == 409
        assert client.put(url, json={"numero_declaration": "NOUVEAU"}).status_code == 200
    with client_factory() as client:
        assert client.get(url).json()["dossier_id"] == "dos_test"
        assert client.delete("/api/declarations/liquidation/" + liquidation["id"]).status_code == 200
        assert client.delete(url).status_code == 200


def test_reaffectation_coherente_permise(client_factory):
    with client_factory() as client:
        premier = parent(client)
        second = parent(client, "dos_autre")
        liquidation = enfant(client, premier).json()
        rep = client.put("/api/declarations/liquidation/" + liquidation["id"], json={
            "dossier_id": "dos_autre", "declaration_id": second})
        assert rep.status_code == 200, rep.text
        assert client.delete("/api/declarations/" + premier).status_code == 200
        assert client.delete("/api/declarations/" + second).status_code == 409


def test_transaction_rollback_deux_collections(tmp_path):
    store = BusinessStore(tmp_path / "metier.sqlite3", "declaration", DeclarationDouaniere)
    with pytest.raises(RuntimeError, match="annuler"):
        with store.transaction() as transaction:
            transaction["decl_test"] = DeclarationDouaniere(id="decl_test")
            enfants = transaction.related("liquidation", Liquidation)
            enfants["liq_test"] = Liquidation(id="liq_test", declaration_id="decl_test")
            raise RuntimeError("annuler")
    assert len(store) == 0
    assert len(BusinessStore(store.path, "liquidation", Liquidation)) == 0


def test_creation_et_suppression_concurrentes_sans_orphelin(client_factory):
    # Les deux requêtes démarrent ensemble sur deux applications distinctes.
    for _ in range(5):
        with client_factory() as client:
            identifiant = parent(client)
        depart = Barrier(2)

        def creer():
            with client_factory() as client:
                depart.wait(timeout=10)
                return enfant(client, identifiant).status_code

        def supprimer():
            with client_factory() as client:
                depart.wait(timeout=10)
                return client.delete("/api/declarations/" + identifiant).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            creation = pool.submit(creer)
            suppression = pool.submit(supprimer)
            resultat = creation.result(timeout=20), suppression.result(timeout=20)
        assert resultat in {(200, 409), (422, 200)}, resultat
    with client_factory() as client:
        parents = {d["id"]: d for d in client.get("/api/declarations").json()}
        for liquidation in client.get("/api/declarations/liquidation").json():
            assert liquidation["declaration_id"] in parents
            assert liquidation["dossier_id"] == parents[liquidation["declaration_id"]]["dossier_id"]
