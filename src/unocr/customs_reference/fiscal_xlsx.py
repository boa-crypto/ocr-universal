"""Mesures XLSX/XLS textuelles : lecture bornée existante, jamais de conversion Excel."""
from .fiscal_csv import verifier_mapping
from .importer import ImportRefuse
from .tabular import lire_xlsx
from .xls_table import lire_xls


def lire_mesures_tableur(original, configuration):
    format_source = configuration.source.format
    if format_source not in {"xls", "xlsx"}:
        raise ImportRefuse("Format tableur autonome XLSX/XLS requis")
    lecteur = lire_xls if format_source == "xls" else lire_xlsx
    etiquette = format_source.upper()
    mapping = verifier_mapping(configuration.colonnes)
    lignes, perimetre = lecteur(original, {"feuille":configuration.feuille,
                                           "ligne_entete":configuration.ligne_entete})
    headers = perimetre.pop("headers")
    if not set(mapping.values()) <= set(headers):
        raise ImportRefuse(f"Mapping de mesures introuvable dans les en-têtes {etiquette}")
    mesures = []
    for numero,ligne in lignes:
        mesure = {champ:ligne[colonne] for champ,colonne in mapping.items()}
        for champ,valeur in list(mesure.items()):
            if valeur is not None and not isinstance(valeur,str):
                raise ImportRefuse(f"Cellules de mesures {etiquette} textuelles requises, jamais nombre/date/booléen converti")
            if valeur in {None,""} and champ in {"taux","unite_taux","date_entree_vigueur","date_fin_validite"}:
                mesure[champ] = None
        mesure["reference"] = {"source_id":configuration.source.id,
                               "localisateur":f"{etiquette}, feuille {configuration.feuille}, ligne {numero}"}
        mesures.append(mesure)
        if len(mesures) > 100_000:
            raise ImportRefuse(f"Maximum 100000 mesures {etiquette} dépassé")
    return mesures,{"format":format_source, "contenu":"tableau_mesures_autonomes", "taux":"chaines_decimales_ou_null",
                    **perimetre,"colonnes_non_importees":sorted(set(headers)-set(mapping.values()))}


# Nom du premier adaptateur conservé pour ses utilisateurs Python (lot 40).
lire_mesures_xlsx = lire_mesures_tableur
