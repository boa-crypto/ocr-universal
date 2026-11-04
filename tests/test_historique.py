"""Historique d'un document : le journal d'audit, filtré et lisible.

Ce que ces tests protègent : un écran « Historique » qui afficherait autre
chose que le journal — ou qui masquerait les événements qu'il ne sait pas
traduire. Un historique troué vaut moins que pas d'historique.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from unocr.api import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    journal = tmp_path / "logs"
    journal.mkdir()
    monkeypatch.setenv("UNOCR_LOG_DIR", str(journal))
    yield TestClient(app), journal


def ecrire(journal, entrees):
    with (journal / "audit.log").open("a", encoding="utf-8") as f:
        for entree in entrees:
            f.write(json.dumps(entree, ensure_ascii=False) + "\n")


def test_evenements_du_job_dans_l_ordre(client):
    api, journal = client
    ecrire(journal, [
        {"ts": 1700000200, "event": "job_done", "job_id": "job_a",
         "pages": 3, "mean_confidence": 0.812},
        {"ts": 1700000100, "event": "job_created", "job_id": "job_a",
         "filename": "connaissement.pdf", "size": 2048, "profile": "generic"},
        {"ts": 1700000300, "event": "dossier_piece_added", "job_id": "job_a",
         "dossier_id": "dos_1", "filename": "connaissement.pdf",
         "acteur": "utilisateur"},
        {"ts": 1700000150, "event": "job_created", "job_id": "job_autre",
         "filename": "autre.pdf", "size": 10, "profile": "generic"},
    ])
    corps = api.get("/api/jobs/job_a/historique").json()

    assert corps["total"] == 3                      # rien du job voisin
    libelles = [e["libelle"] for e in corps["evenements"]]
    assert libelles == ["Document reçu", "Analyse terminée", "Rattaché à un dossier"]
    assert corps["evenements"][0]["detail"].startswith("connaissement.pdf — 2048 octets")
    assert "81%" in corps["evenements"][1]["detail"]
    assert corps["evenements"][2]["acteur"] == "utilisateur"
    assert corps["evenements"][0]["horodatage"]                    # date lisible
    assert corps["job_existe"] is False                             # job purgé


def test_champ_valide_affiche_la_valeur_ou_le_geste(client):
    api, journal = client
    ecrire(journal, [
        {"ts": 1, "event": "field_validated", "job_id": "job_b",
         "field": "date", "confirmed": "2024-03-15", "corrected": None,
         "acteur": "amel"},
        {"ts": 2, "event": "field_validated", "job_id": "job_b",
         "field": "montant", "confirmed": None, "corrected": "1500.00",
         "acteur": "amel"},
    ])
    corps = api.get("/api/jobs/job_b/historique").json()
    details = [e["detail"] for e in corps["evenements"]]
    assert details[0] == "date : 2024-03-15"
    assert corps["evenements"][1]["libelle"] == "Champ corrigé"
    assert details[1] == "montant : 1500.00"


def test_evenement_inconnu_affiche_tel_quel(client):
    """Un événement non traduit ne doit pas disparaître de l'historique."""
    api, journal = client
    ecrire(journal, [
        {"ts": 5, "event": "nouvel_evenement_metier", "job_id": "job_c"},
    ])
    corps = api.get("/api/jobs/job_c/historique").json()
    assert corps["total"] == 1
    assert corps["evenements"][0]["libelle"] == "nouvel evenement metier"
    assert corps["evenements"][0]["evenement"] == "nouvel_evenement_metier"


def test_document_inconnu_repond_vide_avec_explication(client):
    """Pas de 404 : l'écran doit pouvoir dire *pourquoi* c'est vide."""
    api, _journal = client
    reponse = api.get("/api/jobs/job_inexistant/historique")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["total"] == 0 and corps["evenements"] == []
    assert "Document inconnu" in corps["vide"]


def test_lignes_illisibles_signalees(client):
    api, journal = client
    with (journal / "audit.log").open("a", encoding="utf-8") as f:
        f.write("{ pas du json\n")
        f.write(json.dumps({"ts": 9, "event": "job_created", "job_id": "job_d",
                            "filename": "x.pdf", "size": 1, "profile": "generic"}) + "\n")
    corps = api.get("/api/jobs/job_d/historique").json()
    assert corps["total"] == 1
    assert corps["lignes_illisibles"] == 1
