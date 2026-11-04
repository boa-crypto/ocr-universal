"""Tests du moteur de correspondance des champs (Connecteur Hub, phase 4).

Vérifie surtout les garanties de sécurité : une similarité sémantique ne
remplit JAMAIS un champ sans validation humaine, et toute transformation
douteuse est signalée plutôt que choisie en silence.
"""
import pytest

from unocr.connectors.contract import FieldSchema, FormSchema
from unocr.connectors.mapping import (
    MappingEngine,
    MappingRule,
    _similarity,
    _to_iso_date,
    clean_text,
    normalize_key,
    to_decimal,
)


class FakeField:
    """Simule un `FieldValue` du modèle existant."""

    def __init__(self, raw=None, normalized=None, page=1):
        self.raw_value = raw
        self.normalized_value = normalized
        self.corrected_value = None
        self.confirmed_value = None
        self.page_num = page


# ─────────────────────────── normalisation ───────────────────────────

def test_normalize_key_strips_accents_and_punctuation():
    assert normalize_key("N° de connaissement") == "ndeconnaissement"
    assert normalize_key("Container_No.") == "containerno"
    assert normalize_key("  ") == ""


def test_clean_text_normalizes_spaces():
    assert clean_text("  AB\u00a0123 \n CD ") == "AB 123 CD"


# ─────────────────────────── dates ───────────────────────────

def test_iso_date_from_french_convention():
    assert _to_iso_date("12/03/2019") == ("2019-03-12",
                                          "date ambiguë « 12/03/2019 » lue en "
                                          "jj/mm/aaaa — à confirmer")


def test_iso_date_from_us_convention():
    """25/12/2019 en convention US : 25 ne peut être un mois, la lecture
    jj/mm est utilisée et signalée (on ne devine pas en silence)."""
    assert _to_iso_date("25/12/2019", dayfirst=False) == (
        "2019-12-25",
        "« 25/12/2019 » ne suit pas la convention mm/jj/aaaa : "
        "lu dans l'autre ordre — à confirmer")


def test_iso_date_unambiguous_day_first():
    """25/03/2019 : 25 ne peut pas être un mois → lecture certaine."""
    v, warn = _to_iso_date("25/03/2019")
    assert v == "2019-03-25" and warn == ""


def test_iso_date_already_iso():
    assert _to_iso_date("2019-03-12") == ("2019-03-12", "")


def test_iso_date_textual_month():
    assert _to_iso_date("12 mars 2019") == ("2019-03-12", "")


def test_iso_date_invalid_and_unknown():
    assert _to_iso_date("32/13/2019")[0] is None
    assert _to_iso_date("abc")[0] is None
    assert _to_iso_date("")[0] is None


# ─────────────────────────── nombres ───────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("1 234,56", "1234.56"),
    ("1,234.56", "1234.56"),
    ("1.234,56", "1234.56"),
    ("1234,56", "1234.56"),
    ("12 345 678,90", "12345678.90"),
    ("-1 000,00", "-1000.00"),
    ("0,00", "0.00"),
    ("-12,5", "-12.5"),
])
def test_to_decimal_formats(raw, expected):
    v, _ = to_decimal(raw)
    assert v == expected


def test_to_decimal_thousands_are_flagged():
    """Une valeur ambiguë est convertie PUIS signalée, jamais en silence."""
    v, warn = to_decimal("1.234")
    assert v == "1234"
    assert "milliers" in warn


def test_to_decimal_mixed_separators_flagged():
    v, warn = to_decimal("1.000.000,00")
    assert v == "1000000.00"
    assert "à vérifier" in warn


def test_to_decimal_empty_and_garbage():
    assert to_decimal("")[0] is None
    assert to_decimal(None)[0] is None
    assert to_decimal("abc")[0] is None


# ─────────────────────────── similarité ───────────────────────────

def test_similarity_exact_and_partial():
    assert _similarity("containerno", "containerno") == 1.0
    # vrai préfixe → 0.8 ; « container » ⊆ « container_number » → ≥ 0.55
    assert _similarity("container", "containernumber") == 0.8
    assert _similarity("container_number", "container") >= 0.55
    assert _similarity("abc", "xyz") < 0.55


# ─────────────────────────── application ───────────────────────────

def _form(*names_required):
    return FormSchema(form_id="f", fields=[
        FieldSchema(external_name=n, required=r) for n, r in names_required])


