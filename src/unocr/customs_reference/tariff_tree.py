"""Navigation des parents déclarés d'un seul lot tarifaire en quarantaine."""
import re
import unicodedata
from pathlib import Path

from .comparison import charger_lot

NIVEAUX_TARIF = ("sections", "chapitres", "positions", "sh6", "codes")


class ParamArbreTarifInvalide(ValueError):
    """Paramètres de navigation invalides avant lecture du corpus."""


def parcourir_tarif(repertoire: Path, niveau: str = "sections", parent: str | None = None,
                    limite: int = 20, decalage: int = 0) -> dict:
    if not isinstance(niveau, str) or niveau not in NIVEAUX_TARIF:
        raise ParamArbreTarifInvalide("Niveau tarifaire inconnu")
    if type(limite) is not int or not 1 <= limite <= 100 or type(decalage) is not int or not 0 <= decalage <= 1_000_000:
        raise ParamArbreTarifInvalide("Limite entière 1–100 et décalage entier 0–1000000 requis")
    if niveau == "sections":
        if parent is not None:
            raise ParamArbreTarifInvalide("La racine sections n'accepte pas de parent")
    else:
        if (not isinstance(parent, str) or not parent.strip() or len(parent) > 256
                or any(unicodedata.category(c) == "Cc" for c in parent)):
            raise ParamArbreTarifInvalide("Parent exact non vide, sans contrôle, de 256 caractères maximum requis")
        largeur = {"positions": 2, "sh6": 4, "codes": 6}.get(niveau)
        if largeur and re.fullmatch(r"[0-9]{" + str(largeur) + "}", parent) is None:
            raise ParamArbreTarifInvalide("Code parent exact ASCII requis, sans conversion ni remplissage")
    lot, rapport = charger_lot(repertoire)
    # Collection enfant, clé enfant, collection parente, clé parente, référence au parent.
    definitions = {
        "chapitres": (lot.chapitres, "code", lot.sections, "id", "section_id"),
        "positions": (lot.positions, "code", lot.chapitres, "code", "chapitre"),
        "sh6": (lot.sous_positions, "code", lot.positions, "code", "position"),
        "codes": (lot.lignes, "code_tarifaire_10", lot.sous_positions, "code", "code_sh_6"),
    }
    parent_obj = None
    if niveau == "sections":
        elements = sorted(lot.sections, key=lambda v: v.id)
        niveau_suivant = "chapitres"
    else:
        enfants, cle, parents, cle_parent, lien = definitions[niveau]
        parent_obj = next((v for v in parents if getattr(v, cle_parent) == parent), None)
        elements = sorted((v for v in enfants if getattr(v, lien) == parent), key=lambda v: getattr(v, cle))
        niveau_suivant = {"chapitres": "positions", "positions": "sh6", "sh6": "codes", "codes": None}[niveau]
    page = elements[decalage:decalage + limite]
    suivant = decalage + len(page)
    return {
        "type_rapport": "navigation_tarifaire_documentaire", "perimetre": "un_seul_lot_en_quarantaine",
        "lecture_seule": True, "publication_active": False, "validation_juridique": "non_validee",
        "validation_humaine_requise": True, "completude_reglementaire": "non_etablie",
        "fiscalite_applicable_etablie": False, "classement_douanier_valide": False,
        "archive": rapport["archive"], "source_declaree": lot.source.model_dump(mode="json"),
        "niveau": niveau, "parent_exact": parent,
        "parent_trouve": None if niveau == "sections" else parent_obj is not None,
        "parent_declare": parent_obj.model_dump(mode="json") if parent_obj is not None else None,
        "niveau_suivant": niveau_suivant, "total_enfants_declares": len(elements),
        "limite": limite, "decalage": decalage, "decalage_suivant": suivant if suivant < len(elements) else None,
        "enfants_declares": [v.model_dump(mode="json") for v in page],
        "avertissements": [
            "Navigation des seuls parents/enfants reçus et contrôlés, pas nomenclature nationale exhaustive.",
            "Un parent absent ou sans enfant dans ce lot ne prouve pas absence nationale ou abrogation.",
            "Projection SH6 vers code10 ; subdivisions explicites consultables dans la fiche, aucune subdivision inventée.",
            "Libellés, codes et références reçus conservés sans traduction ni correction.",
            "Aucun taux ou mesure fiscale rapproché ; aucune classification, applicabilité ou validation officielle.",
            "Empreintes et rejeu ne prouvent ni authenticité des sources ni exactitude réglementaire.",
        ],
    }
