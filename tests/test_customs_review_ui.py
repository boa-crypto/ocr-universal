"""Pont HTTP isolé vers le TestClient réel ; aucune fixture de production."""
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from tests import test_customs_review
from tests.test_customs_reference import snapshot

revue = test_customs_review.revue


def test_interface_revue_sur_api_reelle(revue):
    root = Path(__file__).resolve().parents[1]
    if not shutil.which("node") or not (root / "node_modules/jsdom").is_dir():
        pytest.skip("Node et npm ci nécessaires au test navigateur JSDOM")
    client, racine, registre, cfg = revue
    cfg.web_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "web/index.html", cfg.web_dir / "index.html")
    avant = snapshot(racine)

    class Pont(BaseHTTPRequestHandler):
        def do_GET(self):
            reponse = client.get(self.path, headers=dict(self.headers))
            self.send_response(reponse.status_code)
            self.send_header("Content-Type", reponse.headers.get("content-type", "application/octet-stream"))
            self.end_headers()
            self.wfile.write(reponse.content)

        def log_message(self, *args):
            pass

    serveur = ThreadingHTTPServer(("0.0.0.0", 0), Pont)
    thread = Thread(target=serveur.serve_forever, daemon=True)
    thread.start()
    try:
        resultat = subprocess.run(
            ["node", "tests/ui_customs_review_integration.js", f"http://127.0.0.1:{serveur.server_port}"],
            cwd=root, capture_output=True, text=True, timeout=30,
        )
        assert resultat.returncode == 0, resultat.stdout + resultat.stderr
        assert snapshot(racine) == avant
    finally:
        serveur.shutdown()
        serveur.server_close()
        thread.join(timeout=5)
