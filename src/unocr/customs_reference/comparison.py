"""Comparaison vérifiée de préparations locales, sans effet juridique ni écriture."""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from .importer import ImportRefuse, _analyser_contenu, _json, _lire
from .models import TariffBatch


class LotRefuse(ImportRefuse):
    """Lot incomplet/incohérent : aucune comparaison partielle présentée valide."""


def charger_lot(repertoire: Path) -> tuple[TariffBatch, dict]:
    if repertoire.is_symlink() or not repertoire.is_dir():
        raise LotRefuse("Répertoire de lot absent ou symbolique")
    manifest_original = _lire(repertoire / "manifest.json")
    manifest = _json(manifest_original)
    if (not isinstance(manifest, dict) or manifest.get("statut") != "quarantaine"
            or manifest.get("publication_active") is not False
            or manifest.get("validation_juridique") != "non_validee"):
        raise LotRefuse("Manifeste de préparation attendu ; aucun lot actif accepté")
    nom_recu = manifest.get("source_nom_recu")
    try:
        date_import = datetime.fromisoformat(manifest["date_importation"])
        if date_import.utcoffset() != timedelta(0):
            raise ValueError("Horodatage UTC requis")
    except (KeyError, TypeError, ValueError) as exc:
        raise LotRefuse("Date d'import UTC absente ou invalide") from exc
    if not isinstance(nom_recu, str) or not nom_recu:
        raise LotRefuse("Nom reçu absent du manifeste")
    empreintes = manifest.get("fichiers_sha256")
    if not isinstance(empreintes, dict):
        raise LotRefuse("Table d'empreintes absente")
    sources = [nom for nom in empreintes if nom in {"source_recue.json", "source_recue.csv", "source_recue.xlsx", "source_recue.xls", "source_recue.xml", "source_recue.zip"}]
    if len(sources) != 1:
        raise LotRefuse("Une source reçue prise en charge est requise")
    attendus = {sources[0], "metadata_original.json", "lot.json", "rapport.json"}
    if set(empreintes) != attendus or {p.name for p in repertoire.iterdir()} != attendus | {"manifest.json"}:
        raise LotRefuse("Fichiers absents/inattendus ou nom d'archive non autorisé")
    fichiers = {}
    for nom in sorted(attendus):
        valeur = empreintes[nom]
        if not isinstance(valeur, str) or re.fullmatch(r"[a-f0-9]{64}", valeur) is None:
            raise LotRefuse("Empreinte invalide")
        contenu = _lire(repertoire / nom)
        if hashlib.sha256(contenu).hexdigest() != valeur:
            raise LotRefuse("Empreinte différente : " + nom)
        fichiers[nom] = contenu
    # Rejet des clés dupliquées avant validation Pydantic.
    brut = _json(fichiers["lot.json"])
    lot = TariffBatch.model_validate_json(json.dumps(brut, ensure_ascii=False))
    if sources[0] != "source_recue." + lot.source.format:
        raise LotRefuse("Format de source incohérent")
    if lot.source.sha256 != empreintes[sources[0]]:
        raise LotRefuse("Source déclarée différente de l'archive reçue")
    # Rejouer le lecteur sans sortie : un lot normalisé modifié puis re-haché
    # ne doit pas diverger silencieusement de sa source et de son mapping.
    reproduit, rapport, _, _ = _analyser_contenu(fichiers[sources[0]], fichiers["metadata_original.json"])
    if reproduit.model_dump(mode="json") != lot.model_dump(mode="json"):
        raise LotRefuse("Lot non reproductible depuis la source reçue et les métadonnées")
    releve = _json(fichiers["rapport.json"])
    # L'ancien lot 1 ne comportait pas perimetre_lecture. Tout champ fourni
    # doit néanmoins correspondre au rejeu (y compris types JSON imbriqués).
    obligatoires = set(rapport) - {"perimetre_lecture"}
    if (not isinstance(releve, dict) or not obligatoires <= set(releve)
            or set(releve) - set(rapport) or releve.get("ecrit") is not True
            or any(json.dumps(releve[cle], sort_keys=True) != json.dumps(rapport[cle], sort_keys=True)
                   for cle in releve if cle != "ecrit")):
        raise LotRefuse("Rapport d'import incohérent")
    rapport["archive"] = {"source_nom_recu": nom_recu, "date_importation": manifest["date_importation"],
                          "manifest_sha256": hashlib.sha256(manifest_original).hexdigest()}

    return lot, rapport


def _contenu(objet):
    return objet.model_dump(mode="json", exclude={"id", "reference"})


