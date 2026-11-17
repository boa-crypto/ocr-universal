"""Vérifications navigateur : les écrans s'ouvrent, cliquent et répondent.

Ce module ne teste pas du code Python : il lance `tests/ui_smoke.js`, qui charge
l'interface dans jsdom comme un navigateur, parcourt huit écrans critiques,
déclenche quatre interactions et **n'émet aucune écriture**.

Pourquoi un test qui peut être sauté : jsdom et un serveur en marche sont deux
dépendances extérieures à la suite Python. Le test ne ment pas sur son état —
il est **sauté explicitement** quand l'environnement manque, avec la raison, et
il échoue franchement dès que `node` et jsdom sont là.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = RACINE / "tests" / "ui_smoke.js"


def _jsdom_disponible() -> bool:
    """jsdom installé ? (`npm install` à la racine du dépôt)"""
    if shutil.which("node") is None:
        return False
    return (RACINE / "node_modules" / "jsdom").is_dir() or bool(
        os.environ.get("NODE_PATH"))


def _serveur(url: str) -> bool:
    try:
        with urllib.request.urlopen(url + "/api/health", timeout=3):
            return True
    except (urllib.error.URLError, OSError):
        return False


def test_interface_dans_un_navigateur():
    if not _jsdom_disponible():
        pytest.skip("jsdom absent : lancer `npm install` à la racine pour activer "
                    "les vérifications navigateur")
    url = os.environ.get("UNIOCR_UI_URL", "http://127.0.0.1:8000")
    if not _serveur(url):
        pytest.skip(f"aucun serveur sur {url} (lancer `python -m unocr.cli serve`)")

    resultat = subprocess.run(
        ["node", str(SCRIPT), url],
        cwd=str(RACINE), capture_output=True, text=True, timeout=240,
        env={**os.environ},
    )
    sortie = (resultat.stdout or "") + (resultat.stderr or "")
    assert resultat.returncode == 0, (
        "vérifications navigateur en échec :\n" + sortie[-4000:])
    assert "Aucune écriture émise" in sortie
    assert "vérifications passées" in sortie


def test_interface_justificatifs():
    if not _jsdom_disponible():
        pytest.skip("jsdom absent : lancer npm install pour tester les justificatifs")
    url = os.environ.get("UNIOCR_UI_URL", "http://127.0.0.1:8000")
    if not _serveur(url):
        pytest.skip(f"aucun serveur sur {url} pour charger les fichiers UI")
    resultat = subprocess.run(
        ["node", str(RACINE / "tests" / "ui_justificatifs.js"), url],
        cwd=RACINE, capture_output=True, text=True, timeout=90,
    )
    assert resultat.returncode == 0, resultat.stdout + resultat.stderr
    assert "lecteur sans mutation" in resultat.stdout
    assert "suppression confirmée" in resultat.stdout
