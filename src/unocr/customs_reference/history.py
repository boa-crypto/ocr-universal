"""Chronologie documentaire déclarée, jamais succession juridique ou droit à date."""
import unicodedata
from pathlib import Path

from .legal_comparison import charger_lot_code
from .search import _apercu


class ParamHistoriqueInvalide(ValueError):
    """Paramètres d'historique invalides, indépendamment de l'intégrité du lot."""


def _pagination(limite, decalage):
    if type(limite) is not int or not 1 <= limite <= 100:
        raise ParamHistoriqueInvalide("Limite entière de 1 à 100 requise")
    if type(decalage) is not int or not 0 <= decalage <= 1_000_000:
        raise ParamHistoriqueInvalide("Décalage entier de 0 à 1000000 requis")


def historique_article(repertoire: Path, numero_article: str, limite: int = 20, decalage: int = 0,
                       limite_relations: int = 20, decalage_relations: int = 0) -> dict:
    if (not isinstance(numero_article, str) or not numero_article.strip() or len(numero_article) > 256
            or any(unicodedata.category(c) == "Cc" for c in numero_article)):
        raise ParamHistoriqueInvalide("Numéro d'article exact non vide, sans contrôle, de 256 caractères maximum requis")
    _pagination(limite, decalage)
    _pagination(limite_relations, decalage_relations)
    lot, rapport = charger_lot_code(repertoire)
    documents = {d.id: d for d in lot.documents}
    par_id = {a.id: a for a in lot.articles}

    def ordre(article):
        doc = documents[article.reference.source_id]
        # Aucune substitution d'une date d'effet ou de transcription à la date source.
        return (doc.date_publication is None, doc.date_publication.isoformat() if doc.date_publication else "",
                doc.id, article.id)

    def decrire(article):
        champs = ("id", "numero_article", "intitule", "nature_version", "version_juridique", "hierarchie",
                  "reference", "reference_jo", "numero_jo", "date_publication", "date_entree_vigueur",
                  "date_fin_validite", "date_abrogation", "statut_juridique_declare", "validation_juridique",
                  "historique_modifications")
        valeur = article.model_dump(mode="json", include=set(champs))
        # Dates de l'article explicitement déclarées, distinctes de celles de la source.
        for cle in ("date_publication", "date_entree_vigueur", "date_fin_validite", "date_abrogation"):
            valeur[cle + "_declaree"] = valeur.pop(cle)
        valeur["apercus"] = {cle: _apercu(getattr(article, cle))
                             for cle in ("texte_integral", "texte_francais", "texte_arabe")}
        return valeur

    selection = sorted((a for a in lot.articles if a.numero_article == numero_article), key=ordre)
    ids = {a.id for a in selection}
    versions = selection[decalage:decalage + limite]
    relations = sorted((r for r in lot.relations if r.origine_id in ids or r.cible_id in ids), key=lambda r: r.id)
    page_relations = relations[decalage_relations:decalage_relations + limite_relations]
    contexte_ids = {cle for r in page_relations for cle in (r.origine_id, r.cible_id)} - {a.id for a in versions}
    contexte = sorted((par_id[cle] for cle in contexte_ids), key=ordre)
    sources = {a.reference.source_id for a in [*versions, *contexte]}
    sources.update(ref.source_id for a in [*versions, *contexte] for ref in a.historique_modifications)
    sources.update(r.reference.source_id for r in page_relations)
    suivant = decalage + len(versions)
    suivant_relations = decalage_relations + len(page_relations)
    return {
        "type_rapport": "historique_documentaire_article", "perimetre": "lot_en_quarantaine",
        "lecture_seule": True, "publication_active": False, "validation_juridique": "non_validee",
        "validation_humaine_requise": True, "completude_reglementaire": "non_etablie",
        "restitution_juridique_a_date": False, "succession_juridique_etablie": False,
        "transcription_verification": "non_verifiee", "archive": rapport["archive"],
        "numero_article_exact": numero_article,
        "ordre": "publication_source_croissante_inconnues_en_fin_puis_source_id_article_id",
        "total_versions_meme_numero": len(selection), "limite": limite, "decalage": decalage,
        "decalage_suivant": suivant if suivant < len(selection) else None,
        "versions_meme_numero": [decrire(a) for a in versions],
        "perimetre_relations": "un_saut_incident_a_toutes_les_versions_du_numero_exact_sans_transitivite",
        "total_relations_declarees": len(relations), "limite_relations": limite_relations,
        "decalage_relations": decalage_relations,
        "decalage_relations_suivant": suivant_relations if suivant_relations < len(relations) else None,
        "relations_declarees": [r.model_dump(mode="json") for r in page_relations],
        "articles_contexte_relations": [decrire(a) for a in contexte],
        "documents_declares_page": [documents[cle].model_dump(mode="json") for cle in sorted(sources)],
        "documents_sans_article_transcrit": rapport["documents_sans_article_transcrit"],
        "avertissements": [
            "Même numéro ne prouve ni identité juridique ni succession de versions ; aucune relation n'est inférée.",
            "Relations déclarées justifiées dans la transcription, sans vérification de leur preuve contre le PDF.",
            "Chronologie de publication des sources seulement ; dates et statuts des articles restent déclarés non validés.",
            "Les articles de contexte proviennent des relations de cette page ; pas de clôture transitive du graphe.",
            "Versions et relations ont des paginations indépendantes ; leurs totaux portent sur ce seul lot.",
            "Aperçus initiaux limités à 512 caractères, aucune consolidation ou version applicable choisie.",
            "Aucun résultat ne signifie seulement aucune correspondance, pas absence d'article ou de droit applicable.",
            "Intégrité locale et empreintes ne prouvent ni authenticité des sources ni exhaustivité réglementaire.",
        ],
    }
