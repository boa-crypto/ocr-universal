"""Routes de gestion des profils d'extraction."""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from ..logging_setup import audit
from ..profiles import (
    AUX_VALIDATORS,
    NORMALIZERS,
    VALIDATORS,
    Profile,
    load_all_profiles,
)
from ..services.profile_store import MAX_FIELDS, MAX_PATTERN_LEN, user_profile_path
from ..config import get_config as _get_config

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def _cfg(request: Request) -> Any:
    return request.app.state.cfg


@router.get("")
def list_profiles(cfg: Any = Depends(_cfg)) -> list[dict]:
    profiles = load_all_profiles(cfg.profiles_dir, cfg.user_profiles_dir)
    return [
        {
            "name": profile.name,
            "label": profile.label,
            "description": profile.description,
            "fields": [field.key for field in profile.fields],
        }
        for profile in profiles.values()
    ]


@router.get("/catalog")
def profile_catalog() -> dict:
    """Vocabulaire accepté par l'éditeur (normalisations, validateurs)."""
    return {
        "normalizations": sorted(NORMALIZERS),
        "validators": sorted(VALIDATORS),
        "aux_validators": sorted(AUX_VALIDATORS),
    }


@router.get("/{name}")
def get_profile(name: str, cfg: Any = Depends(_cfg)) -> dict:
    """Détail complet d'un profil, pour l'éditeur."""
    profiles = load_all_profiles(cfg.profiles_dir, cfg.user_profiles_dir)
    profile = profiles.get(name)
    if profile is None:
        raise HTTPException(404, f"profil '{name}' introuvable")
    user_path = user_profile_path(cfg, name)
    return {
        "name": profile.name,
        "label": profile.label,
        "description": profile.description,
        "document_types": profile.document_types,
        "fields": [field.model_dump() for field in profile.fields],
        "relations": profile.relations,
        "consistency_checks": profile.consistency_checks,
        "export_rules": profile.export_rules,
        "source": "user" if user_path.is_file() else "builtin",
    }


@router.put("/{name}")
def put_profile(name: str, body: dict, cfg: Any = Depends(_cfg)) -> dict:
    """Crée ou met à jour un profil utilisateur, sans modifier les profils livrés."""
    payload = dict(body or {})
    payload["name"] = name
    try:
        profile = Profile.model_validate(payload)
    except Exception as exc:
        raise HTTPException(400, f"profil invalide : {exc}")

    if len(profile.fields) > MAX_FIELDS:
        raise HTTPException(400, f"trop de champs ({MAX_FIELDS} maximum)")
    for field in profile.fields:
        if not field.key:
            raise HTTPException(400, "chaque champ doit avoir une clé")
        for pattern in field.patterns:
            if len(pattern) > MAX_PATTERN_LEN:
                raise HTTPException(400, f"motif trop long ({MAX_PATTERN_LEN} caractères max)")
            try:
                re.compile(pattern)
            except re.error as exc:
                raise HTTPException(400, f"motif invalide pour « {field.key} » : {exc}")
        for validator in field.validators:
            if validator not in VALIDATORS:
                raise HTTPException(400, f"validateur inconnu : {validator}")

    path = user_profile_path(cfg, name)
    path.write_text(
        json.dumps(profile.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    audit(cfg.log_dir, "profile_saved", profile=name, fields=len(profile.fields))
    return {
        "saved": path.name,
        "fields": len(profile.fields),
        "path": str(path),
        "overrides_builtin": name in load_all_profiles(cfg.profiles_dir),
    }


@router.delete("/{name}")
def delete_profile(name: str, cfg: Any = Depends(_cfg)) -> dict:
    """Supprime un profil utilisateur. Les profils livrés ne sont pas touchés."""
    path = user_profile_path(cfg, name)
    if not path.is_file():
        raise HTTPException(404, "ce profil n'est pas un profil utilisateur")
    path.unlink()
    audit(cfg.log_dir, "profile_deleted", profile=name)
    return {"deleted": name}
