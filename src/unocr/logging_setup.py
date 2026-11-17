"""Journalisation structurée + journal d'audit (JSONL)."""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import stat
import sys
import threading
import time
from pathlib import Path
from typing import Any

_CONFIGURED = False


def setup_logging(log_dir: Path | None = None, level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    root = logging.getLogger("unocr")
    root.setLevel(level)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_dir / "unocr.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"unocr.{name}")


def audit(log_dir: Path, event: str, **fields: Any) -> None:
    """Écrit un événement d'audit (JSONL). Ne doit jamais contenir de secret."""
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        entry = {"ts": time.time(), "event": event, **fields}
        with (log_dir / "audit.log").open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except OSError:
        get_logger("audit").exception("impossible d'écrire le journal d'audit")


class AuditIndisponible(RuntimeError):
    """Écriture/synchronisation locale non acquise ; aucun succès ne doit être servi."""


_AUDIT_OBLIGATOIRE_LOCK = threading.Lock()


def audit_obligatoire(log_dir: Path, event: str, **fields: Any) -> None:
    """Append contrôlé pour les succès de revue, sans garantie WORM/exactly-once.

    Ne modifie pas le comportement best-effort du journal legacy. En cas d'échec,
    une entrée peut être absente, partielle ou déjà écrite ; jamais de réparation.
    """
    try:
        contenu = (json.dumps({"ts": time.time(), "event": event, **fields}, ensure_ascii=False,
                              allow_nan=False) + "\n").encode("utf-8")
        if len(contenu) > 16 * 1024:
            raise ValueError("Événement trop volumineux")
        with _AUDIT_OBLIGATOIRE_LOCK:
            if log_dir.is_symlink():
                raise OSError("Répertoire de journal symbolique")
            log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            chemin = log_dir / "audit.log"
            if chemin.is_symlink():
                raise OSError("Journal symbolique")
            flags = os.O_RDWR | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            fd = os.open(chemin, flags, 0o600)
            try:
                infos = os.fstat(fd)
                if not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1:
                    raise OSError("Journal régulier sans lien multiple requis")
                if infos.st_size:
                    os.lseek(fd, -1, os.SEEK_END)
                    if os.read(fd, 1) != b"\n":
                        raise OSError("Fin de journal interrompue, investigation manuelle requise")
                if os.write(fd, contenu) != len(contenu):
                    raise OSError("Écriture d'audit partielle")
                os.fsync(fd)
            finally:
                os.close(fd)
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        raise AuditIndisponible("Journal de revue indisponible") from exc
