"""Routes du module Transit maritime avec contrôle d'accès RBAC renforcé.

Ce module implémente les opérations de transit maritime avec :
- Contrôle d'accès par rôle (RBAC)
- Cloisonnement par dossier
- Journalisation d'audit complète
- Validation serveur des entrées
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from .. import finance
from ..business_links import exiger_dossier
from ..business_store import BusinessStore
from ..config import Config, get_config
from ..logging_setup import audit
from ..models import Conteneur, Frais, TerminalEnlevement
from ..rbac import (
    ACTIONS,
    ADMINISTRATEUR,
    LECTEUR,
    RESPONSABLE_FINANCIER,
)
from ..routes.dependencies import _exige, _exige_dossier, _utilisateur_ou_ouvert

router = APIRouter(prefix="/transit", tags=["transit"])


def _cfg(request: Request) -> Config:
    return getattr(request.app.state, "cfg", None) or get_config()


# ============================================================================
# Helper: Vérification du rôle pour une action maritime
# ============================================================================

def _action_maritime_autorisee(request: Request, action: str,
                               dossier_id: Optional[str] = None) -> Optional[Any]:
    """Vérifie l'autorisation pour une action maritime avec cloisonnement par dossier.

    Args:
        request: La requête FastAPI
        action: Le nom de l'action RBAC (ex: "prise_emplacement", "eta_update")
        dossier_id: ID du dossier (optionnel, pour vérification de périmètre)

    Returns:
        L'utilisateur si autorisé, sinon lève HTTPException(403)
    """
    u = _utilisateur_ou_ouvert(request)
    cfg = _cfg(request)

    # Vérifier le rôle pour l'action
    roles_autorises = ACTIONS.get(action, ())
    if not roles_autorises:
        raise HTTPException(500, f"action inconnue : {action}")

    if not any(u.a_role(role) for role in roles_autorises):
        audit(cfg.log_dir, "acces_refuse_role",
              route=request.url.path,
              methode=request.method,
              acteur=u.nom,
              roles=sorted(u.roles),
              requis=action)
        raise HTTPException(403, f"rôle requis pour l'action '{action}'")

    # Vérifier le périmètre par dossier si spécifié
    if dossier_id and not u.voit_dossier(dossier_id):
        audit(cfg.log_dir, "acces_refuse_dossier",
              route=request.url.path,
              methode=request.method,
              acteur=u.nom,
              dossier=dossier_id)
        raise HTTPException(403, "dossier hors de votre périmètre")

    audit(cfg.log_dir, "acces_applique",
          route=request.url.path,
          methode=request.method,
          acteur=u.nom,
          action=action,
          dossier=dossier_id)
    return u


# ============================================================================
# Routes Dossiers Transit Maritime
# ============================================================================

@router.post("/dossiers")
def create_dossier(
    request: Request,
    label: str = Body(..., min_length=1, max_length=200),
    reference: str = Body("", max_length=50),
    profile: str = Body("personnalise"),
) -> dict:
    """Créer un nouveau dossier de transit maritime.

    Exige le rôle: agent_de_transit ou supérieur.
    """
    u = _action_maritime_autorisee(request, "creation")

    # Validation des entrées
    if not label.strip():
        raise HTTPException(400, "le label est requis")

    from ..dossier import PROFILS_DOSSIER, DossierStore

    if profile not in PROFILS_DOSSIER:
        raise HTTPException(400, f"profil de dossier inconnu: {profile}")

    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)
    dossier = store.creer(label.strip(), profile, acteur=u.nom)
    if reference:
        store.mettre_a_jour(dossier.id, {"reference": reference.strip()}, acteur=u.nom)

    audit(config.log_dir, "dossier_cree",
          acteur=u.nom,
          dossier=dossier.id,
          label=label)

    return {"id": dossier.id, "label": dossier.label, "profile": dossier.profile,
            "state": dossier.state.value}


@router.get("/dossiers")
def list_dossiers(
    request: Request,
    client: Optional[str] = Query(None, max_length=100, description="Filtrer par client importateur"),
    port: Optional[str] = Query(None, max_length=100, description="Filtrer par port de chargement ou de destination"),
    statut: Optional[str] = Query(None, description="Filtrer par état du dossier"),
    priorite: Optional[str] = Query(None, description="Filtrer par priorité"),
    manager: Optional[str] = Query(None, max_length=100, description="Filtrer par gestionnaire"),
    order_by: Optional[str] = Query(None, description="Trier par champ (label, created_at, state, priorite)"),
    order_dir: Optional[str] = Query("asc", description="Direction du tri : asc ou desc"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limite du nombre de résultats"),
    offset: Optional[int] = Query(0, ge=0, description="Offset pour la pagination"),
) -> list[dict]:
    """Lister les dossiers accessibles à l'utilisateur avec filtres et pagination.

    Exige le rôle: lecteur ou supérieur.
    Respect le cloisonnement par dossier.
    Les paramètres de query sont optionnels et filtrent/paginent les résultats.

    Paramètres de tri :
    - order_by : champ sur lequel trier (label, created_at, state, priorite)
    - order_dir : direction du tri (asc ou desc)

    Paramètres de pagination :
    - limit : nombre maximum de résultats à retourner
    - offset : nombre de résultats à ignorer (pour la pagination)
    """
    u = _exige(LECTEUR)(request)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)
    dossiers = [d.as_dict() for d in store.liste()]

    # Filtrer par le périmètre de l'utilisateur
    visibles = [d for d in dossiers if u.voit_dossier(d.get("id", ""))]

    # Application des filtres clients
    if client:
        visibles = [d for d in visibles if d.get("client_importateur", "").lower().strip() == client.lower().strip()]

    # Application des filtres port
    if port:
        port_lower = port.lower()
        visibles = [
            d
            for d in visibles
            if port_lower in (d.get("port_chargement") or "").lower()
            or port_lower in (d.get("port_destination") or "").lower()
        ]

    # Application des filtres statut
    if statut:
        visibles = [d for d in visibles if d.get("state", "").lower().strip() == statut.lower().strip()]

    # Application des filtres priorité
    if priorite:
        visibles = [d for d in visibles if d.get("priorite", "").lower().strip() == priorite.lower().strip()]

    # Application des filtres gestionnaire
    if manager:
        visibles = [d for d in visibles if d.get("manager", "").lower().strip() == manager.lower().strip()]

    # Tri
    if order_by:
        reverse = order_dir and order_dir.lower() == "desc"
        if order_by == "label":
            visibles.sort(key=lambda d: d.get("label", "").lower(), reverse=reverse)
        elif order_by == "created_at":
            visibles.sort(key=lambda d: d.get("created_at", 0), reverse=reverse)
        elif order_by == "state":
            visibles.sort(key=lambda d: d.get("state", "").lower(), reverse=reverse)
        elif order_by == "priorite":
            visibles.sort(key=lambda d: d.get("priorite", "").lower(), reverse=reverse)

    # Pagination
    if offset and offset > 0:
        visibles = visibles[offset:]
    if limit is not None and limit > 0:
        visibles = visibles[:limit]

    return visibles


@router.get("/dossiers/{dossier_id}")
def get_dossier(request: Request, dossier_id: str) -> dict:
    """Obtenir les détails d'un dossier spécifique.

    Exige le rôle: lecteur ou supérieur.
    Vérifie l'accès au dossier.
    """
    _exige(LECTEUR)(request)
    _exige_dossier(dossier_id, request)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)
    dossier = store.get_dossier(dossier_id)

    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    return dossier


@router.patch("/dossiers/{dossier_id}")
def update_dossier(
    request: Request,
    dossier_id: str,
    data: dict = Body(...),
) -> dict:
    """Mettre à jour un dossier de transit.

    Exige le rôle: agent_de_transit ou supérieur.
    Vérifie l'accès au dossier.
    """
    u = _action_maritime_autorisee(request, "modification", dossier_id)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)
    dossier = store.get_dossier(dossier_id)

    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    # Mettre à jour les champs autorisés
    champs_autorises = {
        "label", "reference", "numero_voyage", "navire",
        "eta", "eta_effective", "port_chargement", "port_destination",
        "devise", "valeur_commerciale", "description_marchandise"
    }

    for cle, valeur in data.items():
        if cle in champs_autorises and valeur is not None:
            dossier[cle] = str(valeur)

    store.update_dossier(dossier_id, dossier, acteur=u.nom)

    audit(config.log_dir, "dossier_modifie",
          acteur=u.nom,
          dossier=dossier_id,
          champs=list(data.keys()))

    return {"id": dossier_id, "status": "updated"}


# ============================================================================
# Routes Opérations Maritime Spécifiques
# ============================================================================

@router.post("/dossiers/{dossier_id}/prise_emplacement")
def prise_emplacement(
    request: Request,
    dossier_id: str,
    conteneur: str = Body(..., max_length=50),
    quai: str = Body("", max_length=50),
) -> dict:
    """Enregistrer la prise d'étalage d'un conteneur.

    Exige le rôle: agent_de_transit ou supérieur.
    Vérifie l'accès au dossier.
    """
    u = _action_maritime_autorisee(request, "prise_emplacement", dossier_id)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)

    dossier = store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    dossier["conteneur"] = conteneur
    dossier["quai"] = quai
    dossier["prise_emplacement"] = True

    store.mettre_a_jour(dossier_id, {"numero_conteneur": conteneur}, acteur=u.nom)
    store.journaliser(dossier_id, "prise_emplacement", {"conteneur": conteneur, "quai": quai}, acteur=u.nom)

    audit(config.log_dir, "prise_emplacement_enregistree",
          acteur=u.nom,
          dossier=dossier_id,
          conteneur=conteneur,
          quai=quai)

    return {"id": dossier_id, "conteneur": conteneur, "qui": u.nom}


@router.post("/dossiers/{dossier_id}/eta")
def mettre_a_jour_eta(
    request: Request,
    dossier_id: str,
    eta: str = Body(..., max_length=50),
    eta_type: str = Body("estime"),  # estime, confirme, modifie
) -> dict:
    """Mettre à jour l'ETA (Estimated Time of Arrival).

    Exige le rôle: agent_de_transit ou superviseur.
    Vérifie l'accès au dossier.
    """
    u = _action_maritime_autorisee(request, "eta_update", dossier_id)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)

    dossier = store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    ancien_eta = dossier.get("eta")
    dossier["eta"] = eta
    dossier["eta_type"] = eta_type

    store.mettre_a_jour(dossier_id, {"eta": eta}, acteur=u.nom)

    audit(config.log_dir, "eta_mis_a_jour",
          acteur=u.nom,
          dossier=dossier_id,
          ancien_eta=ancien_eta,
          nouveau_eta=eta,
          type=eta_type)

    return {"id": dossier_id, "eta": eta}


@router.post("/dossiers/{dossier_id}/bl_receive")
def bl_receive(
    request: Request,
    dossier_id: str,
    reference_bl: str = Body(..., min_length=5, max_length=50),
    date_bl: str = Body("", max_length=20),
) -> dict:
    """Enregistrer la réception du Bill of Lading (BL).

    Exige le rôle: agent_de_transit ou superviseur.
    Vérifie l'accès au dossier.
    """
    u = _action_maritime_autorisee(request, "bl_receive", dossier_id)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)

    dossier = store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    dossier["reference_bl"] = reference_bl
    dossier["date_bl"] = date_bl
    dossier["bl_reçu"] = True

    store.mettre_a_jour(dossier_id, {"reference_bl": reference_bl}, acteur=u.nom)
    store.journaliser(dossier_id, "bl_receive", {"reference_bl": reference_bl, "date_bl": date_bl}, acteur=u.nom)

    audit(config.log_dir, "bl_reçu",
          acteur=u.nom,
          dossier=dossier_id,
          reference_bl=reference_bl)

    return {"id": dossier_id, "reference_bl": reference_bl, "status": "bl_reçu"}


# ============================================================================
# Routes Gestion Financière
# ============================================================================

class TransitFraisCreate(BaseModel):
    """Charge historique `/transit/.../frais`, persistée dans le magasin métier."""
    type_frais: str = Field(min_length=1, max_length=100)
    montant: float = Field(gt=0)
    devise: str = Field(default="EUR", min_length=3, max_length=3)
    description: str = Field(default="", max_length=500)

    @field_validator("type_frais")
    @classmethod
    def _type_non_vide(cls, valeur: str) -> str:
        propre = valeur.strip()
        if not propre:
            raise ValueError("type_frais requis")
        return propre

    @field_validator("montant")
    @classmethod
    def _montant_fini(cls, valeur: float) -> float:
        if not math.isfinite(valeur):
            raise ValueError("montant fini requis")
        return valeur

    @field_validator("devise")
    @classmethod
    def _devise_iso(cls, valeur: str) -> str:
        propre = valeur.strip().upper()
        if len(propre) != 3 or not propre.isalpha():
            raise ValueError("devise ISO 4217 à trois lettres attendue")
        return propre


class TransitPaiementCreate(BaseModel):
    """Paiement d'un frais identifié ; `frai_id` reste un alias historique."""
    model_config = ConfigDict(populate_by_name=True)

    frais_id: str = Field(min_length=1, max_length=128,
                          validation_alias=AliasChoices("frais_id", "frai_id"))
    montant: float = Field(gt=0)
    reference_paiement: str = Field(default="", max_length=100)
    mode_paiement: str = Field(default="", max_length=50)

    @field_validator("montant")
    @classmethod
    def _montant_fini(cls, valeur: float) -> float:
        if not math.isfinite(valeur):
            raise ValueError("montant fini requis")
        return valeur


