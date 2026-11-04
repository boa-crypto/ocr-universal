"""Contrat commun des connecteurs — aucune dépendance à un système externe.

**Principe.** Chaque connecteur est un adaptateur indépendant qui implémente
`BaseConnector`. Le noyau OCR ne connaît que ce contrat : ajouter un système
externe ne demande aucune modification du moteur, du modèle de données ni des
connecteurs existants.

**Santé, pas apparence.** Un connecteur n'est jamais déclaré « connecté » parce
qu'un interrupteur est activé. `health` repose sur un **test réel**
(`test_connection`) dont le résultat est horodaté et conservé. Les états
possibles sont explicites et l'état `functional` exige une Preuve de test.

**Honnêteté des capacités.** `capabilities` liste ce que l'adaptateur sait
réallement faire. Une capacité absente n'est jamais simulée : l'interface
l'affiche comme indisponible plutôt que de proposer un bouton qui échouera.
"""
from __future__ import annotations

import time
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class IntegrationMode(str, Enum):
    """Les trois méthodes d'intégration, choisies selon les capacités réelles
    du système cible (jamais selon une préférence esthétique)."""
    API = "api"                      # Mode A — API officielle documentée
    WEB_FORM = "web_form"            # Mode B — préremplissage de formulaire web
    ASSISTED_EXPORT = "assisted_export"  # Mode C — export structuré assisté
    SIMULATED = "simulated"          # démonstration hors ligne (jamais « réel »)


class ConnectorState(str, Enum):
    """États d'un connecteur. `CONNECTED` et `FUNCTIONAL` ne sont atteignables
    qu'après un test réel, jamais par simple activation."""
    UNCONFIGURED = "unconfigured"    # créé, aucune configuration valide
    TO_TEST = "to_test"              # configuré, jamais testé
    CONNECTED = "connected"          # test de connexion réussi
    FUNCTIONAL = "functional"        # test + capacités vérifiées
    DEGRADED = "degraded"            # répond partiellement / capacités réduites
    AUTH_EXPIRED = "auth_expired"    # authentification à renouveler
    ERROR = "error"                  # dernier test en échec
    DISABLED = "disabled"            # désactivé — configuration ET historique conservés


# États qui autorisent une transmission réelle
OPERATIONAL_STATES = {ConnectorState.CONNECTED, ConnectorState.FUNCTIONAL,
                      ConnectorState.DEGRADED}


class ConnectorCapability(str, Enum):
    """Opérations du contrat. Toutes ne sont pas prises en charge par tous les
    systèmes : `capabilities` déclare ce qui est réellement disponible."""
    TEST_CONNECTION = "test_connection"
    CHECK_AUTH = "check_auth"
    FETCH_METADATA = "fetch_metadata"
    DISCOVER_FORMS = "discover_forms"       # nécessite une API qui l'autorise
    IMPORT_DATA = "import_data"
    EXPORT_DATA = "export_data"
    PREFILL_FORM = "prefill_form"
    SUBMIT = "submit"                       # soumission d'un dossier
    GET_STATUS = "get_status"
    GET_ACKNOWLEDGEMENT = "get_acknowledgement"  # accusé de réception
    LIST_ERRORS = "list_errors"
    CANCEL = "cancel"
    RESUME = "resume"


CAPABILITIES = [c.value for c in ConnectorCapability]

CAPABILITY_LABELS = {
    ConnectorCapability.TEST_CONNECTION: "Tester la connexion",
    ConnectorCapability.CHECK_AUTH: "Vérifier l'authentification",
    ConnectorCapability.FETCH_METADATA: "Récupérer les métadonnées",
    ConnectorCapability.DISCOVER_FORMS: "Découvrir les formulaires et champs",
    ConnectorCapability.IMPORT_DATA: "Importer des données",
    ConnectorCapability.EXPORT_DATA: "Exporter des données",
    ConnectorCapability.PREFILL_FORM: "Préremplir un formulaire",
    ConnectorCapability.SUBMIT: "Soumettre un dossier",
    ConnectorCapability.GET_STATUS: "Récupérer un statut",
    ConnectorCapability.GET_ACKNOWLEDGEMENT: "Récupérer un accusé de réception",
    ConnectorCapability.LIST_ERRORS: "Consulter les erreurs",
    ConnectorCapability.CANCEL: "Annuler une opération",
    ConnectorCapability.RESUME: "Reprendre une opération",
}


