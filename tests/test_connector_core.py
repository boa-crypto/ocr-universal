"""Tests du noyau du Connecteur Hub : contrat, registre, cycle de vie.

Vérifient surtout les garanties demandées :
- un connecteur n'est « fonctionnel » qu'après un test réel ;
- désactiver ne supprime rien ;
- une capacité absente lève `NotSupportedError` au lieu d'être simulée ;
- aucun secret n'apparaît en clair.
"""
import json

import pytest

from unocr.connectors.assisted_export import AssistedExportConnector
from unocr.connectors.contract import (
    BaseConnector,
    ConnectionTestResult,
    ConnectorCapability,
    ConnectorState,
    FormSchema,
    IntegrationMode,
    NotSupportedError,
    SecretRedactor,
    SubmissionResult,
)
from unocr.connectors.hub import ConnectorHub
from unocr.connectors.registry import ConnectorRegistry, default_registry
from unocr.connectors.simulated import SIMULATED, SimulatedConnector


@pytest.fixture()
def hub(tmp_path):
    SIMULATED.healthy = True
    h = ConnectorHub(tmp_path / "connectors", tmp_path / "logs")
    yield h
    SIMULATED.healthy = True


# ─────────────────────────── contrat ───────────────────────────

def test_connector_starts_unconfigured():
    c = SimulatedConnector()
    assert c.state is ConnectorState.UNCONFIGURED


def test_configure_moves_to_to_test_not_connected():
    """Configurer ne rend JAMAIS un connecteur opérationnel."""
    c = SimulatedConnector()
    c.configure({"env": "test"})
    assert c.state is ConnectorState.TO_TEST


def test_successful_test_reaches_functional():
    c = SimulatedConnector()
    c.configure({})
    res = c.test_connection()
    assert res.ok is True
    c._record_test(res)
    assert c.state is ConnectorState.FUNCTIONAL


def test_failed_test_reaches_error():
    c = SimulatedConnector()
    c.configure({})
    c.set_healthy(False)
    res = c.test_connection()
    assert res.ok is False
    c._record_test(res)
    assert c.state is ConnectorState.ERROR
    SIMULATED.healthy = True


def test_unsupported_capability_raises():
    """Une capacité absente échoue explicitement — jamais simulée."""
    c = AssistedExportConnector()
    with pytest.raises(NotSupportedError):
        c.submit(FormSchema(form_id="x"), {}, "key")


def test_describe_hides_no_secret():
    c = SimulatedConnector({"api_key": "super-secret"})
    d = c.describe()
    blob = json.dumps(d)
    assert "super-secret" not in blob
    assert d["is_real_external_system"] is False


def test_redactor_masks_sensitive_keys():
    out = SecretRedactor.redact({"password": "x", "token": "y",
                                 "host": "example.org", "nested": {"api_key": "z"}})
    assert out["password"] == "***" and out["token"] == "***"
    assert out["host"] == "example.org"
    assert out["nested"]["api_key"] == "***"


def test_submission_result_defaults_to_pending():
    """Tant qu'il n'y a pas de preuve, on ne suppose pas l'enregistrement."""
    r = SubmissionResult(False)
    assert r.pending_confirmation is True and r.accepted is False


# ─────────────────────────── registre ───────────────────────────

def test_default_registry_has_two_adapters():
    reg = default_registry()
    ids = {a["connector_id"] for a in reg.available_adapters()}
    assert ids == {"demo_simulated", "assisted_export"}


def test_registry_has_no_real_external_adapter():
    """Aucun adaptateur vers une administration réelle n'est livré sans
    documentation et accès autorisés."""
    reg = default_registry()
    assert all(not a["is_real_external_system"]
               for a in reg.available_adapters())


def test_registering_new_adapter_needs_no_core_change():
    """Ajouter un système = enregistrer une classe. Le noyau n'est pas touché."""

    class MyConnector(BaseConnector):
        connector_id = "my_system"
        organization = "Mon organisme"
        system_type = "erp"
        mode = IntegrationMode.API
        is_real_external_system = True
        capabilities = (ConnectorCapability.TEST_CONNECTION,)

        def test_connection(self):
            return ConnectionTestResult(True, "ok")

    reg = default_registry()
    reg.register_adapter(MyConnector)
    assert "my_system" in {a["connector_id"] for a in reg.available_adapters()}
    inst = reg.create("my_system")
    assert inst.test_connection().ok is True


def test_registry_rejects_adapter_without_id():
    class Bad(BaseConnector):
        pass

    with pytest.raises(ValueError):
        ConnectorRegistry().register_adapter(Bad)


def test_registry_operational_only_after_real_test():
    reg = ConnectorRegistry()
    inst = SimulatedConnector()
    reg.add_instance(inst)
    assert reg.operational() == []
    inst.configure({})
    inst._record_test(inst.test_connection())
    assert inst in reg.operational()


# ─────────────────────────── cycle de vie (hub) ───────────────────────────

def test_create_then_test_reaches_functional(hub):
    hub.create("demo_simulated")
    assert hub.get("demo_simulated").state is ConnectorState.TO_TEST
    assert hub.test("demo_simulated").ok is True
    assert hub.get("demo_simulated").state is ConnectorState.FUNCTIONAL


