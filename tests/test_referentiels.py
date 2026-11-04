"""Référentiels métier génériques (`/api/referentiels`).

Ces écrans (ports, pays, devises, équipes, grilles tarifaires, règles
documentaires, paramètres métier…) n'avaient aucun stockage. Les tests
ci-dessous vérifient ce qui compte vraiment : la donnée est réellement
persistée sur disque, relue par une nouvelle requête, protégée contre les
doublons de code, et chaque écriture est tracée.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from unocr.api import app

COLLECTIONS_ATTENDUES = {
    "ports",
    "pays",
    "devises",
    "types-marchandises",
    "tarifs",
    "regles-documentaires",
    "parametres",
    "equipes",
    "types-documents",
    "types-marchandises-complementaires",
    "versions-matrice",
}


def test_catalogue_liste_les_collections_avec_leurs_totaux(tmp_cfg):
    client = TestClient(app)

    reponse = client.get("/api/referentiels")

    assert reponse.status_code == 200
    collections = reponse.json()["collections"]
    assert COLLECTIONS_ATTENDUES <= {c["nom"] for c in collections}
    assert all(c["titre"] and c["description"] and c["champs"] for c in collections)
    assert all(c["total"] == 0 for c in collections)


def test_creation_persiste_sur_disque_et_relecture(tmp_cfg):
    client = TestClient(app)

    creation = client.post(
        "/api/referentiels/ports",
        json={"code": "DZALG", "libelle": "Port d'Alger", "attributs": {"pays": "DZ"}},
    )
    assert creation.status_code == 201
    entree = creation.json()
    assert entree["id"].startswith("port_")
    assert entree["code"] == "DZALG"

    fichier = tmp_cfg.data_dir / "referentiels.json"
    assert fichier.is_file()
    assert entree["id"] in json.loads(fichier.read_text(encoding="utf-8"))["ports"]

    relecture = client.get("/api/referentiels/ports")
    assert relecture.status_code == 200
    corps = relecture.json()
    assert corps["total"] == 1
    assert corps["entrees"][0]["attributs"] == {"pays": "DZ"}


def test_code_duplique_refuse(tmp_cfg):
    client = TestClient(app)
    charge = {"code": "DZORN", "libelle": "Port d'Oran"}

    assert client.post("/api/referentiels/ports", json=charge).status_code == 201
    doublon = client.post("/api/referentiels/ports", json={**charge, "libelle": "Autre"})

    assert doublon.status_code == 409
    assert "existe déjà" in doublon.json()["detail"]
    # Le doublon n'a rien ajouté.
    assert client.get("/api/referentiels/ports").json()["total"] == 1


def test_modification_et_suppression(tmp_cfg):
    client = TestClient(app)
    identifiant = client.post(
        "/api/referentiels/devises", json={"code": "EUR", "libelle": "Euro"}
    ).json()["id"]

    modification = client.put(
        f"/api/referentiels/devises/{identifiant}",
        json={"libelle": "Euro (€)", "attributs": {"symbole": "€"}},
    )
    assert modification.status_code == 200
    assert modification.json()["libelle"] == "Euro (€)"
    assert modification.json()["attributs"] == {"symbole": "€"}

    suppression = client.delete(f"/api/referentiels/devises/{identifiant}")
    assert suppression.status_code == 200
    assert client.get("/api/referentiels/devises").json()["total"] == 0
    assert client.get(f"/api/referentiels/devises/{identifiant}").status_code == 404


def test_collection_inconnue_et_entree_inconnue(tmp_cfg):
    client = TestClient(app)

    assert client.get("/api/referentiels/inconnue").status_code == 404
    assert client.get("/api/referentiels/ports/port_absent").status_code == 404


def test_recherche_filtre_sur_le_contenu(tmp_cfg):
    client = TestClient(app)
    client.post("/api/referentiels/ports", json={"libelle": "Port de Skikda", "code": "DZSKI"})
    client.post("/api/referentiels/ports", json={"libelle": "Port de Bejaia", "code": "DZBJA"})

    resultat = client.get("/api/referentiels/ports", params={"recherche": "skikda"}).json()

    assert resultat["total"] == 1
    assert resultat["entrees"][0]["code"] == "DZSKI"


def test_ecritures_tracees_dans_le_journal_d_audit(tmp_cfg):
    client = TestClient(app)
    client.post("/api/referentiels/equipes", json={"libelle": "Équipe import", "code": "IMP"})

    journal = (tmp_cfg.log_dir / "audit.log").read_text(encoding="utf-8")

    assert "referentiel_cree" in journal
    assert "Équipe import" in journal
