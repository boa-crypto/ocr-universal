"""Tests de l'architecture refactorisée (sans duplication).

Après le refactoring Phase 1, les modules JS ne sont plus dupliqués dans index.html.
Ce test vérifie que l'architecture refactorisée est cohérente.
"""
from pathlib import Path

RACINE = Path(__file__).parent.parent
WEB = RACINE / "web"

def test_index_html_charge_css_externe() -> None:
    """index.html doit charger styles.css en externe."""
    index = (WEB / "index.html").read_text(encoding="utf-8")
    # Les ressources statiques sont servies depuis /web (voir MODULES_WEB_RACINE).
    assert 'rel="stylesheet" href="/web/styles.css"' in index or \
        '<link rel="stylesheet" href="styles.css">' in index, \
        "index.html doit charger styles.css en externe"
    assert "<style>" not in index, \
        "index.html ne doit plus contenir de CSS inline"

def test_index_html_charge_modules_externes() -> None:
    """index.html doit charger les modules JS en externe avec defer."""
    index = (WEB / "index.html").read_text(encoding="utf-8")
    modules_attendus = [
        "connectors.js",
        "dossier.js",
        "formulaire.js",
        "tracabilite.js",
        "transmission.js",
    ]
    for module in modules_attendus:
        # Les modules racine sont aussi servis en chemin absolu (/connectors.js),
        # ce qui évite toute ambiguïté quand la page est ouverte depuis une
        # sous-route. Les deux formes désignent le même fichier de même origine.
        assert (f'<script src="{module}" defer></script>' in index
                or f'<script src="/{module}" defer></script>' in index), \
            f"index.html doit charger {module} en externe avec defer"

def test_pas_de_duplication_js() -> None:
    """index.html ne doit plus contenir les marqueurs de duplication."""
    index = (WEB / "index.html").read_text(encoding="utf-8")
    marqueurs_obsoletes = [
        "CNXHUB:BEGIN",
        "DOSSIER:BEGIN",
        "FORMULAIRE:BEGIN",
        "TRACABILITE:BEGIN",
        "TRANSMISSION:BEGIN",
        "sync_web_module.py",
    ]
    for marqueur in marqueurs_obsoletes:
        assert marqueur not in index, \
            f"index.html ne doit plus contenir {marqueur} (duplication supprimée)"

def test_modules_js_existent() -> None:
    """Tous les modules JS externes doivent exister."""
    modules = [
        "connectors.js",
        "dossier.js",
        "formulaire.js",
        "tracabilite.js",
        "transmission.js",
    ]
    for module in modules:
        path = WEB / module
        assert path.exists(), f"{module} doit exister dans web/"
        assert path.stat().st_size > 1000, f"{module} ne doit pas être vide"

def test_styles_css_existe() -> None:
    """styles.css doit exister et contenir le CSS extrait."""
    styles = WEB / "styles.css"
    assert styles.exists(), "styles.css doit exister"
    content = styles.read_text(encoding="utf-8")
    assert len(content) > 400000, \
        "styles.css doit contenir le CSS extrait (~490KB)"
    # Vérifier quelques éléments clés du CSS
    assert "[data-theme" in content or "data-theme" in content, \
        "styles.css doit contenir les sélecteurs de thèmes"
    # Contient les styles pour les thèmes (même si les mots exacts varient)
    assert len(content) > 450000, "styles.css doit contenir le CSS complet"

def test_service_worker_cache_architecture_refactorisee() -> None:
    """Le service worker doit cacher la nouvelle architecture."""
    sw = (WEB / "sw.js").read_text(encoding="utf-8")
    assert "styles.css" in sw, \
        "Service worker doit cacher styles.css"
    modules = ["connectors.js", "dossier.js", "formulaire.js",
               "tracabilite.js", "transmission.js"]
    for module in modules:
        assert module in sw, \
            f"Service worker doit cacher {module}"

def test_reduction_taille_index() -> None:
    """index.html doit rester une coquille : aucun JS/CSS dupliqué.

    Le plafond est passé de 200 KB à 220 KB avec la refonte premium : le
    cockpit embarque désormais son balisage complet (bandeau d'accueil, cinq
    tuiles KPI, panneaux et graphiques). Ce qui est mesuré ici reste la
    duplication de code — les tests voisins vérifient qu'aucun CSS ni module
    JS n'est réinliné dans le document.
    """
    index_size = (WEB / "index.html").stat().st_size
    assert index_size < 220000, \
        f"index.html doit rester < 220KB (actuellement {index_size/1024:.1f}KB)"
    print(f"✓ index.html contenu à {index_size/1024:.1f}KB")
