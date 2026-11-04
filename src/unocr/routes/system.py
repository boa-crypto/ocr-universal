"""Routes système et de diagnostic de l'API."""
from __future__ import annotations

import time

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api")


@router.get("/health")
def health(request: Request) -> dict:
    registry = request.app.state.registry
    engines = registry.list_engines()
    return {
        "status": "ok",
        "engines_available": [e["name"] for e in engines if e["available"]],
        "engines": engines,
        "time": time.time(),
    }


@router.get("/engines")
def engines(request: Request) -> list[dict]:
    return request.app.state.registry.list_engines()


@router.get("/languages")
def languages(request: Request) -> dict:
    tess = request.app.state.registry.get("tesseract")
    supported = tess.supported_languages() if tess and tess.is_available() else []
    catalog = {
        "fra": "français",
        "eng": "anglais",
        "ara": "arabe",
        "ber": "amazigh (tifinagh)",
        "spa": "espagnol",
        "deu": "allemand",
        "ita": "italien",
        "por": "portugais",
        "tur": "turc",
        "rus": "russe",
        "chi_sim": "chinois simplifié",
        "chi_tra": "chinois traditionnel",
        "jpn": "japonais",
        "kor": "coréen",
        "nld": "néerlandais",
        "pol": "polonais",
        "ukr": "ukrainien",
        "vie": "vietnamien",
        "hin": "hindi",
        "urd": "ourdou",
        "fas": "persan",
        "heb": "hébreu",
        "ell": "grec",
        "ron": "roumain",
        "hun": "hongrois",
        "ces": "tchèque",
        "swe": "suédois",
        "dan": "danois",
        "fin": "finnois",
        "nor": "norvégien",
    }
    return {
        "installed_models": supported,
        "catalog": {c: catalog[c] for c in supported if c in catalog},
        "note": "seules les langues dont le modèle tessdata est installé sont déclarées supportées",
    }
