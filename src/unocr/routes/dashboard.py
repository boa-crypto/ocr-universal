"""Routes API pour le dashboard et le pilotage maritime (Module 14)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..config import get_config
from ..dashboard import get_dashboard_service
from ..logging_setup import get_logger
from .frais import _get_facture_store, _get_frais_store

log = get_logger("dashboard")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic
# ───────────────────────────────────────────────────────────────

class FiltreDossiers(BaseModel):
    limite: Optional[int] = 50
    statut: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Routes Dashboard - Indicateurs maritimes
# ───────────────────────────────────────────────────────────────

@router.get("")
def etat_systeme(
    request: Request,
) -> dict:
    """État général du système UniOCR."""
    service = get_dashboard_service()
    return service.statistiques_generales()


@router.get("/indicateurs")
def indicateurs_operationnels(
    request: Request,
) -> dict:
    """15+ indicateurs opérationnels clés pour le pilotage maritime."""
    service = get_dashboard_service()
    return service.indicateurs_operationnels(
        _get_frais_store(request), _get_facture_store(request)
    )


@router.get("/alertes")
def alertes_systeme(
    request: Request,
) -> dict:
    """Alertes système actives."""
    service = get_dashboard_service()
    return service.alertes_systeme()


@router.get("/financier/{dossier_id}")
def resume_financier(
    dossier_id: str,
    request: Request,
) -> dict:
    """Résumé financier d'un dossier."""
    service = get_dashboard_service()
    return service.resume_financier_dossier(
        dossier_id, _get_frais_store(request), _get_facture_store(request)
    )


@router.get("/historique/{dossier_id}")
def historique_etat(
    dossier_id: str,
    request: Request,
) -> dict:
    """Historique des états d'un dossier."""
    service = get_dashboard_service()
    return service.historique_statuts_dossier(dossier_id)


# Graphiques interactifs (6+ types)
@router.get("/graphique/etat-dossiers")
def graphique_etat_dossiers(
    request: Request,
) -> dict:
    """Graphique: répartition des dossiers par état."""
    service = get_dashboard_service()
    return service.graphique_etat_dossiers()


@router.get("/graphique/financier-mensuel")
def graphique_financier_mensuel(
    request: Request,
    mois_debut: Optional[int] = None,
    mois_fin: Optional[int] = None,
) -> dict:
    """Graphique: évolution financière mensuelle."""
    service = get_dashboard_service()
    return service.graphique_financier_mensuel(
        mois_debut, mois_fin,
        _get_frais_store(request), _get_facture_store(request),
    )


@router.get("/graphique/repartition-par-port")
def graphique_repartition_par_port(
    request: Request,
) -> dict:
    """Graphique: répartition des opérations par port de chargement."""
    service = get_dashboard_service()
    return service.graphique_repartition_par_port()


@router.get("/graphique/top-clients")
def graphique_top_clients(
    request: Request,
    limite: int = 10,
) -> dict:
    """Graphique: top des clients par nombre de dossiers."""
    service = get_dashboard_service()
    return service.graphique_repartition_par_client(limite)


@router.get("/graphique/fret-par-gestionnaire")
def graphique_fret_par_gestionnaire(
    request: Request,
) -> dict:
    """Graphique: coût du fret par gestionnaire."""
    service = get_dashboard_service()
    return service.graphique_fret_par_gestionnaire()


@router.get("/graphique/anomalies-par-type")
def graphique_anomalies_par_type(
    request: Request,
) -> dict:
    """Graphique: répartition des anomalies par type."""
    service = get_dashboard_service()
    return service.graphique_anomalies_par_type()


@router.get("/graphique/taux-reussite-par-mois")
def graphique_taux_reussite_par_mois(
    request: Request,
    mois_debut: Optional[int] = None,
    mois_fin: Optional[int] = None,
) -> dict:
    """Graphique: taux de réussite par mois."""
    service = get_dashboard_service()
    return service.graphique_taux_reussite_par_mois(mois_debut, mois_fin)


@router.get("/sante")
def sante_systeme(
    request: Request,
) -> dict:
    """État de santé du système UniOCR."""
    service = get_dashboard_service()
    stats = service.statistiques_generales()
    alertes = service.alertes_systeme()
    financiers = service.resume_financier_dossier(
        "__synthese__", _get_frais_store(request), _get_facture_store(request)
    )

    return {
        "systeme_actif": True,
        "statistiques": stats,
        # `alertes` (liste complète) est le champ attendu par le contrat d'API ;
        # les deux autres restent pour les consommateurs existants.
        "alertes": alertes.get("alertes", []),
        "alertes_critiques": [a for a in alertes["alertes"] if a["niveau"] in ["critical", "error"]],
        "alertes_totales": alertes["nb_total"],
        "sante_financiere": {
            "total_encours": financiers["total_frais"] + financiers["total_factures_client"],
            "total_impaye": financiers["frais_en_attente"] + financiers["factures_en_attente"],
        },
        "timestamp": datetime.now().isoformat(),
    }
