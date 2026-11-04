"""Référentiels métier génériques (ports, pays, devises, équipes…).

**Pourquoi ce module existe.** Les écrans de référentiel de la mission
(ports, pays, devises, types de marchandises, grilles tarifaires, règles
documentaires, paramètres métier, équipes) n'avaient aucun stockage : ils
n'existaient pas. Plutôt que huit tables quasi identiques, on expose une
collection typée par URL, avec un schéma minimal (libellé, code, attributs
libres) réellement persisté sur disque.

**Ce que ce module ne fait pas.** Il ne crée aucune donnée : une collection
vide reste vide, l'interface propose de la remplir. Il ne valide pas de règle
métier (chaque domaine garde ses contrôles) ; il garantit seulement
l'unicité du code dans une collection et la traçabilité des écritures.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import new_id

log = get_logger("referentiels")

router = APIRouter(prefix="/api/referentiels", tags=["referentiels"])

#: Collections exposées. Le libellé sert de titre quand l'interface n'en
#: fournit pas ; les champs attendus restent déclaratifs (aucune contrainte
#: métier ici, elle appartient aux modules concernés).
COLLECTIONS: dict[str, dict[str, Any]] = {
    "ports": {
        "titre": "Ports",
        "description": "Ports maritimes utilisés dans les dossiers (chargement, destination, escales).",
        "champs": ["libelle", "code", "pays", "type"],
    },
    "pays": {
        "titre": "Pays",
        "description": "Pays d'origine, d'expédition et de destination.",
        "champs": ["libelle", "code", "zone"],
    },
    "devises": {
        "titre": "Devises",
        "description": "Devises utilisées par la facturation et les dossiers.",
        "champs": ["libelle", "code", "symbole"],
    },
    "types-marchandises": {
        "titre": "Types de marchandises",
        "description": "Natures de marchandise et contraintes associées.",
        "champs": ["libelle", "code", "categorie", "contraintes"],
    },
    "tarifs": {
        "titre": "Référentiels tarifaires",
        "description": "Grilles de frais et barèmes appliqués aux dossiers.",
        "champs": ["libelle", "code", "categorie", "montant", "devise", "unite"],
    },
    "regles-documentaires": {
        "titre": "Règles documentaires",
        "description": "Pièces attendues par profil de dossier et conditions d'application.",
        "champs": ["libelle", "code", "profil", "pieces", "obligatoire"],
    },
    "parametres": {
        "titre": "Paramètres métier",
        "description": "Valeurs de configuration propres à l'exploitation.",
        "champs": ["libelle", "cle", "valeur", "portee"],
    },
    "equipes": {
        "titre": "Équipes",
        "description": "Groupes d'utilisateurs et périmètre de responsabilité.",
        "champs": ["libelle", "code", "responsable", "membres"],
    },
    "types-documents": {
        "titre": "Types de documents",
        "description": "Typologie documentaire utilisée par la classification.",
        "champs": ["libelle", "code", "profil", "obligatoire"],
    },
    "types-marchandises-complementaires": {
        "titre": "Types de marchandises (compléments)",
        "description": "Précisions de nomenclature propres à l'exploitation.",
        "champs": ["libelle", "code", "categorie"],
    },
    "versions-matrice": {
        "titre": "Versions documentaires",
        "description": "Registre des versions de formulaires et de matrices utilisées.",
        "champs": ["libelle", "code", "version", "statut"],
    },
}


class EntreeCreate(BaseModel):
    libelle: str = Field(min_length=1, max_length=200)
    code: str = ""
    attributs: dict[str, Any] = Field(default_factory=dict)


class EntreeUpdate(BaseModel):
    libelle: Optional[str] = Field(default=None, min_length=1, max_length=200)
    code: Optional[str] = None
    attributs: Optional[dict[str, Any]] = None


def _chemin() -> Path:
    """Fichier de persistance, résolu à chaque appel.

    La configuration est relue ici (et non capturée à l'import) pour que les
    tests et les déploiements à répertoire de données variable écrivent
    réellement là où l'application est configurée.
    """
    return Path(get_config().data_dir) / "referentiels.json"


def _charger() -> dict[str, dict[str, dict[str, Any]]]:
    chemin = _chemin()
    if not chemin.is_file():
        return {nom: {} for nom in COLLECTIONS}
    try:
        brut = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        log.warning("référentiels illisibles, réinitialisation en mémoire")
        return {nom: {} for nom in COLLECTIONS}
    if not isinstance(brut, dict):
        return {nom: {} for nom in COLLECTIONS}
    return {nom: dict(brut.get(nom) or {}) for nom in COLLECTIONS}


def _sauver(donnees: dict[str, dict[str, dict[str, Any]]]) -> None:
    chemin = _chemin()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(".json.tmp")
    temporaire.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporaire, chemin)


def _collection_valide(collection: str) -> None:
    if collection not in COLLECTIONS:
        raise HTTPException(
            404,
            f"collection inconnue : {collection}. Disponibles : "
            + ", ".join(sorted(COLLECTIONS)),
        )


def _code_unique(entrees: dict[str, dict[str, Any]], code: str, sauf: str = "") -> None:
    if not code:
        return
    for identifiant, entree in entrees.items():
        if identifiant == sauf:
            continue
        if str(entree.get("code") or "").strip().lower() == code.strip().lower():
            raise HTTPException(409, f"le code « {code} » existe déjà dans cette collection")


@router.get("")
def lister_collections() -> dict:
    """Catalogue des collections, avec le nombre d'entrées réelles."""
    donnees = _charger()
    return {
        "collections": [
            {
                "nom": nom,
                "titre": meta["titre"],
                "description": meta["description"],
                "champs": meta["champs"],
                "total": len(donnees.get(nom) or {}),
            }
            for nom, meta in COLLECTIONS.items()
        ]
    }


@router.get("/{collection}")
def lister_entrees(collection: str, recherche: Optional[str] = None) -> dict:
    _collection_valide(collection)
    entrees = list((_charger().get(collection) or {}).values())
    entrees.sort(key=lambda e: str(e.get("libelle", "")).lower())
    if recherche:
        terme = recherche.lower()
        entrees = [
            e for e in entrees
            if terme in json.dumps(e, ensure_ascii=False).lower()
        ]
    return {
        "collection": collection,
        "titre": COLLECTIONS[collection]["titre"],
        "champs": COLLECTIONS[collection]["champs"],
        "total": len(entrees),
        "entrees": entrees,
    }


@router.post("/{collection}", status_code=201)
def creer_entree(request: Request, collection: str, entree: EntreeCreate) -> dict:
    _collection_valide(collection)
    donnees = _charger()
    entrees = donnees.setdefault(collection, {})
    _code_unique(entrees, entree.code)
    identifiant = new_id(f"{collection[:4]}_")
    enregistrement = {
        "id": identifiant,
        "libelle": entree.libelle.strip(),
        "code": entree.code.strip(),
        "attributs": dict(entree.attributs),
        "cree_le": time.time(),
        "modifie_le": time.time(),
    }
    entrees[identifiant] = enregistrement
    _sauver(donnees)
    audit(request.app.state.cfg.log_dir, "referentiel_cree",
          cible=identifiant, collection=collection, libelle=enregistrement["libelle"])
    return enregistrement


@router.get("/{collection}/{entree_id}")
def lire_entree(collection: str, entree_id: str) -> dict:
    _collection_valide(collection)
    entrees = _charger().get(collection) or {}
    if entree_id not in entrees:
        raise HTTPException(404, "entrée introuvable")
    return entrees[entree_id]


@router.put("/{collection}/{entree_id}")
def modifier_entree(
    request: Request,
    collection: str,
    entree_id: str,
    entree: EntreeUpdate,
) -> dict:
    _collection_valide(collection)
    donnees = _charger()
    entrees = donnees.setdefault(collection, {})
    if entree_id not in entrees:
        raise HTTPException(404, "entrée introuvable")
    enregistrement = dict(entrees[entree_id])
    if entree.code is not None:
        _code_unique(entrees, entree.code, sauf=entree_id)
        enregistrement["code"] = entree.code.strip()
    if entree.libelle is not None:
        enregistrement["libelle"] = entree.libelle.strip()
    if entree.attributs is not None:
        enregistrement["attributs"] = dict(entree.attributs)
    enregistrement["modifie_le"] = time.time()
    entrees[entree_id] = enregistrement
    _sauver(donnees)
    audit(request.app.state.cfg.log_dir, "referentiel_modifie",
          cible=entree_id, collection=collection)
    return enregistrement


@router.delete("/{collection}/{entree_id}")
def supprimer_entree(request: Request, collection: str, entree_id: str) -> dict:
    _collection_valide(collection)
    donnees = _charger()
    entrees = donnees.setdefault(collection, {})
    if entree_id not in entrees:
        raise HTTPException(404, "entrée introuvable")
    supprimee = entrees.pop(entree_id)
    _sauver(donnees)
    audit(request.app.state.cfg.log_dir, "referentiel_supprime",
          cible=entree_id, collection=collection, libelle=supprimee.get("libelle"))
    return {"supprime": entree_id, "collection": collection}
