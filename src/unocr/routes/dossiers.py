"""Routes de gestion des dossiers de transit (Modules 02-08)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, List

from ..models import DossierTransit, Fournisseur, new_id
from ..fournisseur import FournisseurStore
from ..config import get_config
from ..logging_setup import audit, get_logger
from ..dossier import DossierStore

log = get_logger("dossiers")

router = APIRouter(prefix="/api/dossiers", tags=["dossiers"])

cfg = get_config()


class DossierTransitCreate(BaseModel):
    label: str
    profile: str = "personnalise"
    client_id: str = ""
    fournisseur_id: str = ""


class DossierTransitUpdate(BaseModel):
    label: Optional[str] = None
    statut: Optional[str] = None
    agent_responsable: Optional[str] = None
    date_echeance: Optional[str] = None
    pays_origine: Optional[str] = None
    pays_provenance: Optional[str] = None
    port_chargement: Optional[str] = None
    port_dechargement: Optional[str] = None
    compagnie_maritime: Optional[str] = None
    navire: Optional[str] = None
    numero_voyage: Optional[str] = None
    eta: Optional[str] = None
    etd: Optional[str] = None
    numero_bl: Optional[str] = None
    incoterm: Optional[str] = None
    regime_douanier: Optional[str] = None
    position_tarifaire: Optional[str] = None


@router.post("")
def creer_dossier(
    request: Request,
    dossier: DossierTransitCreate,
) -> dict:
    """Créer un nouveau dossier de transit."""
    from ..models import DossierTransit

    store = request.app.state.store
    dossier_obj = DossierTransit(
        id=new_id("dossier_"),
        label=dossier.label,
        profile=dossier.profile,
        client_id=dossier.client_id,
        fournisseur_id=dossier.fournisseur_id,
    )
    store.creer_dossier(dossier_obj.label, dossier_obj.profile)
    # Ajouter la pièce initiale
    store.ajouter_piece(dossier_obj.id, "", dossier_obj.label, "transit")
    audit(cfg.log_dir, "dossier_cree", label=dossier.label, profile=dossier.profile)
    return dossier_obj.as_dict()


@router.get("")
def lister_dossiers(
    request: Request,
) -> list[dict]:
    """Lister tous les dossiers."""
    store = request.app.state.store
    dossiers = store.liste()
    return [d.as_dict() for d in dossiers]


@router.get("/{dossier_id}")
def get_dossier(
    dossier_id: str,
    request: Request,
) -> dict:
    """Obtenir un dossier spécifique."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")
    return dossier.as_dict()


@router.post("/{dossier_id}/pieces")
def ajouter_piece(
    dossier_id: str,
    request: Request,
    job_id: str = Body(...),
    category: str = Body("unknown"),
    filename: str = Body(""),
) -> dict:
    """Ajouter une pièce à un dossier."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.ajouter_piece(dossier_id, job_id, filename, category)
    dossier = store.recalculer_etat(dossier_id, {})
    return dossier.as_dict()


@router.delete("/{dossier_id}/pieces/{job_id}")
def retirer_piece(
    dossier_id: str,
    job_id: str,
    request: Request,
) -> dict:
    """Retirer une pièce d'un dossier."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.retirer_piece(dossier_id, job_id)
    dossier = store.recalculer_etat(dossier_id, {})
    return dossier.as_dict()


@router.post("/{dossier_id}/etat")
def recalculer_etat(
    dossier_id: str,
    request: Request,
    etat_documents: dict,
) -> dict:
    """Recalculer l'état d'un dossier."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.recalculer_etat(dossier_id, etat_documents)
    return {"id": dossier.id, "etat": dossier.state.value}


@router.post("/{dossier_id}/constat")
def noter_constat(
    dossier_id: str,
    request: Request,
    regle: str,
    statut: str,
    motif: str = Body(""),
) -> dict:
    """Noter un constat de cohérence."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.trancher_constat(dossier_id, regle, statut, "utilisateur", motif)
    return {"id": dossier.id, "regle": regle, "statut": statut, "motif": motif}


