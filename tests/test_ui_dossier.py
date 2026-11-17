"""L'interface du parcours documentaire doit rendre du contenu réel.

Le contrôle statique est indépendant du serveur. Le rendu charge par HTTP la
page et les modules externes qu'elle référence, sur un serveur éphémère isolé.
Deux PDF synthétiques sont réellement déposés et traités en lecture native,
sans exiger Tesseract/Indra ni modifier le magasin de l'aperçu.

Le rendu visuel, le clavier et l'accessibilité restent **non contrôlés** ici :
c'est dit dans le rapport de phase, pas masqué.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytest_plugins = ["ui_render_server"]

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
    r = subprocess.run(["node", str(CONTROLE), "--static"],
                       capture_output=True, text=True, cwd=RACINE, timeout=300,
                       encoding="utf-8", errors="replace")
    sortie = r.stdout + r.stderr
    assert r.returncode == 0, sortie
    # Ce mode ne sonde pas de serveur et n’exécute aucun rendu.
    assert "Tous les contrôles statiques de l'interface passent." in sortie


@pytest.mark.skipif(not shutil.which("node"), reason="node absent de l'environnement")
def test_rendu_du_parcours_documentaire(ui_render_port) -> None:
    """Le module Dossier rend ses blocs et ses constats, API réelle.

    Un démarrage/chargement/rendu défaillant est un échec, pas un test ignoré.
    """
    port = ui_render_port
    assert _api_vivante(port)
    r = subprocess.run(["node", str(CONTROLE), "--require-render"],
                       capture_output=True, text=True, cwd=RACINE, timeout=600,
                       env={**os.environ, "PORT": port})
    sortie = r.stdout + r.stderr
    assert r.returncode == 0, sortie
    assert "Connecteur Hub : 21 controles de rendu executes" in sortie, sortie
    assert "Parcours documentaire : 55 controles de rendu executes" in sortie, sortie
    assert "[FAIL]" not in sortie, sortie
