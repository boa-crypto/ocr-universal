"""Préparation/rejeu de mesures JSON autonomes, sans écrasement ou activation."""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .fiscal_models import MesuresAutonomesBatch, MetadataMesuresAutonomes
from .importer import MAX_SOURCE, ImportRefuse, _json, _lire
from .measure_search import TYPES_MESURES

TYPE_LOT = "mesures_autonomes_documentaires"
FICHIERS = {"source_mesures_recue.json", "metadata_original.json", "lot_mesures.json", "rapport.json"}


def _analyser_mesures(original: bytes, metadata_original: bytes):
    meta = MetadataMesuresAutonomes.model_validate_json(json.dumps(_json(metadata_original), ensure_ascii=False))
    sha = hashlib.sha256(original).hexdigest()
    if sha != meta.source.sha256:
        raise ImportRefuse("Empreinte de source de mesures différente de la déclaration")
    mesures = _json(original)
    if not isinstance(mesures, list):
        raise ImportRefuse("Source JSON : tableau de mesures autonome attendu")
    # Contrat de taux volontairement restreint, pour ne jamais lire un nombre
    # JSON via float puis faire passer son arrondi pour une valeur source exacte.
    for m in mesures:
        if not isinstance(m, dict):
            raise ImportRefuse("Chaque mesure doit être un objet JSON")
        if m.get("taux") is not None and not isinstance(m["taux"], str):
            raise ImportRefuse("Taux JSON : chaîne décimale exacte ou null requis, jamais nombre converti")
    lot = MesuresAutonomesBatch.model_validate_json(json.dumps({**meta.model_dump(mode="json"), "mesures":mesures},
                                                               ensure_ascii=False, allow_nan=False))
    rapport = {"type_lot":TYPE_LOT, "statut":"quarantaine", "publication_active":False,
        "validation_juridique":"non_validee", "validation_humaine":"requise",
        "source_sha256":sha, "mesures_source_lues":len(mesures), "mesures_importables":len(lot.mesures),
        "codes10_declares_distincts":len({m.code_tarifaire_10 for m in lot.mesures}),
        "mesures_par_type":{t:sum(m.type_mesure == t for m in lot.mesures) for t in TYPES_MESURES},
        "mesures_sans_taux":sum(m.taux is None for m in lot.mesures),
        "existence_codes_dans_nomenclature":"non_verifiee", "nomenclature_incluse":False,
        "completude_reglementaire":"non_etablie", "fiscalite_applicable_etablie":False,
        "restitution_juridique_a_date":False, "utilisable_pour_calcul_douanier":False,
        "perimetre_lecture":{"format":"json", "contenu":"tableau_mesures_autonomes", "taux":"chaines_decimales_ou_null"},
        "avertissements":[
            "Mesures autonomes reçues, sans lignes tarifaires inventées ni rapprochement avec une nomenclature.",
            "Codes syntaxiquement contrôlés seulement ; existence nationale et rattachement non vérifiés.",
            "Source, périodes et références propres conservées ; aucune date héritée d'un tarif ou d'une publication.",
            "Taux inconnus distincts du zéro ; aucune mesure ne prouve ni exonération ni absence de restriction.",
            "Intégrité locale et rejeu ne prouvent ni authenticité, exhaustivité, portée juridique ou applicabilité.",
            "Format JSON strict seulement ; aucun CSV/XLSX/PDF autonome qualifié ici.",
        ], "ecrit":False}
    return lot,rapport


