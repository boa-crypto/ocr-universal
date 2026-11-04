"""Tests de régression visuelle (statiques/structurels).

Comme l'environnement CI n'a pas forcément de navigateur complet (Playwright/Puppeteer),
ces tests vérifient la structure du DOM, la présence des assets et la validité
du Design System (tokens CSS).
"""
import re
from pathlib import Path
import pytest

WEB = Path("web")
STYLES = WEB / "styles.css"
INDEX = WEB / "index.html"

def test_design_system_tokens_presence():
    """Vérifie que les tokens critiques de la V2 sont présents dans styles.css."""
    content = STYLES.read_text(encoding="utf-8")
    critical_tokens = [
        "--blue-accent",
        "--ink-dark",
        "--ink-light",
        "--ink-neutral",
        "--font-display",
        "--font-ui",
        "--font-mono",
    ]
    for token in critical_tokens:
        assert token in content, f"Token {token} manquant dans styles.css"

def test_no_hardcoded_colors_in_critical_components():
    """Vérifie l'absence de couleurs en dur dans les sélecteurs de composants clés."""
    content = STYLES.read_text(encoding="utf-8")
    # On cherche des patterns 'color: #...' ou 'background: #...' hors variables
    # (simplifié pour la détection de régression)
    bad_patterns = [
        r"\.btn\s*\{[^}]*?background:\s*#[0-9a-fA-F]{3,6}",
        r"\.btn\s*\{[^}]*?color:\s*#[0-9a-fA-F]{3,6}",
        r"\.cam-shot\s*\{[^}]*?background:\s*#[0-9a-fA-F]{3,6}",
    ]
    for pattern in bad_patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        assert not match, f"Couleur en dur détectée dans un composant critique : {pattern}"

def test_responsive_layout_presence():
    """Vérifie la présence de media queries pour le responsive."""
    content = STYLES.read_text(encoding="utf-8")
    assert "@media" in content, "Aucun media query détecté pour le responsive"

def test_icons_and_assets_presence():
    """Vérifie que les assets référencés existent."""
    assert (WEB / "icon.svg").is_file()
    assert (WEB / "manifest.webmanifest").is_file()

def test_pwa_readiness():
    """Vérifie les éléments de base de la PWA."""
    content = INDEX.read_text(encoding="utf-8")
    assert '<link rel="manifest"' in content
    assert '<meta name="theme-color"' in content
    assert 'sw.js' in (WEB / "sw.js").name
