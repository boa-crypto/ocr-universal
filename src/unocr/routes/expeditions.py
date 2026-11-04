"""Routes de gestion des expéditions (Module 06 - Suivi maritime)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError

from ..business_links import exiger_dossier
from ..business_store import BusinessStore
from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import Expeditions, new_id

log = get_logger("expeditions")

router = APIRouter(prefix="/api/expeditions", tags=["expeditions"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Stockage SQLite local, partagé avec les autres modules métier.
# ───────────────────────────────────────────────────────────────


def _get_expedition_store(request: Request) -> BusinessStore[Expeditions]:
    return BusinessStore(cfg.data_dir / "metier.sqlite3", "expedition", Expeditions)


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic
# ───────────────────────────────────────────────────────────────

class ExpeditionCreate(BaseModel):
    dossier_id: str
    navire: str = ""
    porte_chargement: str = ""
    porte_destination: str = ""
    ETA: Optional[str] = None
    arrivee_effective: Optional[str] = None
    numero_bl: str = ""
    type_bl: str = ""
    date_emission: Optional[str] = None
    nom_gestionnaire: str = ""
    priorite: str = "normale"
    observations: str = ""


class ExpeditionUpdate(BaseModel):
    dossier_id: Optional[str] = None
    navire: Optional[str] = None
    porte_chargement: Optional[str] = None
    porte_destination: Optional[str] = None
    ETA: Optional[str] = None
    arrivee_effective: Optional[str] = None
    numero_bl: Optional[str] = None
    type_bl: Optional[str] = None
    date_emission: Optional[str] = None
    nom_gestionnaire: Optional[str] = None
    priorite: Optional[str] = None
    observations: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Routes CRUD
# ───────────────────────────────────────────────────────────────

@router.post("")
def create_expedition(
    request: Request,
    expedition: ExpeditionCreate,
) -> dict:
    """Créer une nouvelle expédition."""
    store = _get_expedition_store(request)
    expedition_obj = Expeditions(
        id=new_id("exp_"),
        dossier_id=expedition.dossier_id,
        navire=expedition.navire,
        porte_chargement=expedition.porte_chargement,
        porte_destination=expedition.porte_destination,
        ETA=expedition.ETA,
        arrivee_effective=expedition.arrivee_effective,
        numero_bl=expedition.numero_bl,
        type_bl=expedition.type_bl,
        date_emission=expedition.date_emission,
        nom_gestionnaire=expedition.nom_gestionnaire,
        priorite=expedition.priorite,
        observations=expedition.observations,
    )
    with store.transaction() as transaction:
        exiger_dossier(cfg, expedition_obj.dossier_id)
        transaction[expedition_obj.id] = expedition_obj
    audit(cfg.log_dir, "expedition_cree", dossier=expedition.dossier_id, navire=expedition.navire)
    return expedition_obj.model_dump()


@router.get("")
def list_expeditions(
    request: Request,
    dossier_id: Optional[str] = None,
) -> list[dict]:
    """Lister toutes les expéditions, optionnellement filtrées par dossier."""
    store = _get_expedition_store(request)
    expeditions = list(store.values())
    if dossier_id:
        expeditions = [e for e in expeditions if e.dossier_id == dossier_id]
    return [e.model_dump() for e in expeditions]


@router.get("/{expedition_id}")
def get_expedition(
    expedition_id: str,
    request: Request,
) -> dict:
    """Obtenir une expédition spécifique."""
    store = _get_expedition_store(request)
    expedition = store.get(expedition_id)
    if not expedition:
        raise HTTPException(404, "Expédition introuvable")
    return expedition.model_dump()


@router.put("/{expedition_id}")
def update_expedition(
    expedition_id: str,
    request: Request,
    expedition_update: ExpeditionUpdate,
) -> dict:
    """Mettre à jour une expédition."""
    store = _get_expedition_store(request)
    with store.transaction() as transaction:
        expedition = transaction.get(expedition_id)
        if not expedition:
            raise HTTPException(404, "Expédition introuvable")
        update_data = expedition_update.model_dump(exclude_unset=True)
        try:
            expedition = Expeditions.model_validate({**expedition.model_dump(), **update_data})
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
        exiger_dossier(cfg, expedition.dossier_id)
        transaction[expedition_id] = expedition

    audit(cfg.log_dir, "expedition_modifie", cible=expedition_id)
    return expedition.model_dump()


@router.delete("/{expedition_id}")
def delete_expedition(
    expedition_id: str,
    request: Request,
) -> dict:
    """Supprimer une expédition."""
    store = _get_expedition_store(request)
    if expedition_id not in store:
        raise HTTPException(404, "Expédition introuvable")

    del store[expedition_id]
    audit(cfg.log_dir, "expedition_supprime", cible=expedition_id)
    return {"deleted": True, "id": expedition_id}
