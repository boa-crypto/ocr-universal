"""Horodatage du journal attribué : concordance acteur, pas preuve de révision."""
from pathlib import Path

import pytest
from test_classification_actor import patch
from test_classification_read_consistency import DECISION, KEYS, append, prepare, read
from test_field_correction_scope import auth, fingerprint
from test_field_correction_scope import scoped as scoped

MANUAL={**DECISION,"manual":True,"corrected_by":"a"}


def attributed(job,decision=MANUAL,**overrides):
    return {"event":"document_classified","job_id":job,"ts":8888,
            **{k:decision[k] for k in KEYS},"acteur":"a",**overrides}


@pytest.mark.parametrize("actor",["b",None,""," ",0,True,[],{},["a"],"A"," a "])
def test_conflicting_or_unusable_actor_cannot_supply_timestamp(scoped,actor):
    job=prepare(scoped,MANUAL)
    append(scoped[-1],attributed(job,acteur=actor))
    before=fingerprint(job)
    assert read(scoped,job)==MANUAL
    assert fingerprint(job)==before


@pytest.mark.parametrize("actor",["a","équipe","مراجع"])
def test_matching_nonblank_manual_actor_only_adds_timestamp(scoped,actor):
    decision={**MANUAL,"corrected_by":actor}
    job=prepare(scoped,decision)
    append(scoped[-1],attributed(job,decision,acteur=actor))
    assert read(scoped,job)=={**decision,"ts":8888}


@pytest.mark.parametrize("corrected_by",["a",None,42])
def test_legacy_event_without_actor_keeps_five_field_policy(scoped,corrected_by):
    decision={**MANUAL,"corrected_by":corrected_by}
    job=prepare(scoped,decision)
    entry=attributed(job,decision)
    del entry["acteur"]
    append(scoped[-1],entry)
    assert read(scoped,job)=={**decision,"ts":8888}


def test_latest_actor_conflict_does_not_reuse_older_matching_timestamp(scoped):
    job=prepare(scoped,MANUAL)
    append(scoped[-1],attributed(job))
    append(scoped[-1],attributed(job,acteur="b",ts=8899))
    assert read(scoped,job)==MANUAL


@pytest.mark.parametrize("manual",[False,1,"true",None])
def test_attributed_event_requires_actual_manual_boolean_true(scoped,manual):
    decision={**MANUAL,"manual":manual}
    job=prepare(scoped,decision)
    append(scoped[-1],attributed(job,decision))
    assert read(scoped,job)==decision


@pytest.mark.parametrize("actor",["a",None,""])
def test_no_stored_decision_does_not_infer_actor_for_legacy_fallback(scoped,actor):
    job=prepare(scoped,None)
    append(scoped[-1],attributed(job,acteur=actor))
    assert read(scoped,job)=={k:MANUAL[k] for k in KEYS}


@pytest.mark.parametrize("present",[False,True])
def test_absent_or_null_stored_actor_does_not_match_attributed_trace(scoped,present):
    decision={**MANUAL,"corrected_by":None}
    if not present:
        del decision["corrected_by"]
    job=prepare(scoped,decision)
    append(scoped[-1],attributed(job))
    assert read(scoped,job)==decision


@pytest.mark.parametrize("who,kind,status",[("a","hidden",403),("unknown","visible",401),(None,"visible",401)])
def test_access_guard_precedes_audit_read(scoped,monkeypatch,who,kind,status):
    client,jobs,cfg=scoped
    original=Path.read_text
    def checked(path,*args,**kwargs):
        if path==cfg.log_dir/"audit.log":
            raise AssertionError("audit lu avant autorisation")
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,"read_text",checked)
    response=client.get(f'/api/jobs/{jobs[kind]}/classification',headers=auth(who))
    assert response.status_code==status


@pytest.mark.parametrize("who,kind",[("a","visible"),("b","hidden"),("admin","hidden"),("master","hidden")])
def test_new_real_http_classification_still_receives_its_timestamp(scoped,who,kind):
    client,jobs,_=scoped
    response=patch(scoped,who=who,kind=kind)
    assert response.status_code==200
    decision=response.json()["classification"]
    result=client.get(f'/api/jobs/{jobs[kind]}/classification',headers=auth(who))
    assert result.status_code==200
    payload=result.json()["classification"]
    assert isinstance(payload["ts"],(float,int))
    assert {k:v for k,v in payload.items() if k!="ts"}==decision


def test_timestamp_already_in_stored_decision_is_not_repaired_or_overwritten(scoped):
    decision={**MANUAL,"ts":"STORED88"}
    job=prepare(scoped,decision)
    append(scoped[-1],attributed(job,acteur="b"))
    assert read(scoped,job)==decision
