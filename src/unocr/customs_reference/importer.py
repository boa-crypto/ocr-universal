"""Préparation locale CSV/JSON, sans activation ni inférence réglementaire."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import TariffBatch

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


def preparer_tarif(source: Path, metadata: Path, sortie: Path | None = None) -> dict:
    original = _lire(source)
    metadata_original = _lire(metadata)
    configuration = _json(metadata_original)
    if not isinstance(configuration, dict) or set(configuration) - {"lot", "colonnes", "delimiteur"}:
        raise ImportRefuse("Métadonnées attendues : lot, colonnes et delimiteur optionnels")
    lot = configuration["lot"]
    if "lignes" in lot:
        raise ImportRefuse("Les lignes doivent provenir du fichier source, pas du sidecar")
    empreinte = hashlib.sha256(original).hexdigest()
    if lot["source"]["sha256"] != empreinte:
        raise ImportRefuse("Empreinte du fichier source différente du manifeste déclaré")
    format_source = lot["source"]["format"]
    colonnes_non_importees = []
    if format_source == "json":
        if configuration.get("colonnes") or configuration.get("delimiteur"):
            raise ImportRefuse("Mapping CSV interdit pour JSON")
        lignes = _json(original)
        if not isinstance(lignes, list):
            raise ImportRefuse("Source JSON : tableau de lignes attendu")
    elif format_source == "csv":
        mapping = configuration.get("colonnes")
        if not isinstance(mapping, dict) or not mapping or len(set(mapping.values())) != len(mapping):
            raise ImportRefuse("Mapping CSV explicite et sans colonne partagée requis")
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
            raise ImportRefuse("Noms de colonnes textuels requis")
        delimiteur = configuration.get("delimiteur", ";")
        if not isinstance(delimiteur, str) or len(delimiteur) != 1:
            raise ImportRefuse("Délimiteur CSV unique requis")
        if "reference" in mapping:
            raise ImportRefuse("La localisation CSV est produite par le lecteur, pas par une cellule")
        lecteur = csv.DictReader(io.StringIO(original.decode("utf-8-sig"), newline=""), delimiter=delimiteur, strict=True)
        headers = lecteur.fieldnames
        if not headers or len(headers) != len(set(headers)) or not set(mapping.values()) <= set(headers):
            raise ImportRefuse("En-têtes CSV absents, dupliqués ou mapping introuvable")
        colonnes_non_importees = sorted(set(headers) - set(mapping.values()))
        lignes = []
        try:
            for row in lecteur:
                if None in row or any(v is None for v in row.values()):
                    raise ImportRefuse("Nombre de cellules CSV incohérent")
                ligne = {cle: row[colonne] for cle, colonne in mapping.items()}
                # Ne jamais nettoyer, convertir ou compléter un code. Un champ
                # optionnel vide est inconnu, non un taux nul ou une absence de mesure.
                for cle, valeur in list(ligne.items()):
                    if valeur == "" and cle not in {"code_tarifaire_10", "code_sh_6", "chapitre", "position", "sous_position", "section_id", "id"}:
                        ligne[cle] = None
                if "id" not in ligne:
                    ligne["id"] = lot["source"]["id"] + ":" + ligne.get("code_tarifaire_10", "")
                ligne["reference"] = {"source_id": lot["source"]["id"], "localisateur": f"CSV, fin de ligne physique {lecteur.line_num}"}
                lignes.append(ligne)
        except csv.Error as exc:
            raise ImportRefuse("CSV mal formé ou cellule trop volumineuse") from exc
    else:
        raise ImportRefuse("Adaptateurs disponibles : CSV/JSON uniquement. XLS(X), PDF, XML et ZIP non encore qualifiés")
    # Validation JSON stricte : les dates ISO sont des dates, jamais les codes
    # numériques transformés en chaînes ou des zéros ajoutés par l'importateur.
    donnees = TariffBatch.model_validate_json(json.dumps({**lot, "lignes": lignes}, ensure_ascii=False, allow_nan=False))
    rapport = {"statut": "quarantaine", "publication_active": False,
               "source_sha256": empreinte, "lignes_source_lues": len(lignes),
               "lignes_importables": len(donnees.lignes),
               "codes_uniques": len({ligne.code_tarifaire_10 for ligne in donnees.lignes}),
               "colonnes_non_importees": colonnes_non_importees,
               "completude_reglementaire": "non_etablie", "validation_humaine": "requise",
               "ecrit": sortie is not None}
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
