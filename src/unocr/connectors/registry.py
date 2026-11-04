"""Registre d'adaptateurs — ajouter un système sans toucher au noyau.

Un connecteur s'enregistre par son `connector_id`. Le registre conserve les
**instances configurées** séparément des **classes d'adaptateurs** : désactiver
un connecteur ne détruit ni sa configuration, ni son historique, ni les
transmissions déjà effectuées.
"""
from __future__ import annotations

from typing import Optional

from ..logging_setup import get_logger
from .contract import BaseConnector

log = get_logger("connectors.registry")


class ConnectorRegistry:
    """Deux niveaux : les adaptateurs disponibles et les instances configurées."""

    def __init__(self):
        self._adapters: dict[str, type[BaseConnector]] = {}
        self._instances: dict[str, BaseConnector] = {}

    # ─────────────────────── enregistrement d'adaptateurs ───────────────────────

    def register_adapter(self, cls: type[BaseConnector]) -> type[BaseConnector]:
        """Enregistre une classe d'adaptateur (utilisable comme décorateur)."""
        cid = getattr(cls, "connector_id", "")
        if not cid:
            raise ValueError(f"adaptateur sans connector_id : {cls}")
        if cid in self._adapters and self._adapters[cid] is not cls:
            log.warning("adaptateur %s remplacé", cid)
        self._adapters[cid] = cls
        log.info("adaptateur enregistré : %s (%s)", cid, cls.__name__)
        return cls

    def available_adapters(self) -> list[dict]:
        """Catalogue : ce qui peut être instancié, avant toute configuration."""
        out = []
        for cid, cls in sorted(self._adapters.items()):
            out.append({
                "connector_id": cid,
                "organization": getattr(cls, "organization", ""),
                "system_type": getattr(cls, "system_type", ""),
                "mode": getattr(cls, "mode", "simulated").value
                if hasattr(getattr(cls, "mode", "simulated"), "value")
                else str(getattr(cls, "mode", "simulated")),
                "external_api_version": getattr(cls, "external_api_version", ""),
                "capabilities": [c.value for c in getattr(cls, "capabilities", ())],
                "is_real_external_system": bool(
                    getattr(cls, "is_real_external_system", False)),
            })
        return out

    # ─────────────────────── instances configurées ───────────────────────

    def create(self, connector_id: str, settings: Optional[dict] = None) -> BaseConnector:
        cls = self._adapters.get(connector_id)
        if cls is None:
            raise KeyError(f"adaptateur inconnu : {connector_id}")
        inst = cls(settings or {})
        self._instances[connector_id] = inst
        return inst

    def add_instance(self, inst: BaseConnector) -> BaseConnector:
        self._instances[inst.connector_id] = inst
        return inst

    def get(self, connector_id: str) -> Optional[BaseConnector]:
        return self._instances.get(connector_id)

    def remove_instance(self, connector_id: str) -> bool:
        """Retire l'instance **active** sans effacer sa configuration ni son
        historique (ceux-ci vivent dans le gestionnaire de connecteurs)."""
        return self._instances.pop(connector_id, None) is not None

    def instances(self) -> list[BaseConnector]:
        return list(self._instances.values())

    # ─────────────────────── interrogations ───────────────────────

    def operational(self) -> list[BaseConnector]:
        """Connecteurs dont l'état autorise une transmission réelle."""
        from .contract import OPERATIONAL_STATES
        return [i for i in self._instances.values() if i.state in OPERATIONAL_STATES]

    def describe_all(self) -> list[dict]:
        return [i.describe() for i in self._instances.values()]

    def summary(self) -> dict:
        by_state: dict[str, int] = {}
        for inst in self._instances.values():
            by_state[inst.state.value] = by_state.get(inst.state.value, 0) + 1
        return {
            "adapters_available": len(self._adapters),
            "instances_configured": len(self._instances),
            "by_state": by_state,
            "real_external_adapters": sum(
                1 for c in self._adapters.values()
                if getattr(c, "is_real_external_system", False)),
        }


def default_registry() -> ConnectorRegistry:
    """Registre préchargé avec les adaptateurs livrés.

    Seul le connecteur simulé est fourni : aucun adaptateur vers une
    administration réelle n'est écrit sans documentation et accès autorisés.
    """
    reg = ConnectorRegistry()
    from .assisted_export import AssistedExportConnector
    from .customs import DouaneConnector
    from .simulated import SimulatedConnector

    reg.register_adapter(SimulatedConnector)
    reg.register_adapter(AssistedExportConnector)
    reg.register_adapter(DouaneConnector)
    return reg
