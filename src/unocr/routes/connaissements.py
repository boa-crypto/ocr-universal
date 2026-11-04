"""Routes de gestion des connaissements (BL) et Bons à délivrer (Module 07)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import BonADelivrer, Connaissement, new_id

log = get_logger("connaissements")

router = APIRouter(prefix="/api/connaissements", tags=["connaissements"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Stores en mémoire
# ───────────────────────────────────────────────────────────────

_bl_store: dict[str, Connaissement] = {}
_bad_store: dict[str, BonADelivrer] = {}


def _get_bl_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'bl_store'):
        request.app.state.bl_store = {}
    return request.app.state.bl_store


def _get_bad_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'bad_store'):
        request.app.state.bad_store = {}
    return request.app.state.bad_store


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic - Connaissement
# ───────────────────────────────────────────────────────────────

class ConnaissementCreate(BaseModel):
    dossier_id: str
    numero_bl: str
    type_bl: str = ""  # original, telex, seaway
    date_emission: Optional[str] = None
    emetteur: str = ""
    emitant: str = ""
    chargeur: str = ""
    destinataire: str = ""
    notify_party: str = ""
    port_charge: str = ""
    port_decharge: str = ""
    marchandise: str = ""
    nombre_colis: int = 0
    poids_brut: float = 0.0
    poids_net: float = 0.0
    incoterm: str = ""
    devise: str = "EUR"
    valeur: float = 0.0
    originals_count: int = 0
    frais_maritimes: float = 0.0
    observations: str = ""


class ConnaissementUpdate(BaseModel):
    dossier_id: Optional[str] = None
    numero_bl: Optional[str] = None
    type_bl: Optional[str] = None
    date_emission: Optional[str] = None
    emetteur: Optional[str] = None
    emitant: Optional[str] = None
    chargeur: Optional[str] = None
    destinataire: Optional[str] = None
    notify_party: Optional[str] = None
    port_charge: Optional[str] = None
    port_decharge: Optional[str] = None
    marchandise: Optional[str] = None
    nombre_colis: Optional[int] = None
    poids_brut: Optional[float] = None
    poids_net: Optional[float] = None
    incoterm: Optional[str] = None
    devise: Optional[str] = None
    valeur: Optional[float] = None
    originals_count: Optional[int] = None
    originals_received: Optional[int] = None
    frais_maritimes: Optional[float] = None
    frais_payes: Optional[float] = None
    bad_recu: Optional[bool] = None
    bad_date: Optional[str] = None
    statut: Optional[str] = None
    observations: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic - Bon à Délivrer
# ───────────────────────────────────────────────────────────────

class BonADelivrerCreate(BaseModel):
    dossier_id: str
    numero_bl: str
    numero_bad: str
    emetteur: str = ""
    date_emission: Optional[str] = None
    valabilite: Optional[str] = None
    statut: str = "demandé"
    observations: str = ""


class BonADelivrerUpdate(BaseModel):
    dossier_id: Optional[str] = None
    numero_bl: Optional[str] = None
    numero_bad: Optional[str] = None
    emetteur: Optional[str] = None
    date_emission: Optional[str] = None
    valabilite: Optional[str] = None
    statut: Optional[str] = None
    date_obtention: Optional[str] = None
    observations: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Routes Connaissements (BL)
# ───────────────────────────────────────────────────────────────

@router.post("/bl")
def create_bl(
    request: Request,
    bl: ConnaissementCreate,
) -> dict:
    """Créer un nouveau connaissement."""
    store = _get_bl_store(request)
    bl_obj = Connaissement(
        id=new_id("bl_"),
        dossier_id=bl.dossier_id,
        numero_bl=bl.numero_bl,
        type_bl=bl.type_bl,
        date_emission=bl.date_emission,
        emetteur=bl.emetteur,
        emitant=bl.emitant,
        chargeur=bl.chargeur,
        destinataire=bl.destinataire,
        notify_party=bl.notify_party,
        port_charge=bl.port_charge,
        port_decharge=bl.port_decharge,
        marchandise=bl.marchandise,
        nombre_colis=bl.nombre_colis,
        poids_brut=bl.poids_brut,
        poids_net=bl.poids_net,
        incoterm=bl.incoterm,
        devise=bl.devise,
        valeur=bl.valeur,
        originals_count=bl.originals_count,
        frais_maritimes=bl.frais_maritimes,
        observations=bl.observations,
    )
    store[bl_obj.id] = bl_obj
    audit(cfg.log_dir, "bl_cree", numero=bl.numero_bl, dossier=bl.dossier_id)
    return bl_obj.model_dump()


@router.get("/bl")
def list_bl(
    request: Request,
    dossier_id: Optional[str] = None,
) -> list[dict]:
    """Lister tous les connaissements."""
    store = _get_bl_store(request)
    bls = list(store.values())
    if dossier_id:
        bls = [b for b in bls if b.dossier_id == dossier_id]
    return [b.model_dump() for b in bls]


@router.get("/bl/{bl_id}")
def get_bl(
    bl_id: str,
    request: Request,
) -> dict:
    """Obtenir un connaissement spécifique."""
    store = _get_bl_store(request)
    bl = store.get(bl_id)
    if not bl:
        raise HTTPException(404, "Connaissement introuvable")
    return bl.model_dump()


@router.put("/bl/{bl_id}")
def update_bl(
    bl_id: str,
    request: Request,
    bl_update: ConnaissementUpdate,
) -> dict:
    """Mettre à jour un connaissement."""
    store = _get_bl_store(request)
    bl = store.get(bl_id)
    if not bl:
        raise HTTPException(404, "Connaissement introuvable")

    update_data = bl_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(bl, key, value)

    audit(cfg.log_dir, "bl_modifie", cible=bl_id)
    return bl.model_dump()


@router.delete("/bl/{bl_id}")
def delete_bl(
    bl_id: str,
    request: Request,
) -> dict:
    """Supprimer un connaissement."""
    store = _get_bl_store(request)
    if bl_id not in store:
        raise HTTPException(404, "Connaissement introuvable")

    del store[bl_id]
    audit(cfg.log_dir, "bl_supprime", cible=bl_id)
    return {"deleted": True, "id": bl_id}


# ───────────────────────────────────────────────────────────────
# Routes Bons à Délivrer (BAD)
# ───────────────────────────────────────────────────────────────

@router.post("/bad")
def create_bad(
    request: Request,
    bad: BonADelivrerCreate,
) -> dict:
    """Créer un nouveau bon à délivrer."""
    store = _get_bad_store(request)
    bad_obj = BonADelivrer(
        id=new_id("bad_"),
        dossier_id=bad.dossier_id,
        numero_bl=bad.numero_bl,
        numero_bad=bad.numero_bad,
        emetteur=bad.emetteur,
        date_emission=bad.date_emission,
        valabilite=bad.valabilite,
        statut=bad.statut,
        observations=bad.observations,
    )
    store[bad_obj.id] = bad_obj
    audit(cfg.log_dir, "bad_cree", numero=bad.numero_bad, dossier=bad.dossier_id)
    return bad_obj.model_dump()


@router.get("/bad")
def list_bad(
    request: Request,
    dossier_id: Optional[str] = None,
) -> list[dict]:
    """Lister tous les bons à délivrer."""
    store = _get_bad_store(request)
    bads = list(store.values())
    if dossier_id:
        bads = [b for b in bads if b.dossier_id == dossier_id]
    return [b.model_dump() for b in bads]


@router.get("/bad/{bad_id}")
def get_bad(
    bad_id: str,
    request: Request,
) -> dict:
    """Obtenir un bon à délivrer spécifique."""
    store = _get_bad_store(request)
    bad = store.get(bad_id)
    if not bad:
        raise HTTPException(404, "Bon à délivrer introuvable")
    return bad.model_dump()


@router.put("/bad/{bad_id}")
def update_bad(
    bad_id: str,
    request: Request,
    bad_update: BonADelivrerUpdate,
) -> dict:
    """Mettre à jour un bon à délivrer."""
    store = _get_bad_store(request)
    bad = store.get(bad_id)
    if not bad:
        raise HTTPException(404, "Bon à délivrer introuvable")

    update_data = bad_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(bad, key, value)

    audit(cfg.log_dir, "bad_modifie", cible=bad_id)
    return bad.model_dump()


@router.delete("/bad/{bad_id}")
def delete_bad(
    bad_id: str,
    request: Request,
) -> dict:
    """Supprimer un bon à délivrer."""
    store = _get_bad_store(request)
    if bad_id not in store:
        raise HTTPException(404, "Bon à délivrer introuvable")

    del store[bad_id]
    audit(cfg.log_dir, "bad_supprime", cible=bad_id)
    return {"deleted": True, "id": bad_id}
