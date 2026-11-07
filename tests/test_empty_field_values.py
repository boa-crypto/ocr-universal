"""None seul signifie absence ; une saisie vide ne doit pas réactiver l'OCR."""
import itertools
import json

import pytest
from test_field_correction_scope import auth
from test_field_correction_scope import scoped as scoped

from unocr import api
from unocr.models import FieldValue

KEYS = ("confirmed_value", "corrected_value", "normalized_value", "raw_value")


@pytest.mark.parametrize("values", list(itertools.product([None, "", "0"], repeat=4)))
def test_value_and_audit_state_use_first_non_null_slot(values):
    fields = dict(zip(KEYS, values))
    expected = next((value for value in values if value is not None), None)
    field = FieldValue(name="synthetic76", **fields)
    assert field.value == expected
    state = api._etat_champ(field.model_dump(mode="json"))
    assert state["valeur"] == expected
    assert state["origine"] == "raw" and state["statut"] == "detected"


@pytest.mark.parametrize("slot", KEYS)
@pytest.mark.parametrize("value", ["référence", "المرجع"])
def test_nonempty_unicode_values_keep_priority(slot, value):
    fields = {key: None for key in KEYS}
    fields[slot] = value
    field = FieldValue(name="synthetic76", **fields)
    assert field.value == value
    assert api._etat_champ(fields)["valeur"] == value


def event(cfg, job, name):
    events = [json.loads(line) for line in (cfg.log_dir / "audit.log").read_text().splitlines()]
    return [e for e in events if e.get("job_id") == job and e.get("event") == name][-1]


def replace_field(job, **values):
    result = api.store.load_result(job)
    result["fields"]["sample"].update(values)
    api.store.save_result(job, result)


@pytest.mark.parametrize("slot", ["confirmed_value", "corrected_value"])
@pytest.mark.parametrize("value", ["", "0"])
@pytest.mark.parametrize("normalized", [None, "NORMAL76"])
def test_single_correction_cycle_preserves_empty_and_zero(scoped, slot, value, normalized):
    client, jobs, cfg = scoped
    job = jobs["visible"]
    replace_field(job, normalized_value=normalized, confirmed_value=None, corrected_value=None)
    before = api.store.load_result(job)
    path = f"/api/jobs/{job}/fields/sample"
    response = client.patch(path, headers=auth("a"), json={slot: value})
    assert response.status_code == 200
    stored = api.store.load_result(job)["fields"]["sample"]
    assert stored[slot] == value and FieldValue.model_validate(stored).value == value
    trace = event(cfg, job, "field_validated")
    assert trace["ancienne_valeur"] == (normalized if normalized is not None else "INITIAL72")
    assert trace["confirmed" if slot == "confirmed_value" else "corrected"] == value
    assert api._derniere_correction(job, "sample")["valeur_apres"] == value
    undone = client.post(path + "/undo", headers=auth("a"), json={})
    assert undone.status_code == 200, undone.text
    assert undone.json()["restaure"]["valeur"] == trace["ancienne_valeur"]
    assert api.store.load_result(job) == before
    trace_undo = event(cfg, job, "field_correction_annulee")
    assert trace_undo["valeur_annulee"] == value
    assert trace_undo["valeur_restauree"] == trace["ancienne_valeur"]
    assert client.post(path + "/undo", headers=auth("a"), json={}).status_code == 409


@pytest.mark.parametrize("old_slot", ["confirmed_value", "corrected_value"])
@pytest.mark.parametrize("new_slot", ["confirmed_value", "corrected_value"])
def test_audit_does_not_replace_previous_manual_empty_with_ocr(scoped, old_slot, new_slot):
    client, jobs, cfg = scoped
    job = jobs["visible"]
    replace_field(job, **{old_slot: ""})
    response = client.patch(f"/api/jobs/{job}/fields/sample", headers=auth("a"), json={new_slot: "NEW76"})
    assert response.status_code == 200
    assert event(cfg, job, "field_validated")["ancienne_valeur"] == ""


@pytest.mark.parametrize("body,expected", [
    ({"confirmed_value": "", "corrected_value": "OTHER76"}, ""),
    ({"corrected_value": ""}, ""), ({"confirmed_value": ""}, ""),
])
def test_latest_trace_preserves_empty_in_priority(scoped, body, expected):
    client, jobs, _ = scoped
    job = jobs["visible"]
    assert client.patch(f"/api/jobs/{job}/fields/sample", headers=auth("a"), json=body).status_code == 200
    assert api._derniere_correction(job, "sample")["valeur_apres"] == expected


@pytest.mark.parametrize("value", ["", "0"])
def test_corrected_status_and_value_survive_json_export(scoped, value):
    client, jobs, _ = scoped
    job = jobs["visible"]
    response = client.patch(f"/api/jobs/{job}/fields/sample", headers=auth("a"), json={"corrected_value": value})
    assert response.status_code == 200
    exported = client.get(f"/api/jobs/{job}/export/json", headers=auth("a"))
    assert exported.status_code == 200, exported.text
    field = FieldValue.model_validate(exported.json()["fields"]["sample"])
    assert field.status.value == "corrected" and field.value == value
    assert field.raw_value == "INITIAL72" and field.normalized_value == "NORMAL72"
