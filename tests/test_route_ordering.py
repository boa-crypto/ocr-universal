"""Garde-fou sur l'ordre d'enregistrement des routes.

FastAPI résout les routes dans l'ordre de déclaration : une route
paramétrique (`/api/frais/{frais_id}`) déclarée avant une route littérale
(`/api/frais/facture`) capture cette dernière, qui devient alors
inaccessible — d'où des 404 « introuvable » sur des endpoints pourtant
déclarés. Ces tests figent la règle : aucune route littérale ne doit être
masquée, et les listes autrefois capturées répondent bien 200.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests._routes import iterer_routes, routes_masquees
from unocr.api import app


def test_aucune_route_litterale_n_est_masquee_par_une_route_parametrique() -> None:
    masquees = routes_masquees(app)

    assert masquees == [], "Routes déclarées trop tôt :\n" + "\n".join(masquees)


def test_le_detecteur_repere_une_route_masquee() -> None:
    """Le garde-fou précédent ne vaut que s'il sait voir le problème."""
    app_temoin = FastAPI()

    @app_temoin.get("/api/frais/{frais_id}")
    def _detail(frais_id: str) -> dict:
        return {"id": frais_id}

    @app_temoin.get("/api/frais/facture")
    def _liste() -> list:
        return []

    assert routes_masquees(app_temoin) == ["GET /api/frais/facture"]


def test_listes_liquidation_et_facture_repondent_200() -> None:
    client = TestClient(app)
    for chemin in ("/api/declarations/liquidation", "/api/frais/facture"):
        reponse = client.get(chemin)
        assert reponse.status_code == 200, chemin
        assert isinstance(reponse.json(), list), chemin


def test_template_de_workflow_est_atteignable() -> None:
    """Le template était capturé par `/api/workflow/{dossier_id}`."""
    chemins = {chemin for chemin, methode in iterer_routes(app) if methode == "GET"}

    assert "/api/workflow/workflow/template" in chemins
    reponse = TestClient(app).get("/api/workflow/workflow/template")
    assert reponse.status_code == 200
    assert reponse.json()["etapes"][0]["id"] == "creation"
