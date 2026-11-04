"""Routes de configuration et de contrôle du dossier surveillé."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..logging_setup import audit
from ..watcher import WatchConfig
from ..config import get_config as _get_config

router = APIRouter(prefix="/api/watch", tags=["watch"])


class WatchBody(BaseModel):
    enabled: bool = False
    path: str = "data/watch"
    profile: str = "generic"
    languages: str = ""
    quality_mode: str = "accurate"
    poll_seconds: float = 5.0
    move_done: bool = False


def get_watcher(request: Request):
    """Fournit l'instance FolderWatcher de l'application courante."""
    return request.app.state.watcher


@router.get("")
def watch_status(watcher: Any = Depends(get_watcher)) -> dict:
    return watcher.state()


def _cfg(request: Request) -> Any:
    return request.app.state.cfg


@router.put("")
def watch_configure(
    body: WatchBody,
    cfg: Any = Depends(_cfg),
    watcher: Any = Depends(get_watcher),
) -> dict:
    audit(
        cfg.log_dir,
        "watch_configured",
        enabled=body.enabled,
        path=body.path,
        profile=body.profile,
    )
    watcher.configure(WatchConfig(
        enabled=body.enabled,
        path=body.path,
        profile=body.profile,
        languages=body.languages,
        quality_mode=body.quality_mode,
        poll_seconds=body.poll_seconds,
        move_done=body.move_done,
    ))
    return watcher.state()


@router.post("/scan")
def watch_scan(watcher: Any = Depends(get_watcher)) -> dict:
    return watcher.scan_once()
