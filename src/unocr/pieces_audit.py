"""Relais ciblé de reçus SQLite vers JSONL, opt-in et sans marqueur en base.

Suspendre les écritures serveur. Le verrou flock ne coordonne que les relais
coopérants ; audit() historique ne le prend pas. Pas de garantie exactly-once
face aux autres écrivains, aux rotations ou aux coupures électriques.
"""
from __future__ import annotations

import json
import os
import stat
from datetime import datetime
from pathlib import Path

from .pieces_receipts import consulter_suppression

MAX_JOURNAL = 64 * 1024 * 1024
MAX_LIGNE = 1024 * 1024
LIMITE = "Suspendre les écritures et rotations. SQLite inchangé. Pas de transaction distribuée ni de garantie exactly-once ; conserver le reçu."


class RelaisRefuse(Exception):
    """Conditions insuffisantes : ne jamais deviner ou réparer le journal."""


def _objet_sans_doublon(paires):
    objet = {}
    for cle, valeur in paires:
        if cle in objet:
            raise ValueError("Clé JSON dupliquée")
        objet[cle] = valeur
    return objet


def _constante_refusee(valeur):
    raise ValueError("Constante JSON non standard : " + valeur)


def _inspecter(fichier, attendu: dict) -> str:
    if not stat.S_ISREG(os.fstat(fichier.fileno()).st_mode):
        raise RelaisRefuse("Journal non régulier")
    if os.fstat(fichier.fileno()).st_size > MAX_JOURNAL:
        raise RelaisRefuse("Journal trop volumineux (64 Mio maximum)")
    trouve = False
    lus = 0
    while ligne := fichier.readline(MAX_LIGNE + 1):
        lus += len(ligne)
        if len(ligne) > MAX_LIGNE or lus > MAX_JOURNAL:
            raise RelaisRefuse("Journal ou ligne trop volumineux")
        if not ligne.endswith(b"\n"):
            raise RelaisRefuse("Dernière ligne incomplète : aucun ajout")
        try:
            objet = json.loads(ligne, object_pairs_hook=_objet_sans_doublon, parse_constant=_constante_refusee)
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise RelaisRefuse("Journal JSONL invalide : aucun ajout") from exc
        if not isinstance(objet, dict):
            raise RelaisRefuse("Entrée JSONL non objet")
        if objet.get("recu_id") == attendu["recu_id"]:
            if any(objet.get(cle) != valeur for cle, valeur in attendu.items()):
                raise RelaisRefuse("Événement contradictoire pour ce reçu")
            trouve = True
        elif objet.get("event") == attendu["event"] and objet.get("cible") == attendu["cible"]:
            # L'audit historique n'avait pas de recu_id ni les champs du reçu.
            # Ne pas le dupliquer ni prétendre le compléter/authentifier.
            if objet.get("recu_id") is not None:
                raise RelaisRefuse("Identifiant de reçu contradictoire")
            trouve = True
    if not trouve and lus + len((json.dumps(attendu, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")) > MAX_JOURNAL:
        raise RelaisRefuse("Ajout dépasserait la limite du journal")
    return "deja_present" if trouve else "pret"


def relayer_suppression(racine: Path, identifiant: str, journal: Path, appliquer=False) -> dict:
    rapport = {"id": identifiant, "applique": False, "lecture_seule": not appliquer, "limite": LIMITE}
    tentative = False
    try:
        source = consulter_suppression(racine, identifiant)
        if source["etat"] != "trouve":
            raise RelaisRefuse("Reçu absent ou inexploitable : aucun événement déduit")
        recu = source["recu"]
        attendu = {"ts": datetime.fromisoformat(recu["date_utc"].replace("Z", "+00:00")).timestamp(),
                   "event": recu["event"], "cible": identifiant, "frais": recu["frais_id"],
                   "recu_id": "suppression_justificatif:" + identifiant,
                   "hash_sha256": recu["hash_sha256"], "taille_octets": recu["taille_octets"]}
        ligne = (json.dumps(attendu, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        if len(ligne) > MAX_LIGNE or len(ligne) > MAX_JOURNAL:
            raise RelaisRefuse("Reçu trop volumineux pour le relais")
        rapport["recu_id"] = attendu["recu_id"]
        if journal.is_symlink() or not journal.parent.is_dir() or journal.parent.is_symlink():
            raise RelaisRefuse("Journal symbolique ou répertoire parent absent/symbolique")
        # Ne pas risquer de mélanger le journal JSONL avec la base source.
        base = racine / "metier.sqlite3"
        if journal.exists() and os.path.samefile(journal, base):
            raise RelaisRefuse("Le journal ne peut pas être la base SQLite")
        if journal.exists() and not journal.is_file():
            raise RelaisRefuse("Journal non régulier")
        if not appliquer:
            if journal.exists():
                with journal.open("rb") as fichier:
                    rapport["etat"] = _inspecter(fichier, attendu)
            else:
                rapport["etat"] = "pret"
            return rapport
        try:
            import fcntl
        except ImportError as exc:
            raise RelaisRefuse("Relais avec verrou pris en charge uniquement sous POSIX") from exc
        # O_NOFOLLOW protège le dernier composant ; les parents doivent rester
        # stables. Aucun mkdir, aucune réécriture/troncature du fichier existant.
        fd = os.open(journal, os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "r+b") as fichier:
            fcntl.flock(fichier.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            etat = _inspecter(fichier, attendu)
            if etat == "deja_present":
                rapport["etat"] = etat
                return rapport
            tentative = True
            # O_APPEND s'applique aussi après la lecture. Pas de troncature en
            # cas d'erreur : une écriture partielle doit rester examinable.
            restant = memoryview(ligne)
            while restant:
                ecrits = os.write(fichier.fileno(), restant)
                if ecrits <= 0:
                    raise OSError("Écriture sans progression")
                restant = restant[ecrits:]
            os.fsync(fichier.fileno())
        rapport.update(etat="reporte", applique=True)
    except (RelaisRefuse, OSError, ValueError) as exc:
        rapport.update(etat="indetermine" if tentative else "refuse", applique=None if tentative else False,
                       detail=str(exc))
        if tentative:
            rapport["detail"] += " ; écriture possiblement effectuée, relire avant toute reprise"
    return rapport
