"""Gestionnaire de connecteurs — persistance et cycle de vie (phase 3).

Conserve, dans `data/connectors/` :
- `connectors.json` : les connecteurs configurés (état, historique de tests)
- `forms/`          : les modèles de formulaires (versionnés)
- `transmissions/`  : l'historique des envois et leurs issues

**Désactivation ≠ suppression.** `disable()` passe l'état à `disabled` et
conserve intégralement la configuration, l'historique de tests et les
transmissions déjà effectuées. Seul `delete()` efface, et il ne touche jamais
aux transmissions archivées (elles restent dans `transmissions/`).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from ..logging_setup import audit, get_logger
from .contract import BaseConnector, ConnectionTestResult, ConnectorState
from .registry import default_registry
from .secrets import SecretStore

log = get_logger("connectors.hub")


def _atomic_write_json(path: Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    tmp.replace(path)


class ConnectorRecord:
    """Configuration persistée d'un connecteur (aucun secret en clair)."""

    def __init__(self, connector_id: str, settings: Optional[dict] = None,
                 state: str = ConnectorState.UNCONFIGURED.value,
                 created_at: float = 0.0, tests: Optional[list] = None,
                 note: str = ""):
        self.connector_id = connector_id
        self.settings = settings or {}
        self.state = state
        self.created_at = created_at or time.time()
        self.tests = tests or []          # historique des tests réels
        self.note = note

    def as_dict(self) -> dict:
        return {"connector_id": self.connector_id, "settings": self.settings,
                "state": self.state, "created_at": self.created_at,
                "tests": self.tests[-20:], "note": self.note}

    @classmethod
    def from_dict(cls, d: dict) -> "ConnectorRecord":
        return cls(d.get("connector_id", ""), d.get("settings") or {},
                   d.get("state", ConnectorState.UNCONFIGURED.value),
                   d.get("created_at", 0.0), d.get("tests") or [],
                   d.get("note", ""))


