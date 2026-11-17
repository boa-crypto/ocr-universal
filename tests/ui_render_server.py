"""Serveur transitoire et documents synthétiques réels pour le harnais Node."""
import os
import socket
import subprocess
import sys
import time

import httpx
import pytest


@pytest.fixture
def ui_render_port(tmp_path, fixtures_dir):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "UNOCR_PREVIEW": "1",
           "UNOCR_DATA_DIR": str(tmp_path / "data"),
           "UNOCR_LOG_DIR": str(tmp_path / "logs"),
           "UNOCR_USER_PROFILES_DIR": str(tmp_path / "profiles")}
    with (tmp_path / "server.log").open("w+") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "unocr.cli", "serve", "--host", "0.0.0.0", "--port", str(port)],
            env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30, trust_env=False) as client:
                deadline = time.monotonic() + 30
                while True:
                    try:
                        client.get("/api/health").raise_for_status()
                        break
                    except httpx.TransportError:
                        if process.poll() is not None or time.monotonic() > deadline:
                            log.seek(0)
                            pytest.fail("serveur de rendu non démarré : " + log.read())
                        time.sleep(0.1)
                for source, filename in [("text_pdf.pdf", "facture.pdf"), ("bl_port.pdf", "bl.pdf")]:
                    with (fixtures_dir / source).open("rb") as file:
                        response = client.post("/api/documents", files={"file": (filename, file, "application/pdf")},
                                               data={"engine": "native", "quality_mode": "fast", "extract_tables": "false",
                                                     "extract_barcodes": "false", "dedupe": "false"})
                    response.raise_for_status()
                    job = response.json()["job_id"]
                    deadline = time.monotonic() + 60
                    while True:
                        state = client.get(f"/api/jobs/{job}").raise_for_status().json()["status"]
                        assert state != "error", state
                        if state == "done":
                            break
                        assert time.monotonic() < deadline, state
                        time.sleep(0.1)
                yield str(port)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
