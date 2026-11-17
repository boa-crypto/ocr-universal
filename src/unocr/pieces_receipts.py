"""Reçus locaux de suppression, atomiques avec les seules métadonnées SQLite.

Ni journal infalsifiable, ni relais transactionnel du fichier audit.log. L'absence
historique d'un reçu ne prouve jamais qu'une opération a été annulée.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field, ValidationError

from .business_store import BusinessStore
from .models import Justificatif

COLLECTION = "suppression_justificatif"
LIMITE = "Reçu local depuis la passe 41, non infalsifiable. Absence de reçu ne prouve pas annulation. Audit fichier non transactionnel."


class RecuSuppressionPiece(BaseModel):
    id: str  # identifiant du justificatif supprimé ; un reçu par pièce
    event: Literal["justificatif_supprime"] = "justificatif_supprime"
    frais_id: str
    date_utc: AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hash_sha256: str  # empreinte déclarée, pas une nouvelle vérification du blob
    taille_octets: int


def enregistrer_suppression(transaction: BusinessStore, piece: Justificatif) -> None:
    recus = transaction.related(COLLECTION, RecuSuppressionPiece)
    if piece.id in recus:
        raise sqlite3.IntegrityError("Reçu déjà présent : aucun remplacement autorisé")
    recus[piece.id] = RecuSuppressionPiece(id=piece.id, frais_id=piece.frais_id,
        hash_sha256=piece.hash_sha256, taille_octets=piece.taille_octets)


def consulter_suppression(racine: Path, identifiant: str) -> dict:
    rapport = {"lecture_seule": True, "id": identifiant, "recu": None, "limite": LIMITE}
    connexion = None
    try:
        base = racine / "metier.sqlite3"
        if base.is_symlink() or not base.is_file():
            raise ValueError("Base absente ou symbolique")
        with base.open("rb") as fichier:
            if fichier.read(20)[18:20] == b"\x02\x02":
                raise ValueError("Base WAL refusée pour ne créer aucun sidecar")
        connexion = sqlite3.connect(base.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
        connexion.execute("PRAGMA query_only=ON")
        ligne = connexion.execute("SELECT payload FROM objects WHERE collection=? AND id=?",
                                  (COLLECTION, identifiant)).fetchone()
        if ligne is not None:
            recu = RecuSuppressionPiece.model_validate_json(ligne[0])
            if recu.id != identifiant:
                raise ValueError("Identifiant du reçu incohérent")
            rapport["recu"] = recu.model_dump(mode="json")
        rapport["etat"] = "trouve" if ligne is not None else "absent"
    except (OSError, sqlite3.Error, ValidationError, ValueError):
        rapport["etat"] = "indisponible"
        rapport["detail"] = "Base ou reçu inexploitable : vérifier accès, format et métadonnées (WAL refusé)"
    finally:
        if connexion is not None:
            connexion.close()
    return rapport
