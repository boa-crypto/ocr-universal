"""L'interface du parcours documentaire doit rendre du contenu réel.

**Pourquoi ce test existe.** Aucun navigateur headless n'est disponible ici : le
rendu visuel, le clavier et les lecteurs d'écran ne peuvent pas être contrôlés.
Ce test fait ce qui reste possible — il exécute le module *servi* (extrait de
`web/index.html`, pas de `web/dossier.js`, pour tester ce qui est réellement
livré) sur un DOM simulé branché sur l'API réelle, et vérifie qu'il produit des
éléments et des données, pas seulement du texte.

Le rendu visuel, le clavier et l'accessibilité restent **non contrôlés** ici :
c'est dit dans le rapport de phase, pas masqué.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
CONTROLE = RACINE / "tests" / "ui_stub_check.js"


def _api_vivante(port: str) -> bool:
    """L'API répond-elle sur ce port ?"""
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3):
            return True
    except (urllib.error.URLError, OSError):
        return False


@pytest.mark.skipif(not shutil.which("node"), reason="node absent de l'environnement")
def test_controle_statique_de_l_interface() -> None:
    """Syntaxe, DOM simulé, identifiants, taille, aucune ressource externe."""
    r = subprocess.run([sys.executable and "node", str(CONTROLE)],
                       capture_output=True, text=True, cwd=RACINE, timeout=300,
                       encoding="utf-8", errors="replace")
    sortie = r.stdout + r.stderr
    assert r.returncode == 0, sortie
    # les contrôles de rendu peuvent être ignorés faute de serveur ; les
    # contrôles statiques, eux, doivent passer
    assert "Tous les contrôles statiques de l'interface passent." in sortie


@pytest.mark.skipif(not shutil.which("node"), reason="node absent de l'environnement")
def test_rendu_du_parcours_documentaire() -> None:
    """Le module Dossier rend ses blocs et ses constats, API réelle.

    Sauté si aucun serveur ne tourne : le contrôle statique reste exécuté, et
    le rendu est vérifié dès qu'un serveur est disponible.
    """
    port = os.environ.get("UNIOCR_TEST_PORT", "8123")
    if not _api_vivante(port):
        pytest.skip(f"aucun serveur sur le port {port}")
    r = subprocess.run([sys.executable and "node", str(CONTROLE)],
                       capture_output=True, text=True, cwd=RACINE, timeout=600,
                       env={**os.environ, "PORT": port})
    sortie = r.stdout + r.stderr
    assert "Parcours documentaire : 55 controles de rendu executes" in sortie, sortie
    assert "[FAIL]" not in sortie, sortie
