"""Mesures XLSX textuelles : lecture bornée existante, jamais de conversion Excel."""
from .fiscal_csv import verifier_mapping
from .importer import ImportRefuse
from .tabular import lire_xlsx


def lire_mesures_xlsx(original, configuration):
    mapping = verifier_mapping(configuration.colonnes)
    lignes, perimetre = lire_xlsx(original, {"feuille":configuration.feuille,
                                           "ligne_entete":configuration.ligne_entete})
    headers = perimetre.pop("headers")
    if not set(mapping.values()) <= set(headers):
        raise ImportRefuse("Mapping de mesures introuvable dans les en-têtes XLSX")
    mesures = []
    for numero,ligne in lignes:
        mesure = {champ:ligne[colonne] for champ,colonne in mapping.items()}
        for champ,valeur in list(mesure.items()):
            if valeur is not None and not isinstance(valeur,str):
                raise ImportRefuse("Cellules de mesures XLSX textuelles requises, jamais nombre/date/booléen converti")
            if valeur in {None,""} and champ in {"taux","unite_taux","date_entree_vigueur","date_fin_validite"}:
                mesure[champ] = None
        mesure["reference"] = {"source_id":configuration.source.id,
                               "localisateur":f"XLSX, feuille {configuration.feuille}, ligne {numero}"}
        mesures.append(mesure)
        if len(mesures) > 100_000:
            raise ImportRefuse("Maximum 100000 mesures XLSX dépassé")
    return mesures,{"format":"xlsx", "contenu":"tableau_mesures_autonomes", "taux":"chaines_decimales_ou_null",
                    **perimetre,"colonnes_non_importees":sorted(set(headers)-set(mapping.values()))}