@router.post("/dossiers/{dossier_id}/frais")
def creer_frais(
    request: Request,
    dossier_id: str,
    payload: TransitFraisCreate,
) -> dict:
    """Créer un frais persistant pour un dossier.

    Exige le rôle responsable_transit ou supérieur et l'accès au dossier.
    Le frais est écrit dans `metier.sqlite3`, plus dans une liste JSON annexe.
    """
    u = _action_maritime_autorisee(request, "frais_creation", dossier_id)
    cfg = _cfg(request)
    store = BusinessStore(cfg.data_dir / "metier.sqlite3", "frais", Frais)
    frais_obj = Frais(
        dossier_id=dossier_id,
        categorie=payload.type_frais,
        montant=payload.montant,
        montant_devise=payload.montant,
        devise=payload.devise,
        taux_change=1.0,
        date=time.strftime("%Y-%m-%d"),
        statut_paiement="en_attente",
        commentaire=payload.description,
    )
    with store.transaction() as transaction:
        exiger_dossier(cfg, dossier_id, absent=404)
        transaction[frais_obj.id] = frais_obj

    audit(cfg.log_dir, "frais_cree",
          acteur=u.nom,
          dossier=dossier_id,
          frais_id=frais_obj.id,
          type_frais=frais_obj.categorie,
          montant=frais_obj.montant,
          devise=frais_obj.devise)

    return {"dossier_id": dossier_id, "frais": frais_obj.model_dump()}


