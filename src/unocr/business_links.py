"""Liens métier vers les dossiers JSON, contrôlés sans cache mémoire.

Les routes appellent ces contrôles sous le verrou transactionnel du magasin
métier. Cela coordonne les écritures API, pas les manipulations externes de fichiers.
"""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException

from .business_store import BusinessStore
from .models import (
    DeclarationDouaniere,
    Expeditions,
    Facture,
    Frais,
    Liquidation,
    TerminalEnlevement,
)


def exiger_dossier(cfg: Any, identifiant: str, absent: int = 422) -> None:
    if not isinstance(identifiant, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", identifiant):
        raise HTTPException(422, "Identifiant de dossier invalide")
    chemin = cfg.data_dir / "dossiers" / f"{identifiant}.json"
    try:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(absent, "Le dossier référencé n'existe pas") from None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HTTPException(503, "Impossible de vérifier le dossier référencé") from exc
    if not isinstance(donnees, dict) or donnees.get("id") != identifiant:
        raise HTTPException(503, "Le fichier du dossier référencé est incohérent")


def exiger_dossier_sans_liens(transaction: BusinessStore[DeclarationDouaniere], identifiant: str) -> None:
    for collection, model, nom in [
        ("declaration", DeclarationDouaniere, "une déclaration"),
        ("liquidation", Liquidation, "une liquidation"),
        ("terminal", TerminalEnlevement, "un enlèvement"),
        ("expedition", Expeditions, "une expédition"),
        ("frais", Frais, "un frais"),
        ("facture", Facture, "une facture"),
    ]:
        if any(objet.dossier_id == identifiant for objet in transaction.related(collection, model).values()):
            raise HTTPException(409, f"Suppression refusée : {nom} référence encore ce dossier")
