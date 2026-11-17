"""Routes de gestion du transport et livraison (Module 12)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError

from ..business_links import exiger_dossier
from ..business_store import BusinessStore
from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import Camion, Livraison, Transporteur, new_id
from .dependencies import _exige_dossier, _exige_objet_dossier, _filtre_dossiers

log = get_logger("transport")

router = APIRouter(prefix="/api/transport", tags=["transport"])

cfg = get_config()

STATUTS_LIVRAISON = {"planifie", "affecte", "enleve", "en_route", "arrive", "reponse", "confirme"}
CHAMPS_WORKFLOW_LIVRAISON = {
    "statut", "date_depart", "date_reelle", "reserves_eventuelles",
    "preuve_livraison_signee", "date_signature",
}


# ───────────────────────────────────────────────────────────────
# Stockage SQLite local, partagé avec les autres modules métier.
# ───────────────────────────────────────────────────────────────

def _get_transporteur_store(request: Request) -> BusinessStore[Transporteur]:
    return BusinessStore(cfg.data_dir / "metier.sqlite3", "transporteur", Transporteur)


def _get_camion_store(request: Request) -> BusinessStore[Camion]:
    return BusinessStore(cfg.data_dir / "metier.sqlite3", "camion", Camion)


def _get_livraison_store(request: Request) -> BusinessStore[Livraison]:
    return BusinessStore(cfg.data_dir / "metier.sqlite3", "livraison", Livraison)


def _refuser(livraison_id: str, message: str, statut: int = 409) -> None:
    audit(cfg.log_dir, "livraison_transition_refusee", cible=livraison_id, motif=message)
    raise HTTPException(statut, message)


def _date_iso(valeur: str, champ: str) -> None:
    try:
        date.fromisoformat(valeur)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, f"{champ} : date ISO attendue (AAAA-MM-JJ)") from exc


def _valider_liens(transaction: BusinessStore, transporteur_id: str, camion_id: str) -> None:
    if transporteur_id and transaction.related("transporteur", Transporteur).get(transporteur_id) is None:
        raise HTTPException(422, "Transporteur référencé introuvable")
    camion = transaction.related("camion", Camion).get(camion_id) if camion_id else None
    if camion_id and camion is None:
        raise HTTPException(422, "Camion référencé introuvable")
    if camion is not None and transporteur_id and camion.transporteur_id != transporteur_id:
        raise HTTPException(422, "Le camion n'appartient pas au transporteur indiqué")


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
    if not transporteur.nom.strip():
        raise HTTPException(422, "Le nom du transporteur est obligatoire")
    t = Transporteur(id=new_id("transp_"), **transporteur.model_dump())
    store = _get_transporteur_store(request)
    with store.transaction() as transaction:
        transaction[t.id] = t
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
    with store.transaction() as transaction:
        t = transaction.get(transporteur_id)
        if not t:
            raise HTTPException(404, "Transporteur introuvable")
        update_data = transporteur_update.model_dump(exclude_unset=True)
        try:
            candidate = Transporteur.model_validate({**t.model_dump(), **update_data})
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
        if not candidate.nom.strip():
            raise HTTPException(422, "Le nom du transporteur est obligatoire")
        transaction[transporteur_id] = candidate
    audit(cfg.log_dir, "transporteur_modifie", cible=transporteur_id)
    return candidate.model_dump()


@router.delete("/transporteurs/{transporteur_id}")
def delete_transporteur(
    transporteur_id: str,
    request: Request,
) -> dict:
    """Supprimer un transporteur."""
    store = _get_transporteur_store(request)
    with store.transaction() as transaction:
        if transaction.get(transporteur_id) is None:
            raise HTTPException(404, "Transporteur introuvable")
        if any(c.transporteur_id == transporteur_id for c in transaction.related("camion", Camion).values()):
            raise HTTPException(409, "Transporteur utilisé par des camions : suppression refusée")
        if any(liv.transporteur_id == transporteur_id for liv in transaction.related("livraison", Livraison).values()):
            raise HTTPException(409, "Transporteur utilisé par des livraisons : suppression refusée")
        del transaction[transporteur_id]
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
    if not camion.transporteur_id.strip() or not camion.immatriculation.strip():
        raise HTTPException(422, "Transporteur et immatriculation sont obligatoires")
    c = Camion(id=new_id("cam_"), **camion.model_dump())
    store = _get_camion_store(request)
    with store.transaction() as transaction:
        if transaction.related("transporteur", Transporteur).get(c.transporteur_id) is None:
            raise HTTPException(422, "Transporteur référencé introuvable")
        transaction[c.id] = c
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
    with store.transaction() as transaction:
        c = transaction.get(camion_id)
        if not c:
            raise HTTPException(404, "Camion introuvable")
        update_data = camion_update.model_dump(exclude_unset=True)
        try:
            candidate = Camion.model_validate({**c.model_dump(), **update_data})
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
        if not candidate.transporteur_id.strip() or not candidate.immatriculation.strip():
            raise HTTPException(422, "Transporteur et immatriculation sont obligatoires")
        if transaction.related("transporteur", Transporteur).get(candidate.transporteur_id) is None:
            raise HTTPException(422, "Transporteur référencé introuvable")
        if candidate.transporteur_id != c.transporteur_id and any(
            liv.camion_id == camion_id for liv in transaction.related("livraison", Livraison).values()
        ):
            raise HTTPException(409, "Impossible de changer le transporteur : ce camion est utilisé par des livraisons")
        transaction[camion_id] = candidate
    audit(cfg.log_dir, "camion_modifie", cible=camion_id)
    return candidate.model_dump()


@router.delete("/camions/{camion_id}")
def delete_camion(
    camion_id: str,
    request: Request,
) -> dict:
    """Supprimer un camion."""
    store = _get_camion_store(request)
    with store.transaction() as transaction:
        if transaction.get(camion_id) is None:
            raise HTTPException(404, "Camion introuvable")
        if any(liv.camion_id == camion_id for liv in transaction.related("livraison", Livraison).values()):
            raise HTTPException(409, "Camion utilisé par des livraisons : suppression refusée")
        del transaction[camion_id]
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
    _exige_dossier(livraison.dossier_id, request)
    if livraison.statut not in STATUTS_LIVRAISON:
        raise HTTPException(422, "Statut de livraison invalide")
    liv = Livraison(id=new_id("liv_"), **livraison.model_dump())
    store = _get_livraison_store(request)
    with store.transaction() as transaction:
        exiger_dossier(cfg, liv.dossier_id)
        _valider_liens(transaction, liv.transporteur_id, liv.camion_id)
        transaction[liv.id] = liv
    audit(cfg.log_dir, "livraison_creee", dossier=livraison.dossier_id)
    return liv.model_dump()


@router.get("/livraisons")
def list_livraisons(
    request: Request,
    dossier_id: Optional[str] = None,
) -> list[dict]:
    """Lister toutes les livraisons."""
    store = _get_livraison_store(request)
    livraisons = list(store.values())
    if dossier_id:
        livraisons = [liv for liv in livraisons if liv.dossier_id == dossier_id]
    return [liv.model_dump() for liv in _filtre_dossiers(request, livraisons)]


@router.get("/livraisons/{livraison_id}")
def get_livraison(
    livraison_id: str,
    request: Request,
) -> dict:
    """Obtenir une livraison."""
    store = _get_livraison_store(request)
    liv = store.get(livraison_id)
    if not liv:
        raise HTTPException(404, "Livraison introuvable")
    _exige_objet_dossier(request, liv)
    return liv.model_dump()


@router.put("/livraisons/{livraison_id}")
def update_livraison(
    livraison_id: str,
    request: Request,
    livraison_update: LivraisonUpdate,
) -> dict:
    """Mettre à jour une livraison."""
    store = _get_livraison_store(request)
    with store.transaction() as transaction:
        liv = transaction.get(livraison_id)
        if not liv:
            raise HTTPException(404, "Livraison introuvable")
        _exige_objet_dossier(request, liv)

        update_data = livraison_update.model_dump(exclude_unset=True)
        champs_workflow = CHAMPS_WORKFLOW_LIVRAISON & update_data.keys()
        if champs_workflow and any(update_data[c] != getattr(liv, c) for c in champs_workflow):
            _refuser(livraison_id, "Utilisez les actions de workflow pour changer le statut, les dates et la preuve")
        if liv.statut == "confirme" and any(
            cle != "observations" and valeur != getattr(liv, cle)
            for cle, valeur in update_data.items()
        ):
            _refuser(livraison_id, "Après confirmation, seules les observations peuvent être modifiées")
        try:
            candidate = Livraison.model_validate({**liv.model_dump(), **update_data})
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
        if candidate.statut not in STATUTS_LIVRAISON:
            raise HTTPException(422, "Statut de livraison invalide")
        _exige_objet_dossier(request, candidate)
        exiger_dossier(cfg, candidate.dossier_id)
        _valider_liens(transaction, candidate.transporteur_id, candidate.camion_id)
        transaction[livraison_id] = candidate
    audit(cfg.log_dir, "livraison_modifiee", cible=livraison_id)
    return candidate.model_dump()


@router.delete("/livraisons/{livraison_id}")
def delete_livraison(
    livraison_id: str,
    request: Request,
) -> dict:
    """Supprimer une livraison."""
    store = _get_livraison_store(request)
    with store.transaction() as transaction:
        liv = transaction.get(livraison_id)
        if not liv:
            raise HTTPException(404, "Livraison introuvable")
        _exige_objet_dossier(request, liv)
        del transaction[livraison_id]
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
    with store.transaction() as transaction:
        liv = transaction.get(livraison_id)
        if not liv:
            raise HTTPException(404, "Livraison introuvable")
        _exige_objet_dossier(request, liv)
        if liv.statut not in {"planifie", "affecte", "enleve"}:
            _refuser(livraison_id, "Seule une livraison planifiée, affectée ou enlevée peut démarrer")
        _date_iso(date_depart, "Date de départ")
        liv.date_depart = date_depart
        liv.statut = "en_route"
        exiger_dossier(cfg, liv.dossier_id)
        transaction[livraison_id] = liv
    audit(cfg.log_dir, "livraison_demarree", livraison=livraison_id)
    return liv.model_dump()


@router.post("/livraisons/{livraison_id}/arriver")
def arriver_livraison(
    livraison_id: str,
    request: Request,
    date_reelle: str,
    reserves: str = "",
) -> dict:
    """Enregistrer l'arrivée chez le client."""
    store = _get_livraison_store(request)
    with store.transaction() as transaction:
        liv = transaction.get(livraison_id)
        if not liv:
            raise HTTPException(404, "Livraison introuvable")
        _exige_objet_dossier(request, liv)
        if liv.statut != "en_route":
            _refuser(livraison_id, "Seule une livraison en route peut être enregistrée comme arrivée")
        _date_iso(date_reelle, "Date réelle d'arrivée")
        liv.date_reelle = date_reelle
        liv.reserves_eventuelles = reserves
        liv.statut = "arrive" if not reserves else "reponse"
        exiger_dossier(cfg, liv.dossier_id)
        transaction[livraison_id] = liv
    audit(cfg.log_dir, "livraison_arrivee", livraison=livraison_id, reserves=reserves)
    return liv.model_dump()


@router.post("/livraisons/{livraison_id}/confirmer")
def confirmer_livraison(
    livraison_id: str,
    request: Request,
    preuve_signee: bool,
    date_signature: str,
) -> dict:
    """Confirmer la livraison avec preuve signée."""
    store = _get_livraison_store(request)
    with store.transaction() as transaction:
        liv = transaction.get(livraison_id)
        if not liv:
            raise HTTPException(404, "Livraison introuvable")
        _exige_objet_dossier(request, liv)
        if liv.statut not in {"arrive", "reponse"}:
            _refuser(livraison_id, "Seule une livraison arrivée ou avec réserves peut être confirmée")
        if not preuve_signee:
            _refuser(livraison_id, "Une preuve de livraison signée est obligatoire", 400)
        _date_iso(date_signature, "Date de signature")
        liv.preuve_livraison_signee = preuve_signee
        liv.date_signature = date_signature
        liv.statut = "confirme"
        exiger_dossier(cfg, liv.dossier_id)
        transaction[livraison_id] = liv
    audit(cfg.log_dir, "livraison_confirmee", livraison=livraison_id, preuve=preuve_signee)
    return liv.model_dump()
