"""Tests du gestionnaire de formulaires : 9 types, règles, versions, trames."""
import pytest

from unocr.connectors.contract import FormSchema
from unocr.connectors.forms import (
    FIELD_TYPES,
    FormBuilder,
    FormDefinition,
    FormStore,
    load_template,
)
from unocr.connectors.mapping import MappedValue, MappingEngine, MappingRule
from unocr.connectors.validation import RiskLevel, Validator


@pytest.fixture()
def store(tmp_path):
    return FormStore(tmp_path / "forms")


def _demo() -> FormDefinition:
    b = FormBuilder()
    b.add_field("containerNo", "N° de conteneur", "identifier", True)
    b.add_field("bl_reference", "Référence BL", "identifier", True)
    b.add_field("grossWeight", "Poids brut (kg)", "amount", True, decimals=2)
    return b.build("demo_declaration", "Déclaration de démonstration")


# ─────────────────────────── types de champs ───────────────────────────

def test_all_field_types_are_supported():
    """texte, nombre, date, montant, devise, liste, case, identifiant,
    tableau répétable, référence liée."""
    assert len(FIELD_TYPES) == 10
    for t in FIELD_TYPES:
        b = FormBuilder()
        b.add_field("f", "Champ", t)
        assert b.build("x").fields[0].type == t


def test_unknown_field_type_is_refused():
    b = FormBuilder()
    with pytest.raises(ValueError, match="type de champ inconnu"):
        b.add_field("f", "F", "carte_bancaire")


def test_empty_key_is_refused():
    b = FormBuilder()
    with pytest.raises(ValueError):
        b.add_field("  ", "F")


def test_duplicate_key_is_refused():
    b = FormBuilder()
    b.add_field("f", "F")
    with pytest.raises(ValueError, match="déjà défini"):
        b.add_field("f", "F bis")


def test_form_needs_at_least_one_field():
    with pytest.raises(ValueError, match="au moins un champ"):
        FormBuilder().build("vide")


# ─────────────────────────── cycle de vie ───────────────────────────

def test_create_get_list(store):
    d = store.create(_demo())
    assert store.get("demo_declaration").version == 1
    assert [f.form_id for f in store.list()] == ["demo_declaration"]
    assert d.active is True


def test_duplicate_form_id_is_refused(store):
    store.create(_demo())
    with pytest.raises(ValueError, match="déjà utilisé"):
        store.create(_demo())


def test_persistence_roundtrip(tmp_path):
    s1 = FormStore(tmp_path / "forms")
    s1.create(_demo())
    s2 = FormStore(tmp_path / "forms")
    assert s2.get("demo_declaration") is not None
    assert len(s2.get("demo_declaration").fields) == 3


def test_corrupt_store_does_not_crash(tmp_path):
    (tmp_path / "forms").mkdir()
    (tmp_path / "forms" / "forms.json").write_text("{pas du json", encoding="utf-8")
    s = FormStore(tmp_path / "forms")
    assert s.list() == []


def test_update_creates_new_version(store):
    store.create(_demo())
    v2 = store.update("demo_declaration", name="Nouveau nom")
    assert v2.version == 2
    assert v2.name == "Nouveau nom"
    assert store.get("demo_declaration").version == 2


def test_update_unknown_form_is_refused(store):
    with pytest.raises(KeyError):
        store.update("absent", name="x")


def test_disable_keeps_definition_and_history(store):
    store.create(_demo())
    d = store.disable("demo_declaration")
    assert d.active is False
    assert store.get("demo_declaration") is not None     # pas supprimé
    assert store.list() == []                            # masqué par défaut
    assert len(store.list(include_inactive=True)) == 1


def test_disable_unknown_form_is_refused(store):
    with pytest.raises(KeyError):
        store.disable("absent")


def test_delete(store):
    store.create(_demo())
    assert store.delete("demo_declaration") is True
    assert store.delete("demo_declaration") is False


# ─────────────────────────── comparaison de versions ───────────────────────────

def test_diff_detects_added_removed_changed(store):
    store.create(_demo())
    b = FormBuilder()
    b.add_field("containerNo", "N° de conteneur", "identifier", True)   # identique
    b.add_field("bl_reference", "Référence BL", "text")                # type changé
    b.add_field("newField", "Nouveau", "text")                         # ajouté
    other = b.build("demo_declaration")
    # grossWeight disparaît
    d = store.diff("demo_declaration", other)
    assert d["added"] == ["newField"]
    assert d["removed"] == ["grossWeight"]
    assert d["changed"] == ["bl_reference"]
    assert d["from_version"] == 1 and d["to_version"] == 1