@dataclass
class ConnectionTestResult:
    """Résultat d'un test réel. `ok` seul ne suffit pas : `detail` explique."""
    ok: bool
    detail: str = ""
    at: float = field(default_factory=time.time)
    latency_ms: Optional[float] = None
    evidence: dict = field(default_factory=dict)   # preuve vérifiable

    def as_dict(self) -> dict:
        return {"ok": self.ok, "detail": self.detail, "at": self.at,
                "latency_ms": self.latency_ms, "evidence": self.evidence}


@dataclass
class ConnectorStatus:
    """Santé d'un connecteur, telle qu'exposée à l'interface."""
    state: ConnectorState
    last_test: Optional[ConnectionTestResult] = None
    detail: str = ""

    def as_dict(self) -> dict:
        return {"state": self.state.value,
                "last_test": self.last_test.as_dict() if self.last_test else None,
                "detail": self.detail}


@dataclass
class FieldSchema:
    """Champ attendu par un système externe.

    `external_name` est le nom **réel** du champ chez le système cible. Il ne
    doit jamais être deviné : sans documentation, il reste vide et le mapping
    ne peut pas être automatique.
    """
    external_name: str
    label: str = ""
    field_type: str = "text"        # text | number | date | amount | currency |
                                   # list | checkbox | identifier | table | reference
    required: bool = False
    max_length: Optional[int] = None
    allowed_values: list[str] = field(default_factory=list)
    format_hint: str = ""           # ex. "AAAA-MM-JJ", "2 décimales"
    source: str = "documented"      # documented | discovered | declared

    def as_dict(self) -> dict:
        return {"external_name": self.external_name, "label": self.label,
                "field_type": self.field_type, "required": self.required,
                "max_length": self.max_length, "allowed_values": self.allowed_values,
                "format_hint": self.format_hint, "source": self.source}


@dataclass
class FormSchema:
    """Structure d'un formulaire cible.

    `source` distingue un schéma **documenté** (fourni par l'organisme) d'un
    schéma **déclaré** (saisi par l'utilisateur) ou **découvert** (lu via une
    API qui l'autorise). Un formulaire sans schéma documenté ne permet pas de
    mapping automatique fiable.
    """
    form_id: str
    label: str = ""
    organization: str = ""
    fields: list[FieldSchema] = field(default_factory=list)
    source: str = "declared"        # documented | discovered | declared
    version: str = "1"
    notes: str = ""

    def as_dict(self) -> dict:
        return {"form_id": self.form_id, "label": self.label,
                "organization": self.organization,
                "fields": [f.as_dict() for f in self.fields],
                "source": self.source, "version": self.version, "notes": self.notes}


@dataclass
class SubmissionResult:
    """Règle absolue : `accepted` n'est vrai que sur preuve.

    Tant qu'aucun accusé de réception ou état vérifiable n'est revenu,
    `accepted` reste `False` et `pending_confirmation` est vrai — le système
    ne suppose jamais qu'un dossier a été enregistré.
    """
    accepted: bool
    pending_confirmation: bool = True
    reference: Optional[str] = None       # n° de dossier chez le cible
    detail: str = ""
    errors: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    at: float = field(default_factory=time.time)

    def as_dict(self) -> dict:
        return {"accepted": self.accepted,
                "pending_confirmation": self.pending_confirmation,
                "reference": self.reference, "detail": self.detail,
                "errors": self.errors, "evidence": self.evidence, "at": self.at}


