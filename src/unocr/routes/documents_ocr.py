"""Routes de gestion des documents OCR dans les dossiers transit (Module 03)."""

from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import get_config
from ..logging_setup import audit, get_logger
from ..ocr_integration import get_ocr_integration, suggest_document_type

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

@router.post("/{dossier_id}/documents-ocr")
def creer_document_ocr(
    dossier_id: str,
    request: Request,
    doc: DocumentOCRCreate,
) -> dict:
    """Créer un document OCR à partir d'un job traité."""
    ocr_integration = get_ocr_integration()

    # Vérifier que le dossier existe
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")

    # Auto-détecter le type si non fourni
    type_doc = doc.type_document
    if not type_doc:
        from ..storage import JobStore
        job_store = JobStore(cfg)
        result_json = job_store.load_result(doc.job_id)
        if result_json:
            texte = "\n\n".join(
                page.get("text", "") for page in result_json.get("pages", [])
            )
            type_doc = suggest_document_type(texte) or "generic"

    # Traiter le job OCR
    extraction = ocr_integration.process_job_result(doc.job_id, dossier_id, type_doc)
    if not extraction:
        raise HTTPException(400, "Impossible de traiter le résultat OCR")

    # Ajouter la pièce au dossier
    from ..storage import JobStore
    job_store = JobStore(cfg)
    result_json = job_store.load_result(doc.job_id) or {}
    filename = result_json.get("source_file", doc.job_id)

    dossier = store.ajouter_piece(
        dossier_id,
        doc.job_id,
        filename,
        category=type_doc,
        acteur="systeme"
    )
    dossier = store.recalculer_etat(dossier_id, {})

    audit(cfg.log_dir, "document_ocr_ajoute", dossier_id=dossier_id, job_id=doc.job_id, type=type_doc)
    return extraction.model_dump()


@router.get("/{dossier_id}/documents-ocr")
def lister_documents_ocr(
    dossier_id: str,
    request: Request,
) -> list[dict]:
    """Lister tous les documents OCR d'un dossier."""
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
    ocr_integration = get_ocr_integration()
    extraction = ocr_integration.extraction_store.get(extraction_id)
    if not extraction:
        raise HTTPException(404, "Document OCR introuvable")
    if extraction.dossier_id != dossier_id:
        raise HTTPException(403, "Ce document n'appartient pas à ce dossier")
    return extraction.model_dump()


@router.put("/{dossier_id}/documents-ocr/{extraction_id}")
def update_document_ocr(
    dossier_id: str,
    extraction_id: str,
    request: Request,
    doc_update: DocumentOCRUpdate,
) -> dict:
    """Mettre à jour un document OCR."""
    ocr_integration = get_ocr_integration()
    extraction = ocr_integration.extraction_store.get(extraction_id)
    if not extraction:
        raise HTTPException(404, "Document OCR introuvable")
    if extraction.dossier_id != dossier_id:
        raise HTTPException(403, "Ce document n'appartient pas à ce dossier")

    update_data = doc_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(extraction, key, value)

    extraction.modifie_le = time.strftime("%Y-%m-%d %H:%M:%S")
    ocr_integration.extraction_store._ecrire(extraction)
    audit(cfg.log_dir, "document_ocr_modifie", extraction_id=extraction_id)
    return extraction.model_dump()


@router.post("/{dossier_id}/documents-ocr/{extraction_id}/valider")
def valider_document_ocr(
    dossier_id: str,
    extraction_id: str,
    request: Request,
) -> dict:
    """Valider un document OCR (validation humaine)."""
    ocr_integration = get_ocr_integration()
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
    ocr_integration = get_ocr_integration()
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

    audit(cfg.log_dir, "documents_auto_classes", dossier_id=dossier_id, count=len(results))
    return {"documents_classes": results}
