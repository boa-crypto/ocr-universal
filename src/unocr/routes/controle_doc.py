"""Routes de contrôle documentaire intelligent (Module 04)."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import get_config
from ..controle_documentaire import ControleDocumentaireEngine, analyser_dossier_complet
from ..controle_resolutions import (
    accepter_risque,
    revoquer_resolution,
    store_resolutions,
)
from ..logging_setup import audit, get_logger
from ..rbac import LECTEUR, SUPERVISEUR
from .dependencies import _exige, _exige_dossier, _utilisateur_ou_ouvert

log = get_logger("controle_doc")
router = APIRouter(prefix="/api/controle", tags=["controle-documentaire"])


class ControleRequest(BaseModel):
    dossier_id: str = Field(min_length=1, max_length=128)


class ResolutionRequest(BaseModel):
    regle: str = Field(min_length=1, max_length=200)
    champ: str = ""
    documents: Optional[list[str]] = None
    action: Literal["accepter_risque", "corriger"] = "accepter_risque"
    motif: str = Field(default="", max_length=2000)


def _cfg(request: Request):
    return getattr(request.app.state, "cfg", None) or get_config()


def _acteur(request: Request) -> str:
    return _utilisateur_ou_ouvert(request).nom


def _anomalie_dict(anomalie) -> dict:
    return {
        "type": anomalie.type_anomalie, "regle": anomalie.regle,
        "gravite": anomalie.gravite, "message": anomalie.message,
        "documents": anomalie.documents_concernes, "champ": anomalie.champ,
        "valeurs": anomalie.valeurs,
    }


@router.post("/analyser")
def analyser_dossier(request: Request, body: ControleRequest,
                     current_user=Depends(_exige(LECTEUR))) -> dict:
    _exige_dossier(body.dossier_id, request)
    resultat = analyser_dossier_complet(body.dossier_id, _cfg(request))
    audit(_cfg(request).log_dir, "controle_documentaire_lance",
          dossier_id=body.dossier_id, acteur=_acteur(request),
          total_anomalies=resultat["total_anomalies"],
          bloquantes=resultat["anomalies_bloquantes"])
    return resultat


@router.get("/regles")
def lister_regles() -> dict:
    from ..controle_documentaire import REGLES_COMPARAISON, Gravite, TypeAnomalie
    return {
        "regles": [
            {"nom": nom, "champs": regle["champs"], "types_documents": regle["types_docs"],
             "gravite": regle["gravite"], "message": regle["message"],
             "tolerance": regle.get("tolerance", 0)}
            for nom, regle in REGLES_COMPARAISON.items()
        ],
        "types_anomalie": [v for v in vars(TypeAnomalie).values() if isinstance(v, str)],
        "gravites": [v for v in vars(Gravite).values() if isinstance(v, str)],
    }


@router.get("/{dossier_id}/anomalies")
def get_anomalies_dossier(dossier_id: str, request: Request,
                          current_user=Depends(_exige(LECTEUR))) -> dict:
    _exige_dossier(dossier_id, request)
    resultat = analyser_dossier_complet(dossier_id, _cfg(request))
    return {"dossier_id": dossier_id, "anomalies": resultat["anomalies"],
            "total_anomalies": resultat["total_anomalies"],
            "anomalies_acceptees": resultat["anomalies_acceptees"]}


@router.post("/{dossier_id}/resoudre")
def resoudre_anomalie(dossier_id: str, request: Request, body: ResolutionRequest,
                      current_user=Depends(_exige(SUPERVISEUR))) -> dict:
    """Accepter un risque de façon tracée, ou confirmer une correction constatée.

    Une correction encore détectée n'est jamais marquée résolue d'office.
    L'acteur vient de la session, jamais du corps de requête.
    """
    _exige_dossier(dossier_id, request)
    cfg = _cfg(request)
    acteur = _acteur(request)
    courantes = [_anomalie_dict(a) for a in ControleDocumentaireEngine(cfg).analyser_dossier(dossier_id)]
    candidates = [a for a in courantes if a["regle"] == body.regle]
    if body.champ:
        candidates = [a for a in candidates if a["champ"] == body.champ]
    if body.documents is not None:
        attendus = sorted(body.documents)
        candidates = [a for a in candidates if sorted(a["documents"]) == attendus]

    if body.action == "corriger":
        if candidates:
            raise HTTPException(409, "Anomalie encore détectée : corrigez la source puis relancez le contrôle")
        audit(cfg.log_dir, "anomalie_corrigee_confirmee", dossier_id=dossier_id,
              regle=body.regle, acteur=acteur)
        return {"ok": True, "message": "Anomalie absente du contrôle courant", "resolution": None}

    if not candidates:
        raise HTTPException(404, "Anomalie introuvable dans le contrôle courant")
    if len(candidates) > 1:
        raise HTTPException(409, "Précisez le champ et les documents pour lever l'ambiguïté")
    resolution = accepter_risque(cfg, dossier_id, candidates[0], body.motif, acteur)
    audit(cfg.log_dir, "anomalie_risque_accepte", dossier_id=dossier_id,
          regle=body.regle, resolution=resolution.id, acteur=acteur, motif=resolution.motif)
    return {"ok": True, "message": "Acceptation de risque enregistrée",
            "resolution": resolution.model_dump()}


@router.get("/{dossier_id}/resolutions")
def lister_resolutions(dossier_id: str, request: Request,
                       current_user=Depends(_exige(LECTEUR))) -> list[dict]:
    _exige_dossier(dossier_id, request)
    return [r.model_dump() for r in store_resolutions(_cfg(request)).values()
            if r.dossier_id == dossier_id]


@router.delete("/{dossier_id}/resolutions/{resolution_id}")
def retirer_resolution(dossier_id: str, resolution_id: str, request: Request,
                       current_user=Depends(_exige(SUPERVISEUR))) -> dict:
    _exige_dossier(dossier_id, request)
    resolution = revoquer_resolution(_cfg(request), dossier_id, resolution_id)
    audit(_cfg(request).log_dir, "anomalie_resolution_revoquee", dossier_id=dossier_id,
          resolution=resolution_id, acteur=_acteur(request))
    return {"ok": True, "resolution": resolution.model_dump()}


@router.get("/{dossier_id}/statut")
def statut_controle(dossier_id: str, request: Request,
                    current_user=Depends(_exige(LECTEUR))) -> dict:
    _exige_dossier(dossier_id, request)
    resultat = analyser_dossier_complet(dossier_id, _cfg(request))
    return {
        "dossier_id": dossier_id,
        "statut": "bloque" if not resultat["peut_continuer"] else "ok",
        "total_anomalies": resultat["total_anomalies"],
        "total_detectees": resultat["total_detectees"],
        "anomalies_acceptees": resultat["anomalies_acceptees"],
        "anomalies_bloquantes": resultat["anomalies_bloquantes"],
        "par_gravite": resultat["par_gravite"],
        "peut_continuer": resultat["peut_continuer"],
    }