@router.post("/dossiers/{dossier_id}/paiement")
def enregistrer_paiement(
    request: Request,
    dossier_id: str,
    payload: TransitPaiementCreate,
) -> dict:
    """Enregistrer le paiement complet d'un frais du dossier.

    Exige le rôle responsable_financier ou supérieur. Les paiements partiels
    ou divergents sont refusés tant qu'un modèle d'échéancier n'existe pas.
    """
    u = _action_maritime_autorisee(request, "paiement_frais", dossier_id)
    cfg = _cfg(request)
    store = BusinessStore(cfg.data_dir / "metier.sqlite3", "frais", Frais)
    with store.transaction() as transaction:
        frais = transaction.get(payload.frais_id)
        if frais is None or frais.dossier_id != dossier_id:
            raise HTTPException(404, "frais introuvable pour ce dossier")
        exiger_dossier(cfg, dossier_id, absent=404)
        if frais.statut_paiement == "paye":
            raise HTTPException(409, "frais déjà payé")
        if finance._decimal(payload.montant) != finance._decimal(frais.montant):
            raise HTTPException(422, "le paiement doit couvrir exactement le montant du frais")
        frais.statut_paiement = "paye"
        frais.date_paiement = time.strftime("%Y-%m-%d")
        frais.reference_paiement = payload.reference_paiement
        frais.mode_paiement = payload.mode_paiement
        transaction[frais.id] = frais

    paiement = {
        "montant": frais.montant,
        "devise": frais.devise,
        "reference": frais.reference_paiement,
        "mode": frais.mode_paiement,
        "date": frais.date_paiement,
        "par": u.nom,
    }
    audit(cfg.log_dir, "paiement_enregistre",
          acteur=u.nom,
          dossier=dossier_id,
          frais_id=frais.id,
          montant=frais.montant,
          devise=frais.devise,
          reference=frais.reference_paiement)

    return {"dossier_id": dossier_id, "frais_id": frais.id,
            "frais": frais.model_dump(), "paiement": paiement}


