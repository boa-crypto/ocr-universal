"""Sauvegarde et restauration du magasin UniOCR.

Pourquoi ce module existe : le magasin (`data/jobs`, `data/dossiers`,
`data/exports`, `data/connectors`, `data/formulaires`, `logs/audit.log`) est la
seule trace des documents traités, des corrections humaines et des
transmissions. Rien ne le protégeait d'une suppression accidentelle, d'un
disque plein ou d'une purge trop large. La commande `unocr clean` peut vider
des jours de travail en une seconde.

Contraintes tenues ici :

- une sauvegarde n'écrase jamais la précédente (horodatage dans le nom) ;
- la restauration **refuse** d'écraser un magasin non vide sans `--force` :
  restaurer par-dessus ferait disparaître des documents plus récents ;
- l'intégrité est vérifiée après écriture (manifeste + empreinte) ;
- le journal d'audit est inclus ; restaurer vers des journaux neufs pour ne
  pas remplacer un journal actif (comportement legacy hors quarantaine) ;
- la quarantaine exige une option CLI explicite et ne fusionne jamais avec
  une quarantaine cible existante, même avec force.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterable

from .business_store import BusinessStore
from .logging_setup import audit, get_logger
from .models import Justificatif

log = get_logger("backup")

#: répertoires du magasin à sauvegarder, dans l'ordre de criticité
REPERTOIRES = ("jobs", "dossiers", "exports", "connectors", "formulaires",
               "profiles", "keys", "justificatifs", "customs-quarantine")

#: fichiers isolés à conserver (l'audit est irremplaçable)
#: `rbac.json` figure ici pour une raison de sécurité : sans lui, une
#: restauration rendrait le registre inactif, donc l'API ouverte à tous — et
#: l'opérateur croirait ses rôles toujours en place. Un cloisonnement perdu en
#: silence est pire qu'un cloisonnement jamais mis en place.
FICHIERS = ("audit.log", "calibration.json", "rbac.json", "metier.sqlite3")

MANIFESTE = "manifeste.json"
#: préfixes d'archive : le magasin et les journaux ne sont pas au
#: même endroit sur le disque, l'archive doit le savoir pour restaurer.
PREF_DATA = Path("data")
PREF_LOGS = Path("logs")


class BackupError(Exception):
    """Sauvegarde ou restauration refusée."""


@dataclass
class ResultatSauvegarde:
    chemin: Path
    taille: int = 0
    fichiers: int = 0
    octets: int = 0
    empreinte: str = ""
    erreurs: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "chemin": str(self.chemin),
            "taille": self.taille,
            "fichiers": self.fichiers,
            "octets": self.octets,
            "empreinte": self.empreinte,
            "erreurs": list(self.erreurs),
        }


def _empreinte(path: Path) -> str:
    """SHA-256 d'un fichier, lu par blocs (les exports peuvent être gros)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloc in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def _fichiers_utiles(racine: Path) -> Iterable[tuple[Path, Path]]:
    """(source, nom-dans-l-archive) pour chaque fichier à archiver.

    Ignore les répertoires temporaires et les fichiers de verrou : les
    inclurait des états transitoires sans valeur de reprise.
    """
    for nom in REPERTOIRES:
        base = racine / nom
        if nom in {"justificatifs", "customs-quarantine"} and base.is_symlink():
            raise BackupError(f"répertoire {nom} symbolique refusé")
        if not base.is_dir():
            continue
        for src in sorted(base.rglob("*")):
            if nom in {"justificatifs", "customs-quarantine"} and src.is_symlink():
                raise BackupError(f"lien symbolique de {nom} refusé")
            if nom == "customs-quarantine" and not src.is_dir() and not src.is_file():
                raise BackupError("fichier spécial de quarantaine refusé")
            if not src.is_file():
                continue
            if nom != "customs-quarantine" and (src.name.startswith(".") or src.suffix == ".tmp"):
                continue
            yield src, PREF_DATA / src.relative_to(racine)
    for nom in FICHIERS:
        src = racine / nom
        if src.is_file():
            yield src, PREF_DATA / nom


def _fichiers_journal(cfg) -> Iterable[tuple[Path, Path]]:
    """Le journal d'audit ne vit pas dans le magasin, il est pourtant
    irremplaçable : c'est la seule trace des transmissions et des
    consultations. Une sauvegarde qui l'omettrait perdrait l'historique.
    """
    journal = cfg.log_dir / "audit.log"
    if journal.is_file():
        yield journal, PREF_LOGS / journal.name


