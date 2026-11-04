"""Universal Connector Hub — noyau générique de connecteurs.

Sépare strictement :
- `contract`  : contrat commun + états de santé (aucune dépendance externe)
- `registry`  : registre d'adaptateurs (ajout d'un système sans toucher au noyau)
- `mapping`   : moteur de correspondance des champs (indépendant des connecteurs)
- `forms`     : modèles de formulaires configurables sans code
- `validation`: contrôle avant transmission
- `transmission` : envoi, idempotence, reprises, rapprochement
- `secrets`   : stockage chiffré des identifiants
- `simulated` : connecteur de démonstration (système simulé local)

Aucun connecteur de ce paquet ne contacte un système externe réel sans
configuration et autorisation explicites.
"""
from .contract import (
    CAPABILITIES,
    BaseConnector,
    ConnectorCapability,
    ConnectorState,
    IntegrationMode,
    NotSupportedError,
    SubmissionResult,
)
from .registry import ConnectorRegistry

__all__ = [
    "CAPABILITIES", "BaseConnector", "ConnectorCapability", "ConnectorState",
    "IntegrationMode", "ConnectorRegistry", "NotSupportedError",
    "SubmissionResult",
]
