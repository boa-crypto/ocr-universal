"""Acteur du nouvel audit manuel : principal HTTP, pas déduction du résultat."""
import json

import pytest
from test_classification_actor import CATEGORIES, assert_success, events, patch
from test_field_correction_scope import auth, fingerprint
from test_field_correction_scope import scoped as scoped

from unocr import api, classification
from unocr.classification import ClassificationResult, consigne_classification
from unocr.rbac import RegistreRBAC
from unocr.storage import JobStore

BASE_KEYS={"ts","event","job_id","category","confidence","classifier_version",
           "needs_review","manual","evidence_count"}


def audit_success(scoped,category="invoice",who="a",kind="visible",actor="a",extra="body"):
    cfg=scoped[-1]
    offset=len(events(cfg))
    response=patch(scoped,category,who,kind,extra)
    decision=assert_success(scoped,response,actor,category,kind,who)
    entries=[e for e in events(cfg)[offset:] if e["event"]=="document_classified"]
    assert len(entries)==1
    entry=entries[0]
    assert set(entry)==BASE_KEYS|{"acteur"}
    assert entry["acteur"]==decision["corrected_by"]==actor
    assert entry["job_id"]==scoped[1][kind]
    for key in ("category","confidence","classifier_version","needs_review","manual"):
        assert entry[key]==decision[key]
    assert entry["evidence_count"]==len(decision["evidence"])
    assert not any(s in json.dumps(entry) for s in ("SPOOF86","FAKE72-"))
    return entry


@pytest.mark.parametrize("category",CATEGORIES)
@pytest.mark.parametrize("who,kind,actor",[("a","visible","a"),("b","hidden","b"),
                                         ("admin","hidden","admin"),("master","hidden","environnement")])
def test_manual_event_names_same_server_actor_as_persisted_result(scoped,category,who,kind,actor):
    audit_success(scoped,category,who,kind,actor)


@pytest.mark.parametrize("extra",["body","header","query"])
def test_declared_identity_does_not_replace_audit_actor(scoped,extra):
    audit_success(scoped,extra=extra)


@pytest.mark.parametrize("token",[False,True])
def test_open_or_shared_token_audit_is_anonymous(scoped,monkeypatch,tmp_path,token):
    root=tmp_path/"no-rbac"
    root.mkdir()
    monkeypatch.setattr(api,"_rbac",RegistreRBAC.charger(root))
    monkeypatch.setattr(api,"_AUTH_TOKEN","FAKE72-master" if token else None)
    audit_success(scoped,who="master" if token else None,actor="anonyme")


def test_sequential_audit_actors_follow_requests(scoped):
    assert [audit_success(scoped,who=who,kind="shared",actor=who)["acteur"]
            for who in ("a","b","a")]==["a","b","a"]


@pytest.mark.parametrize("who,kind,status",[("reader","visible",403),("a","hidden",403),
                                          ("unknown","visible",401),(None,"visible",401)])
def test_denied_has_no_attributed_success_or_mutation(scoped,who,kind,status):
    _,jobs,cfg=scoped
    before=fingerprint(jobs[kind])
    offset=len(events(cfg))
    assert patch(scoped,who=who,kind=kind).status_code==status
    assert fingerprint(jobs[kind])==before
    assert not [e for e in events(cfg)[offset:] if e["event"]=="document_classified"]


@pytest.mark.parametrize("category",[""," ","invalid87"])
def test_invalid_category_has_no_attributed_success(scoped,category):
    _,jobs,cfg=scoped
    before=fingerprint(jobs["visible"])
    offset=len(events(cfg))
    assert patch(scoped,category).status_code==422
    assert fingerprint(jobs["visible"])==before
    assert not [e for e in events(cfg)[offset:] if e["event"]=="document_classified"]


def test_conflict_has_no_attributed_success(scoped,monkeypatch):
    _,jobs,cfg=scoped
    before=fingerprint(jobs["visible"])
    offset=len(events(cfg))
    monkeypatch.setattr(api.store,"replace_result_revision",lambda *args:False)
    assert patch(scoped).status_code==409
    assert fingerprint(jobs["visible"])==before
    assert not [e for e in events(cfg)[offset:] if e["event"]=="document_classified"]


def test_missing_job_has_no_attributed_success(scoped):
    cfg=scoped[-1]
    offset=len(events(cfg))
    assert patch(scoped,job="missing87").status_code==404
    assert not [e for e in events(cfg)[offset:] if e["event"]=="document_classified"]


@pytest.mark.parametrize("manual_result,manual_arg",[(False,False),(True,True),(False,True),(True,False)])
def test_helper_without_explicit_actor_does_not_infer_identity(tmp_path,manual_result,manual_arg):
    result=ClassificationResult(category="invoice",label="Invoice",confidence=0.4,
                                manual=manual_result,corrected_by="DECLARED87")
    consigne_classification(tmp_path,"job87",result,manuel=manual_arg)
    entry=json.loads((tmp_path/"audit.log").read_text())
    assert set(entry)==BASE_KEYS
    assert entry["manual"] is (manual_result or manual_arg)
    assert "DECLARED87" not in json.dumps(entry)


def test_helper_explicit_actor_is_caller_input_not_authenticated_identity(tmp_path):
    result=ClassificationResult(category="invoice",label="Invoice",confidence=0.4,
                                manual=True,corrected_by="DECLARED87")
    consigne_classification(tmp_path,"job87",result,acteur="CALLER87")
    entry=json.loads((tmp_path/"audit.log").read_text())
    assert set(entry)==BASE_KEYS|{"acteur"} and entry["acteur"]=="CALLER87"
    assert result.corrected_by=="DECLARED87"


def test_automatic_http_audit_keeps_existing_shape_without_actor(scoped):
    client,jobs,cfg=scoped
    offset=len(events(cfg))
    response=client.post(f'/api/jobs/{jobs["visible"]}/classify',headers=auth("a"))
    assert response.status_code==200,response.text
    entries=[e for e in events(cfg)[offset:] if e["event"]=="document_classified"]
    assert len(entries)==1 and set(entries[0])==BASE_KEYS
    assert entries[0]["manual"] is False


def test_attributed_audit_runs_after_result_is_persisted(scoped,monkeypatch):
    _,jobs,cfg=scoped
    original=classification.audit
    seen=[]
    def checked(log_dir,event,**fields):
        assert event=="document_classified"
        stored=JobStore(cfg).load_result(jobs["visible"])["classification"]
        assert stored["corrected_by"]==fields["acteur"]=="a"
        assert stored["category"]==fields["category"]=="invoice"
        seen.append(event)
        return original(log_dir,event,**fields)
    monkeypatch.setattr(classification,"audit",checked)
    audit_success(scoped)
    assert seen==["document_classified"]