@router.post("/{dossier_id}/constater")
def constater_etat(
    dossier_id: str,
    request: Request,
    etat: str,
    motif: str = Body(""),
) -> dict:
    """Changer l'état explicite d'un dossier."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.forcer_etat(dossier_id, etat, "utilisateur", motif)
    return {"id": dossier.id, "etat": dossier.state.value, "version": dossier.version}


# Document management
@router.post("/{dossier_id}/documents")
def create_document(
    request: Request, dossier_id: str,
    filename: str = Body(...),
    format: str = Body("")) -> dict:
    from fastapi import HTTPException
    from .rbac import _exige, LECTEUR
    _exige(LECTEUR)(request)
    from .dossier import DossierStore
    from .ingest import load_document
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return {"id": "temp_job", "dossier_id": dossier_id, "filename": filename}


@router.get("/{dossier_id}/documents")
def list_documents(
    request: Request, dossier_id: str) -> list[dict]:
    from fastapi import HTTPException
    from .rbac import _exige, LECTEUR
    _exige(LECTEUR)(request)
    from .dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return [{"id": p.job_id, "filename": p.filename, "category": p.category}
            for p in dossier.pieces]


@router.post("/{dossier_id}/controles/{regle}")
def controles_croises(
    request: Request, dossier_id: str, regle: str) -> dict:
    from fastapi import HTTPException
    from .rbac import _exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return {"id": dossier.id, "regle": regle, "resultat": "applique"}


@router.post("/{dossier_id}/controles")
def controles_croises(
    request: Request, dossier_id: str,
    regles: list[str] = Body(...)) -> dict:
    from fastapi import HTTPException
    from .rbac import _exige, ADMINISTRATEUR
    _exige(ADMINISTRATRICE)(request)
    from .dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    resultats = {}
    for regle in regles:
        resultats[regle] = {"resultat": "applique"}
    return {"id": dossier.id, "resultats": resultats}


# Ferry/transport module
@router.post("/{dossier_id}/ferry")
def ferry_dossier(
    request: Request, dossier_id: str) -> dict:
    from fastapi import HTTPException
    from .rbac import _exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return {"id": dossier.id, "ferry": "termine"}


@router.post("/{dossier_id}/liquidation")
def liquidation_dossier(
    request: Request, dossier_id: str) -> dict:
    from fastapi import HTTPException
    from .rbac import _exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return {"id": dossier.id, "liquidation": "terminee"}


@router.post("/{dossier_id}/cloture")
def cloture_dossier(
    request: Request, dossier_id: str,
    motif: str = Body("")) -> dict:
    from fastapi import HTTPException
    from .rbac import _exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return {"id": dossier.id, "cloture": "terminee", "motif": motif}


# ─────────────────────────────────────────────────────────────
# Module 01 : Clients
# ─────────────────────────────────────────────────────────────

from ..models import Client, ClientStatus
from pydantic import BaseModel
from fastapi import Body
from fastapi import HTTPException
from ..rbac import ADMINISTRATEUR, LECTEUR
from ..api import _exige
from typing import Any, Optional, List
import uuid


class ClientCreate(BaseModel):
    name: str
    legal_name: str
    status: str = "active"
    website: str = ""
    tax_id: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    city: str = ""
    country: str = "DZ"
    region: str = ""
    postal_code: str = ""
    contacts: list[str] = []
    notes: str = ""


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    status: Optional[str] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    contacts: Optional[list[str]] = None
    notes: Optional[str] = None


# In-memory client store (replace with DB later)
_client_store: dict[str, Any] = {}


def _get_client_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'client_store'):
        request.app.state.client_store = {}
    return request.app.state.client_store


@router.post("/clients")
def create_client(
    request: Request,
    client: ClientCreate,
    current_user: Any = Depends(_exige(ADMINISTRATEUR)),
) -> dict:
    """Create a new client."""
    from ..models import Client, ClientStatus

    store = _get_client_store(request)
    client_id = f"client_{uuid.uuid4().hex[:12]}"
    client_obj = {
        "id": client_id,
        "name": client.name,
        "legal_name": client.legal_name,
        "status": client.status,
        "website": client.website,
        "tax_id": client.tax_id,
        "phone": client.phone,
        "email": client.email,
        "address": client.address,
        "city": client.city,
        "country": client.country,
        "region": client.region,
        "postal_code": client.postal_code,
        "contacts": client.contacts,
        "notes": client.notes,
    }
    store[client_id] = client_obj
    return {"id": client_id, **client_obj}


@router.get("/clients")
def list_clients(
    request: Request,
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: Any = Depends(_exige(LECTEUR)),
) -> list[dict]:
    """List all clients."""
    store = _get_client_store(request)
    clients = list(store.values())

    if status:
        clients = [c for c in clients if c.get("status") == status]

    if search:
        search_lower = search.lower()
        clients = [c for c in clients if
            search_lower in c.get("name", "").lower() or
            search_lower in c.get("legal_name", "").lower() or
            search_lower in c.get("tax_id", "").lower() or
            search_lower in c.get("email", "").lower()
        ]

    return clients


@router.get("/clients/{client_id}")
def get_client(
    client_id: str,
    request: Request,
    current_user: Any = Depends(_exige(LECTEUR)),
) -> dict:
    """Get a specific client."""
    store = _get_client_store(request)
    client = store.get(client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")
    return client


@router.put("/clients/{client_id}")
def update_client(
    client_id: str,
    request: Request,
    client_update: ClientUpdate,
    current_user: Any = Depends(_exige(ADMINISTRATEUR)),
) -> dict:
    """Update a client."""
    store = _get_client_store(request)
    client = store.get(client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")

    update_data = client_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        client[key] = value

    return client


@router.delete("/clients/{client_id}")
def delete_client(
    client_id: str,
    request: Request,
    current_user: Any = Depends(_exige(ADMINISTRATEUR)),
) -> dict:
    """Delete a client."""
    store = _get_client_store(request)
    if client_id not in store:
        raise HTTPException(404, "Client introuvable")

    del store[client_id]
    return {"deleted": True, "id": client_id}


@router.get("/clients/{client_id}/dossiers")
def list_client_dossiers(
    client_id: str,
    request: Request,
    current_user: Any = Depends(_exige(LECTEUR)),
) -> list[dict]:
    """List dossiers for a specific client."""
    from .dossier import DossierStore
    store = request.app.state.store
    client_store = _get_client_store(request)

    if client_id not in client_store:
        raise HTTPException(404, "Client introuvable")

    dossiers = store.liste()
    # Filter dossiers by client (assuming dossier has a client field or similar)
    # For now, return all dossiers as the association isn't implemented yet
    return [d.as_dict() for d in dossiers]


# ============================================================
# Routes de gestion de workflow
# ============================================================

from ..models import (
    WorkflowStatus, WorkflowStage, WorkflowStageStatus, WorkflowTemplate,
    WorkflowInstance, DocumentValidation, UserAssignment, WorkflowNotification,
    calculer_progression, obtenir_etapes_non_applicables, peut_passer_suivante
)


class WorkflowInstanceBody(BaseModel):
    template_id: str = ""
    responsable: str = ""


class EtapeStatusBody(BaseModel):
    status: str  # valideur enum en string
    motif: str = ""


class AffectationBody(BaseModel):
    role: str = ""


@router.post("/{dossier_id}/workflow/initialiser")
def workflow_initialiser(
    dossier_id: str,
    request: Request,
    body: WorkflowInstanceBody,
) -> dict:
    """Initialiser un nouveau workflow pour un dossier."""
    from ..dossier import DossierStore
    from ..dossier import _dossiers
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")

    # Vérifier que le dossier a au moins une pièce
    if not dossier.pieces:
        raise HTTPException(422, "Impossible d'initialiser le workflow : dossier sans pièces")

    # Vérifier si un workflow existe déjà
    from ..models import new_id
    workflow_id = f"wf_{dossier_id}"

    # Créer l'instance de workflow
    template = _dossiers.templates.get(body.template_id) if hasattr(_dossiers, 'templates') else None
    if template is None:
        # Template par défaut
        template = WorkflowTemplate(
            id=body.template_id or "default",
            nom="Workflow Transit Maritime",
            description="Workflow standard pour les dossiers de transit maritime",
            actif=True,
        )

    workflow = WorkflowInstance(
        id=workflow_id,
        dossier_id=dossier_id,
        template_id=template.id,
        etapes={},
        statut_global=WorkflowStatus.EN_ATTENTE,
        responsable_global=body.responsable or "",
    )

    # Initialiser toutes les étapes
    for stage in WorkflowStage:
        workflow.etapes[stage] = WorkflowStageStatus(
            stage=stage,
            status=WorkflowStatus.EN_ATTENTE,
            responsable="",
        )

    # Stocker le workflow - on utilise la structure existante
    if not hasattr(dossier, '_workflow'):
        dossier._workflow = workflow_id

    dossier.arbitrages[f"workflow:{workflow_id}"] = workflow.model_dump()
    store.update(dossier)

    # Journaliser
    store._journalise(dossier, "workflow_initialise", {
        "workflow_id": workflow_id,
        "template_id": template.id,
        "responsable": body.responsable,
        "etapes_initiales": len(workflow.etapes),
    })

    progression = calculer_progression(workflow)

    return {
        "workflow_id": workflow_id,
        "dossier_id": dossier_id,
        "template_id": template.id,
        "nom_template": template.nom,
        "statut_global": workflow.statut_global.value,
        "progression": progression,
        "message": "Workflow initialisé avec succès",
    }


@router.get("/{dossier_id}/workflow")
def workflow_obtenir(
    dossier_id: str,
    request: Request,
) -> dict:
    """Récupérer l'état actuel du workflow d'un dossier."""
    from ..dossier import DossierStore
    from ..models import _dossiers
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")

    workflow_id = dossier._workflow if hasattr(dossier, '_workflow') else None
    if not workflow_id or f"workflow:{workflow_id}" not in dossier.arbitrages:
        # Aucun workflow initialisé, retourner un état par défaut
        return {
            "workflow_id": None,
            "dossier_id": dossier_id,
            "template_id": None,
            "statut_global": "en_attente",
            "progression": calculer_progression(None),
            "étapes": {},
            "message": "Aucun workflow initialisé pour ce dossier",
        }

    workflow_data = dossier.arbitrages[f"workflow:{workflow_id}"]
    workflow = WorkflowInstance.model_validate(workflow_data)

    progression = calculer_progression(workflow)
    etapes_non_applicables = obtenir_etapes_non_applicables(workflow)

    return {
        "workflow_id": workflow_id,
        "dossier_id": dossier_id,
        "template_id": workflow.template_id,
        "nom_template": _dossiers.templates.get(workflow.template_id, type('T', (), {'nom': workflow.template_id}))().nom if hasattr(_dossiers, 'templates') else workflow.template_id,
        "statut_global": workflow.statut_global.value,
        "progression": progression,
        "étapes": {stage.value: {
            "status": etape.status.value,
            "date_debut": etape.date_debut,
            "date_fin": etape.date_fin,
            "duree": etape.duree,
            "responsable": etape.responsable,
            "pourcentage": etape.pourcentage,
            "motif_blocage": etape.motif_blocage,
            "détails": etape.détaillés,
        } for stage, etape in workflow.etapes.items()},
        "progression_globale": progression,
        "étapes_non_applicables": etapes_non_applicables,
        "peut_passer_suivante": peut_passer_suivante(workflow),
    }


@router.post("/{dossier_id}/workflow/etape/{stage}")
def workflow_mettre_a_jour_etape(
    dossier_id: str,
    request: Request,
    stage: str,
    body: EtapeStatusBody,
) -> dict:
    """Mettre à jour le statut d'une étape de workflow."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")

    workflow_id = dossier._workflow if hasattr(dossier, '_workflow') else None
    if not workflow_id or f"workflow:{workflow_id}" not in dossier.arbitrages:
        raise HTTPException(404, "Workflow non initialisé pour ce dossier")

    from ..models import WorkflowStage
    try:
        stage_enum = WorkflowStage(stage)
    except ValueError:
        raise HTTPException(422, f"Étape invalide : {stage}")

    workflow_data = dossier.arbitrages[f"workflow:{workflow_id}"]
    workflow = WorkflowInstance.model_validate(workflow_data)

    # Mettre à jour le statut
    etape = workflow.set_etape_status(stage_enum, body.status, body.motif or "")

    # Mettre à jour le statut global
    # Une étape bloquée bloque le global
    if etape.status == WorkflowStatus.BLOQUE:
        workflow.statut_global = WorkflowStatus.BLOQUE
    elif etape.status == WorkflowStatus.A_VALIDER:
        # Si une étape demande une validation, on peut considérer le dossier comme en validation
        if workflow.statut_global not in (WorkflowStatus.BLOQUE,):
            workflow.statut_global = WorkflowStatus.EN_VALIDATION
    elif etape.status == WorkflowStatus.TERMINE:
        # Vérifier si toutes les étapes sont terminées
        toutes_terminees = all(
            wf.etapes[s].status == WorkflowStatus.TERMINE
            for s in WorkflowStage
            if s in wf.etapes
        )
        if toutes_terminees:
            workflow.statut_global = WorkflowStatus.TERMINE

    # Stocker le workflow mis à jour
    dossier.arbitrages[f"workflow:{workflow_id}"] = workflow.model_dump()
    store.update(dossier)

    progression = calculer_progression(workflow)

    # Journaliser
    store._journalise(dossier, "etape_modifiee", {
        "workflow_id": workflow_id,
        "stage": stage,
        "status": body.status,
        "motif": body.motif,
        "progression": progression["globale"],
    })

    return {
        "workflow_id": workflow_id,
        "stage": stage,
        "status": etape.status.value,
        "progression": progression,
        "message": f"Étape {stage} mise à jour : {etape.status.label}",
    }