def test_diff_unknown_form_is_refused(store):
    store.create(_demo())
    with pytest.raises(KeyError):
        store.diff("absent", _demo())


# ─────────────────────────── conversion en schéma ───────────────────────────

def test_schema_is_declared_not_documented():
    """Un formulaire créé ici est DÉCLARÉ : il ne prétend pas être officiel."""
    sc = _demo().schema()
    assert sc.source == "declared"
    assert isinstance(sc, FormSchema)


def test_required_fields_mark_required_schema():
    sc = _demo().schema()
    req = {f.external_name for f in sc.fields if f.required}
    assert req == {"containerNo", "bl_reference", "grossWeight"}


def test_format_hints_follow_type():
    sc = _demo().schema()
    hints = {f.external_name: f.format_hint for f in sc.fields}
    assert hints["grossWeight"] == "2 décimale(s)"
    assert "AAAA-MM-JJ" in [
        f.format_hint for f in FormBuilder()
        .add_field("d", "D", "date").build("x").schema().fields]


def test_declared_form_drives_validation(store):
    """Le schéma déclaré alimente directement le validateur."""
    store.create(_demo())
    form = store.get("demo_declaration").schema()
    values = {"containerNo": MappedValue("containerNo", "TGHU1234567", "explicit"),
              "bl_reference": MappedValue("bl_reference", "BL-1", "explicit"),
              "grossWeight": MappedValue("grossWeight", "12.50", "explicit")}
    rep = Validator(RiskLevel.LOW).validate(form, values)
    ok, why = rep.can_transmit()
    assert ok is True, why


# ─────────────────────────── trames prédéfinies ───────────────────────────

def test_customs_template_covers_required_concepts():
    t = load_template("customs_declaration")
    assert t is not None
    keys = {f.key for f in t.fields}
    for expected in ("declaration_number", "manifest_reference",
                     "bill_of_lading", "importer_name", "exporter_name",
                     "customs_broker", "tax_id", "hs_code",
                     "goods_description", "origin_country", "regime",
                     "packages", "gross_weight", "net_weight",
                     "customs_value", "currency", "containers", "seals"):
        assert expected in keys, expected


def test_customs_template_is_labelled_proposal():
    """La trame ne doit jamais être présentée comme un format officiel."""
    t = load_template("customs_declaration")
    assert ("officiel" in (t.description or "").lower()
            or "spécification" in (t.description or "").lower())
    assert t.schema().source == "declared"


def test_port_template_covers_call_concepts():
    t = load_template("port_call")
    keys = {f.key for f in t.fields}
    for expected in ("port_call_id", "vessel_name", "voyage_number",
                     "eta", "etd", "arrival_notice", "manifest_id",
                     "bill_of_lading", "previous_port", "next_port", "status",
                     "declaration_refs"):
        assert expected in keys, expected


def test_port_template_has_repeating_and_linked_types():
    t = load_template("port_call")
    types = {f.type for f in t.fields}
    assert "date" in types and "linked_reference" in types


def test_unknown_template_is_none():
    assert load_template("inconnu") is None


def test_templates_are_independent_copies():
    """Modifier une instance ne doit pas contaminer la trame suivante."""
    a = load_template("customs_declaration")
    a.fields.pop()
    b = load_template("customs_declaration")
    assert len(b.fields) == len(a.fields) + 1


# ─────────────────────────── bout en bout ───────────────────────────

def test_template_mapping_end_to_end(store):
    """Trame → mapping → validation : le circuit complet du builder."""
    store.create(load_template("port_call"))
    form = store.get("port_call").schema()
    eng = MappingEngine([
        MappingRule("vessel_name", "vessel_name"),
        MappingRule("eta", "eta"),
        MappingRule("amount", "gross_weight", "decimal"),
    ])
    values = eng.apply(form, {"vessel_name": "MSC ARIA", "eta": "12/03/2026",
                              "amount": "1 250,50"})
    assert values["vessel_name"].value == "MSC ARIA"
    rep = Validator(RiskLevel.LOW).validate(form, values)
    # il manque les champs obligatoires → transmission bloquée, sans invention
    ok, _why = rep.can_transmit()
    assert ok is False
    missing = [i for i in rep.issues if "obligatoire" in i.message]
    assert missing
