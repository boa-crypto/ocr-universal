"""Routes de gestion du Workflow Opérationnel Maritime (Module E)."""

from __future__ import annotations

import time
from typing import Dict, Optional

from fastapi import APIRouter, Body, Depends, Request
from pydantic import BaseModel

from ..config import get_config
from ..logging_setup import get_logger
from ..models import (
    WorkflowInstance,
)
from ..rbac import LECTEUR
from ..routes.dependencies import _exige

log = get_logger("workflow")

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Modèles de requête/réponse
# ───────────────────────────────────────────────────────────────

class TransitionRequest(BaseModel):
    """Requête de transition d'état."""
    to_stage: str
    responsable: str = ""
    motif: str = ""
    forcer: bool = False


class WorkflowCreate(BaseModel):
    """Création d'un workflow pour un dossier."""
    dossier_id: str
    template_id: Optional[str] = None


class WorkflowResponse(BaseModel):
    """Réponse workflow."""
    id: str
    dossier_id: str
    template_id: str
    current_stage: str
    status: str
    progress: float
    etapes: Dict[str, dict]
    responsable_global: str
    created_at: float
    updated_at: float


# ───────────────────────────────────────────────────────────────
# Moteur de Workflow
# ───────────────────────────────────────────────────────────────

class WorkflowEngine:
    """Moteur de gestion des transitions de workflow."""

    # Transitions autorisées : (from_stage, to_stage) -> conditions
    TRANSITIONS_AUTORISEES = {
        ("creation", "scan"): {"roles": ["operateur", "superviseur"], "auto": True},
        ("scan", "ocr"): {"roles": ["operateur", "superviseur"], "auto": True},
        ("ocr", "verification"): {"roles": ["operateur", "superviseur"], "auto": True},
        ("verification", "douane"): {"roles": ["superviseur", "administrateur"], "auto": False},
        ("douane", "port"): {"roles": ["superviseur", "administrateur"], "auto": False},
        ("port", "transport"): {"roles": ["superviseur", "administrateur"], "auto": False},
        ("transport", "cloture"): {"roles": ["superviseur", "administrateur"], "auto": False},
        # Transitions de retour / correction
        ("verification", "scan"): {"roles": ["superviseur", "administrateur"], "raison_requise": True},
        ("douane", "verification"): {"roles": ["superviseur", "administrateur"], "raison_requise": True},
        ("port", "douane"): {"roles": ["superviseur", "administrateur"], "raison_requise": True},
        ("transport", "port"): {"roles": ["superviseur", "administrateur"], "raison_requise": True},
        # Annulation / blocage
        ("*", "bloque"): {"roles": ["superviseur", "administrateur"], "raison_requise": True},
        ("bloque", "*"): {"roles": ["superviseur", "administrateur"], "raison_requise": True},
    }

    # Ordre des étapes pour calcul de progression
    STAGE_ORDER = [
        "creation",
        "scan",
        "ocr",
        "verification",
        "douane",
        "port",
        "transport",
        "cloture",
    ]

    def __init__(self):
        self.workflows: Dict[str, "WorkflowInstance"] = {}

    def get_workflow(self, workflow_id: str) -> Optional["WorkflowInstance"]:
        """Récupère un workflow par ID."""
        # TODO: récupérer depuis stockage persistant
        return None

    def create_workflow(self, dossier_id: str, template_id: str = "default") -> "WorkflowInstance":
        """Crée un nouveau workflow pour un dossier."""
        from ..models import (
            WorkflowInstance,
            WorkflowTemplate,
        )

        # Template par défaut
        template = WorkflowTemplate(
            id="default",
            nom="Workflow Maritime Standard",
            description="Workflow standard pour dossier transit maritime",
        )

        workflow = WorkflowInstance(
            dossier_id=dossier_id,
            template_id=template.id,
        )

        # Initialiser les étapes
        for stage in self.STAGE_ORDER:
            workflow.etapes[stage] = {
                "status": "en_attente" if stage != "creation" else "en_cours",
                "started_at": None,
                "completed_at": None,
                "responsable": "",
                "pourcentage": 0.0,
            }
        workflow.etapes["creation"]["status"] = "en_cours"
        workflow.etapes["creation"]["started_at"] = time.time()

        return workflow

    def can_transition(self, workflow: "WorkflowInstance", from_stage: str, to_stage: str,
                       user_role: str, user_id: str = "") -> tuple[bool, str]:
        """Vérifie si une transition est autorisée."""
        if (from_stage, to_stage) not in self.TRANSITIONS_AUTORISEES:
            return False, f"Transition non autorisée: {from_stage} -> {to_stage}"

        rule = self.TRANSITIONS_AUTORISEES[(from_stage, to_stage)]

        # Vérifier rôle
        if "roles" in rule:
            if user_role not in rule["roles"]:
                return False, f"Rôle insuffisant: {user_role} (requis: {rule['roles']})"

        # Vérifier raison si requise
        if rule.get("raison_requise") and not hasattr(self, "_raison_transition"):
            # La raison sera fournie dans la requête
            pass

        return True, ""

    def execute_transition(self, workflow_id: str, to_stage: str,
                           user_role: str, user_id: str,
                           motif: str = "") -> tuple[bool, str]:
        """Exécute une transition d'état."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False, "Workflow introuvable"

        can, reason = self.can_transition(workflow, workflow.current_stage, to_stage, "operateur")
        if not can:
            return False, reason

        # TODO: implémenter la transition effective
        return True, "Transition effectuée"

    def get_workflow_status(self, workflow_id: str) -> Optional[dict]:
        """Retourne l'état complet du workflow."""
        return None


