"""Relais CLI sacrifiable avec barrières sur de vrais write/fsync (tests seuls)."""
from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

from unocr.cli import main


def run() -> int:
    racine, marqueur, phase, journal = sys.argv[1:]
    if phase not in {"avant_ecriture", "ecriture_partielle", "apres_ecriture", "apres_fsync"}:
        raise ValueError("Phase de test inconnue")

    def barriere():
        pret = Path(marqueur)
        temporaire = pret.with_suffix(".tmp")
        temporaire.write_text(phase, encoding="utf-8")
        temporaire.replace(pret)
        while True:
            signal.pause()

    original_write, original_fsync = os.write, os.fsync

    def ecrire(fd, contenu):
        if phase == "avant_ecriture":
            barriere()
        if phase in {"ecriture_partielle", "apres_ecriture"}:
            partie = contenu[:5] if phase == "ecriture_partielle" else contenu
            restant = memoryview(partie)
            while restant:
                ecrits = original_write(fd, restant)
                if ecrits <= 0:
                    raise OSError("Écriture sans progression dans le worker")
                restant = restant[ecrits:]
            barriere()
        return original_write(fd, contenu)

    def synchroniser(fd):
        original_fsync(fd)
        if phase == "apres_fsync":
            barriere()

    os.write, os.fsync = ecrire, synchroniser
    return main(["pieces-audit", "just_test", "--data-dir", racine,
                 "--audit-file", journal, "--apply", "--json"])


if __name__ == "__main__":
    raise SystemExit(run())