def preparer_mesures_autonomes(source: Path, metadata: Path, sortie: Path | None = None) -> dict:
    original,meta = _lire(source),_lire(metadata)
    lot,rapport = _analyser_mesures(original,meta)
    rapport["ecrit"] = sortie is not None
    if sortie is not None:
        fichiers = {"source_mesures_recue.json":original, "metadata_original.json":meta,
                    "lot_mesures.json":lot.model_dump_json(indent=2).encode("utf-8"),
                    "rapport.json":json.dumps(rapport,ensure_ascii=False,indent=2).encode("utf-8")}
        manifest = {"type_lot":TYPE_LOT, "schema_version":"1", "statut":"quarantaine", "publication_active":False,
                    "validation_juridique":"non_validee", "date_importation":datetime.now(timezone.utc).isoformat(),
                    "source_nom_recu":source.name,
                    "fichiers_sha256":{nom:hashlib.sha256(contenu).hexdigest() for nom,contenu in fichiers.items()}}
        manifeste = json.dumps(manifest,ensure_ascii=False,indent=2).encode("utf-8")
        if any(len(c) > MAX_SOURCE for c in [*fichiers.values(), manifeste]):
            raise ImportRefuse("Artefact normalisé trop volumineux pour un rejeu borné à 64 Mio")
        sortie.mkdir(mode=0o700,parents=False,exist_ok=False)
        for nom,contenu in fichiers.items():
            with (sortie / nom).open("xb") as f:
                f.write(contenu)
        # Dernier fichier = marqueur de préparation achevée, pas transaction FS.
        with (sortie / "manifest.json").open("xb") as f:
            f.write(manifeste)
    return rapport


def charger_lot_mesures(repertoire: Path) -> tuple[MesuresAutonomesBatch,dict]:
    if repertoire.is_symlink() or not repertoire.is_dir():
        raise ImportRefuse("Répertoire de mesures absent ou symbolique")
    manifeste = _lire(repertoire / "manifest.json")
    m = _json(manifeste)
    cles = {"type_lot", "schema_version", "statut", "publication_active", "validation_juridique",
            "date_importation", "source_nom_recu", "fichiers_sha256"}
    if (not isinstance(m, dict) or set(m) != cles or m["type_lot"] != TYPE_LOT or m["schema_version"] != "1"
            or m["statut"] != "quarantaine" or m["publication_active"] is not False or m["validation_juridique"] != "non_validee"):
        raise ImportRefuse("Manifeste de mesures autonomes en quarantaine attendu")
    date_import = datetime.fromisoformat(m["date_importation"])
    if date_import.utcoffset() != timedelta(0) or not isinstance(m["source_nom_recu"],str) or not m["source_nom_recu"].strip():
        raise ImportRefuse("Date UTC et nom reçu requis")
    empreintes = m["fichiers_sha256"]
    if (not isinstance(empreintes,dict) or set(empreintes) != FICHIERS
            or {p.name for p in repertoire.iterdir()} != FICHIERS | {"manifest.json"}):
        raise ImportRefuse("Fichiers de mesures absents ou inattendus")
    fichiers = {}
    for nom in sorted(FICHIERS):
        sha = empreintes[nom]
        if not isinstance(sha,str) or re.fullmatch(r"[a-f0-9]{64}",sha) is None:
            raise ImportRefuse("Empreinte de fichier invalide")
        contenu = _lire(repertoire / nom)
        if hashlib.sha256(contenu).hexdigest() != sha:
            raise ImportRefuse("Empreinte de fichier de mesures différente")
        fichiers[nom] = contenu
    lot,rapport = _analyser_mesures(fichiers["source_mesures_recue.json"],fichiers["metadata_original.json"])
    recu = MesuresAutonomesBatch.model_validate_json(json.dumps(_json(fichiers["lot_mesures.json"]),ensure_ascii=False))
    if lot.model_dump(mode="json") != recu.model_dump(mode="json"):
        raise ImportRefuse("Lot de mesures non reproductible depuis la source et les métadonnées")
    attendu = {**rapport,"ecrit":True}
    releve = _json(fichiers["rapport.json"])
    if json.dumps(releve,sort_keys=True) != json.dumps(attendu,sort_keys=True):
        raise ImportRefuse("Rapport de mesures non reproductible")
    rapport["archive"] = {"manifest_sha256":hashlib.sha256(manifeste).hexdigest(),
                          "date_importation":m["date_importation"], "source_nom_recu":m["source_nom_recu"],
                          "fichiers_sha256":empreintes}
    return lot,rapport