# Instance globale du moteur
workflow_engine = WorkflowEngine()


# ───────────────────────────────────────────────────────────────
# Routes API
# ───────────────────────────────────────────────────────────────

@router.post("/workflow/create")
async def create_workflow(
    request: Request,
    dossier_id: str = Body(...),
    template_id: str = Body(default="default"),
    current_user: str = Depends(_exige(LECTEUR)),
) -> dict:
    """Crée un nouveau workflow pour un dossier."""
    workflow = workflow_engine.create_workflow(dossier_id, template_id)
    # TODO: sauvegarder en base
    return {
        "workflow_id": getattr(workflow, "id", f"wf_{dossier_id}"),
        "dossier_id": dossier_id,
        "status": "created",
        "current_stage": "creation",
    }


@router.get("/workflow/{dossier_id}")
async def get_workflow_status(
    dossier_id: str,
    request: Request,
    current_user: str = Depends(_exige(LECTEUR)),
) -> dict:
    """Récupère l'état complet du workflow d'un dossier."""
    # TODO: récupérer depuis stockage
    return {
        "dossier_id": dossier_id,
        "current_stage": "creation",
        "status": "en_cours",
        "progress": 12.5,
        "etapes": {
            "creation": {"status": "en_cours", "progress": 0},
            "scan": {"status": "en_attente", "progress": 0},
            "ocr": {"status": "en_attente", "progress": 0},
            "verification": {"status": "en_attente", "progress": 0},
            "douane": {"status": "en_attente", "progress": 0},
            "port": {"status": "en_attente", "progress": 0},
            "transport": {"status": "en_attente", "progress": 0},
            "cloture": {"status": "en_attente", "progress": 0},
        },
        "progress_global": 12.5,
    }


@router.post("/workflow/{dossier_id}/transition")
async def execute_transition(
    dossier_id: str,
    request: Request,
    to_stage: str = Body(...),
    motif: str = Body(default=""),
    current_user: str = Depends(_exige(LECTEUR)),
) -> dict:
    """Exécute une transition d'état."""
    # TODO: implémenter la transition réelle
    return {
        "success": True,
        "message": f"Transition vers {to_stage} effectuée",
        "new_stage": "scan",
    }


@router.get("/workflow/{dossier_id}/historique")
async def get_workflow_history(
    dossier_id: str,
    request: Request,
    current_user: str = Depends(_exige(LECTEUR)),
) -> list:
    """Récupère l'historique des transitions d'un workflow."""
    return []


@router.get("/workflow/template")
async def get_workflow_template(
    request: Request,
    current_user: str = Depends(_exige(LECTEUR)),
) -> dict:
    """Récupère le template de workflow par défaut."""
    return {
        "id": "default",
        "nom": "Workflow Maritime Standard",
        "description": "Workflow standard pour dossier transit maritime",
        "etapes": [
            {"id": "creation", "nom": "Création dossier", "ordre": 1},
            {"id": "scan", "nom": "Numérisation", "ordre": 2},
            {"id": "ocr", "nom": "OCR & Extraction", "ordre": 3},
            {"id": "verification", "nom": "Vérification", "ordre": 4},
            {"id": "douane", "nom": "Douane & Déclaration", "ordre": 5},
            {"id": "port", "nom": "Port & Manutention", "ordre": 6},
            {"id": "transport", "nom": "Transport & Livraison", "ordre": 7},
            {"id": "cloture", "nom": "Clôture & Archivage", "ordre": 8},
        ],
    }
