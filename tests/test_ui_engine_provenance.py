"""Module de provenance HTTP réel, rendu JSDOM contrôlé, jamais fournisseur réel."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytest_plugins = ["ui_render_server"]
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not shutil.which("node"), reason="node absent")
def test_engine_provenance_served_module_and_full_render(ui_render_port):
    result = subprocess.run(
        ["node", "tests/ui_engine_provenance.js", ui_render_port], cwd=ROOT,
        env=os.environ.copy(), capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "47 scénarios provenance réussis" in result.stdout


def test_engine_provenance_shell_loading_order_and_cache():
    from html.parser import HTMLParser

    scripts = []

    class Scripts(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "script" and "src" in dict(attrs):
                scripts.append(dict(attrs)["src"])

    Scripts().feed((ROOT / "web/index.html").read_text())
    path = "/web/engine-provenance.js"
    assert scripts.count(path) == 1
    assert scripts.index(path) < scripts.index("/web/app-extras.js")
    worker = (ROOT / "web/sw.js").read_text()
    assert '"unocr-shell-v98-legal-page-search"' in worker
    assessment = "/web/customs-assessments.js"
    assert scripts.count(assessment) == 1
    assert scripts.index(assessment) < scripts.index("/web/customs-review.js")
    assert worker.count('"' + assessment + '"') == 1
    legal_pages = "/web/customs-legal-pages.js"
    assert scripts.count(legal_pages) == 1
    assert scripts.index(legal_pages) < scripts.index("/web/customs-review.js")
    assert worker.count('"' + legal_pages + '"') == 1
    assert worker.count('"' + path + '"') == 1
