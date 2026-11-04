"""Entrée uvicorn réservée au harnais : marqueur d'identité, aucun mock métier."""
import os

from unocr.api import app

if os.environ.get("UNOCR_E2E_ISOLATED") != "1" or not os.environ.get("UNOCR_E2E_TOKEN"):
    raise RuntimeError("Cette entrée est réservée aux tests isolés")


@app.get("/__e2e__/identite")
def identite_test():
    return {"identite": os.environ["UNOCR_E2E_TOKEN"]}
