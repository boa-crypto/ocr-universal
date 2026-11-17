"""Configuration UniOCR — chargée depuis config/default.json, surchargeable par variables d'env."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .logging_setup import get_logger

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
    def __init__(self, data: dict[str, Any], root: Path,
                 surcharges: dict[str, Any] | None = None):
        self.data = data
        self.root = root
        #: valeurs écrites depuis l'interface (data/parametres.json)
        self.surcharges: dict[str, Any] = dict(surcharges or {})
        #: valeurs de référence (fichier de config + défauts), pour pouvoir
        #: revenir en arrière sans redémarrer le serveur.
        self._defauts: dict[str, Any] = json.loads(json.dumps(data))

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

    @property
    def parametres_path(self) -> Path:
        """Fichier des paramètres modifiés depuis l'interface.

        Séparé de ``config/default.json`` : une mise à jour du projet ne doit
        pas effacer les réglages d'exploitation, et un réglage d'exploitation
        ne doit pas réécrire les défauts livrés.
        """
        return self.data_dir / PARAMETRES_FILE

    # -- écriture des paramètres ----------------------------------------
    def valeur_par_defaut(self, cle: str) -> Any:
        node: Any = self._defauts
        for part in cle.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    def definir(self, cle: str, valeur: Any) -> None:
        """Applique et persiste une valeur ; l'effet est immédiat."""
        parts = cle.split(".")
        node = self.data
        for part in parts[:-1]:
            if not isinstance(node.get(part), dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = valeur
        self.surcharges[cle] = valeur
        self._ecrire_surcharges()

    def reinitialiser(self, cle: str) -> bool:
        """Retire la surcharge et revient à la valeur de référence."""
        if cle not in self.surcharges:
            return False
        self.surcharges.pop(cle, None)
        parts = cle.split(".")
        node = self.data
        for part in parts[:-1]:
            if not isinstance(node, dict) or part not in node:
                node = {}
                break
            node = node[part]
        if isinstance(node, dict):
            defaut = self.valeur_par_defaut(cle)
            if defaut is None:
                node.pop(parts[-1], None)
            else:
                node[parts[-1]] = defaut
        self._ecrire_surcharges()
        return True

    def _ecrire_surcharges(self) -> None:
        try:
            path = self.parametres_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(dict(sorted(self.surcharges.items())),
                                       ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        except OSError:
            get_logger("config").exception("impossible d'écrire les paramètres")


PARAMETRES_FILE = "parametres.json"


def donnees_dir(root: Path) -> Path:
    """Répertoire de données effectif (respecte UNOCR_DATA_DIR)."""
    env = os.environ.get("UNOCR_DATA_DIR")
    return Path(env).resolve() if env else root / "data"


def _lire_surcharges(root: Path) -> dict[str, Any]:
    path = donnees_dir(root) / PARAMETRES_FILE
    if not path.is_file():
        return {}
    try:
        contenu = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        get_logger("config").warning("paramètres illisibles : %s", path)
        return {}
    if not isinstance(contenu, dict):
        return {}
    return {str(k): v for k, v in contenu.items()}


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
    surcharges = _lire_surcharges(root)
    for cle, valeur in surcharges.items():
        parts = cle.split(".")
        node = data
        for part in parts[:-1]:
            if not isinstance(node.get(part), dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = valeur
    return Config(data, root, surcharges)


_CONFIG: Config | None = None


def get_config() -> Config:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = load_config()
    return _CONFIG


def set_config(cfg: Config) -> None:
    global _CONFIG
    _CONFIG = cfg
