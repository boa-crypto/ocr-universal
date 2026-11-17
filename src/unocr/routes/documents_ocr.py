"""Routes de gestion des documents OCR dans les dossiers transit (Module 03)."""

from __future__ import annotations

import time
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import Config, get_config
from ..logging_setup import audit, get_logger
from ..ocr_integration import OCRTransitIntegration, suggest_document_type
from ..rbac import LECTEUR, OPERATEUR
from .dependencies import _exige, _exige_dossier, _utilisateur_ou_ouvert

log = get_logger("documents_ocr")

router = APIRouter(prefix="/api/dossiers", tags=["documents-ocr"])

def _cfg(request: Request) -> Config:
    return getattr(request.app.state, "cfg", None) or get_config()


def _integration(request: Request) -> OCRTransitIntegration:
    return OCRTransitIntegration(_cfg(request).data_dir, config=_cfg(request))


def _acteur(request: Request) -> str:
    return _utilisateur_ou_ouvert(request).nom


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic
# ───────────────────────────────────────────────────────────────

class DocumentOCRCreate(BaseModel):
    dossier_id: str
    job_id: str
    type_document: str = ""  # sera auto-détecté si vide


class DocumentOCRUpdate(BaseModel):
    type_document: Optional[str] = None
    statut: Optional[Literal["extracted", "validated", "corrected"]] = None


class ChampCorrection(BaseModel):
    champ_nom: str
    nouvelle_valeur: str


# ───────────────────────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────────────────────


def _autoriser_dossier(request, dossier_id, role):
    utilisateur = _exige(role)(request)
    _exige_dossier(dossier_id, request)
    return utilisateur


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
    ocr_integration = _integration(request)
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

    audit(_cfg(request).log_dir, "document_ocr_ajoute", dossier_id=dossier_id,
          job_id=doc.job_id, type=type_doc, acteur=_acteur(request))
    return extraction.model_dump()


@router.get("/{dossier_id}/documents-ocr")
def lister_documents_ocr(
    dossier_id: str,
    request: Request,
) -> list[dict]:
    """Lister tous les documents OCR d'un dossier."""
    _autoriser_dossier(request, dossier_id, LECTEUR)
    ocr_integration = _integration(request)
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
    ocr_integration = _integration(request)
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
    ocr_integration = _integration(request)
    extraction = _extraction_du_dossier(ocr_integration, dossier_id, extraction_id)

    update_data = doc_update.model_dump(exclude_unset=True)
    if any(value is None for value in update_data.values()):
        raise HTTPException(422, "les champs fournis ne peuvent pas être nuls")
    for key, value in update_data.items():
        setattr(extraction, key, value)

    extraction.modifie_le = time.strftime("%Y-%m-%d %H:%M:%S")
    ocr_integration.extraction_store.sauvegarder(extraction)
    audit(_cfg(request).log_dir, "document_ocr_modifie", dossier_id=dossier_id,
          extraction_id=extraction_id, acteur=_acteur(request), champs=sorted(update_data))
    return extraction.model_dump()


@router.post("/{dossier_id}/documents-ocr/{extraction_id}/valider")
def valider_document_ocr(
    dossier_id: str,
    extraction_id: str,
    request: Request,
) -> dict:
    """Valider un document OCR (validation humaine)."""
    utilisateur = _autoriser_dossier(request, dossier_id, OPERATEUR)
    ocr_integration = _integration(request)
    _extraction_du_dossier(ocr_integration, dossier_id, extraction_id)
    success = ocr_integration.validate_extraction(extraction_id, utilisateur.nom)
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
    utilisateur = _autoriser_dossier(request, dossier_id, OPERATEUR)
    ocr_integration = _integration(request)
    _extraction_du_dossier(ocr_integration, dossier_id, extraction_id)
    success = ocr_integration.correct_field(extraction_id, correction.champ_nom, correction.nouvelle_valeur, utilisateur.nom)
    if not success:
        raise HTTPException(404, "Document OCR ou champ introuvable")
    extraction = ocr_integration.extraction_store.get(extraction_id)
    return extraction.model_dump()


@router.get("/types-documents")
def lister_types_documents(request: Request) -> list[dict]:
    """Lister tous les types de documents supportés pour le transit."""
    return _integration(request).get_document_types()


@router.post("/{dossier_id}/documents-ocr/auto-classifier")
def auto_classifier_documents(
    dossier_id: str,
    request: Request,
) -> dict:
    """Classifie automatiquement tous les documents non classifiés d'un dossier."""
    _autoriser_dossier(request, dossier_id, OPERATEUR)
    ocr_integration = _integration(request)
    extractions = ocr_integration.extraction_store.par_dossier(dossier_id)

    results = []
    for extraction in extractions:
        if extraction.type_document == "generic" or not extraction.type_document:
            suggested = suggest_document_type(extraction.texte_complet)
            if suggested:
                extraction.type_document = suggested
                extraction.modifie_le = time.strftime("%Y-%m-%d %H:%M:%S")
                ocr_integration.extraction_store.sauvegarder(extraction)
                results.append({
                    "extraction_id": extraction.id,
                    "type_detecte": suggested
                })

    audit(_cfg(request).log_dir, "documents_auto_classes", dossier_id=dossier_id,
          count=len(results), acteur=_acteur(request))
    return {"documents_classes": results}
