"""Routes de gestion de l'enlèvement terminal (Module 11)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, List

from ..models import TerminalEnlevement, new_id
from ..config import get_config
from ..logging_setup import audit, get_logger
from ..rbac import ADMINISTRATEUR, LECTEUR

log = get_logger("terminal")

router = APIRouter(prefix="/api/terminal", tags=["terminal"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Store en mémoire
# ───────────────────────────────────────────────────────────────

_terminal_store: dict[str, TerminalEnlevement] = {}


def _get_terminal_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'terminal_store'):
        request.app.state.terminal_store = {}
    return request.app.state.terminal_store


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic
# ───────────────────────────────────────────────────────────────

class TerminalEnlevementCreate(BaseModel):
    dossier_id: str
    numero_bl: str
    numero_conteneur: str
    date_demande: Optional[str] = None
    date_planifiee: Optional[str] = None
    statut: str = "demande"
    transporteur_id: str = ""
    camion_id: str = ""
    chauffeur_id: str = ""
    immatriculation: str = ""
    chauffeur_nom: str = ""
    chauffeur_permis: str = ""
    mainlevee_obtenue: bool = False
    bad_obtenu: bool = False
    frais_portuaires_payes: bool = False
    observations: str = ""


class TerminalEnlevementUpdate(BaseModel):
    dossier_id: Optional[str] = None
    numero_bl: Optional[str] = None
    numero_conteneur: Optional[str] = None
    date_demande: Optional[str] = None
    date_planifiee: Optional[str] = None
    statut: Optional[str] = None
    transporteur_id: Optional[str] = None
    camion_id: Optional[str] = None
    chauffeur_id: Optional[str] = None
    immatriculation: Optional[str] = None
    chauffeur_nom: Optional[str] = None
    chauffeur_permis: Optional[str] = None
    mainlevee_obtenue: Optional[bool] = None
    bad_obtenu: Optional[bool] = None
    frais_portuaires_payes: Optional[bool] = None
    date_sortie: Optional[str] = None
    justificatif_sortie: Optional[str] = None
    observations: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Routes CRUD
# ───────────────────────────────────────────────────────────────

@router.post("")
def create_enlevement(
    request: Request,
    enlevement: TerminalEnlevementCreate,
) -> dict:
    """Créer une demande d'enlèvement."""
    store = _get_terminal_store(request)
    enlevement_obj = TerminalEnlevement(
        id=new_id("term_"),
        dossier_id=enlevement.dossier_id,
        numero_bl=enlevement.numero_bl,
        numero_conteneur=enlevement.numero_conteneur,
        date_demande=enlevement.date_demande,
        date_planifiee=enlevement.date_planifiee,
        statut=enlevement.statut,
        transporteur_id=enlevement.transporteur_id,
        camion_id=enlevement.camion_id,
        chauffeur_id=enlevement.chauffeur_id,
        immatriculation=enlevement.immatriculation,
        chauffeur_nom=enlevement.chauffeur_nom,
        chauffeur_permis=enlevement.chauffeur_permis,
        mainlevee_obtenue=enlevement.mainlevee_obtenue,
        bad_obtenu=enlevement.bad_obtenu,
        frais_portuaires_payes=enlevement.frais_portuaires_payes,
        observations=enlevement.observations,
    )
    store[enlevement_obj.id] = enlevement_obj
    audit(cfg.log_dir, "enlevement_cree", dossier=enlevement.dossier_id, conteneur=enlevement.numero_conteneur)
    return enlevement_obj.model_dump()


@router.get("")
def list_enlevements(
    request: Request,
    dossier_id: Optional[str] = None,
) -> list[dict]:
    """Lister tous les enlèvements."""
    store = _get_terminal_store(request)
    enlevements = list(store.values())
    if dossier_id:
        enlevements = [e for e in enlevements if e.dossier_id == dossier_id]
    return [e.model_dump() for e in enlevements]


@router.get("/{enlevement_id}")
def get_enlevement(
    enlevement_id: str,
    request: Request,
) -> dict:
    """Obtenir un enlèvement spécifique."""
    store = _get_terminal_store(request)
    enlevement = store.get(enlevement_id)
    if not enlevement:
        raise HTTPException(404, "Enlèvement introuvable")
    return enlevement.model_dump()


