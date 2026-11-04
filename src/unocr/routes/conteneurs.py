"""Routes de gestion des conteneurs (Module 06 - Suivi maritime)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import Conteneur, new_id

log = get_logger("conteneurs")

router = APIRouter(prefix="/api/conteneurs", tags=["conteneurs"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Store en mémoire
# ───────────────────────────────────────────────────────────────

_conteneur_store: dict[str, Conteneur] = {}


def _get_conteneur_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'conteneur_store'):
        request.app.state.conteneur_store = {}
    return request.app.state.conteneur_store


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic
# ───────────────────────────────────────────────────────────────

class ConteneurCreate(BaseModel):
    dossier_id: str
    numero_conteneur: str
    type_conteneur: str = ""
    poids: float = 0.0
    seal_number: str = ""
    statut: str = "reserve"  # reserve, charged, transit, arrived, discharged, available, waiting, picked_up, delivered
    position_actuelle: str = ""
    date_arrivee_port: Optional[str] = None
    date_depart_port: Optional[str] = None
    observations: str = ""


class ConteneurUpdate(BaseModel):
    dossier_id: Optional[str] = None
    numero_conteneur: Optional[str] = None
    type_conteneur: Optional[str] = None
    poids: Optional[float] = None
    seal_number: Optional[str] = None
    statut: Optional[str] = None
    position_actuelle: Optional[str] = None
    date_arrivee_port: Optional[str] = None
    date_depart_port: Optional[str] = None
    observations: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Routes CRUD
# ───────────────────────────────────────────────────────────────

@router.post("")
def create_conteneur(
    request: Request,
    conteneur: ConteneurCreate,
) -> dict:
    """Créer un nouveau conteneur."""
    store = _get_conteneur_store(request)
    conteneur_obj = Conteneur(
        id=new_id("cont_"),
        dossier_id=conteneur.dossier_id,
        numero_conteneur=conteneur.numero_conteneur,
        type_conteneur=conteneur.type_conteneur,
        poids=conteneur.poids,
        seal_number=conteneur.seal_number,
        statut=conteneur.statut,
        position_actuelle=conteneur.position_actuelle,
        date_arrivee_port=conteneur.date_arrivee_port,
        date_depart_port=conteneur.date_depart_port,
        observations=conteneur.observations,
    )
    store[conteneur_obj.id] = conteneur_obj
    audit(cfg.log_dir, "conteneur_cree", numero=conteneur.numero_conteneur, dossier=conteneur.dossier_id)
    return conteneur_obj.model_dump()


@router.get("")
def list_conteneurs(
    request: Request,
    dossier_id: Optional[str] = None,
) -> list[dict]:
    """Lister tous les conteneurs, optionnellement filtrés par dossier."""
    store = _get_conteneur_store(request)
    conteneurs = list(store.values())
    if dossier_id:
        conteneurs = [c for c in conteneurs if c.dossier_id == dossier_id]
    return [c.model_dump() for c in conteneurs]


@router.get("/{conteneur_id}")
def get_conteneur(
    conteneur_id: str,
    request: Request,
) -> dict:
    """Obtenir un conteneur spécifique."""
    store = _get_conteneur_store(request)
    conteneur = store.get(conteneur_id)
    if not conteneur:
        raise HTTPException(404, "Conteneur introuvable")
    return conteneur.model_dump()


@router.put("/{conteneur_id}")
def update_conteneur(
    conteneur_id: str,
    request: Request,
    conteneur_update: ConteneurUpdate,
) -> dict:
    """Mettre à jour un conteneur."""
    store = _get_conteneur_store(request)
    conteneur = store.get(conteneur_id)
    if not conteneur:
        raise HTTPException(404, "Conteneur introuvable")

    update_data = conteneur_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(conteneur, key, value)

    audit(cfg.log_dir, "conteneur_modifie", cible=conteneur_id)
    return conteneur.model_dump()


@router.delete("/{conteneur_id}")
def delete_conteneur(
    conteneur_id: str,
    request: Request,
) -> dict:
    """Supprimer un conteneur."""
    store = _get_conteneur_store(request)
    if conteneur_id not in store:
        raise HTTPException(404, "Conteneur introuvable")

    del store[conteneur_id]
    audit(cfg.log_dir, "conteneur_supprime", cible=conteneur_id)
    return {"deleted": True, "id": conteneur_id}
