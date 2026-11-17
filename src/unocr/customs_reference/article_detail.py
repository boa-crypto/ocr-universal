"""Lecture exacte d'une transcription par fragments, sans validation juridique."""
import unicodedata
from pathlib import Path

from .legal_comparison import charger_lot_code

CHAMPS_TEXTE = ("texte_integral", "texte_francais", "texte_arabe", "texte_origine", "texte_modificatif")
MAX_FRAGMENT = 16_000
MAX_DECALAGE_TEXTE = 64 * 1024 * 1024


class ParamArticleInvalide(ValueError):
    """Identifiant, champ ou plage de lecture invalide avant lecture du lot."""


def consulter_article(repertoire: Path, article_id: str, champ: str = "texte_integral",
                      limite: int = 4000, decalage: int = 0) -> dict:
    if (not isinstance(article_id, str) or not article_id.strip() or len(article_id) > 256
            or any(unicodedata.category(c) == "Cc" for c in article_id)):
        raise ParamArticleInvalide("ID exact non blanc, sans contrôle, de 256 caractères maximum requis")
    if not isinstance(champ, str) or champ not in CHAMPS_TEXTE:
        raise ParamArticleInvalide("Champ de texte déclaré inconnu")
    if type(limite) is not int or not 1 <= limite <= MAX_FRAGMENT:
        raise ParamArticleInvalide("Limite entière de 1 à 16000 caractères requise")
    if type(decalage) is not int or not 0 <= decalage <= MAX_DECALAGE_TEXTE:
        raise ParamArticleInvalide("Décalage entier de 0 à 67108864 requis")
    lot, rapport = charger_lot_code(repertoire)
    article = next((a for a in lot.articles if a.id == article_id), None)
    document = next((d for d in lot.documents if article and d.id == article.reference.source_id), None)
    texte = getattr(article, champ) if article is not None else None
    fragment = texte[decalage:decalage + limite] if texte is not None else None
    suivant = decalage + len(fragment) if fragment is not None else None
    champs_metadata = {"id", "numero_article", "intitule", "hierarchie", "nature_version", "version_juridique",
                       "reference", "date_publication", "date_entree_vigueur", "date_fin_validite", "date_abrogation",
                       "reference_jo", "numero_jo", "statut_juridique_declare", "validation_juridique"}
    metadata = article.model_dump(mode="json", include=champs_metadata) if article else None
    if metadata:
        for cle in ("date_publication", "date_entree_vigueur", "date_fin_validite", "date_abrogation"):
            metadata[cle + "_declaree"] = metadata.pop(cle)
    return {
        "type_rapport": "lecture_article_documentaire", "perimetre": "une_version_dans_un_lot_en_quarantaine",
        "lecture_seule": True, "publication_active": False, "validation_juridique": "non_validee",
        "validation_humaine_requise": True, "completude_reglementaire": "non_etablie",
        "restitution_juridique_a_date": False, "transcription_verification": "non_verifiee",
        "archive": rapport["archive"], "article_id_exact": article_id, "article_trouve": article is not None,
        "version_declaree": metadata, "document_declare": document.model_dump(mode="json") if document else None,
        "champs_texte_renseignes": {cle: getattr(article, cle) is not None for cle in CHAMPS_TEXTE} if article else None,
        "champ_texte": champ, "texte_renseigne": texte is not None,
        "unite_decalage": "points_de_code_unicode_python", "total_caracteres": len(texte) if texte is not None else None,
        "limite": limite, "decalage": decalage, "fragment": fragment,
        "decalage_suivant": suivant if texte is not None and suivant < len(texte) else None,
        "avertissements": [
            "ID de version exact, pas numéro d'article ni choix de version applicable.",
            "Texte transcrit déclaré conservé sans correction, traduction ou consolidation ; non rapproché du PDF.",
            "Un champ de langue absent n'est pas remplacé par un autre et ne prouve pas absence de cette langue dans le PDF.",
            "Fragmentation en points de code Unicode, pas en octets, unités UTF-16, mots ou graphèmes.",
            "Dates et statut de version restent déclarés non validés ; aucune applicabilité déduite.",
            "Absence d'ID signifie seulement absence dans ce lot ; ce n'est pas absence d'article ou de droit.",
            "Empreintes et rejeu ne prouvent ni authenticité, ni transcription fidèle, ni exhaustivité réglementaire.",
        ],
    }
