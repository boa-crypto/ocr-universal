"""Journalisation structurée + journal d'audit (JSONL)."""
from __future__ import annotations

import json
import logging
import logging.handlers
import sys
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
