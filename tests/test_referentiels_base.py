"""Jeu de base des référentiels : données de référence, pas données d'exemple.

**Pourquoi ce fichier existe.** Un poste neuf n'a ni port, ni pays, ni devise :
les formulaires métier n'ont rien à proposer et l'opérateur ressaisit à la main
des listes publiques. L'amorçage comble ce vide — mais il doit rester **sûr** :
idempotent, non destructif, tracé, et limité aux données de référence.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from unocr.api import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("UNOCR_DATA_DIR", str(data))
    monkeypatch.setenv("UNOCR_LOG_DIR", str(tmp_path / "logs"))
    yield TestClient(app), data, tmp_path / "logs"


def test_apercu_annonce_ce_qui_manque(client):
    api, _data, _logs = client
    apercu = api.get("/api/referentiels/ports/base/apercu").json()
    assert apercu["disponible"] is True
    assert apercu["total"] == apercu["nouveaux"] > 0
    assert apercu["deja_presents"] == 0


def test_amorcage_ajoute_et_marque_l_origine(client):
    api, data, logs = client
    reponse = api.post("/api/referentiels/ports/base")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["ajoutes"] == corps["total"] > 0
    assert "Port d'Oran" in corps["libelles"]

    entrees = api.get("/api/referentiels/ports").json()["entrees"]
    assert len(entrees) == corps["total"]
    assert all(e["origine"] == "jeu de base" for e in entrees)
    assert {e["code"] for e in entrees} >= {"DZALG", "DZORN"}

    # persistance réelle : le fichier contient les entrées
    contenu = json.loads((data / "referentiels.json").read_text(encoding="utf-8"))
    assert len(contenu["ports"]) == corps["total"]

    # tracé
    journal = (logs / "audit.log").read_text(encoding="utf-8")
    assert "referentiel_amorce" in journal


def test_amorcage_est_idempotent(client):
    api, _data, _logs = client
    premier = api.post("/api/referentiels/pays/base").json()
    second = api.post("/api/referentiels/pays/base").json()
    assert premier["ajoutes"] > 0
    assert second["ajoutes"] == 0
    assert second["deja_presents"] == premier["ajoutes"]
    assert second["total"] == premier["total"]


def test_entree_existante_jamais_ecrasee(client):
    """Une saisie métier prime sur le jeu de base : on ne réécrit pas."""
    api, _data, _logs = client
    cree = api.post("/api/referentiels/pays",
                    json={"libelle": "Algerie (saisie locale)", "code": "DZ"})
    assert cree.status_code == 201
    avant = cree.json()

    api.post("/api/referentiels/pays/base")

    apres = api.get(f"/api/referentiels/pays/{avant['id']}").json()
    assert apres["libelle"] == "Algerie (saisie locale)"
    assert apres.get("origine") != "jeu de base"


def test_apercu_et_amorcage_refusent_une_collection_sans_base(client):
    api, _data, _logs = client
    apercu = api.get("/api/referentiels/tarifs/base/apercu").json()
    assert apercu["disponible"] is False and apercu["total"] == 0
    refus = api.post("/api/referentiels/tarifs/base")
    assert refus.status_code == 404
    assert "aucun jeu de base" in refus.json()["detail"]


def test_collection_inconnue_renvoie_404(client):
    api, _data, _logs = client
    assert api.post("/api/referentiels/inconnu/base").status_code == 404
    assert api.get("/api/referentiels/inconnu/base/apercu").status_code == 404
