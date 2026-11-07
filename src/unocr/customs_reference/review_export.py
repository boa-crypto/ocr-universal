"""Contrôle local d'un export de revue ; aucune authentification ou importation."""
import hashlib
import json
import math
import os
import stat
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from .models import StrictModel

MAX_EXPORT = 10 * 1024 * 1024
MAX_PROFONDEUR = 64


class ExportRefuse(ValueError):
    """Fichier refusé sans exposer son contenu dans le diagnostic."""


class ObjetDocumentaire(BaseModel):
    model_config = ConfigDict(strict=True, extra="allow")
    __pydantic_extra__: dict[str, JsonValue] = Field(init=False)


class ProvenanceExport(ObjetDocumentaire):
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class ArchivesExport(StrictModel):
    avant: ProvenanceExport
    apres: ProvenanceExport


class RapportSimpleExport(ObjetDocumentaire):
    archive: ProvenanceExport


class RapportDiffExport(ObjetDocumentaire):
    archives: ArchivesExport


MARQUEURS = {
    "schema_version": "1", "type_export": "rapport_revue_documentaire_non_valide",
    "lecture_seule": True, "publication_active": False, "validation_juridique": "non_validee",
    "perimetre": "rapport_ou_page_uniquement_pas_corpus_complet",
}
ROUTE = (r"^/api/v1/customs-review/(?:diff|article-diff|tariff-compare|tariff-measures|lots/[A-Za-z0-9][A-Za-z0-9_-]{0,63}/"
         r"(?:check|search|sources|measure-search|history|coverage|tree|article|article-diff|article-pdf-match|article-relations|relation-pdf-match|code-tree|pdf|fiscal-pdf|tariff/[0-9]{10}))(?:\?[^#\x00-\x20]*)?$")


class ExportRevue(StrictModel):
    schema_version: Literal["1"]
    type_export: Literal["rapport_revue_documentaire_non_valide"]
    lecture_seule: Literal[True]
    publication_active: Literal[False]
    validation_juridique: Literal["non_validee"]
    perimetre: Literal["rapport_ou_page_uniquement_pas_corpus_complet"]
    horodatage_client_non_certifie: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$")
    requete_relative: str = Field(pattern=ROUTE, max_length=16384)
    resultat: RapportSimpleExport | RapportDiffExport

    @model_validator(mode="before")
    @classmethod
    def marqueurs_exacts(cls, value):
        if not isinstance(value, dict) or any(type(value.get(k)) is not type(v) or value[k] != v for k, v in MARQUEURS.items()):
            raise ValueError("Marqueurs d'export incompatibles")
        return value

    @model_validator(mode="after")
    def coherence(self):
        datetime.strptime(self.horodatage_client_non_certifie, "%Y-%m-%dT%H:%M:%S.%fZ")
        # Le pattern JSON Schema seul ne vérifie ni le calendrier ni ce lien.
        diff = self.requete_relative.split("?", 1)[0] in {"/api/v1/customs-review/diff", "/api/v1/customs-review/article-diff",
                "/api/v1/customs-review/tariff-compare", "/api/v1/customs-review/tariff-measures"}
        if diff != isinstance(self.resultat, RapportDiffExport):
            raise ValueError("Provenance incompatible avec la route")
        extras = self.resultat.__pydantic_extra__
        for k, v in {"lecture_seule": True, "publication_active": False, "validation_juridique": "non_validee"}.items():
            if k in extras and (type(extras[k]) is not type(v) or extras[k] != v):
                raise ValueError("Marqueurs du rapport contradictoires")
        # Le contrôle Code expose aussi une liste « archives » de PDF déclarés,
        # distincte de la paire avant/après d'une comparaison.
        if "archive" in extras or ("archives" in extras and not isinstance(extras["archives"], list)):
            raise ValueError("Provenance simple/double ambiguë")
        return self


def _paires(paires):
    resultat = {}
    for cle, valeur in paires:
        if cle in resultat:
            raise ExportRefuse("Clé JSON dupliquée")
        resultat[cle] = valeur
    return resultat


def _constant(_):
    raise ExportRefuse("Nombre JSON non fini")


def _decimal(valeur):
    resultat = float(valeur)
    if not math.isfinite(resultat):
        raise ExportRefuse("Nombre JSON hors plage finie")
    return resultat


def analyser_export(contenu: bytes) -> dict:
    """Retourne un constat technique sans recopier le rapport ou ses paramètres."""
    if type(contenu) is not bytes or not 0 < len(contenu) <= MAX_EXPORT:
        raise ExportRefuse("Export vide ou dépassant 10 Mio")
    try:
        objet = json.loads(contenu.decode("utf-8"), object_pairs_hook=_paires,
                           parse_constant=_constant, parse_float=_decimal)
        pile = [(objet, 0)]
        while pile:
            valeur, profondeur = pile.pop()
            if profondeur > MAX_PROFONDEUR:
                raise ExportRefuse("Profondeur JSON supérieure à 64")
            if isinstance(valeur, dict):
                for cle, item in valeur.items():
                    cle.encode("utf-8")
                    pile.append((item, profondeur + 1))
            elif isinstance(valeur, list):
                pile.extend((item, profondeur + 1) for item in valeur)
            elif isinstance(valeur, str):
                valeur.encode("utf-8")
        # Pydantic expose parfois la valeur d'entrée : ne pas propager ses erreurs.
        modele = ExportRevue.model_validate(objet)
        provenances = ([modele.resultat.archive] if isinstance(modele.resultat, RapportSimpleExport)
                       else [modele.resultat.archives.avant, modele.resultat.archives.apres])
    except ExportRefuse:
        raise
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise ExportRefuse("JSON ou contrat d'export incompatible") from None
    return {"type_controle": "export_revue_hors_ligne", "statut": "structure_compatible",
            "lecture_seule": True, "publication_active": False, "validation_juridique": "non_validee",
            "sha256_fichier": hashlib.sha256(contenu).hexdigest(), "octets": len(contenu),
            "manifestes_declares": [p.manifest_sha256 for p in provenances],
            "authenticite_verifiee": False, "integrite_archives_verifiee": False,
            "audit_serveur_verifie": False,
            "avertissements": ["Contrôle de structure, pas preuve d'origine ou validation du contenu métier.",
                               "Empreinte du fichier reçu seulement ; aucune comparaison aux archives ou au registre.",
                               "Aucun import, publication, calcul, requête réseau ou horodatage certifié."]}


def verifier_export(chemin: Path) -> dict:
    """Lecture bornée d'un fichier régulier ; pas de suivi d'un symlink final."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        if chemin.is_symlink():
            raise ExportRefuse("Lien symbolique final refusé")
        with os.fdopen(os.open(chemin, flags), "rb") as fichier:
            infos = os.fstat(fichier.fileno())
            if not stat.S_ISREG(infos.st_mode) or infos.st_size > MAX_EXPORT:
                raise ExportRefuse("Fichier non régulier ou dépassant 10 Mio")
            contenu = fichier.read(MAX_EXPORT + 1)
    except OSError:
        raise ExportRefuse("Export illisible ou absent") from None
    return analyser_export(contenu)