# ============================================================================
# Routes Export et Gestion
# ============================================================================

@router.post("/dossiers/{dossier_id}/export")
def exporter_dossier(
    request: Request,
    dossier_id: str,
    formats: list[str] = Body(["json"], embed=True),
) -> dict:
    """Exporter un dossier avec les formats demandés.

    Exige le rôle: controleur_documentaire, responsable_financier ou administrateur.
    Vérifie l'accès au dossier.
    """
    u = _action_maritime_autorisee(request, "export", dossier_id)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)

    dossier = store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    # Masquer les données sensibles selon le rôle
    donnees_export = dossier.copy()
    if not u.a_role(RESPONSABLE_FINANCIER) and not u.a_role(ADMINISTRATEUR):
        donnees_export.pop("frais", None)
        donnees_export.pop("valeur_commerciale", None)

    # Valider les formats demandés
    formats_valides = {"json", "csv", "xlsx"}
    formats_demandes = [f.lower().strip() for f in formats if f]
    formats_interdits = set(formats_demandes) - formats_valides
    if formats_interdits:
        raise HTTPException(400, f"formats non supportés: {formats_interdits}")

    audit(config.log_dir, "dossier_exporte",
          acteur=u.nom,
          dossier=dossier_id,
          formats=formats_demandes)

    return {
        "dossier_id": dossier_id,
        "formats": formats_demandes,
        "donnees": donnees_export,
    }


