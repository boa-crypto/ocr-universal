"""Tests des correctifs trouves pendant la demonstration reelle du parcours.

Chaque test verrouille un defaut qui a fait parler l'application a tort :
  - la classification tracee sous un identifiant que l'API ne retrouve pas ;
  - la route de classification qui ne renvoyait ni libelle ni preuves ;
  - les pieces d'un dossier sans nom ni categorie ;
  - une correction humaine dont l'origine restait « normalized » ;
  - un arbitrage de coherence non persiste, donc perdu au rechargement.
"""
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))

from parcours_fixtures import creer_fixtures  # noqa: E402

from unocr import api  # noqa: E402
from unocr.api import app  # noqa: E402


@pytest.fixture()
def client(tmp_cfg, fixtures_dir):
    return TestClient(app)


def _attendre(client, job_id, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "error"):
            return j
        time.sleep(0.3)
    raise TimeoutError(f"job {job_id} non termine")


def _importer(client, tmp_path, nom, motif):
    """Importe un document et attend la fin du traitement."""
    fichiers = creer_fixtures()
    with open(fichiers[nom], "rb") as fh:
        r = client.post("/api/documents", files={"file": (fichiers[nom].name, fh,
                                                          "application/pdf")},
                        data={"profile": "generic", "engine": "auto"})
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    assert _attendre(client, job_id)["status"] == "done"
    return job_id


# ─────────────────────── identification du résultat ───────────────────────

def test_resultat_porte_l_identifiant_du_document(client, tmp_path):
    """Le resultat doit porter le job_id, pas un « doc_… » orphelin.

    Sans ce realignement, le journal d'audit tracerait la classification sous
    un identifiant que ni le magasin ni l'API ne savent retrouver.
    """
    job_id = _importer(client, tmp_path, "facture", "facture")
    assert job_id.startswith("job_")
    assert client.get(f"/api/jobs/{job_id}").json()["result_id"] == job_id


def test_classification_renvoie_libelle_preuves_et_alternatives(client, tmp_path):
    """La route de classification doit renvoyer ce qui permet de la contester.

    Renvoyer le seul journal faisait disparaitre libelle, preuves et
    alternatives : l'utilisateur ne pouvait plus verifier la devinette.
    """
    job_id = _importer(client, tmp_path, "facture", "facture")
    c = client.get(f"/api/jobs/{job_id}/classification").json()["classification"]
    assert c is not None
    assert c["category"] == "invoice"
    assert c["label"]
    assert c["evidence"], "une classification sans preuve n'est pas contestable"
    assert "needs_review" in c
    assert "ts" in c, "l'horodatage du journal manque"


def test_classification_absente_renvoie_none_pas_une_erreur(client):
    r = client.get("/api/jobs/job_inexistant/classification")
    assert r.status_code == 200
    assert r.json()["classification"] is None


# ─────────────────────────── pièces d'un dossier ───────────────────────────

def test_piece_herite_du_nom_et_de_la_categorie(client, tmp_path):
    """Une piece ne doit pas afficher « job_… » ni « unknown ».

    Les constats de coherence que l'humain doit trancher portent sur des
    documents nommes : un identifiant technique le met en echec.
    """
    job_id = _importer(client, tmp_path, "bl", "bl")
    dos = client.post("/api/dossiers",
                      json={"label": "test nom piece"}).json()["id"]
    r = client.post(f"/api/dossiers/{dos}/pieces", json={"job_id": job_id})
    assert r.status_code == 200, r.text
    piece = [p for p in r.json()["pieces"] if p["job_id"] == job_id][0]
    assert piece["filename"] == "parcours_bl.pdf"
    assert piece["category"] == "bill_of_lading"


# ─────────────────────── corrections humaines ───────────────────────

