"""Paramètres généraux : lecture, écriture validée et retour aux défauts.

**Pourquoi ce module existe.** Une page « Paramètres généraux » affichait un
formulaire pré-rempli sans jamais rien enregistrer : la saisie était perdue au
rechargement et le serveur continuait d'appliquer ses valeurs par défaut. Un
écran qui accepte une saisie sans l'appliquer est pire qu'une absence d'écran.

Le catalogue ci-dessous ne contient **que** des réglages réellement lus par le
code d'extraction. Chaque entrée porte la référence de l'endroit qui l'utilise,
ce qui permet de vérifier l'affirmation plutôt que de la croire :

* ``max_file_size_mb`` / ``max_batch_size_mb`` → contrôle de taille à l'import ;
* ``max_pages`` → nombre de pages chargées par document ;
* ``security.retention_days`` → purge des jobs terminés ;
* ``security.max_zip_uncompressed_mb`` / ``max_zip_ratio`` → garde-fous ZIP ;
* ``default_languages`` → langues proposées au moteur OCR.

Les valeurs écrites vont dans ``data/parametres.json`` (jamais dans
``config/default.json``) : une mise à jour du projet ne doit pas écraser les
réglages d'exploitation. L'effet est immédiat **et** persistant — le fichier
est relu au démarrage.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..logging_setup import audit
from ..rbac import ADMINISTRATEUR
from .dependencies import _exige

router = APIRouter(prefix="/api/parametres", tags=["parametres"])


class ModeleValeur(BaseModel):
    valeur: Any = None


class Parametre:
    """Description d'un réglage : type, bornes, effet et où il est appliqué."""

    def __init__(self, cle: str, libelle: str, type_: str, effet: str,
                 defaut: Any = None, mini: float | None = None,
                 maxi: float | None = None, unite: str = "",
                 exemple: str = "") -> None:
        self.cle = cle
        self.libelle = libelle
        self.type = type_
        self.effet = effet
        self.defaut = defaut
        self.mini = mini
        self.maxi = maxi
        self.unite = unite
        self.exemple = exemple

    def valider(self, valeur: Any) -> Any:
        """Renvoie la valeur typée, ou lève 422 en nommant le champ."""
        if self.type == "entier":
            try:
                nombre = int(str(valeur).strip()) if not isinstance(valeur, bool) else int(valeur)
            except (TypeError, ValueError):
                raise HTTPException(422, detail={
                    "champ": self.cle,
                    "message": f"{self.libelle} : entier attendu "
                               f"(reçu {valeur!r}).",
                })
            if self.mini is not None and nombre < self.mini:
                raise HTTPException(422, detail={
                    "champ": self.cle,
                    "message": f"{self.libelle} : minimum {int(self.mini)}"
                               f"{(' ' + self.unite) if self.unite else ''} "
                               f"(reçu {nombre}).",
                })
            if self.maxi is not None and nombre > self.maxi:
                raise HTTPException(422, detail={
                    "champ": self.cle,
                    "message": f"{self.libelle} : maximum {int(self.maxi)}"
                               f"{(' ' + self.unite) if self.unite else ''} "
                               f"(reçu {nombre}).",
                })
            return nombre
        if self.type == "liste":
            if isinstance(valeur, str):
                elements = [v.strip() for v in valeur.split(",") if v.strip()]
            elif isinstance(valeur, (list, tuple)):
                elements = [str(v).strip() for v in valeur if str(v).strip()]
            else:
                raise HTTPException(422, detail={
                    "champ": self.cle,
                    "message": f"{self.libelle} : liste de codes attendue "
                               f"(reçu {valeur!r}).",
                })
            if not elements:
                raise HTTPException(422, detail={
                    "champ": self.cle,
                    "message": f"{self.libelle} : au moins une langue est requise.",
                })
            invalides = [v for v in elements if len(v) != 3 or not v.isalpha()]
            if invalides:
                raise HTTPException(422, detail={
                    "champ": self.cle,
                    "message": f"{self.libelle} : codes à trois lettres attendus "
                               f"(reçu {', '.join(invalides)}).",
                })
            return [v.lower() for v in elements]
        return valeur


