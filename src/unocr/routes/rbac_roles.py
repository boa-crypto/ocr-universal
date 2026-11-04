"""Routes de gestion des rôles, permissions, workflows et notifications (Module 20)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, List

from ..models import Role, Permission, Workflow, Notification, JournalAudit, new_id
from ..config import get_config
from ..logging_setup import audit, get_logger
from ..rbac import ADMINISTRATEUR, LECTEUR

log = get_logger("rbac_roles")

router = APIRouter(prefix="/api/rbac", tags=["rbac"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Stores en mémoire
# ───────────────────────────────────────────────────────────────

_role_store: dict[str, Role] = {}
_permission_store: dict[str, Permission] = {}
_workflow_store: dict[str, Workflow] = {}
_notification_store: dict[str, Notification] = {}
_journal_audit_store: dict[str, JournalAudit] = {}


def _get_role_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'role_store'):
        request.app.state.role_store = {}
    return request.app.state.role_store


def _get_permission_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'permission_store'):
        request.app.state.permission_store = {}
    return request.app.state.permission_store


def _get_workflow_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'workflow_store'):
        request.app.state.workflow_store = {}
    return request.app.state.workflow_store


def _get_notification_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'notification_store'):
        request.app.state.notification_store = {}
    return request.app.state.notification_store


def _get_journal_audit_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'journal_audit_store'):
        request.app.state.journal_audit_store = {}
    return request.app.state.journal_audit_store


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic
# ───────────────────────────────────────────────────────────────

class RoleCreate(BaseModel):
    nom: str
    description: str = ""
    niveau_acces: int = 1
    permissions: List[str] = []


class RoleUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    niveau_acces: Optional[int] = None
    permissions: Optional[List[str]] = None


class PermissionCreate(BaseModel):
    nom: str
    ressource: str = ""
    action: str = ""
    description: str = ""


class PermissionUpdate(BaseModel):
    nom: Optional[str] = None
    ressource: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None


class WorkflowCreate(BaseModel):
    nom: str
    description: str = ""
    etapes: List[dict[str, Any]] = []
    conditions_entree: dict[str, Any] = {}
    conditions_validation: dict[str, Any] = {}
    actions_automatiques: List[dict[str, Any]] = []
    actif: bool = True


class WorkflowUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    etapes: Optional[List[dict[str, Any]]] = None
    conditions_entree: Optional[dict[str, Any]] = None
    conditions_validation: Optional[dict[str, Any]] = None
    actions_automatiques: Optional[List[dict[str, Any]]] = None
    actif: Optional[bool] = None


class NotificationCreate(BaseModel):
    dossier_id: str
    type_notification: str = ""
    destinataire: str = ""
    message: str = ""
    methode: str = "interne"


# ───────────────────────────────────────────────────────────────
# Routes Rôles
# ───────────────────────────────────────────────────────────────

@router.post("/roles")
def create_role(
    request: Request,
    role: RoleCreate,
) -> dict:
    """Créer un nouveau rôle."""
    store = _get_role_store(request)
    role_obj = Role(
        id=new_id("role_"),
        nom=role.nom,
        description=role.description,
        niveau_acces=role.niveau_acces,
        permissions=role.permissions,
    )
    store[role_obj.id] = role_obj
    audit(cfg.log_dir, "role_cree", nom=role.nom)
    return role_obj.model_dump()


@router.get("/roles")
def list_roles(
    request: Request,
) -> list[dict]:
    """Lister tous les rôles."""
    store = _get_role_store(request)
    return [r.model_dump() for r in store.values()]


@router.get("/roles/{role_id}")
def get_role(
    role_id: str,
    request: Request,
) -> dict:
    """Obtenir un rôle spécifique."""
    store = _get_role_store(request)
    role = store.get(role_id)
    if not role:
        raise HTTPException(404, "Rôle introuvable")
    return role.model_dump()


@router.put("/roles/{role_id}")
def update_role(
    role_id: str,
    request: Request,
    role_update: RoleUpdate,
) -> dict:
    """Mettre à jour un rôle."""
    store = _get_role_store(request)
    role = store.get(role_id)
    if not role:
        raise HTTPException(404, "Rôle introuvable")

    update_data = role_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(role, key, value)

    audit(cfg.log_dir, "role_modifie", cible=role_id)
    return role.model_dump()


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: str,
    request: Request,
) -> dict:
    """Supprimer un rôle."""
    store = _get_role_store(request)
    if role_id not in store:
        raise HTTPException(404, "Rôle introuvable")
    del store[role_id]
    audit(cfg.log_dir, "role_supprime", cible=role_id)
    return {"deleted": True, "id": role_id}


# ───────────────────────────────────────────────────────────────
# Routes Permissions
# ───────────────────────────────────────────────────────────────

@router.post("/permissions")
def create_permission(
    request: Request,
    permission: PermissionCreate,
) -> dict:
    """Créer une nouvelle permission."""
    store = _get_permission_store(request)
    perm_obj = Permission(
        id=new_id("perm_"),
        nom=permission.nom,
        ressource=permission.ressource,
        action=permission.action,
        description=permission.description,
    )
    store[perm_obj.id] = perm_obj
    audit(cfg.log_dir, "permission_creee", nom=permission.nom)
    return perm_obj.model_dump()


@router.get("/permissions")
def list_permissions(
    request: Request,
) -> list[dict]:
    """Lister toutes les permissions."""
    store = _get_permission_store(request)
    return [p.model_dump() for p in store.values()]


@router.get("/permissions/{permission_id}")
def get_permission(
    permission_id: str,
    request: Request,
) -> dict:
    """Obtenir une permission spécifique."""
    store = _get_permission_store(request)
    perm = store.get(permission_id)
    if not perm:
        raise HTTPException(404, "Permission introuvable")
    return perm.model_dump()


@router.put("/permissions/{permission_id}")
def update_permission(
    permission_id: str,
    request: Request,
    permission_update: PermissionUpdate,
) -> dict:
    """Mettre à jour une permission."""
    store = _get_permission_store(request)
    perm = store.get(permission_id)
    if not perm:
        raise HTTPException(404, "Permission introuvable")

    update_data = permission_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(perm, key, value)

    audit(cfg.log_dir, "permission_modifiee", cible=permission_id)
    return perm.model_dump()


@router.delete("/permissions/{permission_id}")
def delete_permission(
    permission_id: str,
    request: Request,
) -> dict:
    """Supprimer une permission."""
    store = _get_permission_store(request)
    if permission_id not in store:
        raise HTTPException(404, "Permission introuvable")
    del store[permission_id]
    audit(cfg.log_dir, "permission_supprimee", cible=permission_id)
    return {"deleted": True, "id": permission_id}


# ───────────────────────────────────────────────────────────────
# Routes Workflows
# ───────────────────────────────────────────────────────────────

@router.post("/workflows")
def create_workflow(
    request: Request,
    workflow: WorkflowCreate,
) -> dict:
    """Créer un nouveau workflow."""
    store = _get_workflow_store(request)
    wf_obj = Workflow(
        id=new_id("wf_"),
        nom=workflow.nom,
        description=workflow.description,
        etapes=workflow.etapes,
        conditions_entree=workflow.conditions_entree,
        conditions_validation=workflow.conditions_validation,
        actions_automatiques=workflow.actions_automatiques,
        actif=workflow.actif,
    )
    store[wf_obj.id] = wf_obj
    audit(cfg.log_dir, "workflow_cree", nom=workflow.nom)
    return wf_obj.model_dump()


@router.get("/workflows")
def list_workflows(
    request: Request,
) -> list[dict]:
    """Lister tous les workflows."""
    store = _get_workflow_store(request)
    return [w.model_dump() for w in store.values()]


@router.get("/workflows/{workflow_id}")
def get_workflow(
    workflow_id: str,
    request: Request,
) -> dict:
    """Obtenir un workflow spécifique."""
    store = _get_workflow_store(request)
    wf = store.get(workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow introuvable")
    return wf.model_dump()


@router.put("/workflows/{workflow_id}")
def update_workflow(
    workflow_id: str,
    request: Request,
    workflow_update: WorkflowUpdate,
) -> dict:
    """Mettre à jour un workflow."""
    store = _get_workflow_store(request)
    wf = store.get(workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow introuvable")

    update_data = workflow_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(wf, key, value)

    audit(cfg.log_dir, "workflow_modifie", cible=workflow_id)
    return wf.model_dump()


@router.delete("/workflows/{workflow_id}")
def delete_workflow(
    workflow_id: str,
    request: Request,
) -> dict:
    """Supprimer un workflow."""
    store = _get_workflow_store(request)
    if workflow_id not in store:
        raise HTTPException(404, "Workflow introuvable")
    del store[workflow_id]
    audit(cfg.log_dir, "workflow_supprime", cible=workflow_id)
    return {"deleted": True, "id": workflow_id}


# ───────────────────────────────────────────────────────────────
# Routes Notifications
# ───────────────────────────────────────────────────────────────

@router.post("/notifications")
def create_notification(
    request: Request,
    notification: NotificationCreate,
) -> dict:
    """Créer une nouvelle notification."""
    store = _get_notification_store(request)
    notif_obj = Notification(
        id=new_id("notif_"),
        dossier_id=notification.dossier_id,
        type_notification=notification.type_notification,
        destinataire=notification.destinataire,
        message=notification.message,
        methode=notification.methode,
    )
    store[notif_obj.id] = notif_obj
    audit(cfg.log_dir, "notification_creee", type=notification.type_notification)
    return notif_obj.model_dump()


@router.get("/notifications")
def list_notifications(
    request: Request,
    dossier_id: Optional[str] = None,
) -> list[dict]:
    """Lister toutes les notifications."""
    store = _get_notification_store(request)
    notifs = list(store.values())
    if dossier_id:
        notifs = [n for n in notifs if n.dossier_id == dossier_id]
    return [n.model_dump() for n in notifs]


@router.get("/notifications/{notification_id}")
def get_notification(
    notification_id: str,
    request: Request,
) -> dict:
    """Obtenir une notification spécifique."""
    store = _get_notification_store(request)
    notif = store.get(notification_id)
    if not notif:
        raise HTTPException(404, "Notification introuvable")
    return notif.model_dump()


@router.post("/notifications/{notification_id}/lire")
def marquer_notification_lue(
    notification_id: str,
    request: Request,
) -> dict:
    """Marquer une notification comme lue."""
    store = _get_notification_store(request)
    notif = store.get(notification_id)
    if not notif:
        raise HTTPException(404, "Notification introuvable")
    notif.statut = "lue"
    audit(cfg.log_dir, "notification_lue", notification=notification_id)
    return notif.model_dump()


# ───────────────────────────────────────────────────────────────
# Routes Journal d'Audit
# ───────────────────────────────────────────────────────────────

@router.get("/audit")
def list_audit(
    request: Request,
    limit: int = 100,
    action: Optional[str] = None,
    ressource_type: Optional[str] = None,
    utilisateur: Optional[str] = None,
) -> list[dict]:
    """Lister le journal d'audit."""
    store = _get_journal_audit_store(request)
    audits = list(store.values())

    if action:
        audits = [a for a in audits if a.action == action]
    if ressource_type:
        audits = [a for a in audits if a.ressource_type == ressource_type]
    if utilisateur:
        audits = [a for a in audits if a.utilisateur == utilisateur]

    audits.sort(key=lambda a: a.date_creation, reverse=True)
    return [a.model_dump() for a in audits[:limit]]


@router.post("/audit")
def create_audit_entry(
    request: Request,
    action: str,
    ressource_type: str,
    ressource_id: str,
    utilisateur: str,
    details: dict[str, Any] = {},
) -> dict:
    """Ajouter une entrée au journal d'audit."""
    store = _get_journal_audit_store(request)
    audit_obj = JournalAudit(
        id=new_id("audit_"),
        action=action,
        ressource_type=ressource_type,
        ressource_id=ressource_id,
        utilisateur=utilisateur,
        details=details,
    )
    store[audit_obj.id] = audit_obj
    return audit_obj.model_dump()