"""Contrat navigateur de l'import banque (API simulée, aucune donnée réelle)."""
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_import_banque_ui_roles_et_multipart():
    if not shutil.which("node") or not (ROOT / "node_modules/jsdom").is_dir():
        pytest.skip("node/jsdom absent")
    url = os.environ.get("UNIOCR_UI_URL", "http://127.0.0.1:8000")
    try:
        with urllib.request.urlopen(url + "/api/health", timeout=3):
            pass
    except (urllib.error.URLError, OSError):
        pytest.skip(f"aucun serveur sur {url} (lancer scripts/run_preview.sh)")
    resultat = subprocess.run(["node", "tests/ui_finance_banque.js", url], cwd=ROOT,
                              capture_output=True, text=True, timeout=120)
    assert resultat.returncode == 0, resultat.stdout + resultat.stderr
    assert "OK UI banque lecteur" in resultat.stdout
    assert "OK UI banque operateur" in resultat.stdout
