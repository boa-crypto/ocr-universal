"""Principal serveur pour PATCH/undo, pas identité civile ou journal signé."""
import json

import pytest
from test_field_correction_scope import ACTIONS, auth, fingerprint, perform
from test_field_correction_scope import scoped as scoped

from unocr import api
from unocr.rbac import RegistreRBAC


def events(cfg):
    return [json.loads(line) for line in (cfg.log_dir/"audit.log").read_text().splitlines()]


def act(scoped,action,who="a",kind="visible",extra=None,name="sample"):
    client,jobs,_=scoped
    job=jobs[kind]
    if action=="undo" and name=="sample":
        assert perform(client,job,"confirm",who).status_code==200
    body={"confirm":{"confirmed_value":"VALUE85"},"correct":{"corrected_value":"VALUE85"},
          "status":{"status":"ambiguous"},"undo":{"motif":"NOTE85"}}[action]
    opts={"headers":auth(who)}
    if extra=="body":
        body.update(user="SPOOF85",acteur="SPOOF85",utilisateur="SPOOF85")
    elif extra=="header":
        opts["headers"].update({"X-User":"SPOOF85","X-Actor":"SPOOF85"})
    elif extra=="query":
        opts["params"]={"user":"SPOOF85","acteur":"SPOOF85"}
    before=len(events(scoped[-1]))
    path=f"/api/jobs/{job}/fields/{name}"
    response=(client.post(path+"/undo",json=body,**opts) if action=="undo"
              else client.patch(path,json=body,**opts))
    return response,[e for e in events(scoped[-1])[before:] if e["event"] in ("field_validated","field_correction_annulee")]


def assert_success(scoped,action,response,success,actor,kind="visible"):
    assert response.status_code==200,response.text
    assert len(success)==1
    entry=success[0]
    assert (entry["acteur"],entry["job_id"],entry["field"],entry["event"])==(
        actor,scoped[1][kind],"sample","field_correction_annulee" if action=="undo" else "field_validated")
    text=json.dumps(success)
    assert "SPOOF85" not in text and "FAKE72-" not in text
    field=api.store.load_result(scoped[1][kind])["fields"]["sample"]
    assert field==response.json()["field"]
    assert field["raw_value"]=="INITIAL72" and field["normalized_value"]=="NORMAL72"


@pytest.mark.parametrize("action",ACTIONS)
@pytest.mark.parametrize("who,kind,actor",[("a","visible","a"),("b","hidden","b"),
                                         ("admin","hidden","admin"),("master","hidden","environnement")])
def test_success_names_resolved_server_principal(scoped,action,who,kind,actor):
    response,success=act(scoped,action,who,kind)
    assert_success(scoped,action,response,success,actor,kind)


@pytest.mark.parametrize("action",ACTIONS)
@pytest.mark.parametrize("extra",["body","header","query"])
def test_declarative_actor_cannot_replace_server_principal(scoped,action,extra):
    response,success=act(scoped,action,extra=extra)
    assert_success(scoped,action,response,success,"a")


@pytest.mark.parametrize("action",ACTIONS)
@pytest.mark.parametrize("token",[False,True],ids=["open","shared-token"])
def test_without_rbac_actor_is_anonymous_not_client_identity(scoped,monkeypatch,tmp_path,action,token):
    root=tmp_path/"no-rbac"
    root.mkdir()
    monkeypatch.setattr(api,"_rbac",RegistreRBAC.charger(root))
    monkeypatch.setattr(api,"_AUTH_TOKEN","FAKE72-master" if token else None)
    response,success=act(scoped,action,"master" if token else None,extra="body")
    assert_success(scoped,action,response,success,"anonyme")


@pytest.mark.parametrize("action",ACTIONS)
def test_sequential_users_do_not_inherit_previous_actor(scoped,action):
    actors=[]
    for who in ("a","b","a"):
        response,success=act(scoped,action,who,"shared")
        assert_success(scoped,action,response,success,who,"shared")
        actors.append(success[0]["acteur"])
    assert actors==["a","b","a"]


@pytest.mark.parametrize("action",ACTIONS)
@pytest.mark.parametrize("who,kind,status",[("reader","visible",403),("a","hidden",403),
                                          ("unknown","visible",401),(None,"visible",401)])
def test_denied_request_does_not_modify_or_claim_success(scoped,action,who,kind,status):
    client,jobs,cfg=scoped
    before=fingerprint(jobs[kind])
    offset=len(events(cfg))
    response=perform(client,jobs[kind],action,who)
    assert response.status_code==status
    assert fingerprint(jobs[kind])==before
    assert not [e for e in events(cfg)[offset:] if e["event"] in ("field_validated","field_correction_annulee")]


@pytest.mark.parametrize("action",ACTIONS)
def test_missing_field_has_no_attributed_phantom_success(scoped,action):
    before=fingerprint(scoped[1]["visible"])
    response,success=act(scoped,action,name="absent")
    assert response.status_code==404 and not success
    assert fingerprint(scoped[1]["visible"])==before


@pytest.mark.parametrize("action",ACTIONS)
def test_revision_conflict_does_not_emit_attributed_success(scoped,monkeypatch,action):
    client,jobs,cfg=scoped
    job=jobs["visible"]
    if action=="undo":
        assert perform(client,job,"confirm").status_code==200
    before=fingerprint(job)
    offset=len(events(cfg))
    monkeypatch.setattr(api.store,"replace_result_revision",lambda *args:False)
    def forbidden(*args):
        raise AssertionError("acteur de succès résolu après un commit refusé")
    monkeypatch.setattr(api,"_acteur",forbidden)
    response=perform(client,job,action)
    assert response.status_code==409
    assert fingerprint(job)==before
    assert not [e for e in events(cfg)[offset:] if e["event"] in ("field_validated","field_correction_annulee")]


def test_no_action_has_no_attributed_phantom_validation(scoped,monkeypatch):
    client,jobs,cfg=scoped
    offset=len(events(cfg))
    before=fingerprint(jobs["visible"])
    def forbidden(*args):
        raise AssertionError("acteur résolu pour une demande sans action")
    monkeypatch.setattr(api,"_acteur",forbidden)
    response=client.patch(f'/api/jobs/{jobs["visible"]}/fields/sample',headers=auth("a"),json={"user":"SPOOF85"})
    assert response.status_code==422
    assert fingerprint(jobs["visible"])==before and len(events(cfg))==offset