@router.post("/{dossier_id}/workflow/affecter")
def workflow_affecter_utilisateur(
    dossier_id: str,
    request: Request,
    body: AffectationBody,
) -> dict:
    """Affecter un utilisateur à une étape de workflow."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")

    workflow_id = dossier._workflow if hasattr(dossier, '_workflow') else None
    if not workflow_id or f"workflow:{workflow_id}" not in dossier.arbitrages:
        raise HTTPException(404, "Workflow non initialisé pour ce dossier")

    from ..models import UserAssignment, new_id, WorkflowStage

    workflow_data = dossier.arbitrages[f"workflow:{workflow_id}"]
    workflow = WorkflowInstance.model_validate(workflow_data)

    # Pour l'instant, on stocke l'affectation avec l'étape par défaut
    assignment = UserAssignment(
        id=new_id("ua_"),
        workflow_id=workflow_id,
        utilisateur=body.utilisateur if hasattr(body, 'utilisateur') else "admin",
        rôle=body.role,
        etape=WorkflowStage.ETAPE_1_CREATION,  # Par défaut, à affiner
    )

    if not hasattr(dossier, '_assignations'):
        dossier._assignations = []

    dossier._assignations.append(assignment.model_dump())
    store.update(dossier)

    return {
        "assignment_id": assignment.id,
        "workflow_id": workflow_id,
        "utilisateur": assignment.utilisateur,
        "rôle": assignment.rôle,
        "etape": assignment.etape.value,
        "message": f"Utilisateur {assignment.utilisateur} affecté à l'étape {assignment.etape.value}",
    }


@router.post("/{dossier_id}/workflow/valider")
def workflow_valider_etape(
    dossier_id: str,
    request: Request,
    body: dict,
) -> dict:
    """Valider une étape de workflow (action humaine)."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")

    workflow_id = dossier._workflow if hasattr(dossier, '_workflow') else None
    if not workflow_id or f"workflow:{workflow_id}" not in dossier.arbitrages:
        raise HTTPException(404, "Workflow non initialisé pour ce dossier")

    from ..models import WorkflowStage, WorkflowStatus

    stage_name = body.get("stage", "")
    try:
        stage_enum = WorkflowStage(stage_name)
    except ValueError:
        raise HTTPException(422, f"Étape invalide : {stage_name}")

    workflow_data = dossier.arbitrages[f"workflow:{workflow_id}"]
    workflow = WorkflowInstance.model_validate(workflow_data)

    # Marquer l'étape comme terminée
    etape = workflow.set_etape_status(stage_enum, WorkflowStatus.TERMINE, body.get("responsable", ""))

    # Journaliser
    store._journalise(dossier, "etape_validee", {
        "workflow_id": workflow_id,
        "stage": stage_name,
        "responsable": body.get("responsable", ""),
    })

    # Mettre à jour le workflow stocké
    dossier.arbitrages[f"workflow:{workflow_id}"] = workflow.model_dump()
    store.update(dossier)

    progression = calculer_progression(workflow)

    return {
        "workflow_id": workflow_id,
        "stage": stage_name,
        "status": etape.status.value,
        "progression": progression,
        "message": f"Étape {stage_name} validée par {etape.responsable}",
    }


