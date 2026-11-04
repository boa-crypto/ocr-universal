"""Ressources disponibles — garde-fou mémoire (E1).

**Pourquoi ce module existe.** Les moteurs OCR « lourds » (EasyOCR, PaddleOCR)
dépendent de torch/paddle. Leur simple *import* réussit sur une machine où ils
n'ont pas la place : `is_available()` renvoie alors `True`, le moteur est
activé, et le processus est tué par l'OOM killer au chargement du modèle. Sur
la machine de référence (2 Go de RAM, dont ~1,4 Go disponibles), c'est le
scénario certain.

**Ce que fait ce module.** Exposer les ressources réellement disponibles et un
garde-fou explicite : `can_load(required_mb)` répond non — **avec la raison** —
quand la mémoire libre ne permet pas de charger un moteur. Le registre de
moteurs s'en sert pour ne jamais activer un moteur qui ferait tomber le
service.

**Ce qu'il ne fait pas.** Il ne mesure pas la consommation réelle d'un moteur
non installé : les seuils sont des ordres de grandeur documentés, à ajuster
après mesure sur la machine cible. Aucun moteur lourd n'a pu être chargé ici
pour valider ces chiffres — c'est dit tel quel dans docs/LIMITATIONS.md.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

from .logging_setup import get_logger

log = get_logger("resources")

# ordres de grandeur de chargement (Mo), à valider sur machine cible
ENGINE_RAM_MB = {
    "tesseract": 120,        # binaire + tessdata
    "native": 20,            # texte déjà extrait
    "easyocr": 2200,         # torch + modèles (CPU)
    "paddleocr": 1800,       # paddle + modèles (CPU)
    "indra": 1500,           # onnx runtime + modèles
}
DEFAULT_ENGINE_RAM_MB = 800
# marge de sécurité : on refuse en dessous de ce pourcentage de libre
SAFETY_MARGIN = 0.25


def _meminfo() -> dict[str, int]:
    """Valeurs de /proc/meminfo en Mo (0 si indisponible)."""
    out: dict[str, int] = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2 and parts[0].endswith(":"):
                    out[parts[0][:-1]] = int(parts[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return out


def available_ram_mb() -> int:
    """RAM réellement disponible (MemAvailable), 0 si la sonde échoue."""
    info = _meminfo()
    if "MemAvailable" in info:
        return info["MemAvailable"]
    try:  # repli multi-plateforme
        import psutil
        return int(psutil.virtual_memory().available // (1024 * 1024))
    except Exception:
        return 0


def total_ram_mb() -> int:
    info = _meminfo()
    if "MemTotal" in info:
        return info["MemTotal"]
    try:
        import psutil
        return int(psutil.virtual_memory().total // (1024 * 1024))
    except Exception:
        return 0


def cpu_count() -> int:
    return os.cpu_count() or 1


def disk_free_mb(path: str = ".") -> int:
    try:
        return shutil.disk_usage(path).free // (1024 * 1024)
    except OSError:
        return 0


@dataclass
class ResourceVerdict:
    ok: bool
    reason: str = ""
    available_mb: int = 0
    required_mb: int = 0

    def as_dict(self) -> dict:
        return {"ok": self.ok, "reason": self.reason,
                "available_mb": self.available_mb, "required_mb": self.required_mb}


def can_load(engine_name: str) -> ResourceVerdict:
    """La machine peut-elle charger ce moteur ? Répond toujours, avec raison.

    Sonde indisponible (`available == 0`) : on **autorise** — mieux vaut
    tenter que bloquer une machine dont on ne sait pas mesurer la mémoire.
    """
    required = ENGINE_RAM_MB.get(engine_name, DEFAULT_ENGINE_RAM_MB)
    avail = available_ram_mb()
    if avail == 0:
        return ResourceVerdict(True, "mémoire non mesurable", 0, required)
    needed = int(required * (1 + SAFETY_MARGIN))
    if avail >= needed:
        return ResourceVerdict(True, "", avail, required)
    return ResourceVerdict(
        False,
        f"mémoire insuffisante pour « {engine_name} » : {avail} Mo disponibles, "
        f"{needed} Mo requis (dont marge de {int(SAFETY_MARGIN * 100)} %)",
        avail, required)


def engine_ram_requirement(engine_name: str) -> int:
    """Mémoire annoncée nécessaire pour un moteur (Mo)."""
    return ENGINE_RAM_MB.get(engine_name, DEFAULT_ENGINE_RAM_MB)


def snapshot() -> dict:
    """État des ressources, exposable par l'API (aucune donnée sensible)."""
    return {
        "ram_available_mb": available_ram_mb(),
        "ram_total_mb": total_ram_mb(),
        "cpu_count": cpu_count(),
        "disk_free_mb": disk_free_mb(),
        "engine_requirements_mb": dict(ENGINE_RAM_MB),
    }