@router.put("/{enlevement_id}")
def update_enlevement(
    enlevement_id: str,
    request: Request,
    enlevement_update: TerminalEnlevementUpdate,
) -> dict:
    """Mettre à jour un enlèvement."""
    store = _get_terminal_store(request)
    enlevement = store.get(enlevement_id)
    if not enlevement:
        raise HTTPException(404, "Enlèvement introuvable")

    update_data = enlevement_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(enlevement, key, value)

    audit(cfg.log_dir, "enlevement_modifie", cible=enlevement_id)
    return enlevement.model_dump()


@router.delete("/{enlevement_id}")
def delete_enlevement(
    enlevement_id: str,
    request: Request,
) -> dict:
    """Supprimer un enlèvement."""
    store = _get_terminal_store(request)
    if enlevement_id not in store:
        raise HTTPException(404, "Enlèvement introuvable")

    del store[enlevement_id]
    audit(cfg.log_dir, "enlevement_supprime", cible=enlevement_id)
    return {"deleted": True, "id": enlevement_id}


# ───────────────────────────────────────────────────────────────
# Routes workflow enlèvement
# ───────────────────────────────────────────────────────────────

@router.post("/{enlevement_id}/planifier")
def planifier_enlevement(
    enlevement_id: str,
    request: Request,
    date_planifiee: str,
    transporteur_id: str,
    camion_id: str,
    chauffeur_id: str,
    immatriculation: str,
    chauffeur_nom: str,
    chauffeur_permis: str,
) -> dict:
    """Planifier un enlèvement."""
    store = _get_terminal_store(request)
    enlevement = store.get(enlevement_id)
    if not enlevement:
        raise HTTPException(404, "Enlèvement introuvable")

    enlevement.date_planifiee = date_planifiee
    enlevement.transporteur_id = transporteur_id
    enlevement.camion_id = camion_id
    enlevement.chauffeur_id = chauffeur_id
    enlevement.immatriculation = immatriculation
    enlevement.chauffeur_nom = chauffeur_nom
    enlevement.chauffeur_permis = chauffeur_permis
    enlevement.statut = "planifie"
    audit(cfg.log_dir, "enlevement_planifie", conteneur=enlevement.numero_conteneur, date=date_planifiee)
    return enlevement.model_dump()


@router.post("/{enlevement_id}/autoriser_sortie")
def autoriser_sortie(
    enlevement_id: str,
    request: Request,
    mainlevee_obtenue: bool,
    bad_obtenu: bool,
    frais_portuaires_payes: bool,
    justificatif_sortie: str,
) -> dict:
    """Autoriser la sortie du conteneur du terminal."""
    store = _get_terminal_store(request)
    enlevement = store.get(enlevement_id)
    if not enlevement:
        raise HTTPException(404, "Enlèvement introuvable")

    if not (mainlevee_obtenue and bad_obtenu and frais_portuaires_payes):
        raise HTTPException(400, "Mainlevée, BAD et frais portuaires requis")

    enlevement.mainlevee_obtenue = mainlevee_obtenue
    enlevement.bad_obtenu = bad_obtenu
    enlevement.frais_portuaires_payes = frais_portuaires_payes
    enlevement.statut = "sortie_autorisee"
    enlevement.justificatif_sortie = justificatif_sortie
    audit(cfg.log_dir, "sortie_autorisee", conteneur=enlevement.numero_conteneur)
    return enlevement.model_dump()


@router.post("/{enlevement_id}/sortie")
def enregistrer_sortie(
    enlevement_id: str,
    request: Request,
    date_sortie: str,
) -> dict:
    """Enregistrer la sortie effective du terminal."""
    store = _get_terminal_store(request)
    enlevement = store.get(enlevement_id)
    if not enlevement:
        raise HTTPException(404, "Enlèvement introuvable")

    enlevement.date_sortie = date_sortie
    enlevement.statut = "sortis"
    audit(cfg.log_dir, "sortie_terminal", conteneur=enlevement.numero_conteneur, date=date_sortie)
    return enlevement.model_dump()