@router.post("/{dossier_id}/workflow/blocage")
def workflow_declarer_blocage(
    dossier_id: str,
    request: Request,
    body: dict,
) -> dict:
    """Déclarer un blocage sur une étape de workflow."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")

    workflow_id = dossier._workflow if hasattr(dossier, '_workflow') else None
    if not workflow_id or f"workflow:{workflow_id}" not in dossier.arbitrages:
        raise HTTPException(404, "Workflow non initialisé pour ce dossier")

    from ..models import WorkflowStage, WorkflowStatus

    stage_name = body.get("stage", "")
    motif = body.get("motif", "")

    try:
        stage_enum = WorkflowStage(stage_name)
    except ValueError:
        raise HTTPException(422, f"Étape invalide : {stage_name}")

    workflow_data = dossier.arbitrages[f"workflow:{workflow_id}"]
    workflow = WorkflowInstance.model_validate(workflow_data)

    # Marquer l'étape comme bloquée
    etape = workflow.set_etape_status(stage_enum, WorkflowStatus.BLOQUE, body.get("responsable", ""), motif)

    # Mettre à jour le statut global bloqué
    workflow.statut_global = WorkflowStatus.BLOQUE

    # Journaliser
    store._journalise(dossier, "blocage_declare", {
        "workflow_id": workflow_id,
        "stage": stage_name,
        "motif": motif,
        "responsable": body.get("responsable", ""),
    })

    # Mettre à jour le workflow stocké
    dossier.arbitrages[f"workflow:{workflow_id}"] = workflow.model_dump()
    store.update(dossier)

    progression = calculer_progression(workflow)

    return {
        "workflow_id": workflow_id,
        "stage": stage_name,
        "status": etape.status.value,
        "motif": motif,
        "progression": progression,
        "message": f"Blocage déclaré sur l'étape {stage_name}",
    }


@router.post("/{dossier_id}/workflow/lever_blocage")
def workflow_lever_blocage(
    dossier_id: str,
    request: Request,
    body: dict,
) -> dict:
    """Lever un blocage sur une étape de workflow."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")

    workflow_id = dossier._workflow if hasattr(dossier, '_workflow') else None
    if not workflow_id or f"workflow:{workflow_id}" not in dossier.arbitrages:
        raise HTTPException(404, "Workflow non initialisé pour ce dossier")

    from ..models import WorkflowStage

    stage_name = body.get("stage", "")

    try:
        stage_enum = WorkflowStage(stage_name)
    except ValueError:
        raise HTTPException(422, f"Étape invalide : {stage_name}")

    workflow_data = dossier.arbitrages[f"workflow:{workflow_id}"]
    workflow = WorkflowInstance.model_validate(workflow_data)

    # Lever le blocage - passer à EN ATTENTE ou à la prochaine étape
    if stage_enum in workflow.etapes:
        etape = workflow.etapes[stage_enum]
        if etape.status == WorkflowStatus.BLOQUE:
            etape.status = WorkflowStatus.EN_ATTENTE
            etape.motif_blocage = ""
            etape.responsable = ""

    # Vérifier si on peut maintenant débloquer la suite
    if peut_passer_suivante(workflow):
        pass

    # Mettre à jour le statut global
    if all(
        workflow.etapes.get(s, {}).status != WorkflowStatus.BLOQUE
        for s in workflow.etapes
    ):
        # Vérifier si on peut passer à terminer
        if all(
            workflow.etapes.get(s, {}).status == WorkflowStatus.TERMINE
            for s in WorkflowStage
            if s in workflow.etapes
        ):
            workflow.statut_global = WorkflowStatus.TERMINE
        elif workflow.statut_global == WorkflowStatus.BLOQUE:
            # Vérifier si des étapes sont maintenant en cours ou terminées
            if any(
                workflow.etapes.get(s, {}).status == WorkflowStatus.EN_COURS
                for s in workflow.etapes
            ):
                workflow.statut_global = WorkflowStatus.EN_COURS
            else:
                workflow.statut_global = WorkflowStatus.EN_ATTENTE

    # Journaliser
    store._journalise(dossier, "blocage_levé", {
        "workflow_id": workflow_id,
        "stage": stage_name,
    })

    # Mettre à jour le workflow stocké
    dossier.arbitrages[f"workflow:{workflow_id}"] = workflow.model_dump()
    store.update(dossier)

    progression = calculer_progression(workflow)

    return {
        "workflow_id": workflow_id,
        "stage": stage_name,
        "status": etape.status.value,
        "progression": progression,
        "message": f"Blocage levé sur l'étape {stage_name}",
    }


