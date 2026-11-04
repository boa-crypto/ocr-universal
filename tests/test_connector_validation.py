"""Tests de la validation avant transmission et du coffre de secrets."""
import json

import pytest

from unocr.connectors.contract import FieldSchema, FormSchema
from unocr.connectors.mapping import MappedValue, MappingEngine, MappingRule
from unocr.connectors.secrets import SecretStore
from unocr.connectors.simulated import SimulatedConnector
from unocr.connectors.validation import RiskLevel, Validator


def _form():
    return FormSchema(
        form_id="f1", label="Formulaire test", organization="Test",
        fields=[
            FieldSchema("containerNo", "N° conteneur", "identifier", True,
                        max_length=11),
            FieldSchema("grossWeight", "Poids brut", "amount", True),
            FieldSchema("arrivalDate", "Date arrivée", "date", False,
                        format_hint="AAAA-MM-JJ"),
            FieldSchema("cargoType", "Type", "list", False,
                        allowed_values=["Divers", "Frigo"]),
        ])


def _mv(value, confidence="explicit", warning=""):
    return MappedValue("x", value, confidence, "src", "", 1, "brut", "norm",
                       warning)


# ─────────────────────────── validation ───────────────────────────

def test_missing_required_field_blocks():
    v = Validator(RiskLevel.LOW).validate(
        _form(), {"containerNo": _mv(None), "grossWeight": _mv("10.00")})
    assert v.blocking is True
    assert any(i.kind == "missing_required" for i in v.errors)


def test_bad_format_blocks():
    v = Validator(RiskLevel.LOW).validate(
        _form(), {"containerNo": _mv("TGHU1234567"),
                  "grossWeight": _mv("dix kilos"),
                  "arrivalDate": _mv("12/03/2019")})
    kinds = {i.kind for i in v.errors}
    assert "bad_format" in kinds
    assert any("montant" in i.message or "amount" in i.message for i in v.errors)


def test_max_length_blocks():
    v = Validator(RiskLevel.LOW).validate(
        _form(), {"containerNo": _mv("TROP-LONG-POUR-UN-CONTENEUR"),
                  "grossWeight": _mv("1.00")})
    assert v.blocking is True


def test_value_outside_allowed_list_blocks():
    v = Validator(RiskLevel.LOW).validate(
        _form(), {"containerNo": _mv("TGHU1234567"), "grossWeight": _mv("1.00"),
                  "cargoType": _mv("Voitures")})
    assert any("valeurs autorisées" in i.message for i in v.errors)


def test_suggested_value_always_blocks():
    """Une valeur non validée par un humain ne part jamais."""
    v = Validator(RiskLevel.LOW).validate(
        _form(), {"containerNo": _mv("TGHU1234567", "suggested"),
                  "grossWeight": _mv("1.00")})
    assert v.blocking is True
    assert any(i.kind == "unvalidated_suggestion" for i in v.errors)


def test_transformation_warning_is_not_blocking():
    v = Validator(RiskLevel.LOW).validate(
        _form(), {"containerNo": _mv("TGHU1234567"), "grossWeight": _mv("1.00"),
                  "arrivalDate": _mv("2019-03-12", warning="date ambiguë")})
    assert v.blocking is False
    assert v.warnings and v.warnings[0].kind == "ambiguous"


def test_unknown_target_field_is_warned():
    v = Validator(RiskLevel.LOW).validate(
        _form(), {"containerNo": _mv("TGHU1234567"), "grossWeight": _mv("1.00"),
                  "champInconnu": _mv("x")})
    assert any(i.kind == "unknown_field" for i in v.warnings)


def test_high_risk_requires_explicit_confirmation():
    rep = Validator(RiskLevel.HIGH).validate(
        _form(), {"containerNo": _mv("TGHU1234567"), "grossWeight": _mv("1.00")})
    ok, why = rep.can_transmit()
    assert ok is False and "confirmation" in why
    rep.confirm(by="agent.douanes")
    ok, why = rep.can_transmit()
    assert ok is True


def test_low_risk_needs_no_confirmation():
    rep = Validator(RiskLevel.LOW).validate(
        _form(), {"containerNo": _mv("TGHU1234567"), "grossWeight": _mv("1.00")})
    assert rep.can_transmit()[0] is True


def test_payload_excludes_suggested_values():
    rep = Validator(RiskLevel.LOW).validate(
        _form(), {"containerNo": _mv("TGHU1234567"),
                  "grossWeight": _mv("1.00", "suggested")})
    assert "containerNo" in rep.payload()
    assert "grossWeight" not in rep.payload()


