"""Configuration UniOCR — chargée depuis config/default.json, surchargeable par variables d'env."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULTS: dict[str, Any] = {
    "max_file_size_mb": 50,
    "max_batch_size_mb": 200,
    "max_pages": 500,
    "render_dpi": 200,
    "quality_mode": "accurate",
    "default_languages": ["fra", "eng"],
    "ocr": {
        "engine_order": ["native_pdf", "tesseract"],
        "tesseract_psm": 3,
        "min_word_confidence": 45.0,
    },
    "preprocess": {
        "enabled": True,
        "variant_comparison": True,
        "auto_binarize": True,
        "target_dpi": 200,
    },
    "extraction": {
        "profiles_dir": "profiles",
        "default_profile": "generic",
    },
    "security": {
        "max_zip_uncompressed_mb": 200,
        "max_zip_ratio": 100,
        "retention_days": 30,
        # chiffrement au repos (E3) — DÉSACTIVÉ par défaut.
        # "enabled": true + ("key_file": "keys/master.key"
        #                  ou "passphrase" + "salt" de 16 octets) pour activer.
        # Perdre la clé rend les données définitivement illisibles.
        "encryption": {"enabled": False},
    },
    "jobs": {"data_dir": "data", "workers": 2},
    "api": {"host": "127.0.0.1", "port": 8000},
    "log_dir": "logs",
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self, data: dict[str, Any], root: Path):
        self.data = data
        self.root = root

    # -- accès -----------------------------------------------------------
    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    # -- chemins ---------------------------------------------------------
    @property
    def data_dir(self) -> Path:
        # UNOCR_DATA_DIR permet de sortir les données de la racine du projet
        # (montage de volume Docker, disque dédié).
        env = os.environ.get("UNOCR_DATA_DIR")
        p = Path(env).resolve() if env else self.root / self.get("jobs.data_dir", "data")
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def log_dir(self) -> Path:
        env = os.environ.get("UNOCR_LOG_DIR")
        p = Path(env).resolve() if env else self.root / self.get("log_dir", "logs")
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def profiles_dir(self) -> Path:
        name = self.get("extraction.profiles_dir", "profiles")
        p = self.root / name
        if p.is_dir():
            return p
        # repli sur les profils livrés avec le projet (tests, configs racines)
        fallback = PROJECT_ROOT / name
        return fallback if fallback.is_dir() else p

    @property
    def user_profiles_dir(self) -> Path:
        """Profils créés par l'utilisateur (surcouche aux profils livrés).

        Séparés de `profiles/` pour qu'une mise à jour du projet n'écrase pas
        les profils métier ajoutés localement.
        """
        env = os.environ.get("UNOCR_USER_PROFILES_DIR")
        p = Path(env).resolve() if env else self.data_dir / "profiles"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def web_dir(self) -> Path:
        return self.root / "web"


def load_config(config_path: str | os.PathLike | None = None) -> Config:
    root = Path(os.environ.get("UNOCR_ROOT", PROJECT_ROOT)).resolve()
    path = Path(config_path) if config_path else root / "config" / "default.json"
    data = DEFAULTS
    if path.is_file():
        try:
            user_cfg = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(user_cfg, dict):
                data = _deep_merge(DEFAULTS, user_cfg)
        except (json.JSONDecodeError, OSError):
            pass  # config illisible → défauts, signalé par le journal
    return Config(data, root)


_CONFIG: Config | None = None


def get_config() -> Config:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = load_config()
    return _CONFIG


def set_config(cfg: Config) -> None:
    global _CONFIG
    _CONFIG = cfg
