"""Processus sacrifiable : barrière aux deux côtés de la publication réelle.

Réservé aux tests ; ne jamais appeler sur un magasin utilisateur.
"""
from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

from unocr.cli import main


def run() -> int:
    racine, marqueur, phase = sys.argv[1:]
    if phase not in {"avant_publication", "apres_publication"}:
        raise ValueError("Phase de test inconnue")
    original = os.link

    def publication(source, destination):
        if phase == "apres_publication":
            original(source, destination)
        # Le parent attend cette barrière, puis tue ce processus par SIGKILL.
        # Aucun gestionnaire de signal, finally ou atexit ne pourra nettoyer.
        signal_pret = Path(marqueur)
        temporaire = signal_pret.with_suffix(".tmp")
        temporaire.write_text(phase, encoding="utf-8")
        temporaire.replace(signal_pret)
        while True:
            signal.pause()

    os.link = publication
    return main(["pieces-recover", "just_test", "--data-dir", racine, "--apply", "--json"])


if __name__ == "__main__":
    raise SystemExit(run())
