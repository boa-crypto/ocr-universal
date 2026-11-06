"""Lecture native d'un PDF reçu en quarantaine, pas validation de transcription."""
import hashlib
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

from .article_detail import MAX_DECALAGE_TEXTE, MAX_FRAGMENT
from .importer import _lire
from .legal_comparison import charger_lot_code
from .pdf_worker import MAX_CARACTERES, MAX_PAGES


class ParamPDFInvalide(ValueError):
    """Document/page/plage invalide avant toute lecture du magasin."""


class LecturePDFRefusee(ValueError):
    """PDF absent, illisible, chiffré ou hors limites de l'extracteur."""


def lire_page_pdf(repertoire: Path, document_id: str, page: int = 1, limite: int = 4000, decalage: int = 0) -> dict:
    if (not isinstance(document_id, str) or not document_id.strip() or len(document_id) > 256
            or any(unicodedata.category(c) == "Cc" for c in document_id)):
        raise ParamPDFInvalide("ID documentaire exact de 256 caractères maximum sans contrôle requis")
    if type(page) is not int or not 1 <= page <= MAX_PAGES:
        raise ParamPDFInvalide("Page physique entière de 1 à 10000 requise")
    if type(limite) is not int or not 1 <= limite <= MAX_FRAGMENT:
        raise ParamPDFInvalide("Limite entière de 1 à 16000 requise")
    if type(decalage) is not int or not 0 <= decalage <= MAX_DECALAGE_TEXTE:
        raise ParamPDFInvalide("Décalage entier de 0 à 67108864 requis")
    lot, rapport = charger_lot_code(repertoire)
    selection = next(((i, d) for i, d in enumerate(lot.documents, 1) if d.id == document_id), None)
    if selection is None:
        raise LecturePDFRefusee("Document absent du lot contrôlé")
    numero, document = selection
    nom = f"document_{numero:04d}.pdf"
    contenu = _lire(repertoire / nom)
    sha = hashlib.sha256(contenu).hexdigest()
    if sha != document.sha256 or sha != rapport["archive"]["fichiers_sha256"][nom]:
        raise LecturePDFRefusee("Empreinte du document différente après contrôle")
    try:
        resultat = subprocess.run([sys.executable, str(Path(__file__).with_name("pdf_worker.py")), str(page)],
                                  input=contenu, capture_output=True, timeout=15)
        if resultat.returncode != 0 or len(resultat.stdout) > 3 * 1024 * 1024:
            raise LecturePDFRefusee("PDF illisible, chiffré, page absente ou limites atteintes")
        extraction = json.loads(resultat.stdout)
        texte, nombre = extraction["texte"], extraction["nombre_pages"]
        if (not isinstance(texte, str) or len(texte) > MAX_CARACTERES or type(nombre) is not int
                or not page <= nombre <= MAX_PAGES):
            raise ValueError("Réponse extracteur invalide")
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError):
        raise LecturePDFRefusee("PDF non lisible ou extracteur indisponible/hors limites") from None
    fragment = texte[decalage:decalage + limite]
    suivant = decalage + len(fragment)
    return {"type_rapport": "lecture_page_pdf_recu", "lecture_seule": True, "publication_active": False,
            "validation_juridique": "non_validee", "validation_humaine_requise": True,
            "archive": rapport["archive"], "document_declare": document.model_dump(mode="json"),
            "sha256_pdf_lu": sha, "page_physique": page, "nombre_pages_pdf": nombre,
            "page_physique_suivante": page + 1 if page < nombre else None,
            "methode": "texte_natif_pdfium_sans_ocr", "texte_natif_non_vide": bool(texte.strip()),
            "transcription_verification": "non_verifiee", "authenticite_documentaire": "non_etablie",
            "completude_reglementaire": "non_etablie", "restitution_juridique_a_date": False,
            "unite_decalage": "points_de_code_unicode_python", "total_caracteres": len(texte),
            "limite": limite, "decalage": decalage, "fragment": fragment,
            "decalage_suivant": suivant if suivant < len(texte) else None,
            "avertissements": ["Texte natif extrait par le moteur PDF, pas transcription juridiquement vérifiée.",
                               "Sans texte natif ne signifie ni PDF vide ni absence de droit ; aucun OCR automatique.",
                               "Page physique à partir de 1, pas numéro imprimé du JO ; aucun article localisé automatiquement.",
                               "Ordre visuel, caractères et retours à la ligne peuvent différer du document affiché.",
                               "Aucune URL distante suivie, aucun PDF source remis au navigateur ou rendu graphique.",
                               "Processus séparé et bornes, pas antivirus ni bac à sable OS ou garantie matérielle."]}