def test_reconfigure_resets_to_to_test(hub):
    """Une configuration modifiée doit être retestée : pas de état figé."""
    hub.create("demo_simulated")
    hub.test("demo_simulated")
    assert hub.get("demo_simulated").state is ConnectorState.FUNCTIONAL
    hub.configure("demo_simulated", {"env": "prod"})
    assert hub.get("demo_simulated").state is ConnectorState.TO_TEST


def test_disable_keeps_config_and_history(hub):
    hub.create("demo_simulated", {"env": "test"}, note="essai")
    hub.test("demo_simulated")
    hub.disable("demo_simulated")

    assert hub.get("demo_simulated").state is ConnectorState.DISABLED
    rows = {r["connector_id"]: r for r in hub.list_configured()}
    assert rows["demo_simulated"]["state"] == "disabled"
    assert rows["demo_simulated"]["test_count"] == 1     # historique conservé

    # la configuration est toujours là après rechargement
    hub2 = ConnectorHub(hub.root, hub.log_dir)
    rec = hub2._records["demo_simulated"]
    assert rec.settings["env"] == "test" and rec.note == "essai"


def test_disabled_connector_does_not_change_state_on_test(hub):
    hub.create("demo_simulated")
    hub.disable("demo_simulated")
    hub.test("demo_simulated")
    assert hub.get("demo_simulated").state is ConnectorState.DISABLED


def test_enable_returns_to_to_test(hub):
    hub.create("demo_simulated")
    hub.test("demo_simulated")
    hub.disable("demo_simulated")
    hub.enable("demo_simulated")
    assert hub.get("demo_simulated").state is ConnectorState.TO_TEST


def test_delete_removes_config_and_secrets(hub):
    hub.create("demo_simulated")
    hub.secrets.set("demo_simulated", "token", "secret-value")
    hub.delete("demo_simulated")
    assert "demo_simulated" not in hub._records
    assert hub.secrets.keys_for("demo_simulated") == []


def test_unknown_connector_is_rejected(hub):
    with pytest.raises(KeyError):
        hub.create("nexiste_pas")


def test_catalog_reports_state_and_secret_names(hub):
    hub.create("demo_simulated")
    hub.secrets.set("demo_simulated", "api_key", "valeur-secrète")
    rows = {r["connector_id"]: r for r in hub.catalog()}
    assert rows["demo_simulated"]["configured"] is True
    assert rows["demo_simulated"]["secret_keys"] == ["api_key"]
    # la valeur ne fuite pas
    assert "valeur-secrète" not in json.dumps(rows)


def test_summary_counts_states(hub):
    hub.create("demo_simulated")
    hub.create("assisted_export")
    s = hub.summary()
    assert s["configured"] == 2
    assert s["adapters_available"] == 2
    assert s["real_external_adapters"] == 0


# ─────────────────────────── connecteur simulé ───────────────────────────

def test_simulated_submit_returns_reference():
    c = SimulatedConnector()
    form = c.discover_forms()[0]
    payload = {"containerNo": "TGHU1234567", "bl_reference": "BL-1",
               "grossWeight": "1000.00"}
    out = c.submit(form, payload, "key-1")
    assert out.accepted is True
    assert out.pending_confirmation is False      # preuve obtenue
    assert out.reference and out.reference.startswith("DEMO-")


def test_simulated_submit_reports_validation_errors():
    c = SimulatedConnector()
    form = c.discover_forms()[0]
    out = c.submit(form, {"containerNo": "TGHU1234567"}, "key-2")
    assert out.accepted is False
    assert out.errors and any("obligatoire" in e for e in out.errors)


def test_idempotency_key_prevents_duplicate():
    c = SimulatedConnector()
    form = c.discover_forms()[0]
    payload = {"containerNo": "TGHU9999999", "bl_reference": "BL-9",
               "grossWeight": "10.00"}
    first = c.submit(form, payload, "meme-cle")
    second = c.submit(form, payload, "meme-cle")
    assert first.reference == second.reference    # pas de doublon


def test_status_and_acknowledgement():
    c = SimulatedConnector()
    form = c.discover_forms()[0]
    out = c.submit(form, {"containerNo": "TGHU1234567", "bl_reference": "BL-2",
                          "grossWeight": "1.00"}, "k3")
    st = c.get_status(out.reference)
    assert st["status"] == "accepted" and st["simulated"] is True
    ack = c.get_acknowledgement(out.reference)
    assert ack["acknowledged"] is True


def test_unknown_reference_is_not_accepted():
    c = SimulatedConnector()
    assert c.get_status("DEMO-INCONNU")["status"] == "unknown"
    assert c.get_acknowledgement("DEMO-INCONNU")["acknowledged"] is False


def test_simulated_system_failure_is_reported():
    c = SimulatedConnector()
    form = c.discover_forms()[0]
    SIMULATED.healthy = False
    out = c.submit(form, {"containerNo": "X", "bl_reference": "Y",
                          "grossWeight": "1"}, "k4")
    assert out.accepted is False and out.pending_confirmation is False
    SIMULATED.healthy = True


def test_simulated_form_schema_is_declared_not_documented():
    """Le schéma de démonstration est « déclaré » : il ne prétend pas venir
    d'un organisme réel."""
    form = SimulatedConnector().discover_forms()[0]
    assert form.source == "declared"
    assert "démonstration" in form.notes.lower()
