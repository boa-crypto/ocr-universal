"""Empreintes attendues fournies séparément ; aucune authenticité implicite."""
import hashlib
import re

from .review_export import ExportRefuse, _lire_export


def valider_empreinte(valeur):
    if valeur is not None and (not isinstance(valeur,str) or re.fullmatch(r"[a-f0-9]{64}",valeur) is None):
        raise ExportRefuse("Empreinte attendue SHA256 minuscule de 64 caractères requise")


def verifier_octets(contenu,attendue):
    if attendue is not None and hashlib.sha256(contenu).hexdigest() != attendue:
        raise ExportRefuse("Export différent de l'empreinte attendue fournie")


def verifier_manifeste(repertoire,attendue):
    if attendue is None:
        return
    if repertoire.is_symlink() or not repertoire.is_dir():
        raise ExportRefuse("Dossier de manifeste attendu absent ou symbolique")
    contenu = _lire_export(repertoire / "manifest.json")
    if hashlib.sha256(contenu).hexdigest() != attendue:
        raise ExportRefuse("Manifeste différent de l'empreinte attendue fournie")


def verifier_manifeste_rejoue(actual,attendue):
    if attendue is not None and actual != attendue:
        raise ExportRefuse("Manifeste du rejeu différent de l'empreinte attendue fournie")


def constat_empreintes(export,manifestes):
    nombre = int(export is not None)+sum(v is not None for v in manifestes.values())
    return {"export_epingle":export is not None,
            "manifestes_epingles":{role:v is not None for role,v in manifestes.items()},
            "nombre_empreintes_verifiees":nombre,"authenticite_des_references_verifiee":False}
