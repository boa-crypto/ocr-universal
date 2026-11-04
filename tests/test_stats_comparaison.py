"""Comparaison de périodes : deux fenêtres, aucune variation inventée.

**Pourquoi ce fichier existe.** Une comparaison est le genre d'écran qui ment
sans le faire exprès : une période précédente vide devient « +∞ % », une date
manquante devient « 0 », et l'exploitant prend une absence de mesure pour une
baisse d'activité. Ces tests verrouillent les trois cas.
"""

from __future__ import annotations

from enum import Enum

import pytest
from fastapi.testclient import TestClient

from unocr.api import app
from unocr.routes.statistiques import comparer

JOUR = 86400
MAINTENANT = 1_800_000_000.0


def dossier(created_at=None, updated_at=None, state="en_preparation"):
    return {"created_at": created_at, "updated_at": updated_at, "state": state}


def test_hausse_baisse_et_stabilite():
    dossiers = [
        dossier(MAINTENANT - 5 * JOUR),                      # période courante
        dossier(MAINTENANT - 20 * JOUR, MAINTENANT - 6 * JOUR, "archive"),
        dossier(MAINTENANT - 50 * JOUR),                     # période précédente
    ]
    resultat = comparer(dossiers, [], 30, MAINTENANT)
    par_nom = {i["indicateur"]: i for i in resultat["indicateurs"]}

    ouverts = par_nom["Dossiers ouverts"]
    assert ouverts["courant"] == 2 and ouverts["precedent"] == 1
    assert ouverts["variation"] == 1 and ouverts["tendance"] == "hausse"
    assert ouverts["lecture"] == "+1 (+100 %) vs 1"

    archives = par_nom["Dossiers archivés"]
    assert archives["courant"] == 1 and archives["precedent"] == 0
    # première période vide côté précédent : pas de pourcentage trompeur
    assert archives["variation"] is None
    assert "aucun équivalent avant" in archives["lecture"]


def test_baisse_est_negative():
    dossiers = [dossier(MAINTENANT - 2 * JOUR) for _ in range(2)] + \
               [dossier(MAINTENANT - 45 * JOUR) for _ in range(5)]
    ouverts = {i["indicateur"]: i for i in comparer(dossiers, [], 30, MAINTENANT)["indicateurs"]}["Dossiers ouverts"]
    assert ouverts["courant"] == 2 and ouverts["precedent"] == 5
    assert ouverts["variation"] == -3 and ouverts["tendance"] == "baisse"
    assert ouverts["lecture"].startswith("-3 (-60 %) vs 5")


def test_deux_periodes_vides_restent_stables():
    resultat = comparer([], [], 30, MAINTENANT)
    assert resultat["vide"]
    for indicateur in resultat["indicateurs"]:
        assert indicateur["tendance"] == "stable"
        assert indicateur["variation"] == 0
        assert "aucune activité" in indicateur["lecture"]


def test_dates_manquantes_ne_sont_pas_des_vieux_dossiers():
    resultat = comparer([dossier(), dossier(), dossier(MAINTENANT - 1 * JOUR)],
                        [], 30, MAINTENANT)
    par_nom = {i["indicateur"]: i for i in resultat["indicateurs"]}
    assert par_nom["Dossiers ouverts"]["courant"] == 1   # une seule date réelle
    assert resultat["sans_date"] == 2                     # les autres sont dites
    assert resultat["avertissement"]                    # période précédente vide


def test_etats_enumeration_lus_correctement():
    class Etat(str, Enum):
        ARCHIVE = "archive"

    dossiers = [dossier(MAINTENANT - 3 * JOUR, MAINTENANT - 2 * JOUR, Etat.ARCHIVE)]
    par_nom = {i["indicateur"]: i
               for i in comparer(dossiers, [], 30, MAINTENANT)["indicateurs"]}
    assert par_nom["Dossiers archivés"]["courant"] == 1


def test_jobs_comptes_sur_leur_dernier_etat():
    class Job:
        def __init__(self, status, ts):
            self.status = status
            self.updated_at = ts
            self.created_at = ts

    jobs = [Job("done", MAINTENANT - 2 * JOUR),
            Job("error", MAINTENANT - 3 * JOUR),
            Job("done", MAINTENANT - 40 * JOUR)]
    par_nom = {i["indicateur"]: i
               for i in comparer([], jobs, 30, MAINTENANT)["indicateurs"]}
    assert par_nom["Documents traités"]["courant"] == 1
    assert par_nom["Documents traités"]["precedent"] == 1
    assert par_nom["Documents en erreur"]["courant"] == 1


def test_api_borne_la_periode():
    client = TestClient(app)
    assert client.get("/api/stats/comparaison?jours=0").json()["jours"] == 1
    assert client.get("/api/stats/comparaison?jours=9999").json()["jours"] == 365
    corps = client.get("/api/stats/comparaison").json()
    assert corps["jours"] == 30
    assert {i["indicateur"] for i in corps["indicateurs"]} >= {
        "Dossiers ouverts", "Documents traités", "Dossiers archivés"}


@pytest.mark.parametrize("jours", [7, 30, 90])
def test_fenetres_consecutives(jours):
    corps = comparer([], [], jours, MAINTENANT)
    debut_courant, fin_courant = corps["fenetres"]["courant"]
    debut_precedent, fin_precedent = corps["fenetres"]["precedent"]
    assert fin_courant == MAINTENANT
    assert fin_precedent == debut_courant
    assert fin_courant - debut_courant == debut_courant - debut_precedent == jours * JOUR


def test_documents_en_attente_ne_sont_pas_traites():
    jobs = [{"status": statut, "updated_at": MAINTENANT - JOUR}
            for statut in ["queued", "processing", "cancelled", "error", "done", "not_error"]]
    par_nom = {i["indicateur"]: i for i in comparer([], jobs, 30, MAINTENANT)["indicateurs"]}
    assert par_nom["Documents traités"]["courant"] == 1
    assert par_nom["Documents en erreur"]["courant"] == 1


@pytest.mark.parametrize("date", [float("nan"), float("inf"), float("-inf"), "invalide"])
def test_dates_non_finies_signalees(date):
    corps = comparer([dossier(date)], [], 30, MAINTENANT)
    assert corps["sans_date"] == 1
    assert corps["indicateurs"][0]["courant"] == 0


def test_job_sans_modification_ne_replie_pas_sur_creation():
    corps = comparer([], [{"status": "done", "created_at": MAINTENANT - JOUR}], 30, MAINTENANT)
    assert next(i for i in corps["indicateurs"] if i["indicateur"] == "Documents traités")["courant"] == 0


def test_erreur_magasin_n_est_pas_une_periode_vide(monkeypatch):
    from unocr.api import _dossiers

    def panne():
        raise OSError("indisponible")

    monkeypatch.setattr(_dossiers, "liste", panne)
    reponse = TestClient(app).get("/api/stats/comparaison")
    assert reponse.status_code == 503
    assert "lecture des dossiers" in reponse.json()["detail"]


def test_limite_documents_signalee(monkeypatch):
    from unocr.api import _dossiers

    monkeypatch.setattr(_dossiers, "liste", lambda: [])
    def liste(limit):
        assert limit == 2001
        return [{"status": "done", "updated_at": MAINTENANT - JOUR}] * limit
    monkeypatch.setattr(app.state.store, "list_jobs", liste)
    corps = TestClient(app).get("/api/stats/comparaison").json()
    assert corps["jobs_tronques"] is True
    assert corps["jobs_analyses"] == 2000
    assert "2000" in corps["limites"]
