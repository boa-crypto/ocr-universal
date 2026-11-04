"""Tests de la recherche globale (lot 3).

Ce que ces tests verrouillent : la recherche doit couvre les trois objets que
l'opérateur cherche — dossiers, documents et valeurs de champs — et
**inclure la valeur corrigée**, car c'est celle qu'il a retenue et celle qu'il
veut retrouver ensuite.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))

from parcours_fixtures import creer_fixtures  # noqa: E402

from unocr.api import app  # noqa: E402


@pytest.fixture()
def client(tmp_cfg):
    return TestClient(app)


def _attendre(client, job_id, timeout=120):
    import time

    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "error"):
            return j
        time.sleep(0.3)
    raise TimeoutError(f"job {job_id} non termine")


@pytest.fixture()
def document_importe(client):
    fichiers = creer_fixtures()
    with open(fichiers["facture"], "rb") as fh:
        r = client.post("/api/documents",
                        files={"file": ("facture.pdf", fh, "application/pdf")},
                        data={"profile": "generic", "engine": "auto"})
    job_id = r.json()["job_id"]
    assert _attendre(client, job_id)["status"] == "done"
    return job_id


def test_recherche_trouve_un_champ_extrait(client, document_importe):
    r = client.get("/api/search", params={"q": "INV-2024-118"}).json()
    assert r["returned"] >= 1
    champs = [h for h in r["hits"] if h["kind"] == "field"]
    assert champs
    assert champs[0]["job_id"] == document_importe


def test_recherche_trouve_un_dossier(client):
    dos = client.post("/api/dossiers",
                      json={"label": "Dossier expédition TESTSTAR"}).json()["id"]
    r = client.get("/api/search", params={"q": "TESTSTAR"}).json()
    trouves = [h for h in r["hits"] if h["kind"] == "dossier"]
    assert trouves, "la recherche doit couvrir les dossiers, pas seulement les documents"
    assert trouves[0]["dossier_id"] == dos


def test_recherche_trouve_le_texte_de_la_page(client, document_importe):
    r = client.get("/api/search", params={"q": "TOTAL AMOUNT"}).json()
    textes = [h for h in r["hits"] if h["kind"] == "text"]
    assert textes
    assert textes[0].get("page")


def test_recherche_trouve_la_valeur_corrigee(client, document_importe):
    """Une correction doit être retrouvable par sa nouvelle valeur.

    C'est la valeur que l'opérateur retient : la chercher doit marcher, sinon
    il ne retrouve plus le document qu'il vient de corriger.
    """
    client.patch(f"/api/jobs/{document_importe}/fields/invoice_number",
                 json={"corrected_value": "CORR-9999-ZZ", "status": "corrected"})
    r = client.get("/api/search", params={"q": "CORR-9999-ZZ"}).json()
    assert r["returned"] >= 1
    assert any(h.get("field") == "invoice_number" for h in r["hits"])


def test_recherche_sans_resultat_ne_renvoie_pas_erreur(client):
    r = client.get("/api/search", params={"q": "zzz-introuvable-zzz"})
    assert r.status_code == 200
    assert r.json()["returned"] == 0


def test_recherche_exige_une_requete_non_vide(client):
    assert client.get("/api/search", params={"q": ""}).status_code == 422


def test_recherche_respecte_la_limite(client, document_importe):
    r = client.get("/api/search", params={"q": "e", "limit": 3}).json()
    assert r["returned"] <= 3


def test_recherche_est_insensible_a_la_casse(client, document_importe):
    r = client.get("/api/search", params={"q": "inv-2024-118"}).json()
    assert r["returned"] >= 1
