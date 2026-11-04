"""Suppression réelle dans un processus sacrifiable, magasin de test uniquement."""
from __future__ import annotations

import json
import os
import signal
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from unocr.business_store import BusinessStore
from unocr.routes import frais


def run() -> int:
    racine, marqueur, phase, identifiant = sys.argv[1:]
    if phase not in {"apres_lien", "apres_retrait", "avant_commit", "apres_commit"}:
        raise ValueError("Phase de test inconnue")
    racine = Path(racine)
    frais.cfg = SimpleNamespace(data_dir=racine, log_dir=racine / "logs")
    # Identifie uniquement le chemin déclaré pour cette fixture.
    from unocr.models import Justificatif
    piece = BusinessStore(racine / "metier.sqlite3", "justificatif", Justificatif)[identifiant]
    cible = frais._chemin_justificatif(piece)
    quarantaine = cible.with_name("." + cible.name + ".deleted.tmp")

    def barriere():
        pret = Path(marqueur)
        temporaire = pret.with_suffix(".tmp")
        temporaire.write_text(phase, encoding="utf-8")
        temporaire.replace(pret)
        while True:
            signal.pause()

    original_link, original_unlink, original_del = os.link, Path.unlink, BusinessStore.__delitem__

    def lien(source, destination):
        original_link(source, destination)
        if destination == quarantaine and phase == "apres_lien":
            barriere()

    def retrait(self, *args, **kwargs):
        if self == quarantaine and phase == "apres_commit":
            barriere()
        original_unlink(self, *args, **kwargs)
        if self == cible and phase == "apres_retrait":
            barriere()

    def suppression(self, cle):
        original_del(self, cle)
        if self.collection == "justificatif" and cle == identifiant and phase == "avant_commit":
            barriere()

    os.link, Path.unlink, BusinessStore.__delitem__ = lien, retrait, suppression
    app = FastAPI()
    app.include_router(frais.router)
    with TestClient(app) as client:
        rep = client.delete(f"/api/frais/justificatif/{identifiant}")
        print(json.dumps({"status": rep.status_code, "body": rep.json()}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
