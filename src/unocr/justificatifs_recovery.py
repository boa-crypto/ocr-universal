"""Récupération ciblée : copie vérifiée, sans écrasement ni suppression de preuve.

Le plan est en lecture seule. L'application prend le même verrou SQLite que les
routes des pièces, mais ne modifie aucune métadonnée. La quarantaine est conservée.
"""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import tempfile
from pathlib import Path

from pydantic import ValidationError

from .models import Frais, Justificatif


class RecuperationRefusee(Exception):
    """Conditions insuffisantes : ne rien deviner ni écraser."""


def recuperer_piece(racine: Path, identifiant: str, appliquer: bool = False) -> dict:
    temporaire = None
    connexion = None
    rapport = None
    try:
        base = racine / "metier.sqlite3"
        if base.is_symlink() or not base.is_file():
            raise RecuperationRefusee("Base absente ou symbolique")
        with base.open("rb") as fichier:
            if fichier.read(20)[18:20] == b"\x02\x02":
                raise RecuperationRefusee("Base WAL non prise en charge")
        mode = "rw" if appliquer else "ro"
        connexion = sqlite3.connect(base.resolve().as_uri() + "?mode=" + mode, uri=True, timeout=5)
        if not appliquer:
            connexion.execute("PRAGMA query_only=ON")
        connexion.execute("BEGIN IMMEDIATE" if appliquer else "BEGIN")
        pieces = {}
        parents = {}
        for collection, cle, payload in connexion.execute(
            "SELECT collection,id,payload FROM objects WHERE collection IN ('justificatif','frais')"
        ):
            modele = Justificatif if collection == "justificatif" else Frais
            objet = modele.model_validate_json(payload)
            if objet.id != cle:
                raise RecuperationRefusee("Métadonnée incohérente : identifiant différent de sa clé")
            (pieces if collection == "justificatif" else parents)[cle] = objet
        piece = pieces.get(identifiant)
        if piece is None:
            raise RecuperationRefusee("Métadonnée justificatif absente")
        parent = parents.get(piece.frais_id)
        if parent is None or parent.justificatifs.count(identifiant) != 1:
            raise RecuperationRefusee("Le frais doit référencer exactement une fois cette pièce")
        if any(identifiant in autre.justificatifs for cle, autre in parents.items() if cle != parent.id):
            raise RecuperationRefusee("Plusieurs frais référencent cette pièce")
        if not re.fullmatch(r"justificatifs/[a-f0-9]{32}\.bin", piece.chemin_fichier):
            raise RecuperationRefusee("Chemin non canonique")
        if any(autre.chemin_fichier == piece.chemin_fichier for cle, autre in pieces.items() if cle != identifiant):
            raise RecuperationRefusee("Plusieurs pièces partagent le même chemin")
        if not 0 < piece.taille_octets <= 20 * 1024 * 1024:
            raise RecuperationRefusee("Taille déclarée invalide")
        if not re.fullmatch(r"[a-f0-9]{64}", piece.hash_sha256):
            raise RecuperationRefusee("Empreinte déclarée invalide")
        repertoire = racine / "justificatifs"
        if repertoire.is_symlink() or not repertoire.is_dir():
            raise RecuperationRefusee("Répertoire justificatifs absent ou symbolique")
        cible = racine / piece.chemin_fichier
        quarantaine = cible.with_name("." + cible.name + ".deleted.tmp")
        if cible.exists() or cible.is_symlink():
            raise RecuperationRefusee("Destination déjà présente : aucun écrasement permis")
        if quarantaine.is_symlink() or not quarantaine.is_file():
            raise RecuperationRefusee("Quarantaine absente ou symbolique")
        with quarantaine.open("rb") as fichier:
            contenu = fichier.read(piece.taille_octets + 1)
        if (len(contenu) != piece.taille_octets
                or hashlib.sha256(contenu).hexdigest() != piece.hash_sha256):
            raise RecuperationRefusee("La quarantaine ne correspond pas à la taille et à l'empreinte attendues")
        if appliquer:
            with tempfile.NamedTemporaryFile(dir=repertoire, prefix=".restore-", suffix=".tmp", delete=False) as fichier:
                temporaire = Path(fichier.name)
                fichier.write(contenu)
                fichier.flush()
                os.fsync(fichier.fileno())
            # Publication atomique et exclusive : même en cas de course, link
            # échoue si la destination existe. Aucun fallback écrasant.
            os.link(temporaire, cible)
        rapport = {"etat": "restaure" if appliquer else "pret", "applique": appliquer,
                "id": identifiant, "source": "justificatifs/" + quarantaine.name,
                "destination": piece.chemin_fichier, "octets": piece.taille_octets,
                "sha256": piece.hash_sha256, "quarantaine_conservee": True,
                "limite": "Sauvegarder et copier la quarantaine à part (les .tmp sont exclus des archives). Suspendre les écritures. Aucun lien ni métadonnée réparé."}
        return rapport
    except RecuperationRefusee:
        raise
    except FileExistsError as exc:
        raise RecuperationRefusee("Destination apparue pendant l'opération : aucun écrasement") from exc
    except (OSError, sqlite3.Error, ValidationError) as exc:
        raise RecuperationRefusee("Lecture ou copie impossible ; vérifier accès disque et métadonnées") from exc
    finally:
        if connexion is not None:
            connexion.rollback()
            connexion.close()
        if temporaire is not None:
            # Après publication la copie finale est indépendante du nom temporaire.
            # Un échec de nettoyage est laissé visible au diagnostic.
            try:
                temporaire.unlink(missing_ok=True)
            except OSError:
                if rapport is not None:
                    rapport["residu_temporaire"] = "justificatifs/" + temporaire.name