def creer_sauvegarde(cfg, destination: Path | None = None,
                     etiquette: str = "", inclure_quarantaine: bool = False) -> ResultatSauvegarde:
    """Archive le magasin dans un ZIP horodaté, manifeste inclus.

    Le nom porte l'horodatage : deux sauvegardes dans la même minute ne
    s'écrasent pas, et l'ordre de reprise reste lisible.
    """
    racine = cfg.data_dir
    quarantaine = racine / "customs-quarantine"
    if type(inclure_quarantaine) is not bool:
        raise BackupError("Option de quarantaine booléenne requise")
    if (quarantaine.exists() or quarantaine.is_symlink()) and not inclure_quarantaine:
        raise BackupError("Quarantaine présente : sauvegarde CLI explicite avec --include-customs-quarantine requise")
    if inclure_quarantaine and quarantaine.exists() and not quarantaine.is_dir():
        raise BackupError("Racine de quarantaine non répertoire")
    if not racine.is_dir():
        raise BackupError(f"magasin introuvable : {racine}")

    cible_dir = destination or (racine.parent / ("sauvegardes-quarantaine" if inclure_quarantaine else "sauvegardes"))
    cible_dir.mkdir(mode=0o700 if inclure_quarantaine else 0o777, parents=True, exist_ok=True)
    horodatage = time.strftime("%Y%m%d-%H%M%S")
    suffixe = f"-{etiquette}" if etiquette else ""
    chemin = cible_dir / f"sauvegarde-{horodatage}{suffixe}.zip"

    fichiers: list[dict] = []
    # Même verrou que les téléversements/suppressions : les blobs ne peuvent
    # changer entre leur copie et l'instantané SQLite des métadonnées.
    magasin = BusinessStore(racine / "metier.sqlite3", "justificatif", Justificatif)
    # Réservation exclusive : deux sauvegardes dans la même seconde ne doivent
    # pas écraser l'archive précédente (y compris entre deux processus).
    indice = 0
    while True:
        try:
            archive = zipfile.ZipFile(chemin, "x", zipfile.ZIP_DEFLATED)
            break
        except FileExistsError:
            indice += 1
            chemin = cible_dir / f"sauvegarde-{horodatage}{suffixe}-{indice:04d}.zip"
    with archive as zf, magasin.transaction():
        if inclure_quarantaine:
            try:
                chemin.chmod(0o600)
            except OSError as exc:
                raise BackupError("Impossible de restreindre les permissions de la sauvegarde") from exc
        for src, rel in list(_fichiers_utiles(racine)) + list(
                _fichiers_journal(cfg)):
            nom_archive = rel.as_posix()
            dossier_db = Path("data/customs-quarantine/dossiers_metier.sqlite3")
            if rel in {Path(str(dossier_db)+suffixe) for suffixe in ("-wal","-shm","-journal")}:
                # Ces fichiers ne doivent pas rejouer un WAL antérieur sur l'instantané.
                if not (racine / "customs-quarantine/dossiers_metier.sqlite3").is_file():
                    raise BackupError("Journal de dossiers métier sans base principale")
                continue
            if src.name == "metier.sqlite3" or rel == dossier_db:
                # L'API backup de SQLite fournit un instantané cohérent même
                # lorsqu'une requête écrit dans la base pendant l'archivage.
                with tempfile.TemporaryDirectory() as temporaire:
                    copie = Path(temporaire) / "metier.sqlite3"
                    origine = sqlite3.connect(src.resolve().as_uri() + "?mode=ro", uri=True)
                    destination_db = sqlite3.connect(copie)
                    try:
                        origine.backup(destination_db)
                        if destination_db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                            raise BackupError("Instantané SQLite incohérent")
                    finally:
                        destination_db.close()
                        origine.close()
                    zf.write(copie, nom_archive)
                    fichiers.append({"nom": nom_archive, "octets": copie.stat().st_size,
                                     "empreinte": _empreinte(copie)})
            else:
                zf.write(src, nom_archive)
                fichiers.append({"nom": nom_archive, "octets": src.stat().st_size,
                                 "empreinte": _empreinte(src)})
        manifeste = {
            "version": 1,
            "cree_le": time.strftime("%Y-%m-%d %H:%M:%S"),
            "etiquette": etiquette,
            "racine": str(racine),
            "fichiers": fichiers,
        }
        zf.writestr(MANIFESTE, json.dumps(manifeste, ensure_ascii=False,
                                          indent=1))

    verifier_sauvegarde(chemin)
    res = ResultatSauvegarde(
        chemin=chemin, taille=chemin.stat().st_size,
        fichiers=len(fichiers), octets=sum(f["octets"] for f in fichiers),
        empreinte=_empreinte(chemin))
    audit(cfg.log_dir, "sauvegarde_creee", chemin=str(chemin),
          fichiers=res.fichiers, octets=res.octets, etiquette=etiquette)
    log.info("sauvegarde créée : %s (%d fichiers, %d octets)",
             chemin.name, res.fichiers, res.octets)
    return res


