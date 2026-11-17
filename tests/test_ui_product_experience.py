"""Contracts of the task-first shell; business API permissions stay unchanged."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_product_shell_assets_order_and_offline_cache():
    html = (ROOT/'web/index.html').read_text()
    assert html.index('/web/uniocr-ds.css') < html.index('/web/product-experience.css')
    assert '<script src="/web/product-experience.js" defer></script>' in html
    worker = (ROOT/'web/sw.js').read_text()
    assert '/web/product-experience.js' in worker and '/web/product-experience.css' in worker
    assert 'url.pathname.startsWith("/api/")' in worker


def test_product_interactions_permissions_and_toast():
    if not shutil.which('node') or not (ROOT/'node_modules/jsdom').is_dir():
        pytest.skip('Node/jsdom required')
    result = subprocess.run(['node','tests/ui_product_experience.js'],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stdout+result.stderr


def test_product_does_not_add_business_writes_or_roles():
    source = (ROOT/'web/product-experience.js').read_text()
    assert 'fetch(' not in source and 'localStorage' not in source
    assert "nav.querySelectorAll('a[href^=\"#\"]')" in source
    assert 'Navigation.getConfig' not in source
    assert 'innerHTML' not in source


def test_cockpit_does_not_convert_api_failures_to_empty_success():
    source = (ROOT/'web/cockpit.js').read_text()
    assert 'api("/api/dossiers").catch(function () { return []; })' not in source
    assert 'Synchronisation interrompue' in source


def test_fonts_are_local_csp_compatible_and_cached():
    import re
    css = (ROOT/'web/styles.css').read_text()
    faces = re.findall(r'@font-face\s*\{[^}]+\}', css)
    assert len(faces) == 9
    assert 'data:font' not in css
    worker = (ROOT/'web/sw.js').read_text()
    for face in faces:
        url = re.search(r'url\((/web/fonts/[^)]+)\)', face).group(1)
        assert (ROOT/url.lstrip('/')).is_file()
        assert url in worker
