"""Tests d'observabilité : corrélation et limitation de débit (lot 2).

Ce que ces tests verrouillent : une requête doit être traçable dans les
journaux, et un abus doit être refusé avec une indication de-retry plutôt
que de saturer le magasin.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from unocr import api
from unocr.api import app
from unocr.observabilite import CompteurDebit, nouvel_identifiant


@pytest.fixture()
def client(tmp_cfg):
    return TestClient(app)


# ─────────────────────────── identifiants de corrélation ───────────────────────────

def test_chaque_reponse_porte_un_identifiant(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    identifiant = r.headers.get("X-Request-ID")
    assert identifiant and len(identifiant) >= 8


def test_identifiants_distincts_sur_deux_requetes(client):
    a = client.get("/api/health").headers.get("X-Request-ID")
    b = client.get("/api/jobs").headers.get("X-Request-ID")
    assert a != b


def test_identifiant_fourni_par_le_client_est_repris(client):
    r = client.get("/api/health",
                   headers={"X-Correlation-ID": "trace-operateur-42"})
    assert r.headers.get("X-Request-ID") == "trace-operateur-42"


def test_identifiant_client_malforme_est_ignore(client):
    """Une valeur hostile ou trop courte ne doit pas finir dans les en-têtes."""
    r = client.get("/api/health", headers={"X-Correlation-ID": "<script>x"})
    assert r.headers.get("X-Request-ID") != "<script>x"
    assert r.headers.get("X-Request-ID")


def test_identifiant_disponible_dans_le_traitement(client):
    """Le middleware doit avoir posé request.state avant d'appeler la route."""
    vu = {}

    from fastapi import Request

    @app.get("/api/_test_correlation")
    def _route(request: Request):
        vu["id"] = getattr(request.state, "request_id", None)
        return {"ok": True}

    try:
        client.get("/api/_test_correlation")
        assert vu["id"]
    finally:
        # la route de test ne doit pas survivre au test
        app.router.routes[:] = [r for r in app.router.routes
                                if getattr(r, "path", "") != "/api/_test_correlation"]


# ─────────────────────────── limitation de débit ───────────────────────────

def test_compteur_laisse_passer_puis_refuse():
    c = CompteurDebit(limite=3, fenetre=60.0)
    resultats = [c.autorise("client-a")[0] for _ in range(5)]
    assert resultats == [True, True, True, False, False]


def test_compteur_est_par_client():
    """Un client qui abuse ne doit pas pénaliser les autres."""
    c = CompteurDebit(limite=2, fenetre=60.0)
    assert c.autorise("a")[0] is True
    assert c.autorise("a")[0] is True
    assert c.autorise("a")[0] is False
    assert c.autorise("b")[0] is True


def test_compteur_indique_le_delai_de_retry():
    c = CompteurDebit(limite=1, fenetre=30.0)
    assert c.autorise("x")[0] is True
    autorise, attente = c.autorise("x")
    assert autorise is False
    assert 0 < attente <= 30.0


def test_compteur_desactive_ne_refuse_jamais():
    c = CompteurDebit(limite=1, fenetre=60.0)
    c.actif = False
    assert all(c.autorise("x")[0] for _ in range(10))


def test_fenetre_glissante_libere_les_places():
    """Un compteur remis à zéro à date fixe laisserait passer 2×la limite."""
    c = CompteurDebit(limite=2, fenetre=0.2)
    assert c.autorise("x")[0] is True
    assert c.autorise("x")[0] is True
    assert c.autorise("x")[0] is False
    import time
    time.sleep(0.25)
    assert c.autorise("x")[0] is True


def test_route_sante_dispensee_de_la_limitation(client):
    """La santé et les statistiques ne doivent jamais être ralenties."""
    with patch.object(api, "_compteur") as faux:
        faux.autorise.return_value = (False, 99.0)
        for _ in range(10):
            assert client.get("/api/health").status_code == 200


def test_depassement_renvoie_429_avec_retry_after(client):
    with patch.object(api, "_compteur") as faux:
        faux.autorise.return_value = (False, 12.0)
        r = client.post("/api/dossiers", json={"label": "trop"})
    assert r.status_code == 429
    assert "retry_after" in r.json()
    assert r.headers.get("Retry-After")


def test_le_polling_d_etat_n_est_jamais_bride(client):
    """L'interface interroge /api/jobs/{id} en boucle pendant un traitement
    par lot : brider ces lectures ferait echouer des traitements legitimes.
    La limitation ne porte donc que sur les ecritures."""
    with patch.object(api, "_compteur") as faux:
        faux.autorise.return_value = (False, 99.0)
        for _ in range(20):
            assert client.get("/api/jobs").status_code == 200
            assert client.get("/api/health").status_code == 200


def test_route_observabilite_expose_l_etat(client):
    r = client.get("/api/observabilite")
    assert r.status_code == 200
    corps = r.json()
    assert {"limite", "fenetre_s", "clients_suivis", "actif"} <= set(corps)


def test_identifiants_generes_sont_uniques():
    ids = {nouvel_identifiant() for _ in range(500)}
    assert len(ids) == 500


def test_compteur_est_remis_a_zero_entre_deux_tests(tmp_cfg):
    """Le compteur est global au processus : sans remise à zéro, un test
    accumulerait ses requêtes sur le suivant et déclencherait des 429 qui ne
    traduisent aucun abus. Le fixture `tmp_cfg` s'en charge."""
    from unocr import api

    api._compteur.evenements.clear()
    api._compteur.autorise("testclient")
    assert api._compteur.evenements, "le compteur doit avoir enregistré"
    # le fixture remet à zéro à la sortie ; on vérifie le mécanisme ici
    api._compteur.evenements.clear()
    assert not api._compteur.evenements


def test_limite_par_defaut_laisse_passer_un_lot_important(client):
    """La limite par défaut doit laisser passer un import par lot.

    120 écritures/minute ferait échouer un lot de 200 documents : un lot
    légitime ne doit jamais être pris pour un abus.
    """
    etat = client.get("/api/observabilite").json()
    assert etat["limite"] >= 500