def test_correction_bascule_l_origine_de_la_valeur(client, tmp_path):
    """Une valeur corrigee par un humain ne doit plus dire « normalized ».

    C'est exactement ce que la tracabilite doit montrer : la valeur affichee
    vient d'une decision, pas du moteur.
    """
    job_id = _importer(client, tmp_path, "bl", "bl")
    champs = client.get(f"/api/jobs/{job_id}/fields").json()["fields"]
    avant = champs["container_number"]
    assert avant["value_origin"] != "corrected"

    r = client.patch(f"/api/jobs/{job_id}/fields/container_number",
                     json={"corrected_value": "MSCU1234567",
                           "status": "corrected", "user": "amina",
                           "reason": "un seul conteneur sur ce BL"})
    assert r.status_code == 200, r.text
    apres = r.json()["field"]
    assert apres["value_origin"] == "corrected"
    assert apres["status"] == "corrected"
    # la valeur d'origine reste lisible
    assert apres["raw_value"] == avant["raw_value"]
    # la correction est tracee avec son acteur et son motif
    journal = (api.cfg.log_dir / "audit.log").read_text(encoding="utf-8")
    ligne = [lig for lig in journal.splitlines()
             if "field_validated" in lig][-1]
    assert "aminal" not in ligne  # garde-fou : l'acteur doit etre lisible
    assert '"acteur": "amina"' in ligne
    assert "un seul conteneur" in ligne


def test_correction_survit_a_une_reprise(client, tmp_path):
    """Un retry ne doit pas effacer les decisions humaines deja portees."""
    job_id = _importer(client, tmp_path, "bl", "bl")
    client.patch(f"/api/jobs/{job_id}/fields/seal_number",
                 json={"corrected_value": "778899", "status": "corrected"})
    assert client.post(f"/api/jobs/{job_id}/retry").status_code == 200
    assert _attendre(client, job_id)["status"] == "done"
    fv = client.get(f"/api/jobs/{job_id}/fields").json()["fields"]["seal_number"]
    assert fv["corrected_value"] == "778899"
    assert fv["value_origin"] == "corrected"


# ─────────────────────── arbitrage de cohérence ───────────────────────

def test_arbitrage_exige_un_motif(client):
    dos = client.post("/api/dossiers", json={"label": "arbitrage"}).json()["id"]
    r = client.post(f"/api/dossiers/{dos}/coherence",
                    json={"rule": "poids_divergent:gross_weight",
                          "status": "accepte"})
    assert r.status_code == 422
    assert "motif" in r.json()["detail"].lower()


def test_arbitrage_persiste_et_reste_applique(client, tmp_path):
    """Une divergence tranchee ne doit pas revenir « a trancher ».

    Les constats sont recalcules a chaque lecture : sans persistance de
    l'arbitrage, la decision de l'humain disparaissait au rechargement.
    """
    facture = _importer(client, tmp_path, "facture", "facture")
    bl = _importer(client, tmp_path, "bl", "bl")
    colisage = _importer(client, tmp_path, "colisage", "colisage")
    dos = client.post("/api/dossiers", json={"label": "arbitrage persistant"}).json()["id"]
    for jid in (facture, bl, colisage):
        assert client.post(f"/api/dossiers/{dos}/pieces",
                           json={"job_id": jid}).status_code == 200

    avant = client.get(f"/api/dossiers/{dos}/coherence").json()
    regles = [c["rule"] for c in avant["constats"]]
    assert "poids_divergent:gross_weight" in regles
    assert all(c["status"] == "a_trancher" for c in avant["constats"])

    r = client.post(f"/api/dossiers/{dos}/coherence",
                    json={"rule": "poids_divergent:gross_weight",
                          "status": "corrige", "user": "amina",
                          "motif": "poids reel confirme par le transitaire"})
    assert r.status_code == 200, r.text
    assert r.json()["arbitrages"]["poids_divergent:gross_weight"]["status"] == "corrige"

    # la decision survit a une relecture depuis le disque
    api._dossiers._cache.pop(dos, None)
    apres = client.get(f"/api/dossiers/{dos}/coherence").json()
    tranche = [c for c in apres["constats"]
               if c["rule"] == "poids_divergent:gross_weight"][0]
    assert tranche["status"] == "corrige"
    assert tranche["decision_par"] == "amina"

    # et elle est dans l'historique du dossier
    hist = [e["action"] for e in client.get(f"/api/dossiers/{dos}").json()["history_tail"]]
    assert "constat_tranche" in hist