@router.post("/dossiers/{dossier_id}/cloturer")
def cloturer_dossier(
    request: Request,
    dossier_id: str,
    motif: str = Body("", max_length=500, embed=True),
) -> dict:
    """Clôturer un dossier de transit.

    Exige le rôle: administrateur.
    Vérifie l'accès au dossier.
    """
    u = _action_maritime_autorisee(request, "cloture_dossier", dossier_id)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)

    dossier = store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    if dossier.get("statut_documentaire") == "cloture":
        raise HTTPException(409, "dossier déjà clôturé")
    horodatage = datetime.now(timezone.utc).isoformat()
    store.mettre_a_jour(dossier_id, {"statut_documentaire": "cloture"}, acteur=u.nom)
    store.journaliser(dossier_id, "cloture", {
        "motif": motif, "date": horodatage, "par": u.nom,
    }, acteur=u.nom)

    audit(config.log_dir, "dossier_cloture",
          acteur=u.nom,
          dossier=dossier_id,
          motif=motif)

    return {"id": dossier_id, "status": "cloturé", "motif": motif}


# ───────────────────────────────────────────────────────────────
# Archivage réversible
# ───────────────────────────────────────────────────────────────

@router.post("/dossiers/{dossier_id}/archiver")
def archiver_dossier(
    request: Request,
    dossier_id: str,
    motif: str = Body("", max_length=500, embed=True),
) -> dict:
    """Archiver un dossier de transit.

    Exige le rôle: administrateur.
    L'archivage marque le dossier comme archivé et le retire de la vue active,
    mais il peut être restauré plus tard.
    """
    u = _action_maritime_autorisee(request, "archivage", dossier_id)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)

    dossier = store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    from ..tracabilite import archiver_dossier as archiver_metier

    try:
        synthese = archiver_metier(store, dossier_id, motif=motif, acteur=u.nom)
    except KeyError as exc:
        raise HTTPException(404, "dossier introuvable") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc

    audit(config.log_dir, "dossier_archive",
          acteur=u.nom,
          dossier=dossier_id,
          motif=motif)

    return {"id": dossier_id, "status": "archive", "state": synthese["state"],
            "motif": motif, "avertissements": synthese.get("avertissements_archivage", [])}


