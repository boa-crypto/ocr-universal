"""Store persistant pour les fournisseurs (Module 01)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from unocr.logging_setup import get_logger
from unocr.models import Fournisseur, new_id

log = get_logger("fournisseur")


class FournisseurStore:
    """Persistance JSON des fournisseurs, sous `data/fournisseurs/`."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Fournisseur] = {}

    def _chemin(self, fournisseur_id: str) -> Path:
        return self.root / f"{fournisseur_id}.json"

    def _lire(self, fournisseur_id: str) -> Optional[Fournisseur]:
        if fournisseur_id in self._cache:
            return self._cache[fournisseur_id]
        p = self._chemin(fournisseur_id)
        if not p.is_file():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            log.error("fournisseur illisible (%s) : %s", p.name, exc)
            return None
        fournisseur = Fournisseur(**data)
        self._cache[fournisseur_id] = fournisseur
        return fournisseur

    def _ecrire(self, fournisseur: Fournisseur) -> None:
        tmp = self._chemin(fournisseur.id).with_suffix(".tmp")
        tmp.write_text(json.dumps(fournisseur.as_dict(), ensure_ascii=False, indent=1),
                       encoding="utf-8")
        tmp.replace(self._chemin(fournisseur.id))
        self._cache[fournisseur.id] = fournisseur

    def creer(self, **kwargs) -> Fournisseur:
        fournisseur = Fournisseur(id=new_id("fourn_"), **kwargs)
        self._ecrire(fournisseur)
        return fournisseur

    def get(self, fournisseur_id: str) -> Optional[Fournisseur]:
        return self._lire(fournisseur_id)

    def liste(self) -> list[Fournisseur]:
        fournisseurs = []
        for p in sorted(self.root.glob("*.json")):
            f = self._lire(p.stem)
            if f:
                fournisseurs.append(f)
        fournisseurs.sort(key=lambda f: f.id, reverse=True)
        return fournisseurs

    def supprimer(self, fournisseur_id: str) -> bool:
        fournisseur = self._lire(fournisseur_id)
        if not fournisseur:
            return False
        self._chemin(fournisseur_id).unlink(missing_ok=True)
        self._cache.pop(fournisseur_id, None)
        return True
