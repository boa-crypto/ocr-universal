"""CSV de mesures : cellules textuelles et mapping explicite, jamais zfill/float."""
import csv
import io

from .importer import ImportRefuse
from .models import Mesure


def verifier_mapping(mapping):
    requis = {"id", "code_tarifaire_10", "type_mesure", "description"}
    if (not mapping or not requis <= set(mapping) or set(mapping) - (set(Mesure.model_fields) - {"reference"})
            or len(mapping.values()) != len(set(mapping.values()))):
        raise ImportRefuse("Mapping de mesures explicite, complet, sans partage ou référence réservée requis")
    return mapping


def lire_mesures_csv(original, configuration):
    mapping = verifier_mapping(configuration.colonnes)
    delimiteur = configuration.delimiteur
    if len(delimiteur) != 1 or delimiteur in {'"', '\r', '\n', '\x00', '\ufeff'}:
        raise ImportRefuse("Délimiteur CSV unique sûr requis")
    lecteur = csv.DictReader(io.StringIO(original.decode("utf-8-sig"), newline=""), delimiter=delimiteur, strict=True)
    mesures = []
    try:
        headers = lecteur.fieldnames
        if (not headers or any(not c.strip() for c in headers) or len(headers) != len(set(headers))
                or not set(mapping.values()) <= set(headers)):
            raise ImportRefuse("En-têtes CSV absents, blancs, dupliqués ou mapping introuvable")
        for ligne in lecteur:
            if None in ligne or any(v is None for v in ligne.values()):
                raise ImportRefuse("Nombre de cellules CSV incohérent")
            mesure = {champ:ligne[colonne] for champ,colonne in mapping.items()}
            for champ,valeur in list(mesure.items()):
                if valeur == "" and champ in {"taux", "unite_taux", "date_entree_vigueur", "date_fin_validite"}:
                    mesure[champ] = None
            mesure["reference"] = {"source_id":configuration.source.id,
                                   "localisateur":f"CSV, fin de ligne physique {lecteur.line_num}"}
            mesures.append(mesure)
            if len(mesures) > 100_000:
                raise ImportRefuse("Maximum 100000 mesures CSV dépassé")
    except csv.Error as exc:
        raise ImportRefuse("CSV de mesures mal formé ou cellule hors limite du lecteur") from exc
    return mesures,{"format":"csv", "contenu":"tableau_mesures_autonomes", "taux":"chaines_decimales_ou_null",
                    "delimiteur":delimiteur,"colonnes_non_importees":sorted(set(headers)-set(mapping.values())),
                    "lignes_physiques_lues":lecteur.line_num}