def verifier_sauvegarde(chemin: Path) -> dict:
    """Relit l'archive et contrôle chaque empreinte du manifeste.

    Une sauvegarde dont on ne vérifie pas le contenu n'est pas une sauvegarde :
    c'est un fichier qu'on espère bon.
    """
    if not chemin.is_file():
        raise BackupError(f"sauvegarde introuvable : {chemin}")
    try:
        with zipfile.ZipFile(chemin) as zf:
            noms = zf.namelist()
            if any(info.filename.startswith("data/customs-quarantine/")
                   and stat.S_ISLNK(info.external_attr >> 16) for info in zf.infolist()):
                raise BackupError("lien symbolique ZIP de quarantaine refusé")
            if MANIFESTE not in noms:
                raise BackupError(f"{chemin.name} : sans manifeste, "
                                  "intégrité invérifiable")
            if len(noms) != len(set(noms)):
                raise BackupError(f"{chemin.name} : membre ZIP dupliqué")
            manifeste = json.loads(zf.read(MANIFESTE).decode("utf-8"))
            entrees = manifeste.get("fichiers") if isinstance(manifeste, dict) else None
            if not isinstance(entrees, list):
                raise BackupError(f"{chemin.name} : manifeste invalide")
            declares: set[str] = set()
            manquants, alteres = [], []
            for entree in entrees:
                if not isinstance(entree, dict):
                    raise BackupError(f"{chemin.name} : entrée de manifeste invalide")
                nom = entree.get("nom")
                if not isinstance(nom, str) or "\\" in nom:
                    raise BackupError(f"{chemin.name} : chemin d'archive invalide")
                relatif = PurePosixPath(nom)
                if (relatif.is_absolute() or relatif.as_posix() != nom
                        or len(relatif.parts) < 2
                        or relatif.parts[0] not in {"data", "logs"}
                        or any(part in {".", ".."} for part in relatif.parts)):
                    raise BackupError(f"{chemin.name} : chemin d'archive invalide : {nom}")
                if nom in declares:
                    raise BackupError(f"{chemin.name} : membre déclaré plusieurs fois : {nom}")
                declares.add(nom)
                if nom not in noms:
                    manquants.append(nom)
                    continue
                contenu = zf.read(nom)
                if (len(contenu) != entree.get("octets")
                        or hashlib.sha256(contenu).hexdigest() != entree.get("empreinte")):
                    alteres.append(nom)
            presents = {nom for nom in noms if nom != MANIFESTE and not nom.endswith("/")}
            non_declares = sorted(presents - declares)
            if non_declares:
                raise BackupError(f"{chemin.name} : membre(s) absent(s) du manifeste")
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupError(f"{chemin.name} : archive ou manifeste invalide") from exc
    retour = {"chemin": str(chemin), "fichiers": len(manifeste.get("fichiers", [])),
              "manquants": manquants, "alteres": alteres,
              "valide": not manquants and not alteres,
              "quarantaine_presente": any(nom == "data/customs-quarantine" or nom.startswith("data/customs-quarantine/") for nom in noms)}
    if not retour["valide"]:
        raise BackupError(f"{chemin.name} : {len(manquants)} manquant(s), "
                          f"{len(alteres)} altéré(s)")
    return retour


def lister_sauvegardes(repertoire: Path) -> list[dict]:
    """Sauvegardes disponibles, de la plus récente à la plus ancienne."""
    if not repertoire.is_dir():
        return []
    sortie = []
    for p in sorted(repertoire.glob("sauvegarde-*.zip"), reverse=True):
        try:
            taille = p.stat().st_size
        except OSError:
            continue
        sortie.append({"nom": p.name, "chemin": str(p), "taille": taille})
    return sortie


