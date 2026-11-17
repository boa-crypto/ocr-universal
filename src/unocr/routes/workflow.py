"""Routes du workflow opérationnel maritime, persistantes et cloisonnées."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import get_config
from ..logging_setup import get_logger
from ..rbac import LECTEUR, OPERATEUR
from ..workflow import LIBELLES, STAGES, WorkflowStore
from .dependencies import _exige, _exige_dossier, _utilisateur_ou_ouvert

log = get_logger("workflow")
router = APIRouter(prefix="/api/workflow", tags=["workflow"])


class TransitionRequest(BaseModel):
    to_stage: str = Field(min_length=1, max_length=32)
    motif: str = Field(default="", max_length=2000)
    expected_version: Optional[int] = Field(default=None, ge=1)


class WorkflowCreate(BaseModel):
    dossier_id: str = Field(min_length=1, max_length=128)
    template_id: str = "default"


def _cfg(request: Request):
    return getattr(request.app.state, "cfg", None) or get_config()


def _acteur(request: Request) -> str:
    return _utilisateur_ou_ouvert(request).nom


@router.get("/template")
@router.get("/workflow/template", include_in_schema=False)
async def get_workflow_template(request: Request,
                                current_user=Depends(_exige(LECTEUR))) -> dict:
    return {
        "id": "default", "nom": "Workflow Maritime Standard",
        "description": "Workflow standard pour dossier transit maritime",
        "etapes": [{"id": stage, "nom": LIBELLES[stage], "ordre": i + 1}
                   for i, stage in enumerate(STAGES)],
    }


@router.post("/create")
@router.post("/workflow/create", include_in_schema=False)
async def create_workflow(request: Request, body: WorkflowCreate,
                          current_user=Depends(_exige(OPERATEUR))) -> dict:
    _exige_dossier(body.dossier_id, request)
    workflow, cree = WorkflowStore(_cfg(request)).creer(body.dossier_id, _acteur(request),
                                                       body.template_id)
    return {"workflow_id": workflow.id, "created": cree, **workflow.vue()}


@router.get("/{dossier_id}")
@router.get("/workflow/{dossier_id}", include_in_schema=False)
async def get_workflow_status(dossier_id: str, request: Request,
                              current_user=Depends(_exige(LECTEUR))) -> dict:
    _exige_dossier(dossier_id, request)
    workflow = WorkflowStore(_cfg(request)).get(dossier_id)
    if workflow is None:
        raise HTTPException(404, "Workflow introuvable pour ce dossier")
    return workflow.vue()


@router.post("/{dossier_id}/transition")
@router.post("/workflow/{dossier_id}/transition", include_in_schema=False)
async def execute_transition(dossier_id: str, request: Request, body: TransitionRequest,
                             current_user=Depends(_exige(OPERATEUR))) -> dict:
    _exige_dossier(dossier_id, request)
    utilisateur = _utilisateur_ou_ouvert(request)
    workflow = WorkflowStore(_cfg(request)).transition(
        dossier_id, body.to_stage, utilisateur.nom, body.motif,
        utilisateur=utilisateur, expected_version=body.expected_version,
    )
    return {"success": True, "message": f"Transition vers {workflow.current_stage} enregistrée",
            "new_stage": workflow.current_stage, **workflow.vue()}


@router.get("/{dossier_id}/historique")
@router.get("/workflow/{dossier_id}/historique", include_in_schema=False)
async def get_workflow_history(dossier_id: str, request: Request,
                               current_user=Depends(_exige(LECTEUR))) -> list:
    _exige_dossier(dossier_id, request)
    workflow = WorkflowStore(_cfg(request)).get(dossier_id)
    if workflow is None:
        raise HTTPException(404, "Workflow introuvable pour ce dossier")
    return workflow.historique
