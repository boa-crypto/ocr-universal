"""Routes de gestion du transport et livraison (Module 12)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, List

from ..models import Transporteur, Camion, Livraison, new_id
from ..config import get_config
from ..logging_setup import audit, get_logger
from ..rbac import ADMINISTRATEUR, LECTEUR

log = get_logger("transport")

router = APIRouter(prefix="/api/transport", tags=["transport"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Stores en mémoire
# ───────────────────────────────────────────────────────────────

_transporteur_store: dict[str, Transporteur] = {}
_camion_store: dict[str, Camion] = {}
_livraison_store: dict[str, Livraison] = {}


def _get_transporteur_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'transporteur_store'):
        request.app.state.transporteur_store = {}
    return request.app.state.transporteur_store


def _get_camion_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'camion_store'):
        request.app.state.camion_store = {}
    return request.app.state.camion_store


def _get_livraison_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'livraison_store'):
        request.app.state.livraison_store = {}
    return request.app.state.livraison_store


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic - Transporteur
# ───────────────────────────────────────────────────────────────

class TransporteurCreate(BaseModel):
    nom: str
    raison_sociale: str = ""
    nif: str = ""
    rc: str = ""
    adresse: str = ""
    telephone: str = ""
    email: str = ""
    conducteur_principal: str = ""
    permis_transport: str = ""
    statut: str = "actif"
    notes: str = ""


class TransporteurUpdate(BaseModel):
    nom: Optional[str] = None
    raison_sociale: Optional[str] = None
    nif: Optional[str] = None
    rc: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    conducteur_principal: Optional[str] = None
    permis_transport: Optional[str] = None
    statut: Optional[str] = None
    notes: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic - Camion
# ───────────────────────────────────────────────────────────────

class CamionCreate(BaseModel):
    transporteur_id: str
    immatriculation: str
    marque_modele: str = ""
    capacite: str = ""
    annee: int = 0
    assurance_valide: bool = True
    technique_valide: bool = True
    statut: str = "disponible"
    chauffeur_id: str = ""


class CamionUpdate(BaseModel):
    transporteur_id: Optional[str] = None
    immatriculation: Optional[str] = None
    marque_modele: Optional[str] = None
    capacite: Optional[str] = None
    annee: Optional[int] = None
    assurance_valide: Optional[bool] = None
    technique_valide: Optional[bool] = None
    statut: Optional[str] = None
    chauffeur_id: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic - Livraison
# ───────────────────────────────────────────────────────────────

class LivraisonCreate(BaseModel):
    dossier_id: str
    transport_id: str = ""
    client_id: str = ""
    transporteur_id: str = ""
    camion_id: str = ""
    chauffeur_id: str = ""
    lieu_livraison: str = ""
    date_depart: Optional[str] = None
    date_prevue: Optional[str] = None
    date_reelle: Optional[str] = None
    statut: str = "planifie"
    reserves_eventuelles: str = ""
    observations: str = ""


class LivraisonUpdate(BaseModel):
    dossier_id: Optional[str] = None
    transport_id: Optional[str] = None
    client_id: Optional[str] = None
    transporteur_id: Optional[str] = None
    camion_id: Optional[str] = None
    chauffeur_id: Optional[str] = None
    lieu_livraison: Optional[str] = None
    date_depart: Optional[str] = None
    date_prevue: Optional[str] = None
    date_reelle: Optional[str] = None
    statut: Optional[str] = None
    reserves_eventuelles: Optional[str] = None
    preuve_livraison_signee: Optional[bool] = None
    date_signature: Optional[str] = None
    observations: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Routes Transporteurs
# ───────────────────────────────────────────────────────────────

@router.post("/transporteurs")
def create_transporteur(
    request: Request,
    transporteur: TransporteurCreate,
) -> dict:
    """Créer un nouveau transporteur."""
    store = _get_transporteur_store(request)
    t = Transporteur(
        id=new_id("transp_"),
        nom=transporteur.nom,
        raison_sociale=transporteur.raison_sociale,
        nif=transporteur.nif,
        rc=transporteur.rc,
        adresse=transporteur.adresse,
        telephone=transporteur.telephone,
        email=transporteur.email,
        conducteur_principal=transporteur.conducteur_principal,
        permis_transport=transporteur.permis_transport,
        statut=transporteur.statut,
        notes=transporteur.notes,
    )
    store[t.id] = t
    audit(cfg.log_dir, "transporteur_cree", nom=transporteur.nom)
    return t.model_dump()


@router.get("/transporteurs")
def list_transporteurs(
    request: Request,
) -> list[dict]:
    """Lister tous les transporteurs."""
    store = _get_transporteur_store(request)
    return [t.model_dump() for t in store.values()]


@router.get("/transporteurs/{transporteur_id}")
def get_transporteur(
    transporteur_id: str,
    request: Request,
) -> dict:
    """Obtenir un transporteur."""
    store = _get_transporteur_store(request)
    t = store.get(transporteur_id)
    if not t:
        raise HTTPException(404, "Transporteur introuvable")
    return t.model_dump()


@router.put("/transporteurs/{transporteur_id}")
def update_transporteur(
    transporteur_id: str,
    request: Request,
    transporteur_update: TransporteurUpdate,
) -> dict:
    """Mettre à jour un transporteur."""
    store = _get_transporteur_store(request)
    t = store.get(transporteur_id)
    if not t:
        raise HTTPException(404, "Transporteur introuvable")

    update_data = transporteur_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(t, key, value)

    audit(cfg.log_dir, "transporteur_modifie", cible=transporteur_id)
    return t.model_dump()


@router.delete("/transporteurs/{transporteur_id}")
def delete_transporteur(
    transporteur_id: str,
    request: Request,
) -> dict:
    """Supprimer un transporteur."""
    store = _get_transporteur_store(request)
    if transporteur_id not in store:
        raise HTTPException(404, "Transporteur introuvable")
    del store[transporteur_id]
    audit(cfg.log_dir, "transporteur_supprime", cible=transporteur_id)
    return {"deleted": True, "id": transporteur_id}


# ───────────────────────────────────────────────────────────────
# Routes Camions
# ───────────────────────────────────────────────────────────────

@router.post("/camions")
def create_camion(
    request: Request,
    camion: CamionCreate,
) -> dict:
    """Créer un nouveau camion."""
    store = _get_camion_store(request)
    c = Camion(
        id=new_id("cam_"),
        transporteur_id=camion.transporteur_id,
        immatriculation=camion.immatriculation,
        marque_modele=camion.marque_modele,
        capacite=camion.capacite,
        annee=camion.annee,
        assurance_valide=camion.assurance_valide,
        technique_valide=camion.technique_valide,
        statut=camion.statut,
        chauffeur_id=camion.chauffeur_id,
    )
    store[c.id] = c
    audit(cfg.log_dir, "camion_cree", immatriculation=camion.immatriculation)
    return c.model_dump()


@router.get("/camions")
def list_camions(
    request: Request,
    transporteur_id: Optional[str] = None,
) -> list[dict]:
    """Lister tous les camions."""
    store = _get_camion_store(request)
    camions = list(store.values())
    if transporteur_id:
        camions = [c for c in camions if c.transporteur_id == transporteur_id]
    return [c.model_dump() for c in camions]


@router.get("/camions/{camion_id}")
def get_camion(
    camion_id: str,
    request: Request,
) -> dict:
    """Obtenir un camion."""
    store = _get_camion_store(request)
    c = store.get(camion_id)
    if not c:
        raise HTTPException(404, "Camion introuvable")
    return c.model_dump()


@router.put("/camions/{camion_id}")
def update_camion(
    camion_id: str,
    request: Request,
    camion_update: CamionUpdate,
) -> dict:
    """Mettre à jour un camion."""
    store = _get_camion_store(request)
    c = store.get(camion_id)
    if not c:
        raise HTTPException(404, "Camion introuvable")

    update_data = camion_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(c, key, value)

    audit(cfg.log_dir, "camion_modifie", cible=camion_id)
    return c.model_dump()


@router.delete("/camions/{camion_id}")
def delete_camion(
    camion_id: str,
    request: Request,
) -> dict:
    """Supprimer un camion."""
    store = _get_camion_store(request)
    if camion_id not in store:
        raise HTTPException(404, "Camion introuvable")
    del store[camion_id]
    audit(cfg.log_dir, "camion_supprime", cible=camion_id)
    return {"deleted": True, "id": camion_id}


# ───────────────────────────────────────────────────────────────
# Routes Livraisons
# ───────────────────────────────────────────────────────────────

@router.post("/livraisons")
def create_livraison(
    request: Request,
    livraison: LivraisonCreate,
) -> dict:
    """Créer une nouvelle livraison."""
    store = _get_livraison_store(request)
    l = Livraison(
        id=new_id("liv_"),
        dossier_id=livraison.dossier_id,
        transport_id=livraison.transport_id,
        client_id=livraison.client_id,
        transporteur_id=livraison.transporteur_id,
        camion_id=livraison.camion_id,
        chauffeur_id=livraison.chauffeur_id,
        lieu_livraison=livraison.lieu_livraison,
        date_depart=livraison.date_depart,
        date_prevue=livraison.date_prevue,
        date_reelle=livraison.date_reelle,
        statut=livraison.statut,
        reserves_eventuelles=livraison.reserves_eventuelles,
        observations=livraison.observations,
    )
    store[l.id] = l
    audit(cfg.log_dir, "livraison_creee", dossier=livraison.dossier_id)
    return l.model_dump()


@router.get("/livraisons")
def list_livraisons(
    request: Request,
    dossier_id: Optional[str] = None,
) -> list[dict]:
    """Lister toutes les livraisons."""
    store = _get_livraison_store(request)
    livraisons = list(store.values())
    if dossier_id:
        livraisons = [l for l in livraisons if l.dossier_id == dossier_id]
    return [l.model_dump() for l in livraisons]


@router.get("/livraisons/{livraison_id}")
def get_livraison(
    livraison_id: str,
    request: Request,
) -> dict:
    """Obtenir une livraison."""
    store = _get_livraison_store(request)
    l = store.get(livraison_id)
    if not l:
        raise HTTPException(404, "Livraison introuvable")
    return l.model_dump()


@router.put("/livraisons/{livraison_id}")
def update_livraison(
    livraison_id: str,
    request: Request,
    livraison_update: LivraisonUpdate,
) -> dict:
    """Mettre à jour une livraison."""
    store = _get_livraison_store(request)
    l = store.get(livraison_id)
    if not l:
        raise HTTPException(404, "Livraison introuvable")

    update_data = livraison_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(l, key, value)

    audit(cfg.log_dir, "livraison_modifiee", cible=livraison_id)
    return l.model_dump()


@router.delete("/livraisons/{livraison_id}")
def delete_livraison(
    livraison_id: str,
    request: Request,
) -> dict:
    """Supprimer une livraison."""
    store = _get_livraison_store(request)
    if livraison_id not in store:
        raise HTTPException(404, "Livraison introuvable")
    del store[livraison_id]
    audit(cfg.log_dir, "livraison_supprimee", cible=livraison_id)
    return {"deleted": True, "id": livraison_id}


# ───────────────────────────────────────────────────────────────
# Routes Workflow Livraison
# ───────────────────────────────────────────────────────────────

@router.post("/livraisons/{livraison_id}/demarrer")
def demarrer_livraison(
    livraison_id: str,
    request: Request,
    date_depart: str,
) -> dict:
    """Démarrer une livraison (en route)."""
    store = _get_livraison_store(request)
    l = store.get(livraison_id)
    if not l:
        raise HTTPException(404, "Livraison introuvable")

    l.date_depart = date_depart
    l.statut = "en_route"
    audit(cfg.log_dir, "livraison_demarree", livraison=livraison_id)
    return l.model_dump()


@router.post("/livraisons/{livraison_id}/arriver")
def arriver_livraison(
    livraison_id: str,
    request: Request,
    date_reelle: str,
    reserves: str = "",
) -> dict:
    """Enregistrer l'arrivée chez le client."""
    store = _get_livraison_store(request)
    l = store.get(livraison_id)
    if not l:
        raise HTTPException(404, "Livraison introuvable")

    l.date_reelle = date_reelle
    l.reserves_eventuelles = reserves
    l.statut = "arrive" if not reserves else "reponse"
    audit(cfg.log_dir, "livraison_arrivee", livraison=livraison_id, reserves=reserves)
    return l.model_dump()


@router.post("/livraisons/{livraison_id}/confirmer")
def confirmer_livraison(
    livraison_id: str,
    request: Request,
    preuve_signee: bool,
    date_signature: str,
) -> dict:
    """Confirmer la livraison avec preuve signée."""
    store = _get_livraison_store(request)
    l = store.get(livraison_id)
    if not l:
        raise HTTPException(404, "Livraison introuvable")

    l.preuve_livraison_signee = preuve_signee
    l.date_signature = date_signature
    l.statut = "confirme"
    audit(cfg.log_dir, "livraison_confirmee", livraison=livraison_id, preuve=preuve_signee)
    return l.model_dump()