class BaseConnector(ABC):
    """Interface commune. Toute méthode peut lever `NotSupportedError`."""

    #: identifiant unique, stable, sans espace (ex. "demo_simulated")
    connector_id: str = ""
    #: organisme ou éditeur du système cible
    organization: str = ""
    #: type de système (douanes, portuaire, ERP, …)
    system_type: str = ""
    #: mode d'intégration
    mode: IntegrationMode = IntegrationMode.SIMULATED
    #: version de l'interface externe (documentée)
    external_api_version: str = ""
    #: capacités réellement offertes
    capabilities: tuple[ConnectorCapability, ...] = ()
    #: ce connecteur contacte-t-il un système réel ?
    is_real_external_system: bool = False

    def __init__(self, settings: Optional[dict] = None):
        self.settings = settings or {}
        self._state = ConnectorState.UNCONFIGURED
        self._last_test: Optional[ConnectionTestResult] = None
        self._detail = ""

    # ───────────────────────────── santé ─────────────────────────────

    @property
    def state(self) -> ConnectorState:
        return self._state

    @property
    def last_test(self) -> Optional[ConnectionTestResult]:
        return self._last_test

    def status(self) -> ConnectorStatus:
        return ConnectorStatus(self._state, self._last_test, self._detail)

    def describe(self) -> dict:
        """Fiche du connecteur, exposée par l'API (aucun secret)."""
        return {
            "connector_id": self.connector_id,
            "organization": self.organization,
            "system_type": self.system_type,
            "mode": self.mode.value,
            "external_api_version": self.external_api_version,
            "capabilities": [c.value for c in self.capabilities],
            "capability_labels": [CAPABILITY_LABELS[c] for c in self.capabilities],
            "is_real_external_system": self.is_real_external_system,
            "state": self._state.value,
            "last_test": self._last_test.as_dict() if self._last_test else None,
            "detail": self._detail,
        }

    def supports(self, cap: ConnectorCapability) -> bool:
        return cap in self.capabilities

    def _record_test(self, result: ConnectionTestResult) -> ConnectionTestResult:
        """Historise un test réel et fait évoluer l'état en conséquence."""
        self._last_test = result
        if self._state is ConnectorState.DISABLED:
            return result                      # désactivé : on ne change pas l'état
        if result.ok:
            self._state = (ConnectorState.FUNCTIONAL
                           if self.supports(ConnectorCapability.SUBMIT)
                           else ConnectorState.CONNECTED)
            self._detail = result.detail
        else:
            self._state = ConnectorState.ERROR
            self._detail = result.detail
        return result

    # ─────────────── opérations du contrat (à surcharger) ───────────────

    def configure(self, settings: dict) -> None:
        """Applique une configuration. Ne doit jamais valider un accès réel."""
        self.settings = dict(settings or {})
        if self._state is ConnectorState.UNCONFIGURED:
            self._state = ConnectorState.TO_TEST
            self._detail = "configuré, non testé"

    def test_connection(self) -> ConnectionTestResult:
        """Test **réel** de la connexion. À surcharger impérativement."""
        raise NotSupportedError(self.connector_id, "test_connection")

    def check_auth(self) -> ConnectionTestResult:
        raise NotSupportedError(self.connector_id, "check_auth")

    def fetch_metadata(self) -> dict:
        raise NotSupportedError(self.connector_id, "fetch_metadata")

    def discover_forms(self) -> list[FormSchema]:
        """Découverte des formulaires. Interdite sans API l'autorisant :
        un connecteur ne doit pas prétendre deviner la structure d'un système
        auquel il n'a pas accès."""
        raise NotSupportedError(self.connector_id, "discover_forms")

    def prefill_form(self, form: FormSchema, payload: dict) -> dict:
        raise NotSupportedError(self.connector_id, "prefill_form")

    def submit(self, form: FormSchema, payload: dict,
               idempotency_key: str = "") -> SubmissionResult:
        raise NotSupportedError(self.connector_id, "submit")

    def get_status(self, reference: str) -> dict:
        raise NotSupportedError(self.connector_id, "get_status")

    def get_acknowledgement(self, reference: str) -> dict:
        raise NotSupportedError(self.connector_id, "get_acknowledgement")

    def list_errors(self, reference: str = "") -> list[dict]:
        raise NotSupportedError(self.connector_id, "list_errors")

    def cancel(self, reference: str) -> SubmissionResult:
        raise NotSupportedError(self.connector_id, "cancel")

    def resume(self, reference: str) -> SubmissionResult:
        raise NotSupportedError(self.connector_id, "resume")


class NotSupportedError(Exception):
    """Capacité non offerte par ce connecteur (normal, pas une panne)."""

    def __init__(self, connector_id: str, capability: str):
        self.connector_id = connector_id
        self.capability = capability
        super().__init__(
            f"le connecteur « {connector_id} » ne prend pas en charge "
            f"« {capability} »")


class SecretRedactor:
    """Masque les secrets dans les journaux et les réponses d'API."""

    SENSITIVE_KEYS = {"password", "passphrase", "secret", "token", "api_key",
                      "apikey", "key", "authorization", "auth", "credential",
                      "client_secret", "private_key", "salt_hex"}

    @classmethod
    def redact(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: ("***" if k.lower() in cls.SENSITIVE_KEYS
                        else cls.redact(v)) for k, v in data.items()}
        if isinstance(data, list):
            return [cls.redact(v) for v in data]
        return data
