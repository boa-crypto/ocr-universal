"""Intégration OCR ↔ Dossiers Transit (Module 03 - GED et OCR Intelligent).

Ce module connecte le moteur OCR existant d'UniOCR aux modèles de transit maritime.
Il peuple automatiquement ExtractionOCR et ChampExtrait depuis les résultats OCR.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import get_config
from .logging_setup import audit, get_logger
from .models import (
    ChampExtrait,
    ExtractionOCR,
    FieldValue,
    new_id,
)

log = get_logger("ocr_integration")

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Store persistant pour les extractions OCR
# ───────────────────────────────────────────────────────────────

class ExtractionOCRStore:
    """Persistance JSON des extractions OCR, sous `data/extractions_ocr/`."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, ExtractionOCR] = {}

    def _chemin(self, extraction_id: str) -> Path:
        return self.root / f"{extraction_id}.json"

    def _lire(self, extraction_id: str) -> Optional[ExtractionOCR]:
        if extraction_id in self._cache:
            return self._cache[extraction_id]
        p = self._chemin(extraction_id)
        if not p.is_file():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            log.error("extraction illisible (%s) : %s", p.name, exc)
            return None
        extraction = ExtractionOCR(**data)
        self._cache[extraction_id] = extraction
        return extraction

    def _ecrire(self, extraction: ExtractionOCR) -> None:
        tmp = self._chemin(extraction.id).with_suffix(".tmp")
        tmp.write_text(json.dumps(extraction.model_dump(), ensure_ascii=False, indent=1),
                       encoding="utf-8")
        tmp.replace(self._chemin(extraction.id))
        self._cache[extraction.id] = extraction

    def creer(self, **kwargs) -> ExtractionOCR:
        extraction = ExtractionOCR(id=new_id("ocr_"), **kwargs)
        self._ecrire(extraction)
        return extraction

    def get(self, extraction_id: str) -> Optional[ExtractionOCR]:
        return self._lire(extraction_id)

    def liste(self) -> List[ExtractionOCR]:
        extractions = []
        for p in sorted(self.root.glob("*.json")):
            e = self._lire(p.stem)
            if e:
                extractions.append(e)
        extractions.sort(key=lambda e: e.cree_le, reverse=True)
        return extractions

    def par_dossier(self, dossier_id: str) -> List[ExtractionOCR]:
        """Récupère toutes les extractions d'un dossier."""
        return [e for e in self.liste() if e.dossier_id == dossier_id]


# ───────────────────────────────────────────────────────────────
# Types de documents supportés pour le transit maritime
# ───────────────────────────────────────────────────────────────

TYPES_DOCUMENTS_TRANSIT = {
    "invoice": {
        "nom": "Facture commerciale",
        "code": "invoice",
        "profil": "invoice",
        "champs_cles": ["invoice_number", "invoice_date", "seller", "buyer", "total_amount", "currency", "incoterm", "items"]
    },
    "proforma_invoice": {
        "nom": "Facture pro forma",
        "code": "proforma_invoice",
        "profil": "invoice",
        "champs_cles": ["invoice_number", "invoice_date", "seller", "buyer", "total_amount", "currency", "incoterm"]
    },
    "packing_list": {
        "nom": "Liste de colisage (Packing List)",
        "code": "packing_list",
        "profil": "packing_list",
        "champs_cles": ["invoice_number", "gross_weight", "net_weight", "packages_count", "container_numbers", "items"]
    },
    "bill_of_lading": {
        "nom": "Connaissement maritime (Bill of Lading)",
        "code": "bill_of_lading",
        "profil": "port_bl",
        "champs_cles": ["bl_number", "vessel", "voyage", "port_load", "port_discharge", "shipper", "consignee", "notify_party", "container_numbers", "packages_count", "gross_weight", "goods_description"]
    },
    "certificate_of_origin": {
        "nom": "Certificat d'origine",
        "code": "certificate_of_origin",
        "profil": "generic",
        "champs_cles": ["certificate_number", "issue_date", "exporter", "importer", "country_origin", "goods_description", "hs_code"]
    },
    "certificate_of_conformity": {
        "nom": "Certificat de conformité",
        "code": "certificate_of_conformity",
        "profil": "generic",
        "champs_cles": ["certificate_number", "issue_date", "product", "standard", "validity"]
    },
    "phytosanitary_certificate": {
        "nom": "Certificat phytosanitaire",
        "code": "phytosanitary_certificate",
        "profil": "generic",
        "champs_cles": ["certificate_number", "issue_date", "exporter", "importer", "country_origin", "plant_description", "treatment"]
    },
    "veterinary_certificate": {
        "nom": "Certificat vétérinaire",
        "code": "veterinary_certificate",
        "profil": "generic",
        "champs_cles": ["certificate_number", "issue_date", "exporter", "importer", "animal_products", "health_status"]
    },
    "bank_document": {
        "nom": "Document bancaire",
        "code": "bank_document",
        "profil": "generic",
        "champs_cles": ["document_type", "reference", "amount", "currency", "date", "bank", "beneficiary"]
    },
    "insurance_certificate": {
        "nom": "Attestation d'assurance",
        "code": "insurance_certificate",
        "profil": "generic",
        "champs_cles": ["policy_number", "insured", "coverage", "amount", "currency", "valid_from", "valid_to"]
    },
    "mandate": {
        "nom": "Mandat / Procuration",
        "code": "mandate",
        "profil": "generic",
        "champs_cles": ["mandate_number", "grantor", "grantee", "powers", "valid_from", "valid_to"]
    },
    "commercial_register": {
        "nom": "Registre de commerce",
        "code": "commercial_register",
        "profil": "generic",
        "champs_cles": ["rc_number", "company_name", "legal_form", "capital", "address", "manager", "registration_date"]
    },
    "customs_declaration": {
        "nom": "Déclaration en douane",
        "code": "customs_declaration",
        "profil": "generic",
        "champs_cles": ["declaration_number", "date", "importer", "exporter", "hs_code", "value", "duties", "regime"]
    },
    "delivery_order": {
        "nom": "Bon à délivrer (Delivery Order)",
        "code": "delivery_order",
        "profil": "generic",
        "champs_cles": ["do_number", "bl_number", "consignee", "container_numbers", "release_date"]
    },
    "release_note": {
        "nom": "Mainlevée",
        "code": "release_note",
        "profil": "generic",
        "champs_cles": ["release_number", "declaration_number", "date", "customs_office", "status"]
    },
    "exit_note": {
        "nom": "Bon de sortie",
        "code": "exit_note",
        "profil": "generic",
        "champs_cles": ["exit_number", "container_number", "date", "driver", "vehicle", "terminal"]
    },
    "delivery_note": {
        "nom": "Bon de livraison",
        "code": "delivery_note",
        "profil": "generic",
        "champs_cles": ["delivery_number", "date", "customer", "items", "received_by", "signature"]
    },
    "port_fees_invoice": {
        "nom": "Facture frais portuaires",
        "code": "port_fees_invoice",
        "profil": "generic",
        "champs_cles": ["invoice_number", "date", "terminal", "container_number", "services", "amount", "currency"]
    },
}


