"""SIGKILL borné d'un enfant de test bloqué sur une barrière atomique."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest


def tuer_a_barriere(worker: str, racine: Path, marqueur: Path, phase: str, *arguments: str):
    if os.name != "posix":
        pytest.skip("Preuve SIGKILL réservée aux systèmes POSIX")
    repo = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo / "src"),
           "UNOCR_DATA_DIR": str(racine), "UNOCR_LOG_DIR": str(racine / "logs"),
           "UNOCR_USER_PROFILES_DIR": str(racine / "profiles")}
    enfant = subprocess.Popen(
        [sys.executable, str(repo / "tests" / worker), str(racine), str(marqueur), phase, *arguments],
        cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        echeance = time.monotonic() + 15
        while not marqueur.exists() and enfant.poll() is None and time.monotonic() < echeance:
            time.sleep(0.02)
        if not marqueur.exists():
            if enfant.poll() is None:
                enfant.kill()
            sortie, erreurs = enfant.communicate(timeout=10)
            pytest.fail(f"Barrière {phase} non atteinte : {sortie}\n{erreurs}")
        assert marqueur.read_text(encoding="utf-8") == phase
        assert enfant.poll() is None
        enfant.kill()
        sortie, erreurs = enfant.communicate(timeout=10)
        assert enfant.returncode == -signal.SIGKILL, (sortie, erreurs)
        assert sortie == "", "Un faux rapport de réussite a été émis avant SIGKILL"
    finally:
        if enfant.poll() is None:
            enfant.kill()
        enfant.communicate(timeout=10)