def test_explicit_rule_is_applied():
    eng = MappingEngine([MappingRule("container_number", "containerNo", "clean")])
    out = eng.apply(_form(("containerNo", True)),
                    {"container_number": FakeField("TGHU1234567")})
    assert out["containerNo"].value == "TGHU1234567"
    assert out["containerNo"].confidence == "explicit"
    assert out["containerNo"].ocr_raw == "TGHU1234567"
    assert out["containerNo"].source_page == 1


def test_exact_name_match_is_applied():
    eng = MappingEngine()
    out = eng.apply(_form(("bill_of_lading", True)),
                    {"bill_of_lading": FakeField("BL-8891")})
    assert out["bill_of_lading"].value == "BL-8891"
    assert out["bill_of_lading"].confidence == "exact"


def test_missing_source_field_is_flagged_not_filled():
    eng = MappingEngine([MappingRule("absent", "cible")])
    out = eng.apply(_form(("cible", False)), {"autre": FakeField("x")})
    assert out["cible"].value is None
    assert "absent" in out["cible"].warning


def test_required_field_without_mapping_is_flagged():
    eng = MappingEngine()
    out = eng.apply(_form(("champInconnu", True)), {"a": FakeField("1")})
    assert out["champInconnu"].value is None
    assert "obligatoire" in out["champInconnu"].warning


def test_unknown_field_is_suggested_never_filled():
    """Le garde-fou central : similarité ≠ remplissage silencieux."""
    eng = MappingEngine()
    out = eng.apply(_form(("containerNo", True)),
                    {"container_number": FakeField("TGHU1234567")})
    assert out["containerNo"].value is None
    assert out["containerNo"].confidence == "suggested"


def test_suggestions_are_marked_for_validation():
    eng = MappingEngine()
    sug = eng.suggest([FieldSchema(external_name="containerNo")],
                      {"container_number": FakeField("x")})
    assert sug and sug[0]["confidence"] == "suggested"
    assert "VALIDER" in sug[0]["reason"]


def test_transform_failure_keeps_original_and_warns():
    eng = MappingEngine([MappingRule("d", "dateField", "iso_date")])
    out = eng.apply(_form(("dateField", True)), {"d": FakeField("pas une date")})
    assert out["dateField"].value == "pas une date"     # rien n'est perdu
    assert "non reconnu" in out["dateField"].warning


def test_human_correction_wins_over_ocr():
    """La priorité du modèle existant est préservée : confirmé > corrigé."""
    fv = FakeField("valeur OCR")
    fv.corrected_value = "valeur corrigée"
    fv.confirmed_value = "valeur confirmée"
    eng = MappingEngine([MappingRule("f", "cible")])
    out = eng.apply(_form(("cible", False)), {"f": fv})
    assert out["cible"].value == "valeur confirmée"


def test_decimal_transform_end_to_end():
    eng = MappingEngine([MappingRule("poids", "grossWeight", "decimal")])
    out = eng.apply(_form(("grossWeight", True)),
                    {"poids": FakeField("1 234,56")})
    assert out["grossWeight"].value == "1234.56"


def test_rule_replaces_previous_rule_for_same_target():
    eng = MappingEngine()
    eng.add_rule(MappingRule("a", "cible"))
    eng.add_rule(MappingRule("b", "cible"))
    assert len(eng.rules) == 1 and eng.rules[0].source_field == "b"


def test_remove_rule():
    eng = MappingEngine([MappingRule("a", "cible")])
    assert eng.remove_rule("cible") is True
    assert eng.remove_rule("cible") is False


def test_serialization_roundtrip():
    eng = MappingEngine([MappingRule("a", "b", "iso_date", "note")])
    data = eng.as_dict()
    back = MappingEngine.from_dict(data)
    assert back.rules[0].source_field == "a"
    assert back.rules[0].transform == "iso_date"


def test_from_dict_ignores_unknown_keys():
    eng = MappingEngine.from_dict({"rules": [{"source_field": "a",
                                             "target_field": "b",
                                             "inconnu": 1}]})
    assert len(eng.rules) == 1


def test_apply_accepts_formschema_directly():
    """Le moteur accepte un `FormSchema` autant qu'une liste de champs."""
    eng = MappingEngine([MappingRule("container_number", "containerNo")])
    form = _form(("containerNo", True))
    out = eng.apply(form, {"container_number": FakeField("TGHU1234567")})
    assert out["containerNo"].value == "TGHU1234567"


def test_suggest_accepts_formschema_directly():
    eng = MappingEngine()
    sug = eng.suggest(_form(("container_number", True)),
                      {"container_number": FakeField("x")})
    assert sug and sug[0]["confidence"] == "suggested"


def test_apply_with_none_fields_returns_empty():
    assert MappingEngine().apply(None, {}) == {}
    assert MappingEngine().apply([], {}) == {}
