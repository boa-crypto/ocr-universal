"""Copie binaire du PDF reçu : intégrité locale, pas authenticité ou innocuité."""
import hashlib
import unicodedata
from pathlib import Path

from .importer import _lire
from .legal_comparison import charger_lot_code
from .pdf_page import LecturePDFRefusee, ParamPDFInvalide


def copier_pdf_source(repertoire: Path, document_id: str) -> tuple[dict, bytes]:
    if (not isinstance(document_id, str) or not document_id.strip() or len(document_id) > 256
            or any(unicodedata.category(c) in {"Cc", "Cs"} for c in document_id)):
        raise ParamPDFInvalide("ID source exact non blanc sans contrôle, de 256 caractères maximum requis")
    lot, rapport = charger_lot_code(repertoire)
    selection = next(((i,d) for i,d in enumerate(lot.documents,1) if d.id == document_id),None)
    if selection is None:
        raise LecturePDFRefusee("Document absent du lot contrôlé")
    numero,document = selection
    nom = f"document_{numero:04d}.pdf"
    contenu = _lire(repertoire / nom)
    sha = hashlib.sha256(contenu).hexdigest()
    if sha != document.sha256 or sha != rapport["archive"]["fichiers_sha256"][nom]:
        raise LecturePDFRefusee("Empreinte PDF différente après rejeu")
    return {"type_rapport":"copie_pdf_source_recue", "lecture_seule":True, "publication_active":False,
            "validation_juridique":"non_validee", "authenticite_documentaire":"non_etablie",
            "archive":rapport["archive"], "document_declare":document.model_dump(mode="json"),
            "sha256_pdf_copie":sha, "taille_octets":len(contenu),
            "nom_telechargement":f"uniocr-source-non-validee-{sha}.pdf"},contenu
