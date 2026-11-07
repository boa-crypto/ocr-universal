"""Présence d'un fragment de description dans sa page PDF, pas preuve de fiscalité."""
from pathlib import Path

from .article_pdf_match import (
    ParamRapprochementInvalide,
    constater_fragment_pdf,
    verifier_parametres_fragment,
)
from .fiscal_importer import charger_lot_mesures
from .fiscal_pdf_page import extraire_page_mesures_controlee
from .pdf_page import LecturePDFRefusee


class ParamRapprochementMesureInvalide(ParamRapprochementInvalide):
    """Paramètres de description/page invalides avant lecture."""


def rapprocher_description_mesure_pdf(repertoire: Path, mesure_id: str, page: int,
                                      limite: int = 4000, decalage: int = 0) -> dict:
    try:
        verifier_parametres_fragment(mesure_id,page,"texte_integral",limite,decalage)
    except ParamRapprochementInvalide as exc:
        raise ParamRapprochementMesureInvalide(str(exc)) from None
    lot,rapport = charger_lot_mesures(repertoire)
    if lot.source.format != "pdf":
        raise LecturePDFRefusee("Source PDF absente du lot de mesures contrôlé")
    mesure = next((m for m in lot.mesures if m.id == mesure_id),None)
    texte = mesure.description if mesure else None
    fragment = texte[decalage:decalage+limite] if texte is not None else None
    suivant = decalage+len(fragment) if fragment is not None else None
    constat = constater_fragment_pdf(repertoire,lot,rapport,lot.source,texte,fragment,page,
        "mesure_absente_du_lot" if mesure is None else None,extracteur=extraire_page_mesures_controlee)
    return {"type_rapport":"rapprochement_litteral_description_mesure_pdf", "type_lot":"mesures",
            "lecture_seule":True, "publication_active":False, "validation_juridique":"non_validee",
            "validation_humaine_requise":True, "archive":rapport["archive"],
            "mesure_id_exact":mesure_id, "mesure_trouvee":mesure is not None,
            "mesure_declaree":mesure.model_dump(mode="json",include={"id","code_tarifaire_10","type_mesure","reference"}) if mesure else None,
            "document_declare":lot.source.model_dump(mode="json"), "champ_texte":"description",
            "fragment_description":fragment, "total_caracteres_description":len(texte) if texte is not None else None,
            "limite":limite, "decalage":decalage,
            "decalage_suivant":suivant if texte is not None and suivant < len(texte) else None,
            **constat, "transcription_sha256":rapport["transcription_sha256"],
            "transcription_verification":"non_verifiee", "taux_et_periodes_verifies":False,
            "rattachement_juridique_etabli":False, "utilisable_pour_calcul_douanier":False,
            "authenticite_documentaire":"non_etablie", "completude_reglementaire":"non_etablie",
            "restitution_juridique_a_date":False,
            "avertissements":["Un fragment de description, une page physique choisie explicitement, première occurrence seulement.",
                "Sans normalisation, traduction, OCR ou localisation depuis la référence libre de la mesure.",
                "Présence ne prouve ni taux, unité, code, période, contexte, unicité ou rattachement juridique.",
                "Absence ne prouve pas erreur : ordre, espaces et glyphes natifs peuvent différer du rendu.",
                "Sans texte natif, fragment vide/blanc ou mesure absente : aucune correspondance positive déduite.",
                "Aucune fidélité intégrale attestée, validation humaine, publication ou fiscalité applicable."]}
