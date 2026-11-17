"""Routes de gestion des conteneurs (Module 06 - Suivi maritime)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError

from ..business_links import exiger_dossier
from ..business_store import BusinessStore
from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import Conteneur, TerminalEnlevement, new_id
from .dependencies import _exige_dossier, _exige_objet_dossier, _filtre_dossiers

log = get_logger("conteneurs")

router = APIRouter(prefix="/api/conteneurs", tags=["conteneurs"])

cfg = get_config()

STATUTS_CONTENEUR = {
    "reserve", "charged", "transit", "arrived", "discharged",
    "available", "waiting", "picked_up", "delivered",
}


# ───────────────────────────────────────────────────────────────
# Stockage SQLite local, partagé avec les autres modules métier.
# ───────────────────────────────────────────────────────────────

def _get_conteneur_store(request: Request) -> BusinessStore[Conteneur]:
    return BusinessStore(cfg.data_dir / "metier.sqlite3", "conteneur", Conteneur)


def _valider(conteneur: Conteneur) -> None:
    if not conteneur.dossier_id.strip() or not conteneur.numero_conteneur.strip():
        raise HTTPException(422, "Dossier et numéro de conteneur sont obligatoires")
    if conteneur.statut not in STATUTS_CONTENEUR:
        raise HTTPException(422, "Statut de conteneur invalide")
    if conteneur.poids < 0:
        raise HTTPException(422, "Le poids ne peut pas être négatif")


def _utilise_par_terminal(transaction: BusinessStore[Conteneur], numero: str) -> bool:
    return any(
        e.numero_conteneur == numero
        for e in transaction.related("terminal", TerminalEnlevement).values()
    )


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic
# ───────────────────────────────────────────────────────────────

class ConteneurCreate(BaseModel):
    dossier_id: str
    numero_conteneur: str
    type_conteneur: str = ""
    poids: float = 0.0
    seal_number: str = ""
    statut: str = "reserve"
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
    _exige_dossier(conteneur.dossier_id, request)
    conteneur_obj = Conteneur(
        id=new_id("cont_"),
        **conteneur.model_dump(),
    )
    _valider(conteneur_obj)
    store = _get_conteneur_store(request)
    with store.transaction() as transaction:
        exiger_dossier(cfg, conteneur_obj.dossier_id)
        transaction[conteneur_obj.id] = conteneur_obj
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
    return [c.model_dump() for c in _filtre_dossiers(request, conteneurs)]


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
    _exige_objet_dossier(request, conteneur)
    return conteneur.model_dump()


@router.put("/{conteneur_id}")
def update_conteneur(
    conteneur_id: str,
    request: Request,
    conteneur_update: ConteneurUpdate,
) -> dict:
    """Mettre à jour un conteneur."""
    store = _get_conteneur_store(request)
    with store.transaction() as transaction:
        conteneur = transaction.get(conteneur_id)
        if not conteneur:
            raise HTTPException(404, "Conteneur introuvable")
        _exige_objet_dossier(request, conteneur)

        update_data = conteneur_update.model_dump(exclude_unset=True)
        try:
            candidate = Conteneur.model_validate({**conteneur.model_dump(), **update_data})
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
        _valider(candidate)
        _exige_objet_dossier(request, candidate)
        exiger_dossier(cfg, candidate.dossier_id)
        if candidate.dossier_id != conteneur.dossier_id and _utilise_par_terminal(transaction, conteneur.numero_conteneur):
            raise HTTPException(409, "Impossible de changer le dossier : un enlèvement terminal utilise ce conteneur")
        if candidate.numero_conteneur != conteneur.numero_conteneur and _utilise_par_terminal(transaction, conteneur.numero_conteneur):
            raise HTTPException(409, "Impossible de changer le numéro : un enlèvement terminal utilise ce conteneur")
        transaction[conteneur_id] = candidate
    audit(cfg.log_dir, "conteneur_modifie", cible=conteneur_id)
    return candidate.model_dump()


@router.delete("/{conteneur_id}")
def delete_conteneur(
    conteneur_id: str,
    request: Request,
) -> dict:
    """Supprimer un conteneur."""
    store = _get_conteneur_store(request)
    with store.transaction() as transaction:
        conteneur = transaction.get(conteneur_id)
        if not conteneur:
            raise HTTPException(404, "Conteneur introuvable")
        _exige_objet_dossier(request, conteneur)
        if _utilise_par_terminal(transaction, conteneur.numero_conteneur):
            raise HTTPException(409, "Conteneur utilisé par un enlèvement terminal : suppression refusée")
        del transaction[conteneur_id]
    audit(cfg.log_dir, "conteneur_supprime", cible=conteneur_id)
    return {"deleted": True, "id": conteneur_id}
