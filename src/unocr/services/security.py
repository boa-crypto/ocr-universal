"""Configuration de sécurité centralisée pour l'API FastAPI."""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Hôtes des aperçus distants (bac à sable type e2b.app). Utilisés uniquement
# quand UNOCR_PREVIEW=1 : le déploiement par défaut reste strictement local.
PREVIEW_HOST_PATTERN = "*.e2b.app"


def preview_mode() -> bool:
    """Aperçu navigateur distant activé explicitement (UNOCR_PREVIEW=1).

    Désactivé par défaut : aucune politique permissive n'est appliquée à
    l'insu de l'exploitant.
    """
    return os.environ.get("UNOCR_PREVIEW", "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _normalize_list(raw: Any, default: list[str]) -> list[str]:
    if isinstance(raw, str):
        items = [part.strip() for part in raw.split(",") if part.strip()]
    elif isinstance(raw, (list, tuple)):
        items = [str(part).strip() for part in raw if str(part).strip()]
    else:
        items = []
    return items or default


def _configured_cors_origins(cfg: Any) -> list[str]:
    """Origines CORS autorisées, local-first et sans wildcard par défaut."""
    origins = _normalize_list(cfg.get("api.cors_origins", []), [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://localhost",
    ])
    return origins


def _configured_allowed_hosts(cfg: Any) -> list[str]:
    """Hosts acceptés pour le service ; rien de wildcard par défaut."""
    hosts = _normalize_list(cfg.get("api.allowed_hosts", []), [
        "127.0.0.1",
        "localhost",
        "::1",
    ])
    if preview_mode() and PREVIEW_HOST_PATTERN not in hosts:
        hosts = list(hosts) + [PREVIEW_HOST_PATTERN]
    if "testserver" not in hosts:
        hosts = list(hosts) + ["testserver"]
    return hosts


def default_security_headers(cfg: Any) -> dict[str, str]:
    """Politique HTTP par défaut, centralisée pour éviter les écarts."""
    _ = cfg
    policy = {
        "x_frame_options": "DENY",
        "x_content_type_options": "nosniff",
        "referrer_policy": "no-referrer",
        "permissions_policy": "camera=(), microphone=(), geolocation=()",
        "content_security_policy": (
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' "
            "'unsafe-inline'; script-src 'self' 'unsafe-inline'; object-src 'none'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        ),
        "cache_control": "no-store, no-cache, must-revalidate, max-age=0",
    }
    if preview_mode():
        # Aperçu navigateur : l'UI est affichée dans une iframe d'une origine
        # tierce et charge Chart.js depuis un CDN. On n'assouplit QUE ces deux
        # points ; le reste de la politique demeure.
        policy["x_frame_options"] = ""  # en-tête omis par le middleware
        policy["content_security_policy"] = (
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' "
            "'unsafe-inline'; script-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net; connect-src 'self' https://*.e2b.app; "
            "object-src 'none'; frame-ancestors *; base-uri 'self'; "
            "form-action 'self'"
        )
    return policy


def configure_security_middleware(app: FastAPI, cfg: Any) -> None:
    """Applique les middlewares de sécurité, sans modifier le comportement métier."""
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=_configured_allowed_hosts(cfg),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_configured_cors_origins(cfg),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
