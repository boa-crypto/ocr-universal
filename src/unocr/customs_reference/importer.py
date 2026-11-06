"""Préparation locale CSV/JSON/XLSX/XML/ZIP, sans activation ni inférence réglementaire."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import LigneTarifaire, TariffBatch
from .tabular import lire_xlsx
from .xml_table import lire_xml
from .zip_source import lire_zip

MAX_SOURCE = 64 * 1024 * 1024


class ImportRefuse(ValueError):
    """Préconditions ou intégrité insuffisantes ; aucune publication."""


def _objet(paires):
    result = {}
    for cle, valeur in paires:
        if cle in result:
            raise ImportRefuse("Clé JSON dupliquée : " + cle)
        result[cle] = valeur
    return result


def _constante(valeur):
    raise ImportRefuse("Constante JSON invalide : " + valeur)


def _json(contenu):
    try:
        return json.loads(contenu, object_pairs_hook=_objet, parse_constant=_constante)
    except RecursionError as exc:
        raise ImportRefuse("Structure JSON trop profonde") from exc


def _lire(path):
    if path.is_symlink() or not path.is_file():
        raise ImportRefuse("Fichier absent, non régulier ou symbolique")
    with path.open("rb") as fichier:
        contenu = fichier.read(MAX_SOURCE + 1)
    if len(contenu) > MAX_SOURCE:
        raise ImportRefuse("Fichier trop volumineux (64 Mio maximum)")
    return contenu


def _mapping(configuration, headers):
    mapping = configuration.get("colonnes")
    if not isinstance(mapping, dict) or not mapping:
        raise ImportRefuse("Mapping explicite requis")
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        raise ImportRefuse("Noms de colonnes textuels requis")
    if len(set(mapping.values())) != len(mapping):
        raise ImportRefuse("Colonne partagée dans le mapping")
    if "reference" in mapping or set(mapping) - set(LigneTarifaire.model_fields):
        raise ImportRefuse("Champ de mapping inconnu ou reference réservée au lecteur")
    if not headers or len(headers) != len(set(headers)) or not set(mapping.values()) <= set(headers):
        raise ImportRefuse("En-têtes absents, dupliqués ou mapping introuvable")
    return mapping, sorted(set(headers) - set(mapping.values()))


def _ligne(row, mapping, source_id, localisateur):
    ligne = {cle: row[colonne] for cle, colonne in mapping.items()}
    for cle, valeur in list(ligne.items()):
        if valeur == "" and cle not in {"code_tarifaire_10", "code_sh_6", "chapitre", "position", "sous_position", "section_id", "id"}:
            ligne[cle] = None
    if "id" not in ligne:
        # Identifiant technique seulement ; jamais de reconstitution d'un code.
        ligne["id"] = source_id + ":" + str(ligne.get("code_tarifaire_10", ""))
    ligne["reference"] = {"source_id": source_id, "localisateur": localisateur}
    return ligne


def _analyser_tarif(source: Path, metadata: Path):
    original = _lire(source)
    metadata_original = _lire(metadata)
    return _analyser_contenu(original, metadata_original)


def _analyser_contenu(original: bytes, metadata_original: bytes):
    configuration = _json(metadata_original)
    if not isinstance(configuration, dict) or set(configuration) - {"lot", "colonnes", "delimiteur", "feuille", "ligne_entete", "racine_xml", "ligne_xml", "membre_zip", "format_contenu"}:
        raise ImportRefuse("Métadonnées attendues : lot, colonnes et options de lecteur déclarées")
    lot = configuration["lot"]
    if "lignes" in lot:
        raise ImportRefuse("Les lignes doivent provenir du fichier source, pas du sidecar")
    empreinte = hashlib.sha256(original).hexdigest()
    if lot["source"]["sha256"] != empreinte:
        raise ImportRefuse("Empreinte du fichier source différente du manifeste déclaré")
    format_source = lot["source"]["format"]
    colonnes_non_importees = []
    perimetre = {"format": format_source}
    format_lecture, contenu_source = format_source, original
    if format_source == "zip":
        contenu_source, perimetre_zip = lire_zip(original, configuration)
        perimetre.update(perimetre_zip)
        format_lecture = perimetre_zip["format_contenu"]
    elif {"membre_zip", "format_contenu"} & set(configuration):
        raise ImportRefuse("Options ZIP interdites hors ZIP")
    if format_lecture != "xlsx" and ({"feuille", "ligne_entete"} & set(configuration)):
        raise ImportRefuse("Options de feuille interdites hors lecture XLSX")
    if format_lecture != "xml" and ({"racine_xml", "ligne_xml"} & set(configuration)):
        raise ImportRefuse("Options XML interdites hors XML")
    if format_lecture == "json":
        if configuration.get("colonnes") or configuration.get("delimiteur"):
            raise ImportRefuse("Mapping CSV interdit pour JSON")
        lignes = _json(contenu_source)
        if not isinstance(lignes, list):
            raise ImportRefuse("Source JSON : tableau de lignes attendu")
    elif format_lecture == "csv":
        delimiteur = configuration.get("delimiteur", ";")
        if not isinstance(delimiteur, str) or len(delimiteur) != 1:
            raise ImportRefuse("Délimiteur CSV unique requis")
        lecteur = csv.DictReader(io.StringIO(contenu_source.decode("utf-8-sig"), newline=""), delimiter=delimiteur, strict=True)
        mapping, colonnes_non_importees = _mapping(configuration, lecteur.fieldnames)
        lignes = []
        try:
            for row in lecteur:
                if None in row or any(v is None for v in row.values()):
                    raise ImportRefuse("Nombre de cellules CSV incohérent")
                lignes.append(_ligne(row, mapping, lot["source"]["id"],
                                     f"CSV, fin de ligne physique {lecteur.line_num}"))
        except csv.Error as exc:
            raise ImportRefuse("CSV mal formé ou cellule trop volumineuse") from exc
    elif format_lecture == "xlsx":
        rows, perimetre_xlsx = lire_xlsx(contenu_source, configuration)
        mapping, colonnes_non_importees = _mapping(configuration, perimetre_xlsx.pop("headers"))
        perimetre.update(perimetre_xlsx)
        lignes = [_ligne(row, mapping, lot["source"]["id"],
                         f"XLSX, feuille {configuration['feuille']}, ligne {numero}") for numero, row in rows]
    elif format_lecture == "xml":
        rows, perimetre_xml = lire_xml(contenu_source, configuration)
        mapping, colonnes_non_importees = _mapping(configuration, perimetre_xml.pop("headers"))
        perimetre.update(perimetre_xml)
        lignes = [_ligne(row, mapping, lot["source"]["id"],
                         f"XML, élément {configuration['ligne_xml']}, ligne physique {numero}") for numero, row in rows]
    else:
        raise ImportRefuse("Adaptateurs disponibles : CSV/JSON/XLSX/XML et ZIP explicite. XLS et PDF non encore qualifiés")
    if format_source == "zip" and format_lecture != "json":
        for entree in lignes:
            entree["reference"]["localisateur"] = f"ZIP, membre {configuration['membre_zip']}, " + entree["reference"]["localisateur"]
    # Validation JSON stricte : les dates ISO sont des dates, jamais les codes
    # numériques transformés en chaînes ou des zéros ajoutés par l'importateur.
    donnees = TariffBatch.model_validate_json(json.dumps({**lot, "lignes": lignes}, ensure_ascii=False, allow_nan=False))
    rapport = {"statut": "quarantaine", "publication_active": False,
               "source_sha256": empreinte, "lignes_source_lues": len(lignes),
               "lignes_importables": len(donnees.lignes),
               "codes_uniques": len({ligne.code_tarifaire_10 for ligne in donnees.lignes}),
               "colonnes_non_importees": colonnes_non_importees,
               "completude_reglementaire": "non_etablie", "validation_humaine": "requise",
               "perimetre_lecture": perimetre, "ecrit": False}
    return donnees, rapport, original, metadata_original


def preparer_tarif(source: Path, metadata: Path, sortie: Path | None = None) -> dict:
    donnees, rapport, original, metadata_original = _analyser_tarif(source, metadata)
    format_source = donnees.source.format
    rapport["ecrit"] = sortie is not None
    if sortie is not None:
        # Publication de préparation seulement, dans un répertoire neuf. Le
        # manifeste est écrit en dernier ; un dossier interrompu n'est pas complet.
        sortie.mkdir(mode=0o700, parents=False, exist_ok=False)
        fichiers = {"source_recue." + format_source: original,
                    "metadata_original.json": metadata_original,
                    "lot.json": donnees.model_dump_json(indent=2).encode("utf-8"),
                    "rapport.json": json.dumps(rapport, ensure_ascii=False, indent=2).encode("utf-8")}
        for nom, contenu in fichiers.items():
            with (sortie / nom).open("xb") as fichier:
                fichier.write(contenu)
        manifeste = {"statut": "quarantaine", "source_nom_recu": source.name,
                     "date_importation": datetime.now(timezone.utc).isoformat(),
                     "fichiers_sha256": {nom: hashlib.sha256(b).hexdigest() for nom, b in fichiers.items()},
                     "validation_juridique": "non_validee", "publication_active": False}
        with (sortie / "manifest.json").open("x", encoding="utf-8") as fichier:
            json.dump(manifeste, fichier, ensure_ascii=False, indent=2)
    return rapport
