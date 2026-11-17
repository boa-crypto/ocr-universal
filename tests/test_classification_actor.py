"""Classification manuelle : attribution persistée au principal serveur."""
import json

import pytest
from test_field_correction_scope import auth, fingerprint
from test_field_correction_scope import scoped as scoped

from unocr import api
from unocr.models import DocumentResult
from unocr.rbac import RegistreRBAC
from unocr.storage import JobStore

CATEGORIES=["invoice","bill_of_lading","packing_list"]


def events(cfg):
    return [json.loads(line) for line in (cfg.log_dir/"audit.log").read_text().splitlines()]


def patch(scoped,category="invoice",who="a",kind="visible",extra="body",job=None):
    client,jobs,_=scoped
    body={"category":category}
    opts={"headers":auth(who)}
    if extra=="body":
        body.update(user="SPOOF86",acteur="SPOOF86",corrected_by="SPOOF86")
    elif extra=="header":
        opts["headers"].update({"X-User":"SPOOF86","X-Actor":"SPOOF86"})
    elif extra=="query":
        opts["params"]={"user":"SPOOF86","acteur":"SPOOF86","corrected_by":"SPOOF86"}
    return client.patch(f'/api/jobs/{job or jobs[kind]}/classification',json=body,**opts)


def assert_success(scoped,response,actor,category,kind="visible",who="a"):
    client,jobs,cfg=scoped
    assert response.status_code==200,response.text
    decision=response.json()["classification"]
    assert decision["corrected_by"]==actor
    assert decision["category"]==category and decision["manual"] is True
    assert decision["evidence"]==[]
    fresh=JobStore(cfg).load_result(jobs[kind])
    assert fresh["classification"]==decision
    assert DocumentResult.model_validate(fresh).classification==decision
    read=client.get(f'/api/jobs/{jobs[kind]}/classification',headers=auth(who))
    assert read.status_code==200
    assert {k:v for k,v in read.json()["classification"].items() if k!="ts"}==decision
    assert not any(marker in json.dumps(decision) for marker in ("SPOOF86","FAKE72-"))
    return decision


@pytest.mark.parametrize("category",CATEGORIES)
@pytest.mark.parametrize("who,kind,actor",[("a","visible","a"),("b","hidden","b"),
                                         ("admin","hidden","admin"),("master","hidden","environnement")])
def test_classification_names_server_principal_in_storage_and_get(scoped,category,who,kind,actor):
    response=patch(scoped,category,who,kind)
    assert_success(scoped,response,actor,category,kind,who)


@pytest.mark.parametrize("category",CATEGORIES)
@pytest.mark.parametrize("extra",["body","header","query"])
def test_client_cannot_replace_principal(scoped,category,extra):
    assert_success(scoped,patch(scoped,category,extra=extra),"a",category)


@pytest.mark.parametrize("category",CATEGORIES)
@pytest.mark.parametrize("token",[False,True])
def test_no_rbac_names_anonymous_not_shared_token_identity(scoped,monkeypatch,tmp_path,category,token):
    root=tmp_path/"no-rbac"
    root.mkdir()
    monkeypatch.setattr(api,"_rbac",RegistreRBAC.charger(root))
    monkeypatch.setattr(api,"_AUTH_TOKEN","FAKE72-master" if token else None)
    who="master" if token else None
    assert_success(scoped,patch(scoped,category,who),"anonyme",category,who=who)


def test_sequential_accounts_do_not_reuse_previous_actor(scoped):
    for who in ("a","b","a"):
        assert_success(scoped,patch(scoped,who=who,kind="shared"),who,"invoice","shared",who)


@pytest.mark.parametrize("category",CATEGORIES)
def test_json_export_keeps_server_attribution(scoped,category):
    client,jobs,_=scoped
    decision=assert_success(scoped,patch(scoped,category),"a",category)
    response=client.get(f'/api/jobs/{jobs["visible"]}/export/json',headers=auth("a"))
    assert response.status_code==200,response.text
    assert DocumentResult.model_validate(response.json()).classification==decision


@pytest.mark.parametrize("who,kind,status",[("reader","visible",403),("a","hidden",403),
                                          ("unknown","visible",401),(None,"visible",401)])
def test_refused_has_no_mutation_or_classification_success(scoped,who,kind,status):
    _,jobs,cfg=scoped
    before=fingerprint(jobs[kind])
    offset=len(events(cfg))
    assert patch(scoped,who=who,kind=kind).status_code==status
    assert fingerprint(jobs[kind])==before
    assert not [e for e in events(cfg)[offset:] if e["event"]=="document_classified"]


@pytest.mark.parametrize("category",[""," ","invalid86"])
def test_invalid_has_no_persisted_actor_or_success(scoped,category):
    _,jobs,cfg=scoped
    before=fingerprint(jobs["visible"])
    offset=len(events(cfg))
    assert patch(scoped,category).status_code==422
    assert fingerprint(jobs["visible"])==before
    assert not [e for e in events(cfg)[offset:] if e["event"]=="document_classified"]


def test_conflict_does_not_publish_new_attribution(scoped,monkeypatch):
    _,jobs,cfg=scoped
    before=fingerprint(jobs["visible"])
    offset=len(events(cfg))
    monkeypatch.setattr(api.store,"replace_result_revision",lambda *args:False)
    assert patch(scoped).status_code==409
    assert fingerprint(jobs["visible"])==before
    assert not [e for e in events(cfg)[offset:] if e["event"]=="document_classified"]


def test_missing_job_has_no_classification_success(scoped):
    cfg=scoped[-1]
    offset=len(events(cfg))
    assert patch(scoped,job="missing86").status_code==404
    assert not [e for e in events(cfg)[offset:] if e["event"]=="document_classified"]
