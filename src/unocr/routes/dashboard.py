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


# ───────────────────────────────────────────────────────────────
# Séries temporelles réelles (aucune donnée inventée)
# ───────────────────────────────────────────────────────────────

@router.get("/serie-dossiers")
def serie_dossiers(request: Request, jours: int = 30) -> dict:
    """Créations, mouvements et clôtures par jour, calculés sur les dossiers.

    Une création vient de `created_at`, une clôture d'un passage vers
    `exporte`/`archive`, un mouvement de toute autre action du journal.
    La fenêtre est bornée à 365 jours.
    """
    import time
    from datetime import datetime, timedelta

    from ..dossier import DossierStore

    jours = max(1, min(int(jours), 365))
    conf = request.app.state.cfg
    store = DossierStore(conf.data_dir / "dossiers", log_dir=conf.log_dir)

    aujourdhui = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    debut = aujourdhui - timedelta(days=jours - 1)
    seau = {}
    for i in range(jours):
        jour = debut + timedelta(days=i)
        seau[jour.strftime("%Y-%m-%d")] = {"date": jour.strftime("%Y-%m-%d"),
                                           "crees": 0, "traites": 0, "clotures": 0}

    etats_clos = {"exporte", "archive"}

    def marquer(horodatage, cle):
        try:
            jour = datetime.fromtimestamp(float(horodatage)).replace(
                hour=0, minute=0, second=0, microsecond=0)
        except (TypeError, ValueError, OSError):
            return
        ligne = seau.get(jour.strftime("%Y-%m-%d"))
        if ligne is not None:
            ligne[cle] += 1

    for dossier in store.liste():
        marquer(dossier.created_at, "crees")
        for evenement in dossier.history:
            if evenement.action == "created":
                continue
            if evenement.action in ("state_changed", "state_forced"):
                cible = str((evenement.detail or {}).get("to") or "")
                if cible in etats_clos:
                    marquer(evenement.ts, "clotures")
                    continue
            marquer(evenement.ts, "traites")

    series = [seau[k] for k in sorted(seau)]
    return {
        "periode_jours": jours,
        "debut": series[0]["date"] if series else "",
        "fin": series[-1]["date"] if series else "",
        "series": series,
        "totaux": {cle: sum(ligne[cle] for ligne in series)
                   for cle in ("crees", "traites", "clotures")},
        "genere_le": time.time(),
    }


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
