"""UI métier : simulations isolées et HTTP réel sur fixtures non officielles."""
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from test_customs_review import revue as revue


def test_ui_dossiers_sur_api_reelle(revue):
    root = Path(__file__).resolve().parents[1]
    if not shutil.which("node") or not (root / "node_modules/jsdom").is_dir():
        pytest.skip("Node et npm ci requis")
    client = revue[0]
    class Pont(BaseHTTPRequestHandler):
        def agir(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            response = client.request(self.command, self.path, headers=dict(self.headers), content=body)
            self.send_response(response.status_code)
            for key, value in response.headers.items():
                if key.lower() not in {"connection", "transfer-encoding"}:
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response.content)
        do_GET = do_POST = do_PATCH = agir
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Pont)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for script in ("tests/ui_customs_assessments.js", "tests/ui_customs_assessments_integration.js"):
            result = subprocess.run(["node", script, f"http://127.0.0.1:{server.server_port}"], cwd=root,
                                    capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stdout + result.stderr
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
