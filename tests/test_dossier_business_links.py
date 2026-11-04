"""Références métier aux dossiers : garde-fous sur la vraie API isolée."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from unocr import api
from unocr.business_store import BusinessStore
from unocr.models import DeclarationDouaniere, Liquidation, TerminalEnlevement
from unocr.routes import declarations, terminal


@pytest.fixture
def contexte(tmp_cfg, monkeypatch):
    monkeypatch.setattr(declarations, "cfg", tmp_cfg)
    monkeypatch.setattr(terminal, "cfg", tmp_cfg)
    api._recharge_rbac()
    dossier = api._dossiers.creer("Dossier temporaire")
    with TestClient(api.app) as client:
        yield client, tmp_cfg, dossier.id


def corps(route, dossier_id):
    data = {"dossier_id": dossier_id}
    if route == "/api/terminal":
        data.update(numero_bl="BL", numero_conteneur="CONT")
    return data


@pytest.mark.parametrize("route", ["/api/declarations", "/api/terminal"])
@pytest.mark.parametrize("identifiant", ["dos_inconnu", "../dossier", ""])
def test_reference_inexistante_refusee(contexte, route, identifiant):
    client, _, _ = contexte
    rep = client.post(route, json=corps(route, identifiant))
    assert rep.status_code == 422, rep.text
    assert client.get(route).json() == []


@pytest.mark.parametrize("route", ["/api/declarations", "/api/terminal"])
def test_reaffectation_invalide_preserve_objet(contexte, route):
    client, _, identifiant = contexte
    creation = client.post(route, json=corps(route, identifiant))
    assert creation.status_code == 200, creation.text
    avant = creation.json()
    url = route + "/" + avant["id"]
    assert client.put(url, json={"dossier_id": "dos_inconnu"}).status_code == 422
    assert client.get(url).json() == avant


@pytest.mark.parametrize("collection,modele", [
    ("declaration", DeclarationDouaniere), ("liquidation", Liquidation),
    ("terminal", TerminalEnlevement),
])
def test_dossier_reference_protege_meme_par_ancienne_liquidation(contexte, collection, modele):
    client, cfg, identifiant = contexte
    # Insertion directe pour couvrir aussi les liens anciens sans parent valide.
    magasin = BusinessStore(cfg.data_dir / "metier.sqlite3", collection, modele)
    magasin["objet_test"] = modele(id="objet_test", dossier_id=identifiant)
    url = "/api/dossiers/" + identifiant
    assert client.delete(url).status_code == 409
    assert (cfg.data_dir / "dossiers" / f"{identifiant}.json").exists()
    del magasin["objet_test"]
    assert client.delete(url).status_code == 200
    assert not (cfg.data_dir / "dossiers" / f"{identifiant}.json").exists()


def test_cache_dossier_ne_valide_pas_un_fichier_supprime(contexte):
    client, cfg, identifiant = contexte
    assert api._dossiers.get(identifiant) is not None
    (cfg.data_dir / "dossiers" / f"{identifiant}.json").unlink()
    assert client.post("/api/declarations", json={"dossier_id": identifiant}).status_code == 422
    assert client.delete("/api/dossiers/" + identifiant).status_code == 404


def test_dossier_illisible_ne_produit_pas_de_reference(contexte):
    client, cfg, identifiant = contexte
    (cfg.data_dir / "dossiers" / f"{identifiant}.json").write_text("{invalide", encoding="utf-8")
    assert client.post("/api/declarations", json={"dossier_id": identifiant}).status_code == 503
    assert client.get("/api/declarations").json() == []


@pytest.mark.parametrize("route", ["/api/declarations", "/api/terminal"])
def test_course_creation_reference_et_suppression_dossier(contexte, route):
    client, cfg, _ = contexte
    for _ in range(5):
        dossier = api._dossiers.creer("Course isolée")
        depart = Barrier(2)

        def creer():
            with TestClient(api.app) as concurrent:
                depart.wait(timeout=10)
                return concurrent.post(route, json=corps(route, dossier.id)).status_code

        def supprimer():
            with TestClient(api.app) as concurrent:
                depart.wait(timeout=10)
                return concurrent.delete("/api/dossiers/" + dossier.id).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            creation = pool.submit(creer)
            suppression = pool.submit(supprimer)
            resultat = creation.result(timeout=20), suppression.result(timeout=20)
        assert resultat in {(200, 409), (422, 200)}, resultat
    for objet in client.get(route).json():
        assert (cfg.data_dir / "dossiers" / f"{objet['dossier_id']}.json").is_file()