@router.post("/dossiers/{dossier_id}/restorer")
def restaurer_dossier(
    request: Request,
    dossier_id: str,
) -> dict:
    """Restaurer un dossier archivé.

    Exige le rôle: administrateur.
    Restaure un dossier archivé pour le rendre à nouveau actif.
    """
    u = _action_maritime_autorisee(request, "restauration_dossier", dossier_id)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)

    dossier = store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    if dossier.get("state") != "archive":
        raise HTTPException(400, "Ce dossier n'est pas archivé")

    from ..dossier import DossierState

    precedent = DossierState.EN_PREPARATION
    for evenement in reversed(dossier.get("history", [])):
        detail = evenement.get("detail") or {}
        if evenement.get("action") == "state_forced" and detail.get("to") == "archive":
            try:
                precedent = DossierState(detail.get("from"))
            except ValueError:
                precedent = DossierState.EN_PREPARATION
            break
    restaure = store.forcer_etat(dossier_id, precedent, acteur=u.nom,
                                 motif="restauration depuis l'archive")

    audit(config.log_dir, "dossier_restaurer",
          acteur=u.nom,
          dossier=dossier_id)

    return {"id": dossier_id, "status": "actif", "state": restaure.state.value,
            "message": "Dossier restauré avec succès"}


@router.post("/dossiers/{dossier_id}/conteneurs")
def lier_conteneur_dossier(
    request: Request,
    dossier_id: str,
    conteneur: str = Body(..., max_length=50),
    scelle: str = Body("", max_length=50),
    poids: float = Body(0.0),
) -> dict:
    """Lier un conteneur à un dossier.

    Exige le rôle: agent_de_transit ou supérieur.
    Vérifie l'accès au dossier.
    """
    u = _action_maritime_autorisee(request, "prise_emplacement", dossier_id)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)

    dossier = store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    numero = conteneur.strip()
    if not numero:
        raise HTTPException(422, "numéro de conteneur requis")
    if not math.isfinite(poids) or poids < 0:
        raise HTTPException(422, "poids fini positif ou nul requis")

    metier = BusinessStore(config.data_dir / "metier.sqlite3", "conteneur", Conteneur)
    with metier.transaction() as transaction:
        exiger_dossier(config, dossier_id, absent=404)
        existant = next((c for c in transaction.values() if c.numero_conteneur == numero), None)
        if existant is not None:
            if existant.dossier_id == dossier_id:
                raise HTTPException(400, "Ce conteneur est déjà lié à ce dossier")
            raise HTTPException(409, "Ce conteneur est déjà lié à un autre dossier")
        objet = Conteneur(dossier_id=dossier_id, numero_conteneur=numero,
                          seal_number=scelle, poids=poids)
        transaction[objet.id] = objet

    store.journaliser(dossier_id, "conteneur_lie", {
        "conteneur_id": objet.id, "numero": numero, "scelle": scelle,
        "poids": poids, "lie_par": u.nom,
    }, acteur=u.nom)
    audit(config.log_dir, "conteneur_lie",
          acteur=u.nom,
          dossier=dossier_id,
          conteneur=numero,
          conteneur_id=objet.id)

    return {"dossier_id": dossier_id, "conteneur": numero, "conteneur_id": objet.id,
            "message": "Conteneur lié avec succès"}


@router.delete("/dossiers/{dossier_id}/conteneurs/{conteneur}")
def delier_conteneur_dossier(
    request: Request,
    dossier_id: str,
    conteneur: str,
) -> dict:
    """Délier un conteneur d'un dossier.

    Exige le rôle: agent_de_transit ou supérieur.
    Vérifie l'accès au dossier.
    """
    u = _action_maritime_autorisee(request, "prise_emplacement", dossier_id)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)

    dossier = store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    metier = BusinessStore(config.data_dir / "metier.sqlite3", "conteneur", Conteneur)
    with metier.transaction() as transaction:
        objet = next((c for c in transaction.values()
                      if c.dossier_id == dossier_id and c.numero_conteneur == conteneur), None)
        if objet is None:
            raise HTTPException(404, "Ce conteneur n'est pas lié à ce dossier")
        if any(e.numero_conteneur == conteneur for e in
               transaction.related("terminal", TerminalEnlevement).values()):
            raise HTTPException(409, "Conteneur référencé par un enlèvement terminal")
        del transaction[objet.id]

    store.journaliser(dossier_id, "conteneur_delie", {
        "conteneur_id": objet.id, "numero": conteneur, "delie_par": u.nom,
    }, acteur=u.nom)
    audit(config.log_dir, "conteneur_delié",
          acteur=u.nom,
          dossier=dossier_id,
          conteneur=conteneur,
          conteneur_id=objet.id)

    return {"dossier_id": dossier_id, "conteneur": conteneur, "message": "Conteneur délié avec succès"}


