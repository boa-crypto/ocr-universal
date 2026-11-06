"""Indicateurs descriptifs d'un lot, sans score de complétude réglementaire."""
from collections import Counter
from pathlib import Path

from .comparison import charger_lot
from .legal_comparison import charger_lot_code
from .models import NIVEAUX


class ParamCouvertureInvalide(ValueError):
    """Type de lot explicite requis, sans autodécouverte du disque."""


def _absents(elements, champs):
    # Un zéro déclaré n'est jamais compté comme inconnu.
    return {champ: sum(getattr(v, champ) is None or
                       (isinstance(getattr(v, champ), str) and not getattr(v, champ).strip()) for v in elements)
            for champ in champs}


def diagnostiquer_couverture(repertoire: Path, type_lot: str) -> dict:
    if not isinstance(type_lot, str) or type_lot not in {"tarif", "code"}:
        raise ParamCouvertureInvalide("Type de lot explicite tarif ou code requis")
    if type_lot == "tarif":
        lot, rapport = charger_lot(repertoire)
        sources = [lot.source]
        mesures_par_code = {m.code_tarifaire_10 for m in lot.mesures}
        indicateurs = {
            "compteurs": {"sections": len(lot.sections), "chapitres": len(lot.chapitres),
                          "positions": len(lot.positions), "sh6": len(lot.sous_positions),
                          "lignes_code10": len(lot.lignes), "mesures": len(lot.mesures)},
            "lignes_champs_non_renseignes": _absents(lot.lignes, (
                "designation_officielle_fr", "designation_officielle_ar", "unite_statistique", "unite_supplementaire",
                "date_entree_vigueur", "date_fin_validite", "taux_droits_douane", "taux_tva")),
            "mesures_champs_non_renseignes": _absents(lot.mesures, ("taux", "unite_taux", "date_entree_vigueur", "date_fin_validite")),
            "mesures_par_type": {cle: sum(m.type_mesure == cle for m in lot.mesures)
                                 for cle in ("droit", "tva", "autre_taxe", "restriction", "autorisation", "regime")},
            "lignes_sans_mesure_declaree": sum(v.code_tarifaire_10 not in mesures_par_code for v in lot.lignes),
            "parents_sans_ligne_code10": {
                "sections": len({v.id for v in lot.sections} - {v.section_id for v in lot.lignes}),
                "chapitres": len({v.code for v in lot.chapitres} - {v.chapitre for v in lot.lignes}),
                "positions": len({v.code for v in lot.positions} - {v.position for v in lot.lignes}),
                "sh6": len({v.code for v in lot.sous_positions} - {v.code_sh_6 for v in lot.lignes}),
            },
            "subdivision_nationale_intermediaire": "non_decrite_par_le_contrat",
            "rapprochement_fiscal_multi_source": "non_effectue",
        }
    else:
        lot, rapport = charger_lot_code(repertoire)
        sources = lot.documents
        participants = {cle for r in lot.relations for cle in (r.origine_id, r.cible_id)}
        niveaux = Counter(n.niveau for a in lot.articles for n in a.hierarchie)
        indicateurs = {
            "compteurs": {"documents": len(sources), "articles_transcrits": len(lot.articles),
                          "numeros_article_distincts": len({a.numero_article for a in lot.articles}),
                          "relations_declarees": len(lot.relations)},
            "documents_par_nature": {cle: sum(d.nature_document == cle for d in sources)
                                     for cle in ("code_original", "acte_modificatif", "compilation")},
            "articles_par_nature": rapport["articles_par_nature"],
            "articles_champs_non_renseignes": _absents(lot.articles, (
                "texte_francais", "texte_arabe", "date_publication", "date_entree_vigueur",
                "date_fin_validite", "date_abrogation", "reference_jo", "numero_jo")),
            "documents_sans_article_transcrit": rapport["documents_sans_article_transcrit"],
            "empreintes_documentaires_dupliquees": rapport["empreintes_documentaires_dupliquees"],
            "articles_sans_relation_declaree": sum(a.id not in participants for a in lot.articles),
            "occurrences_niveaux_hierarchiques": {cle: niveaux[cle] for cle in NIVEAUX},
            "relations_par_type": {cle: sum(r.type_relation == cle for r in lot.relations)
                                   for cle in ("modifie", "complete", "abroge", "rectifie", "renvoie_a")},
            "transcription_verification": "non_verifiee",
        }
    return {
        "type_rapport": "couverture_documentaire_declaree", "type_lot": type_lot,
        "perimetre": "un_seul_lot_en_quarantaine", "lecture_seule": True,
        "publication_active": False, "validation_juridique": "non_validee",
        "validation_humaine_requise": True, "completude_reglementaire": "non_etablie",
        "nombre_officiel_attendu": None, "pourcentage_completude_reglementaire": None,
        "utilisable_pour_calcul_douanier": False, "restitution_juridique_a_date": False,
        "archive": rapport["archive"], "integrite_locale": "coherente_au_rejeu",
        "sources_champs_non_renseignes": _absents(sources, ("date_publication",)),
        "sources_declarees": [{"id": s.id, "sha256": s.sha256, "verification": s.verification} for s in sorted(sources, key=lambda s: s.id)],
        "indicateurs": indicateurs,
        "avertissements": [
            "Compteurs du lot reçu seulement ; aucun dénominateur officiel ni pourcentage de complétude calculé.",
            "Champs non renseignés : constats descriptifs, pas erreurs juridiques ou exigences universelles.",
            "Un champ linguistique absent ne prouve pas l'absence de cette langue dans le texte intégral ou le PDF.",
            "Aucune mesure ne prouve pas exonération ; un taux inconnu ne signifie pas zéro.",
            "Parents sans ligne ou niveaux sans occurrence ne prouvent pas un corpus national incomplet ou erroné.",
            "Aucune relation ne prouve pas absence de modification ; dates et statuts restent déclarés non validés.",
            "Authenticité, transcription/PDF, exhaustivité des modifications et applicabilité restent à vérifier humainement.",
            "Aucun score, seuil de publication, choix de version ou calcul douanier autorisé par ce rapport.",
        ],
    }
