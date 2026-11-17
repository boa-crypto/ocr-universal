"""Résolutions persistantes des anomalies du contrôle documentaire.

Une acceptation de risque est liée à l'empreinte exacte du constat courant.
Si les documents ou valeurs changent, l'ancienne acceptation ne s'applique plus.
Une correction ne se décrète pas : elle se constate par la disparition de
l'anomalie après modification de la source et nouveau contrôle.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .business_store import BusinessStore


class ResolutionControle(BaseModel):
    id: str
    dossier_id: str
    regle: str
    champ: str = ""
    documents: list[str] = Field(default_factory=list)
    empreinte: str
    action: str = "acceptation_risque"
    motif: str
    acteur: str
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    anomalie: dict[str, Any] = Field(default_factory=dict)


def _canonique(valeur: Any) -> str:
    return json.dumps(valeur, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def empreinte_anomalie(anomalie: dict[str, Any]) -> str:
    charge = {
        "type": anomalie.get("type", ""),
        "regle": anomalie.get("regle", ""),
        "champ": anomalie.get("champ", ""),
        "gravite": anomalie.get("gravite", ""),
        "documents": sorted(anomalie.get("documents") or []),
        "valeurs": anomalie.get("valeurs") or {},
    }
    return hashlib.sha256(_canonique(charge).encode("utf-8")).hexdigest()


def _id(dossier_id: str, empreinte: str) -> str:
    return "res_" + hashlib.sha256((dossier_id + "\0" + empreinte).encode("utf-8")).hexdigest()[:24]


def store_resolutions(cfg: Any) -> BusinessStore[ResolutionControle]:
    return BusinessStore(cfg.data_dir / "metier.sqlite3", "controle_resolution", ResolutionControle)


def appliquer_resolutions(cfg: Any, dossier_id: str, anomalies: list[dict[str, Any]]) -> dict[str, Any]:
    connues = {r.empreinte: r for r in store_resolutions(cfg).values() if r.dossier_id == dossier_id}
    actives: list[dict[str, Any]] = []
    enrichies: list[dict[str, Any]] = []
    acceptees = 0
    for anomalie in anomalies:
        copie = dict(anomalie)
        empreinte = empreinte_anomalie(copie)
        resolution = connues.get(empreinte)
        # Alias de présentation pour l'interface historique (niveau / document).
        copie.setdefault("niveau", copie.get("gravite", ""))
        copie.setdefault("document", ", ".join(copie.get("documents") or []))
        if resolution is not None and resolution.action == "acceptation_risque":
            copie["statut"] = "acceptee"
            copie["resolue"] = True
            copie["resolution"] = resolution.model_dump()
            acceptees += 1
        else:
            copie["statut"] = "active"
            copie["resolue"] = False
            actives.append(copie)
        enrichies.append(copie)
    par_gravite: dict[str, int] = {}
    for anomalie in actives:
        gravite = str(anomalie.get("gravite", ""))
        par_gravite[gravite] = par_gravite.get(gravite, 0) + 1
    bloquantes = [a for a in actives if a.get("gravite") == "blocking"]
    return {
        "total_detectees": len(anomalies),
        "total_anomalies": len(actives),
        "anomalies_acceptees": acceptees,
        "par_gravite": par_gravite,
        "anomalies_bloquantes": len(bloquantes),
        "peut_continuer": not bloquantes,
        "anomalies": enrichies,
    }


def accepter_risque(cfg: Any, dossier_id: str, anomalie: dict[str, Any], motif: str,
                    acteur: str) -> ResolutionControle:
    motif = motif.strip()
    if not motif:
        raise HTTPException(422, "Un motif est requis pour accepter le risque")
    empreinte = empreinte_anomalie(anomalie)
    identifiant = _id(dossier_id, empreinte)
    maintenant = time.time()
    with store_resolutions(cfg).transaction() as transaction:
        existante = transaction.get(identifiant)
        if existante is not None:
            return existante
        resolution = ResolutionControle(
            id=identifiant, dossier_id=dossier_id, regle=anomalie.get("regle", ""),
            champ=anomalie.get("champ", ""), documents=sorted(anomalie.get("documents") or []),
            empreinte=empreinte, motif=motif, acteur=acteur,
            created_at=maintenant, updated_at=maintenant, anomalie=dict(anomalie),
        )
        transaction[identifiant] = resolution
    return resolution


def revoquer_resolution(cfg: Any, dossier_id: str, resolution_id: str) -> ResolutionControle:
    with store_resolutions(cfg).transaction() as transaction:
        resolution = transaction.get(resolution_id)
        if resolution is None or resolution.dossier_id != dossier_id:
            raise HTTPException(404, "Résolution introuvable pour ce dossier")
        del transaction[resolution_id]
    return resolution