def test_traceability_records_source():
    mv = MappedValue("containerNo", "TGHU1234567", "explicit",
                     "container_number", "clean", 2, "TGHU 1234567", None, "")
    rep = Validator(RiskLevel.LOW).validate(_form(), {"containerNo": mv,
                                                     "grossWeight": _mv("1.00")})
    tr = {t["target_field"]: t for t in rep.traceability()}
    assert tr["containerNo"]["source_field"] == "container_number"
    assert tr["containerNo"]["source_page"] == 2
    assert tr["containerNo"]["ocr_raw"] == "TGHU 1234567"


def test_as_dict_is_serializable():
    rep = Validator(RiskLevel.MEDIUM).validate(
        _form(), {"containerNo": _mv("TGHU1234567"), "grossWeight": _mv("1.00")})
    blob = json.dumps(rep.as_dict())
    assert "can_transmit" in blob


# ─────────────────────────── bout en bout simulé ───────────────────────────

def test_full_flow_with_real_document_fields():
    """Du formulaire découvert à l'accusé de réception, en passant par la
    validation et la confirmation humaine."""
    c = SimulatedConnector()
    c.configure({})
    form = c.discover_forms()[0]

    class FV:
        def __init__(self, raw, page=1):
            self.raw_value = raw
            self.normalized_value = raw
            self.corrected_value = None
            self.confirmed_value = None
            self.page_num = page

    eng = MappingEngine([
        MappingRule("container_number", "containerNo", "clean"),
        MappingRule("bl_reference", "bl_reference", "clean"),
        MappingRule("gross_weight", "grossWeight", "decimal"),
    ])
    values = eng.apply(form, {
        "container_number": FV("TGHU1234567"),
        "bl_reference": FV("BL-8891"),
        "gross_weight": FV("18 450,5")})
    rep = Validator(RiskLevel.HIGH).validate(form, values)
    assert rep.can_transmit()[0] is False        # confirmation exigée
    rep.confirm(by="utilisateur.test")
    assert rep.can_transmit()[0] is True

    out = c.submit(form, rep.payload(), "cle-flow-1")
    assert out.accepted is True and out.reference
    assert c.get_acknowledgement(out.reference)["acknowledged"] is True


def test_flow_blocked_when_required_field_missing():
    """Un champ obligatoire absent empêche l'envoi, sans exception."""
    c = SimulatedConnector()
    form = c.discover_forms()[0]
    values = {"containerNo": MappedValue("containerNo", "TGHU1234567", "explicit")}
    rep = Validator(RiskLevel.HIGH).validate(form, values)
    rep.confirm()
    ok, why = rep.can_transmit()
    assert ok is False and "obligatoire" in why


# ─────────────────────────── coffre de secrets ───────────────────────────

def test_secrets_are_encrypted_at_rest(tmp_path):
    store = SecretStore(tmp_path / "secrets")
    store.set("c1", "password", "mot-de-passe-tres-secret")
    raw = (tmp_path / "secrets" / "secrets.enc").read_bytes()
    assert b"mot-de-passe-tres-secret" not in raw
    assert store.get("c1", "password") == "mot-de-passe-tres-secret"


def test_secret_keys_are_exposed_values_are_not(tmp_path):
    store = SecretStore(tmp_path / "secrets")
    store.set("c1", "api_key", "valeur")
    assert store.keys_for("c1") == ["api_key"]
    blob = json.dumps(store.describe())
    assert "valeur" not in blob


def test_secret_key_file_is_restricted(tmp_path):
    import os
    store = SecretStore(tmp_path / "secrets")
    store.set("c1", "k", "v")
    # Windows n'a pas de bits de permission POSIX : la restriction y passe
    # par l'ACL du compte, et non par un mode.
    if os.name == "posix":
        mode = oct(os.stat(tmp_path / "secrets" / "secret.key").st_mode & 0o777)
        assert mode == "0o600"


def test_secret_delete(tmp_path):
    store = SecretStore(tmp_path / "secrets")
    store.set("c1", "k", "v")
    assert store.delete("c1", "k") is True
    assert store.delete("c1", "k") is False


def test_secret_delete_connector(tmp_path):
    store = SecretStore(tmp_path / "secrets")
    store.set("c1", "k", "v")
    assert store.delete_connector("c1") is True
    assert store.keys_for("c1") == []


def test_empty_secret_is_refused(tmp_path):
    store = SecretStore(tmp_path / "secrets")
    with pytest.raises(ValueError):
        store.set("c1", "", "valeur")
    with pytest.raises(ValueError):
        store.set("c1", "k", None)


def test_corrupt_vault_returns_empty_not_crash(tmp_path):
    store = SecretStore(tmp_path / "secrets")
    store.set("c1", "k", "v")
    (tmp_path / "secrets" / "secrets.enc").write_bytes(b"donnees corrompues")
    assert store.all_for("c1") == {}      # pas d'exception, coffre vide
