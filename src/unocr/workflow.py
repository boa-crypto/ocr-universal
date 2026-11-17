"""Workflow opérationnel maritime persistant.

Un seul workflow par dossier, conservé dans le magasin métier SQLite déjà
sauvegardé. Ce module ne prétend pas remplacer les preuves douanières ou
portuaires : il ordonne les étapes déclaratives et trace qui les a franchies.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .business_links import exiger_dossier
from .business_store import BusinessStore
from .logging_setup import audit
from .rbac import OPERATEUR, SUPERVISEUR

STAGES = ("creation", "scan", "ocr", "verification", "douane", "port", "transport", "cloture")
LIBELLES = {
    "creation": "Création dossier", "scan": "Numérisation", "ocr": "OCR & Extraction",
    "verification": "Vérification", "douane": "Douane & Déclaration",
    "port": "Port & Manutention", "transport": "Transport & Livraison",
    "cloture": "Clôture & Archivage",
}
TRANSITIONS = {
    ("creation", "scan"): (OPERATEUR, False),
    ("scan", "ocr"): (OPERATEUR, False),
    ("ocr", "verification"): (OPERATEUR, False),
    ("verification", "douane"): (SUPERVISEUR, False),
    ("douane", "port"): (SUPERVISEUR, False),
    ("port", "transport"): (SUPERVISEUR, False),
    ("transport", "cloture"): (SUPERVISEUR, True),
    ("verification", "scan"): (SUPERVISEUR, True),
    ("douane", "verification"): (SUPERVISEUR, True),
    ("port", "douane"): (SUPERVISEUR, True),
    ("transport", "port"): (SUPERVISEUR, True),
}


class WorkflowOperationnel(BaseModel):
    id: str
    dossier_id: str
    template_id: str = "default"
    current_stage: str = "creation"
    status: str = "en_cours"
    progress: float = 12.5
    etapes: dict[str, dict[str, Any]] = Field(default_factory=dict)
    responsable_global: str = ""
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    historique: list[dict[str, Any]] = Field(default_factory=list)
    avant_blocage: str = ""
    version: int = 1

    def vue(self) -> dict[str, Any]:
        data = self.model_dump()
        data["progress_global"] = self.progress
        return data


def _progress(stage: str) -> float:
    if stage == "bloque":
        return 0.0
    return round((STAGES.index(stage) + 1) * 100.0 / len(STAGES), 2)


def _etapes_initiales(acteur: str) -> dict[str, dict[str, Any]]:
    maintenant = time.time()
    return {
        stage: {
            "status": "en_cours" if stage == "creation" else "en_attente",
            "started_at": maintenant if stage == "creation" else None,
            "completed_at": None,
            "responsable": acteur if stage == "creation" else "",
            "pourcentage": 100.0 if stage == "creation" else 0.0,
            "motif": "",
        }
        for stage in STAGES
    }


class WorkflowStore:
    def __init__(self, cfg: Any):
        self.cfg = cfg
        self.store = BusinessStore(cfg.data_dir / "metier.sqlite3", "workflow_operationnel",
                                   WorkflowOperationnel)

    def get(self, dossier_id: str) -> Optional[WorkflowOperationnel]:
        return self.store.get("wf_" + dossier_id)

    def creer(self, dossier_id: str, acteur: str, template_id: str = "default") -> tuple[WorkflowOperationnel, bool]:
        if template_id != "default":
            raise HTTPException(422, "Template de workflow inconnu")
        with self.store.transaction() as transaction:
            exiger_dossier(self.cfg, dossier_id, absent=404)
            existant = transaction.get("wf_" + dossier_id)
            if existant is not None:
                if existant.template_id != template_id:
                    raise HTTPException(409, "Le dossier utilise déjà un autre template")
                return existant, False
            maintenant = time.time()
            workflow = WorkflowOperationnel(
                id="wf_" + dossier_id, dossier_id=dossier_id, template_id=template_id,
                etapes=_etapes_initiales(acteur), responsable_global=acteur,
                created_at=maintenant, updated_at=maintenant,
                historique=[{"evenement": "workflow_cree", "stage": "creation",
                             "acteur": acteur, "motif": "", "ts": maintenant, "version": 1}],
            )
            transaction[workflow.id] = workflow
        audit(self.cfg.log_dir, "workflow_cree", dossier=dossier_id, acteur=acteur)
        return workflow, True

    def transition(self, dossier_id: str, to_stage: str, acteur: str,
                   motif: str = "", utilisateur: Any = None,
                   expected_version: Optional[int] = None) -> WorkflowOperationnel:
        if to_stage not in (*STAGES, "bloque"):
            raise HTTPException(422, "Étape de workflow inconnue")
        with self.store.transaction() as transaction:
            exiger_dossier(self.cfg, dossier_id, absent=404)
            workflow = transaction.get("wf_" + dossier_id)
            if workflow is None:
                raise HTTPException(404, "Workflow introuvable pour ce dossier")
            if expected_version is not None and expected_version != workflow.version:
                raise HTTPException(409, "Version du workflow obsolète")
            courant = workflow.current_stage
            if courant == "cloture":
                raise HTTPException(409, "Un workflow clôturé ne peut plus transitionner")
            motif = motif.strip()
            if courant == "bloque":
                if to_stage != workflow.avant_blocage:
                    raise HTTPException(409, "Déblocage uniquement vers l'étape précédant le blocage")
                role, motif_requis = SUPERVISEUR, True
            elif to_stage == "bloque":
                role, motif_requis = SUPERVISEUR, True
            else:
                regle = TRANSITIONS.get((courant, to_stage))
                if regle is None:
                    raise HTTPException(409, f"Transition non autorisée : {courant} -> {to_stage}")
                role, motif_requis = regle
            if utilisateur is not None and not utilisateur.a_role(role):
                audit(self.cfg.log_dir, "workflow_transition_refusee", dossier=dossier_id,
                      acteur=acteur, raison="role", requis=role)
                raise HTTPException(403, f"Rôle « {role} » requis pour cette transition")
            if motif_requis and not motif:
                raise HTTPException(422, "Un motif est requis pour cette transition")

            maintenant = time.time()
            precedent = workflow.current_stage
            if to_stage == "bloque":
                workflow.avant_blocage = courant
                workflow.current_stage = "bloque"
                workflow.status = "bloque"
                etape = workflow.etapes.get(courant, {})
                etape.update(status="bloque", motif=motif, responsable=acteur)
                workflow.etapes[courant] = etape
            else:
                if precedent == "bloque":
                    workflow.avant_blocage = ""
                ancienne = workflow.etapes.get(precedent)
                if ancienne is not None and precedent != "bloque":
                    ancienne.update(status="termine", completed_at=maintenant,
                                    pourcentage=100.0, responsable=acteur)
                cible = workflow.etapes.setdefault(to_stage, {})
                statut_cible = "termine" if to_stage == "cloture" else "en_cours"
                cible.update(status=statut_cible, started_at=cible.get("started_at") or maintenant,
                             completed_at=maintenant if to_stage == "cloture" else None,
                             responsable=acteur, pourcentage=100.0 if to_stage == "cloture" else 0.0,
                             motif="")
                workflow.current_stage = to_stage
                workflow.status = "termine" if to_stage == "cloture" else "en_cours"
                workflow.progress = _progress(to_stage)
            workflow.responsable_global = acteur
            workflow.updated_at = maintenant
            workflow.version += 1
            workflow.historique.append({
                "evenement": "workflow_transition", "de": precedent, "vers": workflow.current_stage,
                "acteur": acteur, "motif": motif, "ts": maintenant, "version": workflow.version,
            })
            transaction[workflow.id] = workflow
        audit(self.cfg.log_dir, "workflow_transition", dossier=dossier_id, acteur=acteur,
              de=precedent, vers=workflow.current_stage, motif=motif, version=workflow.version)
        return workflow
