"""Le PATCH ne doit pas enregistrer un statut illisible par le modèle de résultat."""
import json

import pytest
from test_field_correction_scope import auth, fingerprint
from test_field_correction_scope import scoped as scoped

from unocr import api
from unocr.models import DocumentResult, FieldStatus
from unocr.storage import JobStore

BODIES = [{}, {"confirmed_value":"CONFIRMED83"}, {"corrected_value":"CORRECTED83"}]


def patch(scoped, body):
    client,jobs,_=scoped
    return client.patch(f"/api/jobs/{jobs['visible']}/fields/sample",headers=auth("a"),json=body)


def events(scoped):
    return [json.loads(line) for line in (scoped[-1].log_dir/"audit.log").read_text().splitlines()]


@pytest.mark.parametrize("status", list(FieldStatus))
@pytest.mark.parametrize("body", BODIES)
def test_known_statuses_persist_as_strings_and_parse(scoped,status,body):
    _,jobs,cfg=scoped
    response=patch(scoped,{**body,"status":status.value})
    assert response.status_code==200,response.text
    stored=JobStore(cfg).load_result(jobs["visible"])
    assert type(stored["fields"]["sample"]["status"]) is str
    assert stored["fields"]["sample"]["status"]==status.value
    assert DocumentResult.model_validate(stored).fields["sample"].status is status
    assert response.json()["field"]==stored["fields"]["sample"]
    assert stored["fields"]["sample"]["raw_value"]=="INITIAL72"
    assert stored["fields"]["sample"]["normalized_value"]=="NORMAL72"


@pytest.mark.parametrize("status", ["VALIDATED","","validated ","unknown83",83,True,{},[],["validated"]])
@pytest.mark.parametrize("body", BODIES)
def test_unknown_status_refused_without_read_write_or_success(scoped,monkeypatch,status,body):
    _,jobs,_=scoped
    before=fingerprint(jobs["visible"])
    before_events=events(scoped)
    def forbidden(*args,**kwargs):
        raise AssertionError("stockage appelé pour un statut invalide")
    monkeypatch.setattr(api.store,"load_result_revision",forbidden)
    monkeypatch.setattr(api.store,"replace_result_revision",forbidden)
    response=patch(scoped,{**body,"status":status})
    assert response.status_code==422,response.text
    assert any(error["loc"]==["body","status"] for error in response.json()["detail"])
    assert fingerprint(jobs["visible"])==before
    assert events(scoped)==before_events


@pytest.mark.parametrize("explicit_null", [False,True],ids=["absent","null"])
@pytest.mark.parametrize("body,expected", [( {},"detected"),({"confirmed_value":""},"validated"),({"corrected_value":""},"corrected")])
def test_missing_and_null_status_keep_existing_behavior(scoped,body,expected,explicit_null):
    _,jobs,cfg=scoped
    response=patch(scoped,{**body,**({"status":None} if explicit_null else {})})
    assert response.status_code==200
    model=DocumentResult.model_validate(JobStore(cfg).load_result(jobs["visible"]))
    assert model.fields["sample"].status.value==expected
    for key,value in body.items():
        assert getattr(model.fields["sample"],key)==value


@pytest.mark.parametrize("status", list(FieldStatus))
def test_status_can_roundtrip_through_actual_json_export(scoped,status):
    client,jobs,_=scoped
    assert patch(scoped,{"status":status.value}).status_code==200
    response=client.get(f"/api/jobs/{jobs['visible']}/export/json",headers=auth("a"))
    assert response.status_code==200,response.text
    assert DocumentResult.model_validate(response.json()).fields["sample"].status is status


def test_openapi_status_enum_is_the_result_model_enum(scoped):
    client,_,_=scoped
    schema=client.get("/openapi.json").json()["components"]["schemas"]
    assert schema["FieldStatus"]["enum"]==[status.value for status in FieldStatus]
    assert {"$ref":"#/components/schemas/FieldStatus"} in schema["FieldPatch"]["properties"]["status"]["anyOf"]
