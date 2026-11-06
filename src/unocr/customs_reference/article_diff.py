"""Écart littéral borné entre deux transcriptions, pas modification juridique."""
import unicodedata
from pathlib import Path

from .article_detail import CHAMPS_TEXTE, MAX_DECALAGE_TEXTE, MAX_FRAGMENT
from .legal_comparison import charger_lot_code


class ParamDiffArticleInvalide(ValueError):
    """Identités, champ ou fragments invalides avant lecture du lot."""


def comparer_versions_article(repertoire: Path, avant_id: str, apres_id: str, champ: str = "texte_integral",
                              limite: int = 4000, decalage_avant: int = 0, decalage_apres: int = 0) -> dict:
    for identifiant in (avant_id, apres_id):
        if (not isinstance(identifiant, str) or not identifiant.strip() or len(identifiant) > 256
                or any(unicodedata.category(c) == "Cc" for c in identifiant)):
            raise ParamDiffArticleInvalide("Deux IDs exacts non blancs de 256 caractères maximum sans contrôle requis")
    if not isinstance(champ, str) or champ not in CHAMPS_TEXTE:
        raise ParamDiffArticleInvalide("Champ transcrit inconnu")
    if type(limite) is not int or not 1 <= limite <= MAX_FRAGMENT:
        raise ParamDiffArticleInvalide("Limite entière de 1 à 16000 requise")
    if any(type(v) is not int or not 0 <= v <= MAX_DECALAGE_TEXTE for v in (decalage_avant, decalage_apres)):
        raise ParamDiffArticleInvalide("Décalages entiers de 0 à 67108864 requis")
    lot, rapport = charger_lot_code(repertoire)
    articles = {a.id: a for a in lot.articles}
    documents = {d.id: d for d in lot.documents}
    a, b = articles.get(avant_id), articles.get(apres_id)
    ta, tb = getattr(a, champ) if a else None, getattr(b, champ) if b else None
    comparable = ta is not None and tb is not None
    prefixe, suffixe = None, None
    if comparable:
        prefixe = 0
        maximum = min(len(ta), len(tb))
        while prefixe < maximum and ta[prefixe] == tb[prefixe]:
            prefixe += 1
        suffixe = 0
        while suffixe < maximum - prefixe and ta[len(ta) - 1 - suffixe] == tb[len(tb) - 1 - suffixe]:
            suffixe += 1

    def decrire(article, texte, decalage):
        fin = len(texte) - suffixe if comparable else None
        milieu = texte[prefixe:fin] if comparable else None
        fragment = milieu[decalage:decalage + limite] if milieu is not None else None
        suivant = decalage + len(fragment) if fragment is not None else None
        return {"article_trouve": article is not None,
                "version_declaree": article.model_dump(mode="json", include={"id", "numero_article", "nature_version",
                    "version_juridique", "reference", "validation_juridique"}) if article else None,
                "document_declare": documents[article.reference.source_id].model_dump(mode="json") if article else None,
                "champ_renseigne": texte is not None, "total_caracteres_texte": len(texte) if texte is not None else None,
                "debut_bloc_different": prefixe, "fin_bloc_different_exclusive": fin,
                "total_caracteres_bloc_different": len(milieu) if milieu is not None else None,
                "decalage_dans_bloc": decalage, "fragment_bloc_different": fragment,
                "decalage_suivant": suivant if milieu is not None and suivant < len(milieu) else None}

    relations = [r.model_dump(mode="json") for r in lot.relations
                 if {r.origine_id, r.cible_id} == {avant_id, apres_id}]
    return {"type_rapport": "comparaison_litterale_versions_article", "lecture_seule": True,
            "publication_active": False, "validation_juridique": "non_validee", "validation_humaine_requise": True,
            "archive": rapport["archive"], "avant_id_exact": avant_id, "apres_id_exact": apres_id, "champ_texte": champ,
            "champs_comparables": comparable, "textes_identiques": ta == tb if comparable else None,
            "prefixe_commun_caracteres": prefixe, "suffixe_commun_caracteres": suffixe,
            "unite_decalage": "points_de_code_unicode_python", "limite": limite,
            "avant": decrire(a, ta, decalage_avant), "apres": decrire(b, tb, decalage_apres),
            "relations_directes_declarees": relations, "relation_juridique_etablie": False,
            "transcription_verification": "non_verifiee", "restitution_juridique_a_date": False,
            "completude_reglementaire": "non_etablie",
            "avertissements": ["Deux IDs choisis explicitement, pas appariement par numéro, traduction ou similarité.",
                               "Bloc central après retrait du préfixe/suffixe communs, pas diff minimal ni alignement mot à mot.",
                               "Aucune normalisation des espaces, accents, langues ou fins de ligne ; aucune correction.",
                               "Champ absent : comparaison indisponible, pas égalité ni repli sur une autre langue.",
                               "Avant/après désigne l'ordre demandé, pas une succession juridique ou chronologie établie.",
                               "Relations reçues à titre documentaire seulement, sans preuve rapprochée du PDF.",
                               "Empreintes et rejeu ne prouvent ni authenticité, fidélité des transcriptions ou droit applicable."]}
