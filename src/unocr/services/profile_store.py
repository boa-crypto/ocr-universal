"""Accès sécurisé aux profils utilisateur."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from ..security import sanitize_filename

MAX_PATTERN_LEN = 500
MAX_FIELDS = 60


def user_profile_path(cfg: Any, name: str) -> Path:
    """Construit un chemin de profil sans permettre de traversal."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", (name or "").strip())[:60]
    if not cleaned or cleaned in (".", ".."):
        raise HTTPException(400, "nom de profil invalide")
    safe = sanitize_filename(cleaned)
    return cfg.user_profiles_dir / f"{safe}.json"
