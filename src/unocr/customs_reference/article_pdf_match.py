"""Présence littérale d'un fragment dans une page native, sans attestation humaine."""
import unicodedata
from pathlib import Path

from .article_detail import CHAMPS_TEXTE, MAX_DECALAGE_TEXTE, MAX_FRAGMENT
from .legal_comparison import charger_lot_code
from .pdf_page import extraire_page_controlee
from .pdf_worker import MAX_PAGES


class ParamRapprochementInvalide(ValueError):
    """Fragment/page invalides avant chargement du lot."""


def rapprocher_fragment_article_pdf(repertoire: Path, article_id: str, page: int,
                                    champ: str = "texte_integral", limite: int = 4000, decalage: int = 0) -> dict:
    if (not isinstance(article_id, str) or not article_id.strip() or len(article_id) > 256
            or any(unicodedata.category(c) in {"Cc", "Cs"} for c in article_id)):
        raise ParamRapprochementInvalide("ID exact non blanc sans contrôle de 256 caractères maximum requis")
    if not isinstance(champ, str) or champ not in CHAMPS_TEXTE:
        raise ParamRapprochementInvalide("Champ de transcription inconnu")
    if type(page) is not int or not 1 <= page <= MAX_PAGES:
        raise ParamRapprochementInvalide("Page physique entière de 1 à 10000 requise")
    if type(limite) is not int or not 1 <= limite <= MAX_FRAGMENT:
        raise ParamRapprochementInvalide("Limite entière de 1 à 16000 requise")
    if type(decalage) is not int or not 0 <= decalage <= MAX_DECALAGE_TEXTE:
        raise ParamRapprochementInvalide("Décalage entier de 0 à 67108864 requis")
    lot, rapport = charger_lot_code(repertoire)
    article = next((a for a in lot.articles if a.id == article_id), None)
    document = next((d for d in lot.documents if article and d.id == article.reference.source_id), None)
    texte = getattr(article, champ) if article else None
    fragment = texte[decalage:decalage + limite] if texte is not None else None
    suivant = decalage + len(fragment) if fragment is not None else None
    natif, nombre, sha, debut = None, None, None, None
    correspondance = None
    if article is None:
        constat = "article_absent_du_lot"
    elif texte is None:
        constat = "champ_absent"
    elif not fragment:
        constat = "fragment_vide"
    elif not fragment.strip():
        constat = "fragment_sans_caractere_non_blanc"
    else:
        natif, nombre, sha, document = extraire_page_controlee(repertoire, lot, rapport, document.id, page)
        if not natif.strip():
            constat = "texte_natif_absent"
        else:
            position = natif.find(fragment)
            correspondance = position >= 0
            debut = position if correspondance else None
            constat = "correspondance_litterale_trouvee" if correspondance else "correspondance_litterale_non_trouvee"
    return {"type_rapport": "rapprochement_litteral_fragment_article_pdf", "lecture_seule": True,
            "publication_active": False, "validation_juridique": "non_validee", "validation_humaine_requise": True,
            "archive": rapport["archive"], "article_id_exact": article_id, "article_trouve": article is not None,
            "version_declaree": article.model_dump(mode="json", include={"id", "numero_article", "nature_version",
                "version_juridique", "reference", "validation_juridique"}) if article else None,
            "document_declare": document.model_dump(mode="json") if document else None,
            "champ_texte": champ, "texte_renseigne": texte is not None,
            "fragment_article": fragment, "limite": limite, "decalage": decalage,
            "total_caracteres_article": len(texte) if texte is not None else None,
            "decalage_suivant": suivant if texte is not None and suivant < len(texte) else None,
            "page_physique_demandee": page, "page_choisie_explicitement": True,
            "extraction_effectuee": natif is not None, "sha256_pdf_lu": sha, "nombre_pages_pdf": nombre,
            "total_caracteres_page": len(natif) if natif is not None else None,
            "texte_natif_non_vide": bool(natif.strip()) if natif is not None else None,
            "constat": constat, "fragment_present_litteralement": correspondance,
            "position_debut_pdf": debut, "position_fin_pdf_exclusive": debut + len(fragment) if debut is not None else None,
            "occurrence_restituee": "premiere_uniquement_sans_denombrement",
            "unite_decalage": "points_de_code_unicode_python", "methode": "texte_natif_pdfium_sans_ocr",
            "transcription_verification": "non_verifiee", "authenticite_documentaire": "non_etablie",
            "completude_reglementaire": "non_etablie", "restitution_juridique_a_date": False,
            "avertissements": [
                "Recherche littérale d'un seul fragment dans une seule page explicitement choisie de sa source déclarée.",
                "Aucune localisation automatique depuis le numéro d'article ou le localisateur libre ; page physique, pas page imprimée.",
                "Sans normalisation, traduction ou OCR ; ordre, espaces, retours et glyphes extraits peuvent différer de l'affichage.",
                "Présence ne prouve ni unicité, emplacement juridique, fidélité du reste de l'article ou authenticité du document.",
                "Absence de correspondance ne prouve pas erreur de transcription ; absence de texte natif reste indéterminée.",
                "Fragment vide/blanc ou champ absent : aucune extraction, aucune correspondance positive déduite.",
                "Aucune attestation humaine, consolidation, publication ou donnée applicable à un calcul douanier réel.",
            ]}
