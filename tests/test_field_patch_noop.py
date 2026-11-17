"""Un PATCH sans action ne valide pas et ne pollue pas l'historique d'annulation."""
import json

import pytest
from test_field_correction_scope import auth, fingerprint
from test_field_correction_scope import scoped as scoped

from unocr import api
from unocr.models import FieldStatus

NO_ACTION = [{}, {"user":"DECLARED84"}, {"reason":"NOTE84"},
             {"confirmed_value":None}, {"corrected_value":None}, {"status":None},
             {"confirmed_value":None,"corrected_value":None,"status":None,"user":"DECLARED84","reason":"NOTE84"}]


def events(cfg):
    return [json.loads(line) for line in (cfg.log_dir/"audit.log").read_text().splitlines()]


def patch(client,job,body,who="a"):
    return client.patch(f"/api/jobs/{job}/fields/sample",headers=auth(who),json=body)


@pytest.mark.parametrize("body",NO_ACTION)
def test_no_action_refused_before_revision_access_without_audit(scoped,monkeypatch,body):
    client,jobs,cfg=scoped
    job=jobs["visible"]
    before,before_events=fingerprint(job),events(cfg)
    def forbidden(*args,**kwargs):
        raise AssertionError("résultat lu/écrit pour une demande sans action")
    monkeypatch.setattr(api.store,"load_result_revision",forbidden)
    monkeypatch.setattr(api.store,"replace_result_revision",forbidden)
    response=patch(client,job,body)
    assert response.status_code==422,response.text
    assert response.json()=={"detail":"aucune modification de champ fournie"}
    assert fingerprint(job)==before and events(cfg)==before_events


@pytest.mark.parametrize("slot",["confirmed_value","corrected_value"])
@pytest.mark.parametrize("body",[{}, {"reason":"NOTE84"}, {"status":None}])
def test_rejected_noop_does_not_block_existing_correction_undo(scoped,slot,body):
    client,jobs,cfg=scoped
    job=jobs["visible"]
    assert patch(client,job,{slot:"VALUE84"}).status_code==200
    before,before_events=fingerprint(job),events(cfg)
    assert patch(client,job,body).status_code==422
    assert fingerprint(job)==before and events(cfg)==before_events
    undone=client.post(f"/api/jobs/{job}/fields/sample/undo",headers=auth("a"),json={})
    assert undone.status_code==200,undone.text
    assert undone.json()["restaure"]["valeur"]=="NORMAL72"


@pytest.mark.parametrize("slot",["confirmed_value","corrected_value"])
@pytest.mark.parametrize("value",["","0"])
def test_empty_and_zero_are_explicit_actions(scoped,slot,value):
    client,jobs,cfg=scoped
    job=jobs["visible"]
    response=patch(client,job,{slot:value,"status":None})
    assert response.status_code==200
    assert response.json()["field"][slot]==value
    assert api.store.load_result(job)["fields"]["sample"][slot]==value
    assert [e for e in events(cfg) if e.get("job_id")==job and e["event"]=="field_validated"]


@pytest.mark.parametrize("status",list(FieldStatus))
def test_explicit_known_status_alone_is_still_an_action(scoped,status):
    client,jobs,_=scoped
    response=patch(client,jobs["visible"],{"status":status.value})
    assert response.status_code==200 and response.json()["field"]["status"]==status.value


@pytest.mark.parametrize("who,kind,status",[("reader","visible",403),("a","hidden",403),
                                          ("unknown","visible",401),(None,"visible",401)])
def test_authorization_still_precedes_no_action_guard(scoped,monkeypatch,who,kind,status):
    client,jobs,_=scoped
    def forbidden(*args):
        raise AssertionError("révision lue avant autorisation")
    monkeypatch.setattr(api.store,"load_result_revision",forbidden)
    assert patch(client,jobs[kind],{},who).status_code==status


def test_explicit_reconfirmation_same_value_is_not_rejected_as_noop(scoped):
    client,jobs,cfg=scoped
    job=jobs["visible"]
    body={"confirmed_value":"VALUE84"}
    assert patch(client,job,body).status_code==200
    assert patch(client,job,body).status_code==200
    assert len([e for e in events(cfg) if e.get("job_id")==job and e["event"]=="field_validated"])==2