def restaurer_sauvegarde(cfg, chemin: Path, force: bool = False,
                         inclure_quarantaine: bool = False) -> dict:
    """Restaure le magasin depuis une archive vérifiée.

    `force` est exigé si le magasin contient déjà des données : restaurer
    par-dessus ferait disparaître des documents plus récents que la
    sauvegarde, et l'opérateur ne s'en rendrait pas compte.
    """
    controle = verifier_sauvegarde(chemin)
    if type(inclure_quarantaine) is not bool:
        raise BackupError("Option de quarantaine booléenne requise")
    if controle["quarantaine_presente"] and not inclure_quarantaine:
        raise BackupError("Reprise de quarantaine : CLI explicite --include-customs-quarantine requis")
    racine = cfg.data_dir
    quarantaine = racine / "customs-quarantine"
    if quarantaine.exists() or quarantaine.is_symlink():
        raise BackupError("Quarantaine cible déjà présente : reprise dans un magasin neuf requise, même avec force")
    existants = [p for p in racine.iterdir() if p.is_dir() or p.name == "metier.sqlite3"] if racine.is_dir() else []
    if existants and not force:
        raise BackupError(
            "magasin non vide (%d répertoires) : confirmer avec force=True, "
            "sinon des documents plus récents que la sauvegarde seraient "
            "perdus" % len(existants))

    racine.mkdir(parents=True, exist_ok=True)
    # chaque préfixe de l'archive a sa destination réelle : data/ -> magasin,
    # logs/ -> répertoire des journaux. Extraire tout sous data/ mettrait
    # l'audit au mauvais endroit et il ne serait plus jamais relu.
    destinations = {"data": racine.resolve(), "logs": cfg.log_dir.resolve()}
    bornes = dict(destinations)
    restaures = 0
    with zipfile.ZipFile(chemin) as zf:
        for membre in zf.namelist():
            if membre == MANIFESTE or membre.endswith("/"):
                continue
            prefixe = membre.split("/", 1)[0]
            base = destinations.get(prefixe)
            if base is None:
                raise BackupError(f"préfixe inconnu dans l'archive : {membre}")
            # garde anti-traversée : un nom hostile ne sort jamais de sa base
            relatif = PurePosixPath(membre)
            if (relatif.is_absolute() or "\\" in membre
                    or any(part in {".", ".."} for part in relatif.parts)):
                raise BackupError(f"chemin hors magasin refusé : {membre}")
            cible = base.joinpath(*relatif.parts[1:]).resolve()
            try:
                cible.relative_to(bornes[prefixe])
            except ValueError:
                raise BackupError(f"chemin hors magasin refusé : {membre}")
            if prefixe == "data" and relatif.parts[1] == "customs-quarantine":
                # La quarantaine n'existait pas au précontrôle : fichiers neufs
                # exclusivement, pas de fusion même si un écrivain intervient.
                (racine / "customs-quarantine").mkdir(mode=0o700, exist_ok=True)
                cible.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with cible.open("xb") as fichier:
                    fichier.write(zf.read(membre))
            else:
                cible.parent.mkdir(parents=True, exist_ok=True)
                cible.write_bytes(zf.read(membre))
            restaures += 1
    audit(cfg.log_dir, "sauvegarde_restauree", chemin=str(chemin),
          fichiers=restaures, force=bool(force))
    log.info("sauvegarde restaurée : %s (%d fichiers)", chemin.name, restaures)
    return {"chemin": str(chemin), "fichiers": restaures, "force": bool(force)}


def purger_sauvegardes(repertoire: Path, conserver: int = 5) -> list[str]:
    """Ne garde que les `conserver` sauvegardes les plus récentes.

    Une sauvegarde qu'on ne purge jamais remplit le disque, ce qui finit par
    faire échouer la sauvegarde suivante. La purge est journalisée.
    """
    if conserver < 1:
        raise BackupError("conserver doit valoir au moins 1")
    toutes = lister_sauvegardes(repertoire)   # déjà triées, plus récente d'abord
    supprimees = []
    for entree in toutes[conserver:]:
        try:
            Path(entree["chemin"]).unlink()
            supprimees.append(entree["nom"])
        except OSError as exc:
            log.error("purge impossible (%s) : %s", entree["nom"], exc)
    return supprimees