# ───────────────────────────────────────────────────────────────
# Service d'intégration principal
# ───────────────────────────────────────────────────────────────

class OCRTransitIntegration:
    """Service principal d'intégration OCR vers dossiers transit."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.extraction_store = ExtractionOCRStore(data_dir / "extractions_ocr")
        self.types_store = data_dir / "document_types"
        self.types_store.mkdir(parents=True, exist_ok=True)

    def process_job_result(self, job_id: str, dossier_id: str, document_type: str,
                           *, result_json: Optional[dict] = None) -> Optional[ExtractionOCR]:
        """
        Traite le résultat d'un job OCR et crée l'extraction structurée.

        Args:
            job_id: ID du job OCR terminé
            dossier_id: ID du dossier de transit associé
            document_type: Type de document (ex: "invoice", "bill_of_lading")

        Returns:
            ExtractionOCR créée ou None si erreur
        """
        from .models import DocumentResult
        from .storage import JobStore

        if result_json is None:
            job_store = JobStore(cfg)
            result_json = job_store.load_result(job_id)
        if not result_json:
            log.warning("Aucun résultat OCR pour job %s", job_id)
            return None

        result = DocumentResult.model_validate(result_json)

        # Construire le texte complet
        texte_complet = "\n\n".join(
            page.text for page in result.pages if page.text
        )

        # Créer l'extraction OCR
        extraction = ExtractionOCR(
            id=new_id("ocr_"),
            document_id=job_id,
            dossier_id=dossier_id,
            type_document=document_type,
            texte_complet=texte_complet,
            pages=result.pages,
            champs_extraits=self._convert_fields(result.fields),
            classification=result.classification,
            confiance_globale=result.quality.mean_global_confidence if result.quality else 0.0,
            statut="extracted",
            cree_le=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        self.extraction_store._ecrire(extraction)

        # Audit
        audit(cfg.log_dir, "ocr_extraction_creee",
              job_id=job_id, dossier_id=dossier_id,
              type=document_type, champs=len(extraction.champs_extraits))

        return extraction

    def _convert_fields(self, fields: Dict[str, FieldValue]) -> List[ChampExtrait]:
        """Convertit les champs FieldValue en ChampExtrait."""
        champs = []
        for nom, fv in fields.items():
            champ = ChampExtrait(
                id=new_id("champ_"),
                extraction_id="",  # sera mis à jour après
                nom=nom,
                valeur_raw=fv.raw_value or "",
                valeur_normale=fv.normalized_value,
                valeur_confirmee=fv.confirmed_value,
                valeur_correctee=fv.corrected_value,
                origine=fv.value_origin.value if fv.value_origin else "ocr",
                confiance=fv.confidence,
                page_num=fv.page_num,
                bbox=fv.bbox,
                statut=fv.status.value if fv.status else "detected",
                anomalies=fv.anomalies or [],
            )
            champs.append(champ)
        return champs

    def validate_extraction(self, extraction_id: str, user: str) -> bool:
        """Valide une extraction OCR par un humain."""
        extraction = self.extraction_store.get(extraction_id)
        if not extraction:
            return False

        extraction.statut = "validated"
        extraction.modifie_le = time.strftime("%Y-%m-%d %H:%M:%S")
        self.extraction_store._ecrire(extraction)
        audit(cfg.log_dir, "ocr_extraction_validee", extraction_id=extraction_id, user=user)
        return True

    def correct_field(self, extraction_id: str, champ_nom: str, nouvelle_valeur: str, user: str) -> bool:
        """Corrige un champ extrait."""
        extraction = self.extraction_store.get(extraction_id)
        if not extraction:
            return False

        for champ in extraction.champs_extraits:
            if champ.nom == champ_nom:
                champ.valeur_correctee = nouvelle_valeur
                champ.valeur_confirmee = nouvelle_valeur
                champ.origine = "corrected"
                champ.statut = "corrected"
                break

        extraction.modifie_le = time.strftime("%Y-%m-%d %H:%M:%S")
        self.extraction_store._ecrire(extraction)
        audit(cfg.log_dir, "ocr_champ_corrige", extraction_id=extraction_id, champ=champ_nom, user=user)
        return True

    def get_document_types(self) -> List[Dict[str, Any]]:
        """Retourne la liste des types de documents supportés."""
        return [
            {"code": k, **v} for k, v in TYPES_DOCUMENTS_TRANSIT.items()
        ]


# ───────────────────────────────────────────────────────────────
# Instance globale (initialisée dans api.py)
# ───────────────────────────────────────────────────────────────

_ocr_integration: Optional[OCRTransitIntegration] = None


def get_ocr_integration() -> OCRTransitIntegration:
    """Récupère l'instance globale d'intégration OCR."""
    global _ocr_integration
    if _ocr_integration is None:
        _ocr_integration = OCRTransitIntegration(cfg.data_dir)
    return _ocr_integration


# ───────────────────────────────────────────────────────────────
# Helpers pour classification automatique
# ───────────────────────────────────────────────────────────────

def suggest_document_type(texte: str) -> Optional[str]:
    """
    Suggère le type de document basé sur le texte extrait.
    Utilise des mots-clés simples (le classificateur complet est dans classification.py).
    """
    texte_upper = texte.upper()

    # Scores par type
    scores = {}

    # Facture
    if any(kw in texte_upper for kw in ["INVOICE", "FACTURE", "TOTAL HT", "TOTAL TTC", "TVA", "MONTANT"]):
        scores["invoice"] = scores.get("invoice", 0) + 3

    # BL
    if any(kw in texte_upper for kw in ["BILL OF LADING", "CONNAISSEMENT", "SHIPPER", "CONSIGNEE", "NOTIFY PARTY", "VESSEL", "VOYAGE"]):
        scores["bill_of_lading"] = scores.get("bill_of_lading", 0) + 3

    # Packing List
    if any(kw in texte_upper for kw in ["PACKING LIST", "LISTE DE COLISAGE", "GROSS WEIGHT", "NET WEIGHT", "PACKAGES", "COLIS"]):
        scores["packing_list"] = scores.get("packing_list", 0) + 3

    # Certificat origine
    if any(kw in texte_upper for kw in ["CERTIFICATE OF ORIGIN", "CERTIFICAT D'ORIGINE", "COUNTRY OF ORIGIN", "PAYS D'ORIGINE"]):
        scores["certificate_of_origin"] = scores.get("certificate_of_origin", 0) + 3

    # Certificat phytosanitaire
    if any(kw in texte_upper for kw in ["PHYTOSANITARY", "PHYTOSANITAIRE", "IPPC"]):
        scores["phytosanitary_certificate"] = scores.get("phytosanitary_certificate", 0) + 3

    # Certificat vétérinaire
    if any(kw in texte_upper for kw in ["VETERINARY", "VÉTÉRINAIRE", "VETERINAIRE"]):
        scores["veterinary_certificate"] = scores.get("veterinary_certificate", 0) + 3

    # Mainlevée
    if any(kw in texte_upper for kw in ["MAINLEVÉE", "MAINLEVEE", "RELEASE"]):
        scores["release_note"] = scores.get("release_note", 0) + 3

    # Bon à délivrer
    if any(kw in texte_upper for kw in ["BON À DÉLIVRER", "BON A DELIVRER", "DELIVERY ORDER"]):
        scores["delivery_order"] = scores.get("delivery_order", 0) + 3

    if not scores:
        return None

    return max(scores, key=scores.get)
