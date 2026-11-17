"""Routes de gestion des connaissements (BL) et Bons à délivrer (Module 07)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError

from ..business_links import exiger_dossier
from ..business_store import BusinessStore
from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import BonADelivrer, Connaissement, Expeditions, TerminalEnlevement, new_id
from .dependencies import _exige_dossier, _exige_objet_dossier, _filtre_dossiers

log = get_logger("connaissements")

router = APIRouter(prefix="/api/connaissements", tags=["connaissements"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Stockage SQLite local, partagé avec les autres modules métier.
# ───────────────────────────────────────────────────────────────

def _get_bl_store(request: Request) -> BusinessStore[Connaissement]:
    return BusinessStore(cfg.data_dir / "metier.sqlite3", "connaissement", Connaissement)


def _get_bad_store(request: Request) -> BusinessStore[BonADelivrer]:
    return BusinessStore(cfg.data_dir / "metier.sqlite3", "bon_a_delivrer", BonADelivrer)


def _valider_bl(bl: Connaissement) -> None:
    if not bl.dossier_id.strip() or not bl.numero_bl.strip():
        raise HTTPException(422, "Dossier et numéro de connaissement sont obligatoires")
    if bl.nombre_colis < 0 or bl.originals_count < 0 or bl.originals_received < 0:
        raise HTTPException(422, "Les quantités ne peuvent pas être négatives")
    if bl.originals_received > bl.originals_count:
        raise HTTPException(422, "Originaux reçus supérieurs aux originaux émis")
    if bl.poids_brut < 0 or bl.poids_net < 0 or bl.valeur < 0 or bl.frais_maritimes < 0:
        raise HTTPException(422, "Poids, valeur et frais ne peuvent pas être négatifs")


def _valider_bad(bad: BonADelivrer) -> None:
    if not bad.dossier_id.strip() or not bad.numero_bl.strip() or not bad.numero_bad.strip():
        raise HTTPException(422, "Dossier, numéro de BL et numéro de BAD sont obligatoires")


def _bl_existant(transaction: BusinessStore, dossier_id: str, numero_bl: str) -> bool:
    return any(
        bl.dossier_id == dossier_id and bl.numero_bl == numero_bl
        for bl in transaction.related("connaissement", Connaissement).values()
    )


def _bl_reference(transaction: BusinessStore, numero_bl: str) -> bool:
    if any(b.numero_bl == numero_bl for b in transaction.related("bon_a_delivrer", BonADelivrer).values()):
        return True
    if any(e.numero_bl == numero_bl for e in transaction.related("expedition", Expeditions).values()):
        return True
    return any(e.numero_bl == numero_bl for e in transaction.related("terminal", TerminalEnlevement).values())


def _aliases_update(data: dict) -> dict:
    """Accepte les noms ASCII historiques et les mappe vers le modèle métier."""
    if "frais_payes" in data:
        data["frais_payés"] = data.pop("frais_payes")
    if "bad_recu" in data:
        data["bad_reçu"] = data.pop("bad_recu")
    return data


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
    _exige_dossier(bl.dossier_id, request)
    bl_obj = Connaissement(id=new_id("bl_"), **bl.model_dump())
    _valider_bl(bl_obj)
    store = _get_bl_store(request)
    with store.transaction() as transaction:
        exiger_dossier(cfg, bl_obj.dossier_id)
        transaction[bl_obj.id] = bl_obj
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
    return [b.model_dump() for b in _filtre_dossiers(request, bls)]


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
    _exige_objet_dossier(request, bl)
    return bl.model_dump()


@router.put("/bl/{bl_id}")
def update_bl(
    bl_id: str,
    request: Request,
    bl_update: ConnaissementUpdate,
) -> dict:
    """Mettre à jour un connaissement."""
    store = _get_bl_store(request)
    with store.transaction() as transaction:
        bl = transaction.get(bl_id)
        if not bl:
            raise HTTPException(404, "Connaissement introuvable")
        _exige_objet_dossier(request, bl)

        update_data = _aliases_update(bl_update.model_dump(exclude_unset=True))
        try:
            candidate = Connaissement.model_validate({**bl.model_dump(), **update_data})
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
        _valider_bl(candidate)
        _exige_objet_dossier(request, candidate)
        exiger_dossier(cfg, candidate.dossier_id)
        if (candidate.dossier_id != bl.dossier_id or candidate.numero_bl != bl.numero_bl) and _bl_reference(transaction, bl.numero_bl):
            raise HTTPException(409, "Impossible de changer le dossier ou le numéro : ce connaissement est référencé")
        transaction[bl_id] = candidate
    audit(cfg.log_dir, "bl_modifie", cible=bl_id)
    return candidate.model_dump()


@router.delete("/bl/{bl_id}")
def delete_bl(
    bl_id: str,
    request: Request,
) -> dict:
    """Supprimer un connaissement."""
    store = _get_bl_store(request)
    with store.transaction() as transaction:
        bl = transaction.get(bl_id)
        if not bl:
            raise HTTPException(404, "Connaissement introuvable")
        _exige_objet_dossier(request, bl)
        if _bl_reference(transaction, bl.numero_bl):
            raise HTTPException(409, "Connaissement référencé par un BAD, une expédition ou un enlèvement : suppression refusée")
        del transaction[bl_id]
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
    _exige_dossier(bad.dossier_id, request)
    bad_obj = BonADelivrer(id=new_id("bad_"), **bad.model_dump())
    _valider_bad(bad_obj)
    store = _get_bad_store(request)
    with store.transaction() as transaction:
        exiger_dossier(cfg, bad_obj.dossier_id)
        if not _bl_existant(transaction, bad_obj.dossier_id, bad_obj.numero_bl):
            raise HTTPException(422, "Le BAD doit référencer un connaissement existant du même dossier")
        transaction[bad_obj.id] = bad_obj
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
    return [b.model_dump() for b in _filtre_dossiers(request, bads)]


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
    _exige_objet_dossier(request, bad)
    return bad.model_dump()


@router.put("/bad/{bad_id}")
def update_bad(
    bad_id: str,
    request: Request,
    bad_update: BonADelivrerUpdate,
) -> dict:
    """Mettre à jour un bon à délivrer."""
    store = _get_bad_store(request)
    with store.transaction() as transaction:
        bad = transaction.get(bad_id)
        if not bad:
            raise HTTPException(404, "Bon à délivrer introuvable")
        _exige_objet_dossier(request, bad)

        update_data = bad_update.model_dump(exclude_unset=True)
        try:
            candidate = BonADelivrer.model_validate({**bad.model_dump(), **update_data})
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
        _valider_bad(candidate)
        _exige_objet_dossier(request, candidate)
        exiger_dossier(cfg, candidate.dossier_id)
        if not _bl_existant(transaction, candidate.dossier_id, candidate.numero_bl):
            raise HTTPException(422, "Le BAD doit référencer un connaissement existant du même dossier")
        transaction[bad_id] = candidate
    audit(cfg.log_dir, "bad_modifie", cible=bad_id)
    return candidate.model_dump()


@router.delete("/bad/{bad_id}")
def delete_bad(
    bad_id: str,
    request: Request,
) -> dict:
    """Supprimer un bon à délivrer."""
    store = _get_bad_store(request)
    with store.transaction() as transaction:
        bad = transaction.get(bad_id)
        if not bad:
            raise HTTPException(404, "Bon à délivrer introuvable")
        _exige_objet_dossier(request, bad)
        del transaction[bad_id]
    audit(cfg.log_dir, "bad_supprime", cible=bad_id)
    return {"deleted": True, "id": bad_id}
