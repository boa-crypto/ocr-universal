"""Routes de contrôle documentaire intelligent (Module 04)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, List

from ..controle_documentaire import analyser_dossier_complet, ControleDocumentaireEngine
from ..config import get_config
from ..logging_setup import audit, get_logger
from ..rbac import ADMINISTRATEUR, LECTEUR

log = get_logger("controle_doc")

router = APIRouter(prefix="/api/controle", tags=["controle-documentaire"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic
# ───────────────────────────────────────────────────────────────

class ControleRequest(BaseModel):
    dossier_id: str


# ───────────────────────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────────────────────

@router.post("/analyser")
def analyser_dossier(
    request: Request,
    body: ControleRequest,
) -> dict:
    """Lance l'analyse complète de contrôle documentaire d'un dossier."""
    resultat = analyser_dossier_complet(body.dossier_id)

    audit(cfg.log_dir, "controle_documentaire_lance",
          dossier_id=body.dossier_id,
          total_anomalies=resultat["total_anomalies"],
          bloquantes=resultat["anomalies_bloquantes"])

    return resultat


@router.get("/{dossier_id}/anomalies")
def get_anomalies_dossier(
    dossier_id: str,
    request: Request,
) -> dict:
    """Récupère les anomalies d'un dossier (depuis le dernier contrôle)."""
    engine = ControleDocumentaireEngine()
    anomalies = engine.analyser_dossier(dossier_id)

    return {
        "dossier_id": dossier_id,
        "anomalies": [
            {
                "type": a.type_anomalie,
                "regle": a.regle,
                "gravite": a.gravite,
                "message": a.message,
                "documents": a.documents_concernes,
                "champ": a.champ,
                "valeurs": a.valeurs,
            }
            for a in anomalies
        ]
    }


@router.get("/regles")
def lister_regles() -> dict:
    """Liste les règles de comparaison configurées."""
    from ..controle_documentaire import REGLES_COMPARAISON, TypeAnomalie, Gravite

    return {
        "regles": [
            {
                "nom": nom,
                "champs": regle["champs"],
                "types_documents": regle["types_docs"],
                "gravite": regle["gravite"],
                "message": regle["message"],
                "tolerance": regle.get("tolerance", 0)
            }
            for nom, regle in REGLES_COMPARAISON.items()
        ],
        # `TypeAnomalie` / `Gravite` sont des classes de constantes (pas des
        # Enum) : les parcourir directement levait « 'type' object is not
        # iterable ». On lit donc les attributs texte déclarés.
        "types_anomalie": [v for v in vars(TypeAnomalie).values()
                           if isinstance(v, str)],
        "gravites": [v for v in vars(Gravite).values() if isinstance(v, str)],
    }


@router.post("/{dossier_id}/resoudre")
def resoudre_anomalie(
    dossier_id: str,
    request: Request,
    body: dict,
) -> dict:
    """Marque une anomalie comme résolue (action corrective effectuée)."""
    # TODO: Implémenter la persistance des résolutions
    audit(cfg.log_dir, "anomalie_resolue",
          dossier_id=dossier_id,
          regle=body.get("regle"),
          action=body.get("action"),
          utilisateur=body.get("utilisateur"))

    return {"ok": True, "message": "Anomalie marquée comme résolue"}


@router.get("/{dossier_id}/statut")
def statut_controle(
    dossier_id: str,
    request: Request,
) -> dict:
    """Statut global du contrôle documentaire pour un dossier."""
    resultat = analyser_dossier_complet(dossier_id)

    return {
        "dossier_id": dossier_id,
        "statut": "bloque" if not resultat["peut_continuer"] else "ok",
        "total_anomalies": resultat["total_anomalies"],
        "anomalies_bloquantes": resultat["anomalies_bloquantes"],
        "par_gravite": resultat["par_gravite"],
        "peut_continuer": resultat["peut_continuer"],
    }