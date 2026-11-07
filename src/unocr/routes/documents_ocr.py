"""Routes de gestion des documents OCR dans les dossiers transit (Module 03)."""

from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import get_config
from ..logging_setup import audit, get_logger
from ..ocr_integration import get_ocr_integration, suggest_document_type
from ..rbac import LECTEUR, OPERATEUR
from .dependencies import _exige, _exige_dossier

log = get_logger("documents_ocr")

router = APIRouter(prefix="/api/dossiers", tags=["documents-ocr"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic
# ───────────────────────────────────────────────────────────────

class DocumentOCRCreate(BaseModel):
    dossier_id: str
    job_id: str
    type_document: str = ""  # sera auto-détecté si vide


class DocumentOCRUpdate(BaseModel):
    type_document: Optional[str] = None
    statut: Optional[str] = None  # extracted, validated, corrected


class ChampCorrection(BaseModel):
    champ_nom: str
    nouvelle_valeur: str


# ───────────────────────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────────────────────


def _autoriser_dossier(request, dossier_id, role):
    _exige(role)(request)
    _exige_dossier(dossier_id, request)


def _extraction_du_dossier(integration, dossier_id, extraction_id):
    extraction = integration.extraction_store.get(extraction_id)
    if not extraction:
        raise HTTPException(404, "Document OCR introuvable")
    if extraction.dossier_id != dossier_id:
        raise HTTPException(403, "Ce document n'appartient pas à ce dossier")
    return extraction

@router.post("/{dossier_id}/documents-ocr")
def creer_document_ocr(
    dossier_id: str,
    request: Request,
    doc: DocumentOCRCreate,
) -> dict:
    """Créer un document OCR à partir d'un job traité."""
    _autoriser_dossier(request, dossier_id, OPERATEUR)
    if doc.dossier_id != dossier_id:
        raise HTTPException(422, "dossier_id du corps différent du chemin")
    from .. import api

    api._exige_job(request, doc.job_id)
    store = api._dossiers
    if not store.get(dossier_id):
        raise HTTPException(404, "Dossier introuvable")
    if api.store.get(doc.job_id) is None:
        raise HTTPException(404, "Document introuvable")
    result_json = api.store.load_result(doc.job_id) or {}
    type_doc = doc.type_document
    if not type_doc:
        texte = "\n\n".join(page.get("text", "") for page in result_json.get("pages", []))
        type_doc = suggest_document_type(texte) or "generic"
    ocr_integration = get_ocr_integration()
    extraction = ocr_integration.process_job_result(
        doc.job_id, dossier_id, type_doc, result_json=result_json)
    if not extraction:
        raise HTTPException(400, "Impossible de traiter le résultat OCR")
    filename = result_json.get("source_file", doc.job_id)

    store.ajouter_piece(
        dossier_id,
        doc.job_id,
        filename,
        category=type_doc,
        acteur="systeme"
    )
    store.recalculer_etat(dossier_id, {})

    audit(request.app.state.cfg.log_dir, "document_ocr_ajoute", dossier_id=dossier_id, job_id=doc.job_id, type=type_doc)
    return extraction.model_dump()


@router.get("/{dossier_id}/documents-ocr")
def lister_documents_ocr(
    dossier_id: str,
    request: Request,
) -> list[dict]:
    """Lister tous les documents OCR d'un dossier."""
    _autoriser_dossier(request, dossier_id, LECTEUR)
    ocr_integration = get_ocr_integration()
    extractions = ocr_integration.extraction_store.par_dossier(dossier_id)
    return [e.model_dump() for e in extractions]


@router.get("/{dossier_id}/documents-ocr/{extraction_id}")
def get_document_ocr(
    dossier_id: str,
    extraction_id: str,
    request: Request,
) -> dict:
    """Obtenir un document OCR spécifique."""
    _autoriser_dossier(request, dossier_id, LECTEUR)
    ocr_integration = get_ocr_integration()
    extraction = _extraction_du_dossier(ocr_integration, dossier_id, extraction_id)
    return extraction.model_dump()


@router.put("/{dossier_id}/documents-ocr/{extraction_id}")
def update_document_ocr(
    dossier_id: str,
    extraction_id: str,
    request: Request,
    doc_update: DocumentOCRUpdate,
) -> dict:
    """Mettre à jour un document OCR."""
    _autoriser_dossier(request, dossier_id, OPERATEUR)
    ocr_integration = get_ocr_integration()
    extraction = _extraction_du_dossier(ocr_integration, dossier_id, extraction_id)

    update_data = doc_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(extraction, key, value)

    extraction.modifie_le = time.strftime("%Y-%m-%d %H:%M:%S")
    ocr_integration.extraction_store._ecrire(extraction)
    audit(request.app.state.cfg.log_dir, "document_ocr_modifie", extraction_id=extraction_id)
    return extraction.model_dump()


@router.post("/{dossier_id}/documents-ocr/{extraction_id}/valider")
def valider_document_ocr(
    dossier_id: str,
    extraction_id: str,
    request: Request,
) -> dict:
    """Valider un document OCR (validation humaine)."""
    _autoriser_dossier(request, dossier_id, OPERATEUR)
    ocr_integration = get_ocr_integration()
    _extraction_du_dossier(ocr_integration, dossier_id, extraction_id)
    success = ocr_integration.validate_extraction(extraction_id, "utilisateur")
    if not success:
        raise HTTPException(404, "Document OCR introuvable")
    extraction = ocr_integration.extraction_store.get(extraction_id)
    return extraction.model_dump()


@router.post("/{dossier_id}/documents-ocr/{extraction_id}/corriger")
def corriger_champ_ocr(
    dossier_id: str,
    extraction_id: str,
    request: Request,
    correction: ChampCorrection,
) -> dict:
    """Corriger un champ extrait par l'OCR."""
    _autoriser_dossier(request, dossier_id, OPERATEUR)
    ocr_integration = get_ocr_integration()
    _extraction_du_dossier(ocr_integration, dossier_id, extraction_id)
    success = ocr_integration.correct_field(extraction_id, correction.champ_nom, correction.nouvelle_valeur, "utilisateur")
    if not success:
        raise HTTPException(404, "Document OCR ou champ introuvable")
    extraction = ocr_integration.extraction_store.get(extraction_id)
    return extraction.model_dump()


@router.get("/types-documents")
def lister_types_documents() -> list[dict]:
    """Lister tous les types de documents supportés pour le transit."""
    ocr_integration = get_ocr_integration()
    return ocr_integration.get_document_types()


@router.post("/{dossier_id}/documents-ocr/auto-classifier")
def auto_classifier_documents(
    dossier_id: str,
    request: Request,
) -> dict:
    """Classifie automatiquement tous les documents non classifiés d'un dossier."""
    _autoriser_dossier(request, dossier_id, OPERATEUR)
    ocr_integration = get_ocr_integration()
    extractions = ocr_integration.extraction_store.par_dossier(dossier_id)

    results = []
    for extraction in extractions:
        if extraction.type_document == "generic" or not extraction.type_document:
            suggested = suggest_document_type(extraction.texte_complet)
            if suggested:
                extraction.type_document = suggested
                extraction.modifie_le = time.strftime("%Y-%m-%d %H:%M:%S")
                ocr_integration.extraction_store._ecrire(extraction)
                results.append({
                    "extraction_id": extraction.id,
                    "type_detecte": suggested
                })

    audit(request.app.state.cfg.log_dir, "documents_auto_classes", dossier_id=dossier_id, count=len(results))
    return {"documents_classes": results}
