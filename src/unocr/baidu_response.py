"""Scores et coordonnées déclarés par Baidu : validation sans coercition."""
from __future__ import annotations

import math


def confidence_from_item(item: dict) -> tuple[float, str]:
    """Moyenne fournisseur finie [0,1] ; sinon zéro conservateur, non mesuré."""
    if "probability" not in item:
        return 0.0, "missing"
    probability = item["probability"]
    if not isinstance(probability, dict):
        return 0.0, "invalid"
    value = probability.get("average")
    # Pas de booléen ni coercition de texte : JSON numérique uniquement.
    if type(value) not in (int, float) or not 0 <= value <= 1 or not math.isfinite(value):
        return 0.0, "invalid"
    return float(value), "reported"


class InvalidLocation(ValueError):
    """Localisation fournie inutilisable ; aucun contenu distant dans l'erreur."""


def bbox_from_location(location, page_width: int, page_height: int):
    """Boîte déclarée strictement positive et dans l'image, sans coercition/clipping."""
    from .models import BBox

    if any(type(size) is not int or not 0 < size <= 2**31 - 1
           for size in (page_width, page_height)):
        raise InvalidLocation("dimensions image invalides")
    keys = ("left", "top", "width", "height")
    if not isinstance(location, dict) or any(key not in location for key in keys):
        raise InvalidLocation("localisation invalide")
    values = [location[key] for key in keys]
    if any(type(value) not in (int, float) or
           (type(value) is float and not math.isfinite(value)) for value in values):
        raise InvalidLocation("localisation invalide")
    x, y, width, height = values
    # Bornes avant float() : un entier JSON démesuré n'est jamais converti.
    if not (0 <= x <= page_width and 0 <= y <= page_height and
            0 < width <= page_width and 0 < height <= page_height):
        raise InvalidLocation("localisation invalide")
    x, y, width, height = map(float, values)
    right, bottom = x + width, y + height
    if not (x < right <= page_width and y < bottom <= page_height and
            (right - x) * (bottom - y) > 0):
        raise InvalidLocation("localisation invalide")
    return BBox(x0=x, y0=y, x1=right, y1=bottom)
