"""Sécurité : validation des fichiers, protections zip-bomb, anti-injection.

Le texte extrait est considéré comme non fiable : jamais exécuté, jamais passé à un
shell, toujours échappé dans les sorties XML/CSV.
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .logging_setup import get_logger

log = get_logger("security")

MAX_FILENAME_LEN = 200

ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp",
    ".docx", ".odt", ".txt", ".rtf", ".csv", ".xlsx", ".xls",
}

# Signatures magiques (préfixe octets -> formats acceptés)
_MAGIC: list[tuple[bytes, set[str]]] = [
    (b"%PDF-", {".pdf"}),
    (b"\x89PNG\r\n\x1a\n", {".png"}),
    (b"\xff\xd8\xff", {".jpg", ".jpeg"}),
    (b"II*\x00", {".tif", ".tiff"}),
    (b"MM\x00*", {".tif", ".tiff"}),
    (b"BM", {".bmp"}),
    (b"PK\x03\x04", {".docx", ".odt", ".xlsx"}),   # conteneurs zip
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", {".xls"}),  # OLE2
    (b"{\\rtf", {".rtf"}),
]

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class SecurityError(Exception):
    """Fichier refusé pour raison de sécurité ou de format."""


@dataclass
class FileInfo:
    path: Path
    extension: str
    size_bytes: int
    magic_ok: bool


def sanitize_filename(name: str) -> str:
    name = Path(name).name  # supprime toute traversée de répertoire
    name = re.sub(r"[^\w.\- ]", "_", name, flags=re.UNICODE)
    name = name.strip(" .") or "document"
    return name[:MAX_FILENAME_LEN]


def _check_zip_safety(path: Path, max_uncompressed_mb: int, max_ratio: int) -> None:
    """Garde zip-bomb : taille totale décompressée et ratio de compression."""
    try:
        with zipfile.ZipFile(path) as zf:
            total_uncompressed = 0
            total_compressed = 0
            for info in zf.infolist():
                if info.is_dir():
                    continue
                total_uncompressed += info.file_size
                total_compressed += max(info.compress_size, 1)
                if info.file_size > max_uncompressed_mb * 1024 * 1024:
                    raise SecurityError(
                        f"membre zip trop volumineux à la décompression: {info.filename}"
                    )
            if total_uncompressed > max_uncompressed_mb * 1024 * 1024:
                raise SecurityError("archive zip trop volumineuse à la décompression")
            if total_compressed and total_uncompressed / total_compressed > max_ratio:
                raise SecurityError("ratio de compression zip suspect (zip bomb ?)")
    except zipfile.BadZipFile as exc:
        raise SecurityError(f"archive zip invalide: {exc}") from exc


def validate_file(
    path: Path | str,
    max_size_mb: int = 50,
    max_zip_uncompressed_mb: int = 200,
    max_zip_ratio: int = 100,
) -> FileInfo:
    """Valide existence, taille, extension et signature magique. Lève SecurityError."""
    p = Path(path)
    if not p.is_file():
        raise SecurityError(f"fichier introuvable: {p.name}")
    size = p.stat().st_size
    if size == 0:
        raise SecurityError("fichier vide")
    if size > max_size_mb * 1024 * 1024:
        raise SecurityError(f"fichier trop volumineux (> {max_size_mb} Mo)")
    ext = p.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise SecurityError(f"extension non autorisée: {ext or '(aucune)'}")

    with p.open("rb") as fh:
        header = fh.read(16)
    magic_ok = False
    for magic, exts in _MAGIC:
        if header.startswith(magic) and ext in exts:
            magic_ok = True
            break
    if not magic_ok:
        # formats texte (txt/csv) : pas de signature, contrôle heuristique
        if ext in {".txt", ".csv"}:
            with p.open("rb") as fh:
                sample = fh.read(4096)
            if b"\x00" in sample:
                raise SecurityError("contenu binaire inattendu pour un fichier texte")
            magic_ok = True
        else:
            raise SecurityError(
                f"signature de fichier incohérente avec l'extension {ext}"
            )

    if ext in {".docx", ".odt", ".xlsx"}:
        _check_zip_safety(p, max_zip_uncompressed_mb, max_zip_ratio)

    return FileInfo(path=p, extension=ext, size_bytes=size, magic_ok=True)


# ------------------------------------------------------- anti-injection sorties
def sanitize_for_csv(value: object) -> str:
    """Neutralise les formules (CSV injection) sans altérer la donnée métier."""
    s = "" if value is None else str(value)
    if s.startswith(FORMULA_PREFIXES):
        return "'" + s
    return s


def sanitize_text(text: str) -> str:
    """Supprime les caractères de contrôle dangereux (le reste est conservé à l'identique)."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


PROMPT_INJECTION_RE = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior)\s+instructions|"
    r"disregard\s+(all\s+)?(previous|prior)|"
    r"you\s+are\s+now\s+(a|an)\s+|"
    r"system\s*prompt|"
    r"exécute\s+la\s+commande|"
    r"ignorez\s+(toutes\s+)?les\s+instructions|"
    r"ouvre\s+l['’]url|"
    r"télécharge|"
    r"exécute\s+le\s+script)",
    re.IGNORECASE,
)


def flag_untrusted_content(text: str) -> list[str]:
    """Détecte des instructions potentiellement injectées dans le document.

    Ces instructions ne sont JAMAIS exécutées : elles sont seulement signalées.
    """
    hits = []
    for m in PROMPT_INJECTION_RE.finditer(text or ""):
        hits.append(m.group(0)[:80])
    return hits
