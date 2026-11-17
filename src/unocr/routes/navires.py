"""Routes de gestion des navires (Module 06 - Suivi maritime)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import Navire, new_id

log = get_logger("navires")

router = APIRouter(prefix="/api/navires", tags=["navires"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Store en mémoire (remplacé par DB plus tard)
# ───────────────────────────────────────────────────────────────

_navire_store: dict[str, Navire] = {}


def _get_navire_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'navire_store'):
        request.app.state.navire_store = {}
    return request.app.state.navire_store


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic
# ───────────────────────────────────────────────────────────────

class NavireCreate(BaseModel):
    nom: str
    numero_imo: str = ""
    compagnie: str = ""
    pays_immatri: str = ""
    type_navire: str = ""
    notes: str = ""


class NavireUpdate(BaseModel):
    nom: Optional[str] = None
    numero_imo: Optional[str] = None
    compagnie: Optional[str] = None
    pays_immatri: Optional[str] = None
    type_navire: Optional[str] = None
    notes: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Routes CRUD
# ───────────────────────────────────────────────────────────────

@router.post("")
def create_navire(
    request: Request,
    navire: NavireCreate,
) -> dict:
    """Créer un nouveau navire."""
    store = _get_navire_store(request)
    navire_obj = Navire(
        id=new_id("nav_"),
        nom=navire.nom,
        numero_imo=navire.numero_imo,
        compagnie=navire.compagnie,
        pays_immatri=navire.pays_immatri,
        type_navire=navire.type_navire,
        notes=navire.notes,
    )
    store[navire_obj.id] = navire_obj
    audit(cfg.log_dir, "navire_cree", nom=navire.nom, imo=navire.numero_imo)
    return navire_obj.model_dump()


@router.get("")
def list_navires(
    request: Request,
) -> list[dict]:
    """Lister tous les navires."""
    store = _get_navire_store(request)
    navires = list(store.values())
    return [n.model_dump() for n in navires]


@router.get("/{navire_id}")
def get_navire(
    navire_id: str,
    request: Request,
) -> dict:
    """Obtenir un navire spécifique."""
    store = _get_navire_store(request)
    navire = store.get(navire_id)
    if not navire:
        raise HTTPException(404, "Navire introuvable")
    return navire.model_dump()


@router.put("/{navire_id}")
def update_navire(
    navire_id: str,
    request: Request,
    navire_update: NavireUpdate,
) -> dict:
    """Mettre à jour un navire."""
    store = _get_navire_store(request)
    navire = store.get(navire_id)
    if not navire:
        raise HTTPException(404, "Navire introuvable")

    update_data = navire_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(navire, key, value)

    audit(cfg.log_dir, "navire_modifie", cible=navire_id)
    return navire.model_dump()


@router.delete("/{navire_id}")
def delete_navire(
    navire_id: str,
    request: Request,
) -> dict:
    """Supprimer un navire."""
    store = _get_navire_store(request)
    if navire_id not in store:
        raise HTTPException(404, "Navire introuvable")

    del store[navire_id]
    audit(cfg.log_dir, "navire_supprime", cible=navire_id)
    return {"deleted": True, "id": navire_id}
