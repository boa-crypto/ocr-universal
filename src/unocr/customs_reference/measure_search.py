"""Recherche de descriptions de mesures reçues, sans rapprochement ou calcul fiscal."""
import re
import unicodedata
from pathlib import Path

from .comparison import charger_lot
from .search import ParamRechercheInvalide, _correspondances, _parametres, _rapport

TYPES_MESURES = ("droit", "tva", "autre_taxe", "restriction", "autorisation", "regime")


def rechercher_mesures_tarif(repertoire: Path, requete: str = "", code10: str | None = None,
                             type_mesure: str | None = None, limite: int = 20, decalage: int = 0,
                             type_lot: str = "tarif") -> dict:
    if not isinstance(type_lot, str) or type_lot not in {"tarif", "mesures"}:
        raise ParamRechercheInvalide("Recherche de mesures : type explicite tarif ou mesures requis")
    if code10 is not None and (not isinstance(code10, str) or re.fullmatch(r"[0-9]{10}", code10) is None):
        raise ParamRechercheInvalide("Code exact de dix chiffres ASCII requis, sans conversion")
    if type_mesure is not None and (not isinstance(type_mesure, str) or type_mesure not in TYPES_MESURES):
        raise ParamRechercheInvalide("Type de mesure déclaré inconnu")
    termes = _parametres(requete, limite, decalage, code10 is not None or type_mesure is not None)
    if any(unicodedata.category(c) == "Cs" for c in requete):
        raise ParamRechercheInvalide("Substitut Unicode isolé interdit dans la requête")
    if type_lot == "mesures":
        from .fiscal_importer import charger_lot_mesures
        lot, rapport = charger_lot_mesures(repertoire)
        lignes = {}
    else:
        lot, rapport = charger_lot(repertoire)
        lignes = {v.code_tarifaire_10: v for v in lot.lignes}
    resultats, total = [], 0
    for mesure in sorted(lot.mesures, key=lambda m: (m.code_tarifaire_10, m.id)):
        if ((code10 is not None and mesure.code_tarifaire_10 != code10)
                or (type_mesure is not None and mesure.type_mesure != type_mesure)):
            continue
        preuves = _correspondances({"description": mesure.description}, termes)
        if preuves is None:
            continue
        if decalage <= total < decalage + limite:
            ligne = lignes.get(mesure.code_tarifaire_10)
            resultats.append({"mesure_declaree": mesure.model_dump(mode="json"),
                              "ligne_declaree": ligne.model_dump(mode="json", include={"id", "code_tarifaire_10",
                                  "designation_officielle_fr", "designation_officielle_ar", "reference"}) if ligne else None,
                              "champs_correspondants": preuves})
        total += 1
    rep = _rapport("mesures_autonomes_documentaires" if type_lot == "mesures" else "mesures_tarifaires_documentaires", requete, termes, "description_normalisee_et_filtres_exacts",
                   {"code10_exact": code10, "type_mesure": type_mesure}, rapport, total, resultats, limite, decalage)
    rep["type_lot"] = type_lot
    if type_lot == "mesures":
        rep["existence_codes_dans_nomenclature"] = "non_verifiee"
        rep["rattachement_nomenclature"] = "non_effectue"
        rep["avertissements"].append("Mesures autonomes : aucune ligne tarifaire incluse, recherchée ou rattachée.")
    rep["source_declaree"] = lot.source.model_dump(mode="json")
    rep["champs_recherches"] = ["mesure.description"]
    rep["ordre"] = "code10_ascii_puis_id_mesure_unicode_croissants"
    rep["fiscalite_applicable_etablie"] = False
    rep["utilisable_pour_calcul_douanier"] = False
    rep["avertissements"].extend([
        "Recherche dans les seules descriptions de mesures reçues ; désignations, taux et localisateurs non recherchés.",
        "Types et périodes sont déclarés, pas règles applicables ni taux à retenir ; aucun filtre à date.",
        "Les taux restent des chaînes décimales exactes ; null n'est ni zéro ni exonération.",
        "Code filtré exact, pas préfixe SH6 ; aucun regroupement des mesures par identité ou source externe.",
    ])
    return rep