class ConnectorHub:
    """Point d'entrée unique du module Connecteur Hub."""

    def __init__(self, root: Path, log_dir: Path, registry=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path(log_dir)
        self.registry = registry or default_registry()
        self.secrets = SecretStore(self.root / "secrets")
        self._config_path = self.root / "connectors.json"
        self._records: dict[str, ConnectorRecord] = {}
        self._load()

    # ─────────────────────────── persistance ───────────────────────────

    def _load(self) -> None:
        if not self._config_path.is_file():
            return
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            for cid, rec in (data.get("connectors") or {}).items():
                self._records[cid] = ConnectorRecord.from_dict(rec)
        except (json.JSONDecodeError, OSError):
            log.exception("configuration des connecteurs illisible")

    def _save(self) -> None:
        _atomic_write_json(self._config_path,
                           {"connectors": {c: r.as_dict()
                                           for c, r in self._records.items()}})

    # ─────────────────────────── cycle de vie ───────────────────────────

    def create(self, connector_id: str, settings: Optional[dict] = None,
               note: str = "") -> BaseConnector:
        """Crée (ou met à jour) une instance de connecteur configurée."""
        if connector_id not in {a["connector_id"]
                                for a in self.registry.available_adapters()}:
            raise KeyError(f"adaptateur inconnu : {connector_id}")
        rec = self._records.get(connector_id)
        if rec is None:
            rec = ConnectorRecord(connector_id, settings, note=note)
            self._records[connector_id] = rec
        else:
            if settings is not None:
                rec.settings.update(settings)
            if note:
                rec.note = note
            # reconfigurer remet à tester : une config neuve n'est plus validée
            if rec.state not in (ConnectorState.DISABLED.value,):
                rec.state = ConnectorState.TO_TEST.value

        inst = self.registry.create(connector_id, rec.settings)
        inst.configure(rec.settings)
        # l'état du record suit celui de l'instance : configure() vient de le
        # faire passer à « à tester » (sauf s'il était désactivé)
        rec.state = inst.state.value
        self._save()
        audit(self.log_dir, "connector_created", connector=connector_id)
        return inst

    def get(self, connector_id: str) -> Optional[BaseConnector]:
        """Instance active, ou reconstruction depuis la configuration."""
        inst = self.registry.get(connector_id)
        if inst is not None:
            return inst
        rec = self._records.get(connector_id)
        if rec is None:
            return None
        return self.create(connector_id, rec.settings)

    def configure(self, connector_id: str, settings: dict) -> BaseConnector:
        return self.create(connector_id, settings)

    def disable(self, connector_id: str) -> bool:
        """Désactive SANS rien supprimer (config, tests, transmissions)."""
        rec = self._records.get(connector_id)
        if rec is None:
            return False
        rec.state = ConnectorState.DISABLED.value
        self._save()
        inst = self.registry.get(connector_id)
        if inst is not None:
            inst._state = ConnectorState.DISABLED
        audit(self.log_dir, "connector_disabled", connector=connector_id)
        return True

    def enable(self, connector_id: str) -> bool:
        """Réactive un connecteur désactivé — il repart à « à tester » : un
        interrupteur ne rend jamais un connecteur opérationnel."""
        rec = self._records.get(connector_id)
        if rec is None:
            return False
        rec.state = ConnectorState.TO_TEST.value
        self._save()
        inst = self.registry.get(connector_id)
        if inst is not None:
            inst._state = ConnectorState.TO_TEST
        audit(self.log_dir, "connector_enabled", connector=connector_id)
        return True

    def delete(self, connector_id: str) -> bool:
        """Supprime la configuration et les secrets. Les transmissions
        archivées restent (preuve de ce qui a été fait)."""
        if connector_id not in self._records:
            return False
        del self._records[connector_id]
        self._save()
        self.registry.remove_instance(connector_id)
        self.secrets.delete_connector(connector_id)
        audit(self.log_dir, "connector_deleted", connector=connector_id)
        return True

    # ─────────────────────────── tests réels ───────────────────────────

    def test(self, connector_id: str) -> ConnectionTestResult:
        """Exécute le test de connexion réel et historise le résultat.

        L'état du connecteur évolue selon la preuve, jamais selon un réglage.
        """
        inst = self.get(connector_id)
        if inst is None:
            raise KeyError(f"connecteur inconnu : {connector_id}")
        rec = self._records[connector_id]
        t0 = time.perf_counter()
        try:
            result = inst.test_connection()
        except Exception as exc:
            result = ConnectionTestResult(False, f"test impossible : {exc}",
                                latency_ms=(time.perf_counter() - t0) * 1000)
        if result.latency_ms is None:
            result.latency_ms = (time.perf_counter() - t0) * 1000
        inst._record_test(result)
        rec.state = inst.state.value
        rec.tests.append(result.as_dict())
        self._save()
        audit(self.log_dir, "connector_tested", connector=connector_id,
              ok=result.ok, detail=result.detail)
        return result

    # ─────────────────────────── consultation ───────────────────────────

    def catalog(self) -> list[dict]:
        """Catalogue des adaptateurs, enrichi de l'état configuré."""
        out = []
        for a in self.registry.available_adapters():
            rec = self._records.get(a["connector_id"])
            row = dict(a)
            row["configured"] = rec is not None
            row["state"] = rec.state if rec else ConnectorState.UNCONFIGURED.value
            row["last_test"] = (rec.tests[-1] if rec and rec.tests else None)
            row["secret_keys"] = self.secrets.keys_for(a["connector_id"])
            out.append(row)
        return out

    def list_configured(self) -> list[dict]:
        out = []
        for cid, rec in self._records.items():
            adapter = next((a for a in self.registry.available_adapters()
                            if a["connector_id"] == cid), {})
            out.append({
                "connector_id": cid,
                "organization": adapter.get("organization", ""),
                "system_type": adapter.get("system_type", ""),
                "mode": adapter.get("mode", ""),
                "is_real_external_system": adapter.get(
                    "is_real_external_system", False),
                "state": rec.state,
                "created_at": rec.created_at,
                "note": rec.note,
                "last_test": rec.tests[-1] if rec.tests else None,
                "test_count": len(rec.tests),
                "secret_keys": self.secrets.keys_for(cid),
                "capabilities": adapter.get("capabilities", []),
            })
        return out

    def summary(self) -> dict:
        states: dict[str, int] = {}
        for rec in self._records.values():
            states[rec.state] = states.get(rec.state, 0) + 1
        return {
            "adapters_available": len(self.registry.available_adapters()),
            "configured": len(self._records),
            "by_state": states,
            "real_external_adapters": sum(
                1 for a in self.registry.available_adapters()
                if a["is_real_external_system"]),
            "secrets": self.secrets.describe(),
        }
