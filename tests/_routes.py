"""Énumération fiable des routes effectives d'une application FastAPI.

Les versions récentes de FastAPI n'aplatissent plus les routeurs inclus :
`app.routes` contient des `_IncludedRouter` imbriqués. Les helpers ci-dessous
parcourent récursivement cette arborescence pour retrouver le chemin complet
et l'ordre réel de résolution — l'ordre compte, car une route paramétrique
déclarée avant une route littérale masque cette dernière.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI
from starlette.routing import Mount


def iterer_routes(app: FastAPI) -> Iterator[tuple[str, str]]:
    """(chemin complet, méthode HTTP) dans l'ordre de résolution."""
    yield from _parcourir(app.routes, "")


def _parcourir(routes, prefixe: str) -> Iterator[tuple[str, str]]:
    for route in routes:
        nom = type(route).__name__
        if nom == "_IncludedRouter":
            yield from _parcourir(
                route.original_router.routes,
                prefixe + (getattr(route.include_context, "prefix", "") or ""),
            )
        elif nom == "APIRoute":
            for methode in sorted(route.methods):
                yield prefixe + route.path, methode
        elif isinstance(route, Mount):
            yield prefixe + route.path, "MOUT"


def signature(chemin: str) -> list[str]:
    """Découpe un chemin ; tout segment paramétrique devient `*`."""
    return [
        "*" if morceau.startswith("{") else morceau
        for morceau in chemin.strip("/").split("/")
        if morceau
    ]


def routes_masquees(app: FastAPI) -> list[str]:
    """Routes littérales inaccessibles car capturées par une route antérieure."""
    vues: dict[tuple[str, int], list[list[str]]] = {}
    masquees: list[str] = []
    for chemin, methode in iterer_routes(app):
        if methode in {"HEAD", "OPTIONS", "MOUT"}:
            continue
        segments = signature(chemin)
        cle = (methode, len(segments))
        signatures = vues.setdefault(cle, [])
        if any(segments != autre and all(a == "*" or b == a for a, b in zip(autre, segments))
               for autre in signatures):
            masquees.append(f"{methode} {chemin}")
            continue
        signatures.append(segments)
    return masquees
