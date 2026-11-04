"""CRUD navigateur contre une vraie API, trois démarrages et SQLite temporaire."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]


def test_crud_declarations_navigateur_et_redemarrage(tmp_path):
    if not shutil.which("node") or not (RACINE / "node_modules/jsdom").is_dir():
        pytest.skip("node/jsdom absent : lancer npm install pour activer le CRUD navigateur réel")
    with socket.socket() as port_libre:
        port_libre.bind(("127.0.0.1", 0))
        port = port_libre.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    env = {**os.environ, "PYTHONPATH": str(RACINE / "src"),
           "UNOCR_DATA_DIR": str(tmp_path / "data"),
           "UNOCR_LOG_DIR": str(tmp_path / "logs"),
           "UNOCR_USER_PROFILES_DIR": str(tmp_path / "profiles"),
           "UNOCR_PREVIEW": "1", "UNOCR_E2E_ISOLATED": "1"}
    processus = None

    def lire(route):
        with urllib.request.urlopen(base + route, timeout=5) as rep:
            return json.load(rep)

    def demarrer(journal):
        nonlocal processus
        processus = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "unocr.api:app", "--host", "0.0.0.0",
             "--port", str(port)], cwd=RACINE, env=env,
            stdout=journal, stderr=subprocess.STDOUT)
        limite = time.monotonic() + 30
        while time.monotonic() < limite:
            if processus.poll() is not None:
                pytest.fail("API isolée arrêtée : " + (tmp_path / "serveur.log").read_text()[-3000:])
            try:
                lire("/api/health")
                return
            except (urllib.error.URLError, OSError):
                time.sleep(0.1)
        pytest.fail("API isolée non prête après 30 secondes")

    def arreter():
        nonlocal processus
        if processus is not None:
            processus.terminate()
            try:
                processus.wait(timeout=10)
            except subprocess.TimeoutExpired:
                processus.kill()
                processus.wait(timeout=5)
            processus = None

    def navigateur(phase, dossier_id):
        rep = subprocess.run(
            ["node", str(RACINE / "tests/ui_declarations_e2e.js"), base, phase, dossier_id],
            cwd=RACINE, env=env, capture_output=True, text=True, timeout=90)
        assert rep.returncode == 0, rep.stdout + rep.stderr
        assert "OK E2E réel" in rep.stdout

    with (tmp_path / "serveur.log").open("w") as journal:
        try:
            demarrer(journal)
            req = urllib.request.Request(base + "/api/dossiers", method="POST",
                                         data=json.dumps({"label": "Dossier E2E isolé"}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as rep:
                dossier_id = json.load(rep)["id"]
            navigateur("creer-modifier", dossier_id)
            arreter()
            assert (tmp_path / "data/metier.sqlite3").is_file()
            demarrer(journal)
            declarations = lire("/api/declarations")
            assert len(declarations) == 1
            declaration = declarations[0]
            assert declaration["numero_declaration"] == "DECL-E2E-MODIFIEE"
            assert declaration["statut"] == "deposee"
            assert declaration["date_depot"] == "2026-11-04"
            assert declaration["agent_declarant"] == "Agent E2E"
            navigateur("supprimer", dossier_id)
            arreter()
            demarrer(journal)
            assert lire("/api/declarations") == []
        finally:
            arreter()