CATALOGUE: list[Parametre] = [
    Parametre("max_file_size_mb", "Taille maximale d'un fichier", "entier",
              "refuse un document plus lourd avant toute lecture",
              mini=1, maxi=500, unite="Mo"),
    Parametre("max_batch_size_mb", "Taille maximale d'un lot", "entier",
              "plafonne la somme des fichiers d'un import groupé",
              mini=1, maxi=2000, unite="Mo"),
    Parametre("max_pages", "Pages maximales par document", "entier",
              "tronque la lecture d'un PDF trop long",
              mini=1, maxi=5000, unite="pages"),
    Parametre("security.retention_days", "Rétention des jobs", "entier",
              "purge les jobs terminés au-delà de ce délai",
              mini=1, maxi=3650, unite="jours"),
    Parametre("security.max_zip_uncompressed_mb", "Taille décompressée (ZIP)",
              "entier", "garde-fou contre une archive gonflée à l'extrême",
              mini=1, maxi=5000, unite="Mo"),
    Parametre("security.max_zip_ratio", "Ratio de compression (ZIP)", "entier",
              "garde-fou contre une bombe de décompression",
              mini=1, maxi=1000, unite=":1"),
    Parametre("default_languages", "Langues OCR par défaut", "liste",
              "langues proposées au moteur quand le document n'en impose pas",
              exemple="fra, eng"),
]

_PAR_CLE: dict[str, Parametre] = {p.cle: p for p in CATALOGUE}


def _config(request: Request):
    return getattr(request.app.state, "cfg", None)


def _etat(cle: str, cfg) -> dict:
    par = _PAR_CLE[cle]
    valeur = cfg.get(cle, par.defaut)
    return {
        "id": cle,
        "cle": cle,
        "libelle": par.libelle,
        "type": par.type,
        "unite": par.unite,
        "effet": par.effet,
        "valeur": value_to_text(valeur),
        "defaut": value_to_text(par.defaut if par.defaut is not None
                                else cfg.valeur_par_defaut(cle)),
        "modifie": cle in getattr(cfg, "surcharges", {}),
        "etat": "modifié" if cle in getattr(cfg, "surcharges", {}) else "défaut",
        "exemple": par.exemple,
    }


def value_to_text(valeur: Any) -> str:
    if isinstance(valeur, (list, tuple)):
        return ", ".join(str(v) for v in valeur)
    if valeur is None:
        return ""
    if isinstance(valeur, bool):
        return "oui" if valeur else "non"
    return str(valeur)


@router.get("")
def lister(request: Request) -> dict:
    """Tous les réglages modifiables, avec leur valeur effective."""
    cfg = _config(request)
    if cfg is None:  # pragma: no cover - configuration toujours présente
        raise HTTPException(500, "configuration indisponible")
    parametres = [_etat(p.cle, cfg) for p in CATALOGUE]
    return {
        "parametres": parametres,
        "total": len(parametres),
        "modifies": sum(1 for p in parametres if p["modifie"]),
        "fichier": str(getattr(cfg, "parametres_path", "")),
    }


@router.get("/{cle}")
def lire(cle: str, request: Request) -> dict:
    cfg = _config(request)
    if cle not in _PAR_CLE:
        raise HTTPException(404, f"paramètre inconnu : {cle}")
    return _etat(cle, cfg)


@router.put("/{cle}")
def modifier(cle: str, payload: ModeleValeur, request: Request) -> dict:
    """Écrit un réglage : validé, appliqué immédiatement, persisté, tracé."""
    _exige(ADMINISTRATEUR)(request)
    cfg = _config(request)
    par = _PAR_CLE.get(cle)
    if par is None:
        raise HTTPException(404, f"paramètre inconnu : {cle}")
    avant = value_to_text(cfg.get(cle, par.defaut))
    valeur = par.valider(payload.valeur)
    cfg.definir(cle, valeur)
    audit(cfg.log_dir, "parametre_modifie", cle=cle,
          avant=avant, apres=value_to_text(valeur))
    return _etat(cle, cfg)


@router.delete("/{cle}")
def reinitialiser(cle: str, request: Request) -> dict:
    """Retire une surcharge : la valeur de référence revient."""
    _exige(ADMINISTRATEUR)(request)
    cfg = _config(request)
    par = _PAR_CLE.get(cle)
    if par is None:
        raise HTTPException(404, f"paramètre inconnu : {cle}")
    if not cfg.reinitialiser(cle):
        raise HTTPException(409, f"{par.libelle} utilise déjà la valeur par défaut")
    audit(cfg.log_dir, "parametre_reinitialise", cle=cle,
          valeur=value_to_text(cfg.get(cle, par.defaut)))
    return _etat(cle, cfg)