@router.get("/{dossier_id}/workflow/progression")
def workflow_progression(
    dossier_id: str,
    request: Request,
) -> dict:
    """Obtenir uniquement la progression du workflow."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")

    workflow_id = dossier._workflow if hasattr(dossier, '_workflow') else None
    if not workflow_id or f"workflow:{workflow_id}" not in dossier.arbitrages:
        return {
            "progression_globale": 0,
            "etapes_par_statut": {},
            "étape_courante": None,
            "message": "Aucun workflow initialisé",
        }

    workflow_data = dossier.arbitrages[f"workflow:{workflow_id}"]
    from ..models import WorkflowInstance
    workflow = WorkflowInstance.model_validate(workflow_data)

    return calculer_progression(workflow)


@router.post("/{dossier_id}/workflow/non_applicable")
def workflow_marquer_non_applicable(
    dossier_id: str,
    request: Request,
    body: dict,
) -> dict:
    """Marquer une étape comme non applicable avec justification."""
    from ..dossier import DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")

    workflow_id = dossier._workflow if hasattr(dossier, '_workflow') else None
    if not workflow_id or f"workflow:{workflow_id}" not in dossier.arbitrages:
        raise HTTPException(404, "Workflow non initialisé pour ce dossier")

    from ..models import WorkflowStage

    stage_name = body.get("stage", "")

    try:
        stage_enum = WorkflowStage(stage_name)
    except ValueError:
        raise HTTPException(422, f"Étape invalide : {stage_name}")

    motif = body.get("motif", "")

    workflow_data = dossier.arbitrages[f"workflow:{workflow_id}"]
    workflow = WorkflowInstance.model_validate(workflow_data)

    # Marquer l'étape comme non applicable
    if stage_enum in workflow.etapes:
        etape = workflow.etapes[stage_enum]
        etape.status = WorkflowStatus.NON_APPLICABLE
        etape.motif_blocage = motif
        # Ajouter une justification dans détails
        etape.détaillés["justification"] = motif

    # Journaliser
    store._journalise(dossier, "etape_non_applicable", {
        "workflow_id": workflow_id,
        "stage": stage_name,
        "motif": motif,
    })

    # Mettre à jour le workflow stocké
    dossier.arbitrages[f"workflow:{workflow_id}"] = workflow.model_dump()
    store.update(dossier)

    progression = calculer_progression(workflow)

    return {
        "workflow_id": workflow_id,
        "stage": stage_name,
        "status": etape.status.value,
        "motif": motif,
        "progression": progression,
        "message": f"Étape {stage_name} marquée comme non applicable",
    }