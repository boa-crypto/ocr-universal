"""Sélection explicite et fail-closed du journal de correction pour l'annulation."""
import json

import pytest
from test_field_correction_scope import auth, fingerprint
from test_field_correction_scope import scoped as scoped

from unocr import api


@pytest.fixture
def corrected(scoped):
    client, jobs, cfg = scoped
    job = jobs["visible"]
    assert client.patch(f"/api/jobs/{job}/fields/sample",headers=auth("a"),json={"corrected_value":"VALUE82"}).status_code == 200
    return client,job,cfg


def append(cfg,entry):
    with (cfg.log_dir/"audit.log").open("a") as out:
        out.write(json.dumps(entry)+"\n")


def latest(job):
    return {k:v for k,v in api._derniere_correction(job,"sample").items() if k != "valeur_apres"}


def undos(cfg,job):
    entries=[json.loads(line) for line in (cfg.log_dir/"audit.log").read_text().splitlines() if line.startswith('{') and 'broken82' not in line]
    return [e for e in entries if isinstance(e,dict) and e.get("event")=="field_correction_annulee" and e.get("job_id")==job]


@pytest.mark.parametrize("noise", ["field_validated",["field_validated"],None,82,
                                  {"event":"note82"},{"event":"field_validated_suffix"}])
def test_non_event_json_does_not_replace_real_correction(corrected,noise):
    client,job,cfg=corrected
    original=latest(job)
    if isinstance(noise,dict):
        noise={**original,"message":"field_validated","ancienne_valeur":"WRONG82",**noise}
    append(cfg,noise)
    assert api._derniere_correction(job,"sample")["ancienne_valeur"]=="NORMAL72"
    response=client.post(f"/api/jobs/{job}/fields/sample/undo",headers=auth("a"),json={})
    assert response.status_code==200,response.text
    assert response.json()["restaure"]["valeur"]=="NORMAL72"
    assert len(undos(cfg,job))==1


@pytest.mark.parametrize("wrong", ["job","field"])
def test_other_target_is_ignored(corrected,wrong):
    _,job,cfg=corrected
    original=latest(job)
    append(cfg,{**original,"job_id":"other82" if wrong=="job" else job,
                "field":"other82" if wrong=="field" else "sample","ancienne_valeur":"WRONG82"})
    assert api._derniere_correction(job,"sample")["ancienne_valeur"]=="NORMAL72"


def test_broken_json_is_ignored(corrected):
    _,job,cfg=corrected
    with (cfg.log_dir/"audit.log").open("a") as out:
        out.write('{"event":"field_validated",broken82\n')
    assert api._derniere_correction(job,"sample")["ancienne_valeur"]=="NORMAL72"


@pytest.mark.parametrize("missing", ["ancienne_valeur","ancienne_origine","ancien_statut"])
def test_latest_incomplete_trace_blocks_undo_not_older_trace(corrected,missing):
    client,job,cfg=corrected
    entry=latest(job)
    del entry[missing]
    append(cfg,entry)
    before=fingerprint(job)
    assert api._derniere_correction(job,"sample") is None
    response=client.post(f"/api/jobs/{job}/fields/sample/undo",headers=auth("a"),json={})
    assert response.status_code==409
    assert fingerprint(job)==before and undos(cfg,job)==[]


@pytest.mark.parametrize("values", [{"confirmed":None,"corrected":None},{}])
def test_no_value_change_trace_blocks_undo(corrected,values):
    client,job,cfg=corrected
    entry={k:v for k,v in latest(job).items() if k not in {"confirmed","corrected"}}
    append(cfg,{**entry,**values})
    before=fingerprint(job)
    assert api._derniere_correction(job,"sample") is None
    assert client.post(f"/api/jobs/{job}/fields/sample/undo",headers=auth("a"),json={}).status_code==409
    assert fingerprint(job)==before and undos(cfg,job)==[]


@pytest.mark.parametrize("slot", ["confirmed_value","corrected_value"])
def test_empty_value_is_still_a_real_correction(scoped,slot):
    client,jobs,_=scoped
    job=jobs["visible"]
    assert client.patch(f"/api/jobs/{job}/fields/sample",headers=auth("a"),json={slot:""}).status_code==200
    assert api._derniere_correction(job,"sample")["valeur_apres"]==""
    assert client.post(f"/api/jobs/{job}/fields/sample/undo",headers=auth("a"),json={}).status_code==200


def test_real_status_only_request_after_correction_refuses_undo(corrected):
    client,job,cfg=corrected
    assert client.patch(f"/api/jobs/{job}/fields/sample",headers=auth("a"),json={"status":"ambiguous"}).status_code==200
    before=fingerprint(job)
    assert client.post(f"/api/jobs/{job}/fields/sample/undo",headers=auth("a"),json={}).status_code==409
    assert fingerprint(job)==before and undos(cfg,job)==[]
