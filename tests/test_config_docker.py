"""Parité de configuration embarquée : l'image ne doit pas retomber sur les défauts Python."""
from __future__ import annotations

import shutil
from pathlib import Path

from unocr.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_copie_la_configuration():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY config ./config" in dockerfile


def test_config_default_json_est_bien_charge(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    shutil.copyfile(ROOT / "config" / "default.json", tmp_path / "config" / "default.json")
    monkeypatch.setenv("UNOCR_ROOT", str(tmp_path))
    cfg = load_config()
    assert cfg.get("ocr.engine_order") == ["native_pdf", "indra", "tesseract"]


def test_dockerfile_installe_le_verrou_runtime():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "requirements.lock.txt" in dockerfile
    assert "pip install --no-cache-dir -r requirements.lock.txt" in dockerfile
    assert "pip install --no-cache-dir --no-deps ." in dockerfile


def test_verrous_minimaux_et_coherents():
    import re

    runtime = (ROOT / "requirements.lock.txt").read_text(encoding="utf-8")
    dev = (ROOT / "requirements-dev.lock.txt").read_text(encoding="utf-8")
    assert "-r requirements.lock.txt" in dev
    pins = []
    for texte in (runtime, dev):
        for ligne in texte.splitlines():
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#") or ligne.startswith("-r"):
                continue
            assert re.fullmatch(r"[A-Za-z0-9_.-]+==[^\s;]+", ligne), ligne
            pins.append(ligne.lower())
    assert len(pins) == len(set(pins))
    interdit = ("jupyter", "ipykernel", "e2b", "gensim", "librosa", "plotly",
                "matplotlib", "seaborn", "spacy", "opencv-python==")
    assert not any(p.startswith(interdit) for p in pins)
    assert "opencv-python-headless==" in runtime
    assert "indra-ocr==" in dev and "indra-ocr==" not in runtime


def test_ci_utilise_le_verrou_dev():
    for nom in (".github/workflows/ci.yml", ".github/workflows/customs-review.yml"):
        texte = (ROOT / nom).read_text(encoding="utf-8")
        assert "pip install -r requirements-dev.lock.txt" in texte
        assert "pip install --no-deps -e ." in texte


def test_pyproject_et_requirements_utilisent_opencv_headless():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "opencv-python-headless" in pyproject
    assert "opencv-python>=" not in pyproject
    assert "opencv-python-headless" in requirements
    assert "opencv-python>=" not in requirements
