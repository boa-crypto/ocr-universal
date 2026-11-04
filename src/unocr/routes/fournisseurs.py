"""Routes de gestion des fournisseurs (Module 01)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import Fournisseur, new_id

log = get_logger("fournisseurs")

router = APIRouter(prefix="/api/fournisseurs", tags=["fournisseurs"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Store par défaut (en mémoire, remplacé par DB plus tard)
# ───────────────────────────────────────────────────────────────

_fournisseur_store: dict[str, Fournisseur] = {}


def _get_fournisseur_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'fournisseur_store'):
        request.app.state.fournisseur_store = {}
    return request.app.state.fournisseur_store


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic
# ───────────────────────────────────────────────────────────────

class FournisseurCreate(BaseModel):
    nom: str
    nom_commercial: str
    pays: str = ""  # code ISO 3166-1 alpha-2
    adresse: str = ""
    contact: str = ""
    telephone: str = ""
    email: str = ""
    nif: str = ""
    rc: str = ""
    notes: str = ""


class FournisseurUpdate(BaseModel):
    nom: Optional[str] = None
    nom_commercial: Optional[str] = None
    pays: Optional[str] = None
    adresse: Optional[str] = None
    contact: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    nif: Optional[str] = None
    rc: Optional[str] = None
    notes: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Routes CRUD
# ───────────────────────────────────────────────────────────────

@router.post("")
def create_fournisseur(
    request: Request,
    fournisseur: FournisseurCreate,
) -> dict:
    """Créer un nouveau fournisseur."""
    store = _get_fournisseur_store(request)
    fournisseur_obj = Fournisseur(
        id=new_id("fourn_"),
        nom=fournisseur.nom,
        nom_commercial=fournisseur.nom_commercial,
        pays=fournisseur.pays,
        adresse=fournisseur.adresse,
        contact=fournisseur.contact,
        telephone=fournisseur.telephone,
        email=fournisseur.email,
        nif=fournisseur.nif,
        rc=fournisseur.rc,
        notes=fournisseur.notes,
    )
    store[fournisseur_obj.id] = fournisseur_obj
    audit(cfg.log_dir, "fournisseur_cree", nom=fournisseur.nom)
    return fournisseur_obj.as_dict()


@router.get("")
def list_fournisseurs(
    request: Request,
) -> list[dict]:
    """Lister tous les fournisseurs."""
    store = _get_fournisseur_store(request)
    fournisseurs = list(store.values())
    return [f.as_dict() for f in fournisseurs]


@router.get("/{fournisseur_id}")
def get_fournisseur(
    fournisseur_id: str,
    request: Request,
) -> dict:
    """Obtenir un fournisseur spécifique."""
    store = _get_fournisseur_store(request)
    fournisseur = store.get(fournisseur_id)
    if not fournisseur:
        raise HTTPException(404, "Fournisseur introuvable")
    return fournisseur.as_dict()


@router.put("/{fournisseur_id}")
def update_fournisseur(
    fournisseur_id: str,
    request: Request,
    fournisseur_update: FournisseurUpdate,
) -> dict:
    """Mettre à jour un fournisseur."""
    store = _get_fournisseur_store(request)
    fournisseur = store.get(fournisseur_id)
    if not fournisseur:
        raise HTTPException(404, "Fournisseur introuvable")

    update_data = fournisseur_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(fournisseur, key, value)

    audit(cfg.log_dir, "fournisseur_modifie", cible=fournisseur_id)
    return fournisseur.as_dict()


@router.delete("/{fournisseur_id}")
def delete_fournisseur(
    fournisseur_id: str,
    request: Request,
) -> dict:
    """Supprimer un fournisseur."""
    store = _get_fournisseur_store(request)
    if fournisseur_id not in store:
        raise HTTPException(404, "Fournisseur introuvable")

    del store[fournisseur_id]
    audit(cfg.log_dir, "fournisseur_supprime", cible=fournisseur_id)
    return {"deleted": True, "id": fournisseur_id}
