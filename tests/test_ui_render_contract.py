"""Contrats du harnais : les échecs ne doivent jamais devenir des ignorés."""
import os
import shutil
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="node absent")


def run(*args, port):
    return subprocess.run([NODE, str(ROOT / "tests/ui_stub_check.js"), *args],
                          cwd=ROOT, env={**os.environ, "PORT": str(port)},
                          capture_output=True, text=True, timeout=40)


def test_node_loader_and_output_contracts():
    result = subprocess.run([NODE, "--test", "--test-reporter=tap", "tests/ui_served_modules.test.js"],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# fail 0" in result.stdout


@pytest.mark.parametrize("required", [False, True])
def test_absent_server_only_optional_in_auto_mode(required):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        # Le port réservé n'écoute pas : refus garanti sans course d'allocation.
        result = run(*(["--require-render"] if required else []), port=port)
    assert result.returncode == (1 if required else 0), result.stdout + result.stderr
    assert ("rendu non exécuté" in result.stdout) is not required


@pytest.mark.parametrize("broken", ["module_404", "module_invalide", "health_500"])
def test_reachable_server_failures_are_not_ignored(broken):
    html = (ROOT / "web/index.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            status, body = 200, b"{}"
            if self.path == "/":
                body = html
            elif self.path == "/api/health":
                status = 500 if broken == "health_500" else 200
            elif self.path.endswith(".js"):
                status = 404 if broken == "module_404" else 200
                body = b"const invalid = ;"
            self.send_response(status)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = run(port=server.server_port)
        assert result.returncode == 1, result.stdout + result.stderr
        assert "[FAIL]" in result.stdout
        assert "rendu non exécuté" not in result.stdout
        assert "controle de rendu ignore" not in result.stdout
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