def _diff_collection(avant, apres, cle):
    a = {getattr(o, cle): o for o in avant}
    b = {getattr(o, cle): o for o in apres}
    modifications = []
    for identifiant in sorted(a.keys() & b.keys()):
        ancien, nouveau = _contenu(a[identifiant]), _contenu(b[identifiant])
        champs = {k: {"avant": ancien[k], "apres": nouveau[k]} for k in ancien if ancien[k] != nouveau[k]}
        if champs:
            modifications.append({"identifiant": identifiant, "changements": champs})
    return {"ajoutes": sorted(b.keys() - a.keys()), "retires": sorted(a.keys() - b.keys()), "modifies": modifications}


def _origine(objet):
    origine = {"reference": objet.reference.model_dump(mode="json")}
    if hasattr(objet, "id"):
        origine["id"] = objet.id
    return origine


def _provenances(avant, apres, cle):
    a = {getattr(o, cle): o for o in avant}
    b = {getattr(o, cle): o for o in apres}
    changements = []
    for identifiant in sorted(a.keys() & b.keys()):
        ancien, nouveau = _origine(a[identifiant]), _origine(b[identifiant])
        if ancien != nouveau:
            changements.append({"identifiant": identifiant, "avant": ancien, "apres": nouveau})
    return changements


def _mesures(lot):
    result = defaultdict(list)
    details = defaultdict(list)
    origines = defaultdict(list)
    for mesure in lot.mesures:
        valeur = _contenu(mesure)
        if mesure.taux is not None:
            # normalize() dépend de la précision du contexte Decimal et peut
            # arrondir : comparaison exacte, sans calcul ni arrondi de taux.
            # Clé coefficient/exposant : ne pas développer un exposant énorme.
            signe, chiffres, exposant = mesure.taux.as_tuple()
            fin = len(chiffres)
            while fin and chiffres[fin - 1] == 0:
                fin -= 1
            coefficient = "".join(str(chiffre) for chiffre in chiffres[:fin])
            valeur["taux"] = (("-" if signe else "") + coefficient + "e" + str(exposant + len(chiffres) - fin)) if fin else "0"
        result[mesure.code_tarifaire_10].append(valeur)
        details[mesure.code_tarifaire_10].append(mesure.model_dump(mode="json"))
        origines[mesure.code_tarifaire_10].append({**valeur, **_origine(mesure)})
    def trier(collection):
        return {cle: sorted(valeurs, key=lambda v: json.dumps(v, sort_keys=True)) for cle, valeurs in collection.items()}
    return trier(result), trier(details), trier(origines)


def comparer_lots(avant: Path, apres: Path) -> dict:
    a, rapport_a = charger_lot(avant)
    b, rapport_b = charger_lot(apres)
    mesures_a, details_a, origines_a = _mesures(a)
    mesures_b, details_b, origines_b = _mesures(b)
    mesures = [{"code_tarifaire_10": code, "avant": details_a.get(code, []), "apres": details_b.get(code, [])}
               for code in sorted(mesures_a.keys() | mesures_b.keys()) if mesures_a.get(code, []) != mesures_b.get(code, [])]
    avertissements = ["Différences entre lots reçus : ni abrogations ni nouveaux droits applicables déduits.",
                      "Empreintes et reproductibilité ne prouvent pas authenticité, exhaustivité ou applicabilité."]
    if a.source.version_source == b.source.version_source and a.source.sha256 != b.source.sha256:
        avertissements.append("Même version déclarée mais contenus sources différents : revue requise.")
    perimetre_a, perimetre_b = rapport_a["perimetre_lecture"], rapport_b["perimetre_lecture"]
    if perimetre_a != perimetre_b:
        avertissements.append("Périmètres de lecture différents : vérifier feuilles et découpages avant interprétation.")
    return {"lecture_seule": True, "publication_active": False, "validation_humaine_requise": True,
            "completude_reglementaire": "non_etablie", "sources": {"avant": a.source.model_dump(mode="json"), "apres": b.source.model_dump(mode="json")},
            "perimetres": {"avant": perimetre_a, "apres": perimetre_b},
            "archives": {"avant": rapport_a["archive"], "apres": rapport_b["archive"]},
            "lignes": _diff_collection(a.lignes, b.lignes, "code_tarifaire_10"),
            "hierarchie": {nom: _diff_collection(getattr(a, nom), getattr(b, nom), "id" if nom == "sections" else "code")
                           for nom in ("sections", "chapitres", "positions", "sous_positions")},
            "mesures_modifiees": mesures,
            "provenances_modifiees": {
                "lignes": _provenances(a.lignes, b.lignes, "code_tarifaire_10"),
                "hierarchie": {nom: _provenances(getattr(a, nom), getattr(b, nom), "id" if nom == "sections" else "code")
                               for nom in ("sections", "chapitres", "positions", "sous_positions")},
                "mesures": [{"code_tarifaire_10": code, "avant": details_a.get(code, []), "apres": details_b.get(code, [])}
                            for code in sorted(mesures_a.keys() & mesures_b.keys())
                            if mesures_a[code] == mesures_b[code] and origines_a[code] != origines_b[code]],
            }, "avertissements": avertissements}