@router.get("/dossiers/{dossier_id}/conteneurs")
def lister_conteneurs_dossier(
    request: Request,
    dossier_id: str,
) -> dict:
    """Lister les conteneurs liés à un dossier.

    Exige le rôle: lecteur ou supérieur.
    Vérifie l'accès au dossier.
    """
    _exige(LECTEUR)(request)
    _exige_dossier(dossier_id, request)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)

    dossier = store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    metier = BusinessStore(config.data_dir / "metier.sqlite3", "conteneur", Conteneur)
    conteneurs = []
    for objet in metier.values():
        if objet.dossier_id != dossier_id:
            continue
        donnees = objet.model_dump()
        donnees["numero"] = objet.numero_conteneur
        conteneurs.append(donnees)
    return {"dossier_id": dossier_id, "conteneurs": conteneurs}


# ───────────────────────────────────────────────────────────────
# Historique chronologique
# ───────────────────────────────────────────────────────────────

@router.get("/dossiers/{dossier_id}/historique")
def historique_dossier(
    request: Request,
    dossier_id: str,
) -> dict:
    """Récupérer l'historique chronologique des modifications d'un dossier.

    Exige le rôle: lecteur ou supérieur.
    Vérifie l'accès au dossier.
    """
    _exige(LECTEUR)(request)
    _exige_dossier(dossier_id, request)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)

    dossier = store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    return {"dossier_id": dossier_id, "historique": dossier.get("history", [])}


@router.get("/dossiers/{dossier_id}/export")
def export_dossier(
    request: Request,
    dossier_id: str,
    fmt: str = Query("json", pattern="^(json|csv|xlsx)$"),
) -> dict:
    """Exporter un dossier au format demandé.

    Exige le rôle: controleur_documentaire, responsable_financier ou administrateur.
    Vérifie l'accès au dossier.
    """
    u = _action_maritime_autorisee(request, "export", dossier_id)

    from ..dossier import DossierStore
    config = _cfg(request)
    store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)

    dossier = store.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")

    # Masquer les données sensibles selon le rôle
    donnees_export = dossier.copy()
    if not u.a_role(RESPONSABLE_FINANCIER) and not u.a_role(ADMINISTRATEUR):
        donnees_export.pop("frais", None)
        donnees_export.pop("valeur_commerciale", None)

    if fmt == "json":
        return {"dossier_id": dossier_id, "format": "json", "donnees": donnees_export}
    elif fmt == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(donnees_export.keys())
        writer.writerow(donnees_export.values())
        return {"dossier_id": dossier_id, "format": "csv", "contenu": output.getvalue()}
    elif fmt == "xlsx":
        # Pour l'instant, on renvoie une indication que l'export xlsx est disponible
        return {"dossier_id": dossier_id, "format": "xlsx", "message": "Export XLSX disponible sur demande"}

    return {"dossier_id": dossier_id, "format": fmt, "message": "Format non supporté"}


# ───────────────────────────────────────────────────────────────
# Vérification de doublons
# ───────────────────────────────────────────────────────────────

class DoublonRecherche(BaseModel):
    """Critères de recherche de doublons."""
    label: Optional[str] = None
    client: Optional[str] = None
    port: Optional[str] = None


