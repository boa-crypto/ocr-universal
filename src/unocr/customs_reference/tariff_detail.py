"""Fiche tarifaire documentaire d'un lot contrôlé, sans fiscalité applicable."""
import re
from pathlib import Path

from .comparison import charger_lot


class ParamFicheTarifInvalide(ValueError):
    """Code exact invalide, distinct d'une archive incohérente."""


def consulter_code(repertoire: Path, code10: str, limite_mesures: int = 20, decalage_mesures: int = 0) -> dict:
    if not isinstance(code10, str) or re.fullmatch(r"[0-9]{10}", code10) is None:
        raise ParamFicheTarifInvalide("Code exact : chaîne de dix chiffres ASCII requise, sans conversion")
    if type(limite_mesures) is not int or not 1 <= limite_mesures <= 100:
        raise ParamFicheTarifInvalide("Limite entière de 1 à 100 requise")
    if type(decalage_mesures) is not int or not 0 <= decalage_mesures <= 1_000_000:
        raise ParamFicheTarifInvalide("Décalage entier de 0 à 1000000 requis")
    lot, rapport = charger_lot(repertoire)
    ligne = next((v for v in lot.lignes if v.code_tarifaire_10 == code10), None)
    hierarchie = None
    if ligne is not None:
        # Les parents sont ceux déclarés et contrôlés au rejeu, pas des libellés reconstruits.
        hierarchie = {
            "section": next(v for v in lot.sections if v.id == ligne.section_id).model_dump(mode="json"),
            "chapitre": next(v for v in lot.chapitres if v.code == ligne.chapitre).model_dump(mode="json"),
            "position": next(v for v in lot.positions if v.code == ligne.position).model_dump(mode="json"),
            "sh6": next(v for v in lot.sous_positions if v.code == ligne.code_sh_6).model_dump(mode="json"),
            "subdivision_nationale_intermediaire": None,
        }
    mesures = sorted((m for m in lot.mesures if m.code_tarifaire_10 == code10), key=lambda m: m.id)
    page = mesures[decalage_mesures:decalage_mesures + limite_mesures]
    suivant = decalage_mesures + len(page)
    return {
        "type_rapport": "fiche_tarifaire_documentaire", "perimetre": "lot_en_quarantaine",
        "lecture_seule": True, "publication_active": False, "validation_juridique": "non_validee",
        "validation_humaine_requise": True, "completude_reglementaire": "non_etablie",
        "classement_douanier_valide": False, "fiscalite_applicable_etablie": False,
        "restitution_juridique_a_date": False, "archive": rapport["archive"],
        "code_tarifaire_10_exact": code10, "ligne_trouvee": ligne is not None,
        "ligne_declaree": ligne.model_dump(mode="json") if ligne else None,
        "hierarchie_declaree": hierarchie, "source_declaree": lot.source.model_dump(mode="json"),
        "total_mesures_declarees": len(mesures), "limite_mesures": limite_mesures,
        "decalage_mesures": decalage_mesures,
        "decalage_mesures_suivant": suivant if suivant < len(mesures) else None,
        "mesures_declarees": [m.model_dump(mode="json") for m in page],
        "avertissements": [
            "Fiche d'un seul lot en quarantaine, pas du tarif national officiel courant ou exhaustif.",
            "Absence dans ce lot ne signifie ni inexistence nationale du code ni interdiction de classement.",
            "Parents déclarés conservés ; aucune subdivision intermédiaire nationale n'est documentée par ce contrat.",
            "Mesures de la même source seulement ; fiscalité d'autres sources/dates non rapprochée ici.",
            "Dates, unités et mesures restent déclarées non validées ; aucune applicabilité à date choisie.",
            "Aucune mesure ou taux null ne signifie pas exonération ou taux zéro ; aucun calcul de droits.",
            "Les taux décimaux sont sérialisés comme chaînes exactes, sans arrondi ni conversion en flottants.",
            "Empreintes et rejeu ne prouvent ni authenticité de la source ni exactitude ou exhaustivité réglementaire.",
        ],
    }
