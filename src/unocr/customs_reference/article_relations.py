"""Relations explicitement déclarées incidentes à une version, sans transitivité."""
import unicodedata
from pathlib import Path

from .legal_comparison import charger_lot_code

SENS_RELATIONS = ("tous", "entrantes", "sortantes")
TYPES_RELATIONS = ("modifie", "complete", "abroge", "rectifie", "renvoie_a")


class ParamRelationsArticleInvalide(ValueError):
    """Version, filtres ou pagination invalides avant lecture."""


def consulter_relations_article(repertoire: Path, article_id: str, sens: str = "tous",
                                type_relation: str | None = None, limite: int = 20, decalage: int = 0) -> dict:
    if (not isinstance(article_id, str) or not article_id.strip() or len(article_id) > 256
            or any(unicodedata.category(c) in {"Cc", "Cs"} for c in article_id)):
        raise ParamRelationsArticleInvalide("ID de version exact non blanc sans contrôle de 256 caractères maximum requis")
    if not isinstance(sens, str) or sens not in SENS_RELATIONS:
        raise ParamRelationsArticleInvalide("Sens tous/entrantes/sortantes requis")
    if type_relation is not None and (not isinstance(type_relation, str) or type_relation not in TYPES_RELATIONS):
        raise ParamRelationsArticleInvalide("Type de relation déclaré inconnu")
    if type(limite) is not int or not 1 <= limite <= 100 or type(decalage) is not int or not 0 <= decalage <= 1_000_000:
        raise ParamRelationsArticleInvalide("Limite entière 1–100 et décalage entier 0–1000000 requis")
    lot, rapport = charger_lot_code(repertoire)
    articles = {a.id: a for a in lot.articles}
    documents = {d.id: d for d in lot.documents}
    article = articles.get(article_id)
    incidents = sorted((r for r in lot.relations if article_id in (r.origine_id, r.cible_id)), key=lambda r: r.id)
    filtres = [r for r in incidents if (sens == "tous" or (sens == "sortantes" and r.origine_id == article_id)
               or (sens == "entrantes" and r.cible_id == article_id))
               and (type_relation is None or r.type_relation == type_relation)]
    page = filtres[decalage:decalage + limite]
    sources = {article.reference.source_id} if article else set()

    def decrire(a):
        return a.model_dump(mode="json", include={"id", "numero_article", "intitule", "nature_version",
                           "version_juridique", "reference", "validation_juridique"})

    resultats = []
    for r in page:
        autre_id = r.cible_id if r.origine_id == article_id else r.origine_id
        autre = articles[autre_id]
        sources.update((r.reference.source_id, autre.reference.source_id))
        resultats.append({"relation_declaree": r.model_dump(mode="json"),
                          "sens_par_rapport_a_version": "sortante" if r.origine_id == article_id else "entrante",
                          "autre_version_declaree": decrire(autre)})
    suivant = decalage + len(page)
    return {"type_rapport": "relations_documentaires_version_article", "lecture_seule": True,
            "publication_active": False, "validation_juridique": "non_validee", "validation_humaine_requise": True,
            "archive": rapport["archive"], "article_id_exact": article_id, "article_trouve": article is not None,
            "version_declaree": decrire(article) if article else None,
            "sens": sens, "type_relation_filtre": type_relation,
            "perimetre_relations": "un_saut_incident_a_une_version_exacte_sans_transitivite",
            "ordre": "id_relation_unicode_croissant", "total_relations_incidentes": len(incidents),
            "totaux_incidents_par_sens": {"entrantes": sum(r.cible_id == article_id for r in incidents),
                                          "sortantes": sum(r.origine_id == article_id for r in incidents)},
            "total_relations_filtrees": len(filtres), "limite": limite, "decalage": decalage,
            "decalage_suivant": suivant if suivant < len(filtres) else None,
            "relations_declarees": resultats,
            "documents_declares_page": [documents[s].model_dump(mode="json") for s in sorted(sources)],
            "relation_juridique_etablie": False, "preuve_rapprochee_pdf": False,
            "transcription_verification": "non_verifiee", "restitution_juridique_a_date": False,
            "completude_reglementaire": "non_etablie",
            "avertissements": [
                "Une version exacte dans un seul lot, pas toutes les versions de même numéro ni graphe transitif.",
                "Sens relatif à origine_id/cible_id déclaré, jamais une chronologie ou succession juridique déduite.",
                "Type et justification déclarés non vérifiés contre la preuve PDF ; aucune relation validée par cette lecture.",
                "Sources et localisateurs conservés sans conversion automatique en page physique ni URL suivie.",
                "Aucun lien créé par numéro, similarité, préfixe, traduction ou liste articles_lies.",
                "Absence de relation dans le lot ou les filtres ne prouve ni absence de droit ni absence de modification.",
                "Empreintes/rejeu ne prouvent ni authenticité, exhaustivité ou fidélité des transcriptions.",
            ]}
