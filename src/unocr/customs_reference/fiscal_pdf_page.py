"""Texte natif d'une page PDF fiscal reçu, jamais validation des mesures transcrites."""
import hashlib
from pathlib import Path

from .fiscal_importer import charger_lot_mesures
from .importer import _lire
from .pdf_page import LecturePDFRefusee, extraire_octets_pdf, valider_parametres_pdf


def lire_page_pdf_mesures(repertoire: Path, document_id: str, page: int = 1,
                          limite: int = 4000, decalage: int = 0) -> dict:
    valider_parametres_pdf(document_id,page,limite,decalage)
    lot,rapport = charger_lot_mesures(repertoire)
    texte,nombre,sha,_ = extraire_page_mesures_controlee(repertoire,lot,rapport,document_id,page)
    fragment = texte[decalage:decalage+limite]
    suivant = decalage+len(fragment)
    return {"type_rapport":"lecture_page_pdf_mesures_recu", "type_lot":"mesures",
            "lecture_seule":True, "publication_active":False, "validation_juridique":"non_validee",
            "validation_humaine_requise":True, "archive":rapport["archive"],
            "document_declare":lot.source.model_dump(mode="json"), "sha256_pdf_lu":sha,
            "transcription_sha256":rapport["transcription_sha256"], "transcription_verification":"non_verifiee",
            "lecture_pdf_effectuee":True, "mesures_transcrites_comparees":False,
            "page_physique":page, "nombre_pages_pdf":nombre,
            "page_physique_suivante":page+1 if page < nombre else None,
            "methode":"texte_natif_pdfium_sans_ocr", "texte_natif_non_vide":bool(texte.strip()),
            "authenticite_documentaire":"non_etablie", "completude_reglementaire":"non_etablie",
            "restitution_juridique_a_date":False, "utilisable_pour_calcul_douanier":False,
            "unite_decalage":"points_de_code_unicode_python", "total_caracteres":len(texte),
            "limite":limite, "decalage":decalage, "fragment":fragment,
            "decalage_suivant":suivant if suivant < len(texte) else None,
            "avertissements":["Texte natif de la page, pas mesure extraite ou transcription vérifiée.",
                "Aucun rapprochement des descriptions, taux, références ou périodes transcrits avec le PDF.",
                "Page physique à partir de 1, pas numéro imprimé ; ordre visuel et caractères peuvent différer.",
                "Sans texte natif ne prouve ni page vide ni absence de droit ; aucun OCR automatique.",
                "Aucun PDF brut, rendu ou URL distante ouvert ; archive et rapport d'import inchangés.",
                "Worker séparé borné, pas antivirus, bac à sable OS, mémoire constante ou quota global."]}


def extraire_page_mesures_controlee(repertoire,lot,rapport,document_id,page):
    """Interne : archive et paramètres déjà contrôlés, page native entière bornée."""
    if lot.source.format != "pdf" or lot.source.id != document_id:
        raise LecturePDFRefusee("Source PDF exacte absente du lot de mesures contrôlé")
    nom = "source_mesures_recue.pdf"
    contenu = _lire(repertoire / nom)
    sha = hashlib.sha256(contenu).hexdigest()
    if sha != lot.source.sha256 or sha != rapport["archive"]["fichiers_sha256"][nom]:
        raise LecturePDFRefusee("Empreinte PDF différente après rejeu")
    texte,nombre = extraire_octets_pdf(contenu,page)
    return texte,nombre,sha,lot.source
