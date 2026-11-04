"""Tests E1 : garde-fou mémoire pour les moteurs OCR lourds.

Le point clé : un moteur dont la bibliothèque est installée mais qui dépasse
la RAM disponible doit être **refusé avec une raison**, pas activé puis tué
par l'OOM killer. La bibliothèque n'étant pas installée ici, on simule sa
présence (et l'absence de mémoire) pour prouver le garde-fou.
"""
import sys
from pathlib import Path

import pytest

from unocr.ocr_engines import EasyOCREngine, EngineRegistry, PaddleOCREngine
from unocr.resources import (
    ENGINE_RAM_MB,
    can_load,
    engine_ram_requirement,
    snapshot,
)

SRC = Path(__file__).resolve().parent.parent / "src"


@pytest.fixture()
def fake_installed(monkeypatch):
    """Simule easyocr+paddleocr installés, sans les importer réellement."""
    import types

    for mod in ("easyocr", "paddleocr"):
        monkeypatch.setitem(sys.modules, mod, types.ModuleType(mod))


# ─────────────────────────── décision mémoire ───────────────────────────

def test_can_load_ok_when_plenty_of_ram(monkeypatch):
    monkeypatch.setattr("unocr.resources.available_ram_mb", lambda: 8000)
    v = can_load("tesseract")
    assert v.ok is True and v.reason == ""


def test_can_load_refuses_heavy_engine(monkeypatch):
    """1,4 Go libre < 2,2 Go requis (+ marge) → refus motivé."""
    monkeypatch.setattr("unocr.resources.available_ram_mb", lambda: 1400)
    v = can_load("easyocr")
    assert v.ok is False
    assert "insuffisante" in v.reason
    assert v.available_mb == 1400 and v.required_mb == ENGINE_RAM_MB["easyocr"]


def test_can_load_includes_safety_margin(monkeypatch):
    """La marge de sécurité est bien appliquée au seuil."""
    monkeypatch.setattr("unocr.resources.available_ram_mb", lambda: 2000)
    # 2000 < 2200 * 1.25 = 2750
    assert can_load("easyocr").ok is False
    monkeypatch.setattr("unocr.resources.available_ram_mb", lambda: 2800)
    assert can_load("easyocr").ok is True


def test_unmeasurable_ram_allows_attempt(monkeypatch):
    """Sonde indisponible : on tente plutôt que de bloquer à l'aveugle."""
    monkeypatch.setattr("unocr.resources.available_ram_mb", lambda: 0)
    v = can_load("easyocr")
    assert v.ok is True and "non mesurable" in v.reason


def test_unknown_engine_uses_default(monkeypatch):
    monkeypatch.setattr("unocr.resources.available_ram_mb", lambda: 10000)
    assert engine_ram_requirement("moteur_inconnu") == 800
    assert can_load("moteur_inconnu").ok is True


# ─────────────────────────── garde-fou dans le registre ───────────────────────────

def test_heavy_engine_refused_when_low_ram(monkeypatch, fake_installed):
    """C'est le test central : bibliothèque présente, mémoire absente → refus."""
    monkeypatch.setattr("unocr.resources.available_ram_mb", lambda: 1400)

    eng = EasyOCREngine()
    assert eng.is_available() is False
    assert "insuffisante" in eng.unavailable_reason
    assert "easyocr" in eng.unavailable_reason

    pad = PaddleOCREngine()
    assert pad.is_available() is False
    assert "insuffisante" in pad.unavailable_reason


def test_heavy_engine_allowed_when_enough_ram(monkeypatch, fake_installed):
    """Avec assez de mémoire, le moteur est bien déclaré disponible."""
    monkeypatch.setattr("unocr.resources.available_ram_mb", lambda: 8000)
    assert EasyOCREngine().is_available() is True
    assert EasyOCREngine().unavailable_reason == ""


def test_not_installed_reports_installation_hint(monkeypatch):
    """Sans la bibliothèque, la raison dit quoi installer."""
    monkeypatch.setitem(sys.modules, "easyocr", None)   # import échoue
    eng = EasyOCREngine()
    assert eng.is_available() is False
    assert "non installé" in eng.unavailable_reason
    assert "pip install" in eng.unavailable_reason


def test_registry_never_activates_unloadable_engine(monkeypatch, fake_installed):
    """Aucun moteur impossible à charger n'apparaît comme actif."""
    monkeypatch.setattr("unocr.resources.available_ram_mb", lambda: 1400)
    engines = {e["name"]: e for e in EngineRegistry().list_engines()}
    assert engines["easyocr"]["available"] is False
    assert engines["easyocr"]["active"] is False
    assert "unavailable_reason" in engines["easyocr"]
    assert engines["tesseract"]["available"] is True


def test_registry_reports_ram_requirement():
    rows = {e["name"]: e for e in EngineRegistry().list_engines()}
    assert rows["easyocr"]["ram_required_mb"] == ENGINE_RAM_MB["easyocr"]
    assert rows["tesseract"]["ram_required_mb"] == ENGINE_RAM_MB["tesseract"]


def test_light_engines_always_available():
    """Tesseract et le texte natif ne sont jamais bloqués par ce garde-fou."""
    rows = {e["name"]: e for e in EngineRegistry().list_engines()}
    assert rows["tesseract"]["available"] is True
    assert rows["native_pdf"]["available"] is True


# ─────────────────────────── instantané ───────────────────────────

def test_snapshot_is_informative_and_safe():
    snap = snapshot()
    assert snap["cpu_count"] >= 1
    assert snap["ram_total_mb"] >= 0
    assert "engine_requirements_mb" in snap
    assert snap["engine_requirements_mb"]["easyocr"] == ENGINE_RAM_MB["easyocr"]
    # aucune donnée sensible : que des compteurs
    assert set(snap) <= {"ram_available_mb", "ram_total_mb", "cpu_count",
                         "disk_free_mb", "engine_requirements_mb"}
