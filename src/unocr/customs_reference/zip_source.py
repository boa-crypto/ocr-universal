"""Sélection explicite d'un membre ZIP, sans extraction ou récursion générique."""
import hashlib
import io
import stat
import unicodedata
import zipfile
import zlib

MAX_ARCHIVE = 64 * 1024 * 1024
MAX_MEMBRES = 256
MAX_MEMBRE = 64 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_RATIO = 200
FORMATS = {"csv", "json", "xlsx", "xls", "xml"}


class ZIPRefuse(ValueError):
    """Archive ambiguë, dangereuse ou hors périmètre."""


def _nom(nom, dossier=False):
    if (not isinstance(nom, str) or not nom or len(nom) > 256
            or any(unicodedata.category(c).startswith("C") for c in nom)
            or "\\" in nom or ":" in nom or nom.startswith("/")):
        raise ZIPRefuse("Nom de membre ZIP non sûr")
    parties = nom[:-1].split("/") if dossier and nom.endswith("/") else nom.split("/")
    if any(p in {"", ".", ".."} for p in parties):
        raise ZIPRefuse("Chemin de membre ZIP non sûr")


def lire_zip(original: bytes, configuration: dict) -> tuple[bytes, dict]:
    membre, format_contenu = configuration.get("membre_zip"), configuration.get("format_contenu")
    _nom(membre)
    if not isinstance(format_contenu, str) or format_contenu not in FORMATS:
        raise ZIPRefuse("Format du membre requis : csv, json, xlsx, xls ou xml")
    if type(original) is not bytes or not 0 < len(original) <= MAX_ARCHIVE:
        raise ZIPRefuse("Archive ZIP vide ou dépassant 64 Mio")
    # Pas d'auto-détection d'un exécutable auto-extractible ou d'un autre format.
    if not original.startswith(b"PK\x03\x04"):
        raise ZIPRefuse("ZIP ordinaire avec membre attendu")
    try:
        with zipfile.ZipFile(io.BytesIO(original)) as archive:
            membres = archive.infolist()
            if not 1 <= len(membres) <= MAX_MEMBRES:
                raise ZIPRefuse("Nombre de membres ZIP hors borne")
            if min(i.header_offset for i in membres) != 0 or len({i.header_offset for i in membres}) != len(membres):
                raise ZIPRefuse("Préambule ou offsets ZIP ambigus")
            noms, total, selection = set(), 0, None
            for info in membres:
                _nom(info.filename, dossier=info.is_dir())
                if info.orig_filename != info.filename:
                    raise ZIPRefuse("Nom ZIP tronqué ou ambigu")
                canonique = info.filename.rstrip("/")
                if canonique in noms:
                    raise ZIPRefuse("Nom de membre ZIP dupliqué")
                noms.add(canonique)
                mode = info.external_attr >> 16
                if stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}:
                    raise ZIPRefuse("Lien ou membre ZIP spécial refusé")
                if ((stat.S_IFMT(mode) == stat.S_IFDIR or info.external_attr & 0x10) and not info.is_dir()
                        or info.is_dir() and (stat.S_IFMT(mode) == stat.S_IFREG or info.file_size != 0)):
                    raise ZIPRefuse("Type de membre ZIP ambigu")
                if (info.flag_bits & 1 or info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}):
                    raise ZIPRefuse("ZIP chiffré ou compression non prise en charge")
                total += info.file_size
                if (info.file_size > MAX_MEMBRE or total > MAX_TOTAL
                        or info.file_size > max(1, info.compress_size) * MAX_RATIO):
                    raise ZIPRefuse("Bornes de décompression ZIP dépassées")
                if info.filename == membre and not info.is_dir():
                    selection = info
            if selection is None:
                raise ZIPRefuse("Membre ZIP exact absent")
            with archive.open(selection) as fichier:
                contenu = fichier.read(MAX_MEMBRE + 1)
            if not contenu or len(contenu) > MAX_MEMBRE or len(contenu) != selection.file_size:
                raise ZIPRefuse("Contenu ZIP vide ou taille incohérente")
            return contenu, {"format_contenu": format_contenu, "membre_zip": membre,
                             "octets_membre_lus": len(contenu), "sha256_membre_lu": hashlib.sha256(contenu).hexdigest(),
                             "membres_declares": len(membres),
                             "membres_non_importes": sorted(i.filename for i in membres if i.filename != membre),
                             "controle_autres_membres": "metadonnees_zip_seulement_pas_crc_ni_contenu"}
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError, ValueError, OSError, zlib.error) as exc:
        if isinstance(exc, ZIPRefuse):
            raise
        raise ZIPRefuse("Archive ZIP illisible ou membre corrompu") from None
