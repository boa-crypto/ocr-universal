"""Petit serveur uvicorn jetable pour les tests jsdom contre la vraie API."""
from __future__ import annotations

import json
import os
import secrets
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


class ApiIsolee:
    def __init__(self, repertoire: Path):
        if not shutil.which("node") or not (RACINE / "node_modules/jsdom").is_dir():
            pytest.skip("node/jsdom absent : lancer npm install pour activer le test navigateur réel")
        self.repertoire = repertoire
        with socket.socket() as port_libre:
            port_libre.bind(("127.0.0.1", 0))
            self.port = port_libre.getsockname()[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.env = {**os.environ, "PYTHONPATH": str(RACINE / "src"),
                    "UNOCR_DATA_DIR": str(repertoire / "data"),
                    "UNOCR_LOG_DIR": str(repertoire / "logs"),
                    "UNOCR_USER_PROFILES_DIR": str(repertoire / "profiles"),
                    "UNOCR_PREVIEW": "1", "UNOCR_E2E_ISOLATED": "1",
                    "UNOCR_E2E_TOKEN": secrets.token_hex(24)}
        self.processus = None
        self.journal = None

    def __enter__(self):
        self.journal = (self.repertoire / "serveur.log").open("w")
        try:
            self.demarrer()
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *_):
        try:
            self.arreter()
        finally:
            self.journal.close()

    def requete(self, route: str, corps: dict | None = None):
        req = urllib.request.Request(self.base + route,
                                     data=None if corps is None else json.dumps(corps).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as rep:
            return json.load(rep)

    def demarrer(self):
        self.processus = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "tests._api_isolee_app:app", "--host", "0.0.0.0",
             "--port", str(self.port)], cwd=RACINE, env=self.env,
            stdout=self.journal, stderr=subprocess.STDOUT)
        limite = time.monotonic() + 30
        while time.monotonic() < limite:
            if self.processus.poll() is not None:
                pytest.fail("API isolée arrêtée : " + (self.repertoire / "serveur.log").read_text()[-3000:])
            try:
                identite = self.requete("/__e2e__/identite")
                assert identite.get("identite") == self.env["UNOCR_E2E_TOKEN"], "Port occupé par un autre serveur"
                self.requete("/api/health")
                return
            except (urllib.error.URLError, OSError):
                time.sleep(0.1)
        pytest.fail("API isolée non prête après 30 secondes")

    def arreter(self):
        if self.processus is not None:
            self.processus.terminate()
            try:
                self.processus.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.processus.kill()
                self.processus.wait(timeout=5)
            self.processus = None

    def redemarrer(self):
        self.arreter()
        self.demarrer()

    def navigateur(self, script: str, *arguments: str):
        rep = subprocess.run(["node", str(RACINE / "tests" / script), self.base, *arguments],
                             cwd=RACINE, env=self.env, capture_output=True, text=True, timeout=90)
        assert rep.returncode == 0, rep.stdout + rep.stderr
        assert "OK E2E réel" in rep.stdout
