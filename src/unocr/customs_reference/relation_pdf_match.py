"""Présence littérale d'une justification dans sa source, jamais preuve juridique."""
from pathlib import Path

from .article_pdf_match import (
    ParamRapprochementInvalide,
    constater_fragment_pdf,
    verifier_parametres_fragment,
)
from .legal_comparison import charger_lot_code


class ParamJustificationPDFInvalide(ValueError):
    """Relation/page/fragment invalides avant lecture du lot."""


def rapprocher_justification_pdf(repertoire: Path, relation_id: str, page: int,
                                 limite: int = 4000, decalage: int = 0) -> dict:
    try:
        verifier_parametres_fragment(relation_id, page, "texte_integral", limite, decalage)
    except ParamRapprochementInvalide as exc:
        raise ParamJustificationPDFInvalide(str(exc)) from None
    lot, rapport = charger_lot_code(repertoire)
    relation = next((r for r in lot.relations if r.id == relation_id), None)
    document = next((d for d in lot.documents if relation and d.id == relation.reference.source_id), None)
    texte = relation.justification if relation else None
    fragment = texte[decalage:decalage + limite] if texte is not None else None
    suivant = decalage + len(fragment) if fragment is not None else None
    constat = constater_fragment_pdf(repertoire, lot, rapport, document, texte, fragment, page,
                                     "relation_absente_du_lot" if relation is None else None)
    return {"type_rapport": "rapprochement_litteral_justification_relation_pdf", "lecture_seule": True,
            "publication_active": False, "validation_juridique": "non_validee", "validation_humaine_requise": True,
            "archive": rapport["archive"], "relation_id_exact": relation_id, "relation_trouvee": relation is not None,
            "relation_declaree": relation.model_dump(mode="json", exclude={"justification"}) if relation else None,
            "document_declare": document.model_dump(mode="json") if document else None,
            "fragment_justification": fragment, "total_caracteres_justification": len(texte) if texte is not None else None,
            "limite": limite, "decalage": decalage,
            "decalage_suivant": suivant if texte is not None and suivant < len(texte) else None,
            **constat,
            "relation_juridique_etablie": False, "preuve_juridique_verifiee": False,
            "authenticite_documentaire": "non_etablie", "transcription_verification": "non_verifiee",
            "completude_reglementaire": "non_etablie", "restitution_juridique_a_date": False,
            "avertissements": [
                "Justification déclarée, pas nécessairement une citation littérale du PDF ; fragment et page choisis explicitement.",
                "Source imposée par relation.reference.source_id ; aucune localisation depuis le localisateur libre ou numéro imprimé.",
                "Présence ne prouve ni portée juridique, lien entre les articles, unicité ou authenticité du document.",
                "Absence ne prouve pas erreur de justification : formulation, traduction, glyphes et retours peuvent différer.",
                "Sans OCR, normalisation, traduction ou recherche floue ; première occurrence seulement dans une page native bornée.",
                "Relation absente ou fragment vide/blanc : aucune extraction ; page sans texte natif : résultat indéterminé.",
                "Aucune validation humaine, modification de relation, publication ou utilisation pour calcul douanier réel.",
            ]}