@router.post("/dossiers/doublons")
def rechercher_doublons(
    request: Request,
    recherche: DoublonRecherche = Body(...),
) -> dict:
    """Rechercher des doublons potentiels parmi les dossiers.

    Exige le rôle: lecteur ou supérieur.
    Compare les dossiers selon les critères fournis.
    """
    u = _exige(LECTEUR)(request)

    from ..dossier import DossierStore
    config = _cfg(request)
    dossier_store = DossierStore(config.data_dir / "dossiers", log_dir=config.log_dir)
    dossiers = [d.as_dict() for d in dossier_store.liste() if u.voit_dossier(d.id)]

    doublons = []

    # Recherche par label
    if recherche.label:
        label_lower = recherche.label.lower().strip()
        candidats = [d for d in dossiers if label_lower in (d.get("label") or "").lower()]
        if len(candidats) > 1:
            doublons.append({
                "type": "label",
                "valeur": recherche.label,
                "count": len(candidats),
                "dossiers": [d.get("id") for d in candidats],
            })

    # Recherche par client
    if recherche.client:
        client_lower = recherche.client.lower().strip()
        candidats = [d for d in dossiers if client_lower in (d.get("client_importateur") or "").lower()]
        if len(candidats) > 1:
            doublons.append({
                "type": "client",
                "valeur": recherche.client,
                "count": len(candidats),
                "dossiers": [d.get("id") for d in candidats],
            })

    # Recherche par port
    if recherche.port:
        port_lower = recherche.port.lower().strip()
        candidats = [
            d
            for d in dossiers
            if port_lower in (d.get("port_chargement") or "").lower()
            or port_lower in (d.get("port_destination") or "").lower()
        ]
        if len(candidats) > 1:
            doublons.append({
                "type": "port",
                "valeur": recherche.port,
                "count": len(candidats),
                "dossiers": [d.get("id") for d in candidats],
            })

    return {"dossier_id": None, "doublons": doublons, "total": len(doublons)}


# ============================================================================
# Routes Documentation et Audit
# ============================================================================

@router.get("/audit")
def audit_logs(
    request: Request,
    dossier_id: Optional[str] = Query(None, max_length=50),
    action: Optional[str] = Query(None, max_length=50),
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    """Consulter les logs d'audit pour un dossier ou une action.

    Exige le rôle: lecteur ou supérieur.
    Les lecteurs ne voient que les logs de leurs dossiers.
    """
    u = _exige(LECTEUR)(request)

    audit_file = _cfg(request).log_dir / "audit.log"

    if not audit_file.exists():
        return {"logs": [], "total": 0}

    import json

    lignes = audit_file.read_text(encoding="utf-8").splitlines()
    logs_filtres = []
    for ligne in reversed(lignes):
        try:
            entree = json.loads(ligne)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(entree, dict):
            continue
        entree_dossier = entree.get("dossier") or entree.get("dossier_id")
        if dossier_id and entree_dossier != dossier_id:
            continue
        if action and entree.get("action") != action and entree.get("event") != action:
            continue
        if not u.a_role(ADMINISTRATEUR):
            if not entree_dossier or not u.voit_dossier(entree_dossier):
                continue
        logs_filtres.append(entree)
        if len(logs_filtres) >= limit:
            break
    logs_filtres.reverse()

    return {
        "logs": logs_filtres,
        "total": len(logs_filtres),
        "filtres": {
            "dossier": dossier_id,
            "action": action,
        }
    }


# ============================================================================
# Routes de diagnostic sécurité
# ============================================================================

@router.get("/security")
def security_status(request: Request) -> dict:
    """État des permissions RBAC pour le module transit.

    Exige le rôle: lecteur ou supérieur.
    """
    from ..routes.dependencies import _utilisateur_courant

    u = _utilisateur_courant(request)
    if u is None:
        return {"rbac_actif": False, "detail": "RBAC inactif"}

    return {
        "rbac_actif": True,
        "utilisateur": u.nom,
        "roles": sorted(u.roles),
        "dossiers_accessibles": list(u.dossiers),
        "actions_disponibles": [
            action for action, roles in ACTIONS.items()
            if any(u.a_role(role) for role in roles)
        ],
    }


__all__ = [
    "create_dossier", "list_dossiers", "get_dossier", "update_dossier",
    "prise_emplacement", "mettre_a_jour_eta", "bl_receive",
    "creer_frais", "enregistrer_paiement", "exporter_dossier",
    "cloturer_dossier", "audit_logs", "security_status",
]
