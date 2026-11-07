"""Score déclaré par Baidu, jamais remplacé par une confiance inventée."""
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
