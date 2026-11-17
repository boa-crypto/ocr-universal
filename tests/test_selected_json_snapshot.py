"""JSON sélectionné indépendant des fichiers et de requêtes concurrentes."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

import pytest
from test_classification_actor import patch as classify
from test_field_correction_scope import auth, fingerprint, perform
from test_field_correction_scope import scoped as scoped

from unocr import api
from unocr.models import DocumentResult, FieldValue


def selected(scoped,fields="sample",who="a",kind="visible",job=None,fmt="json"):
    client,jobs,_=scoped
    return client.get(f'/api/jobs/{job or jobs[kind]}/export/{fmt}/selected',
                      params={"fields":fields},headers=auth(who))


def expected(job,names=("sample",)):
    result=DocumentResult.model_validate(api.store.load_result(job))
    return result.model_copy(update={"fields":{k:v for k,v in result.fields.items() if k in names}}).model_dump(mode="json")


def success(response,body):
    assert response.status_code==200,response.text
    assert response.json()==body
    assert response.headers["content-type"]=="application/json"
    assert response.headers["content-disposition"]=='attachment; filename="selection.json"'
    assert response.headers["cache-control"]=="no-store"
    assert "etag" not in response.headers and "last-modified" not in response.headers


@pytest.mark.parametrize("fields",["sample","sample,sample"," absent , sample "])
def test_selection_policy_and_download_headers(scoped,fields):
    job=scoped[1]["visible"]
    before=fingerprint(job)
    success(selected(scoped,fields),expected(job))
    assert fingerprint(job)==before


@pytest.mark.parametrize("fields,status",[("unknown90",400),("",422),("   ",400),(",,",400)])
def test_empty_or_unknown_selection_retains_rejection(scoped,fields,status):
    assert selected(scoped,fields).status_code==status


def test_only_fields_are_filtered_other_sections_are_preserved(scoped):
    job=scoped[1]["visible"]
    result=api.store.load_result(job)
    result["fields"]["other"]=FieldValue(name="other",raw_value="OTHER90").model_dump(mode="json")
    result["classification"]={"category":"invoice","manual":True,"corrected_by":"a","reason":"METADATA90"}
    api.store.save_result(job,result)
    body=expected(job)
    success(selected(scoped),body)
    assert list(body["fields"])==["sample"] and body["classification"]==result["classification"]


@pytest.mark.parametrize("name",["../outside90","x/y","اسم","x\";evil"])
def test_field_name_is_not_used_as_a_filesystem_or_attachment_path(scoped,name):
    job=scoped[1]["visible"]
    result=api.store.load_result(job)
    result["fields"][name]=FieldValue(name=name,raw_value="VALUE90").model_dump(mode="json")
    api.store.save_result(job,result)
    success(selected(scoped,name),expected(job,(name,)))
    assert not (api.store.job_dir(job)/"exports").exists()


def test_existing_selected_file_is_untouched(scoped):
    job=scoped[1]["visible"]
    root=api.store.export_dir(job)/"selected"
    root.mkdir()
    path=root/"selection_sample.json"
    path.write_bytes(b"EXISTING90")
    success(selected(scoped),expected(job))
    assert path.read_bytes()==b"EXISTING90"


def test_download_does_not_call_export_directory(scoped,monkeypatch):
    body=expected(scoped[1]["visible"])
    def forbidden(*args):
        raise AssertionError("répertoire d'export appelé pour JSON sélectionné")
    monkeypatch.setattr(api.store,"export_dir",forbidden)
    success(selected(scoped),body)


@pytest.mark.parametrize("action",["correct","undo","manual","auto"])
def test_subsequent_request_reflects_new_result(scoped,action):
    client,jobs,_=scoped
    job=jobs["visible"]
    if action=="undo":
        assert perform(client,job,"confirm").status_code==200
    before=selected(scoped).json()
    if action=="manual":
        response=classify(scoped)
    elif action=="auto":
        response=client.post(f"/api/jobs/{job}/classify",headers=auth("a"))
    else:
        response=perform(client,job,action)
    assert response.status_code==200
    body=expected(job)
    assert body!=before
    success(selected(scoped),body)


@pytest.mark.parametrize("who,kind,status",[("a","hidden",403),("unknown","visible",401),(None,"visible",401)])
def test_access_denied_before_result_read(scoped,monkeypatch,who,kind,status):
    def forbidden(*args):
        raise AssertionError("résultat lu avant autorisation")
    monkeypatch.setattr(api.store,"load_result",forbidden)
    assert selected(scoped,who=who,kind=kind).status_code==status


def test_missing_job_stays_404(scoped):
    assert selected(scoped,job="missing90").status_code==404


def test_missing_result_stays_409(scoped):
    job=api.store.create_job("no-result90.txt",b"no-result90")
    assert selected(scoped,job=job.id).status_code==409


def test_unsupported_format_stays_400(scoped):
    assert selected(scoped,fmt="exe").status_code==400


def test_selected_txt_still_uses_a_file(scoped):
    job=scoped[1]["visible"]
    response=selected(scoped,fmt="txt")
    path=api.store.job_dir(job)/"exports"/"selected"/"selection_sample.txt"
    assert response.status_code==200 and path.is_file()
    assert response.content==path.read_bytes()


def test_two_http_downloads_do_not_replace_each_others_snapshot(scoped,monkeypatch):
    client,jobs,_=scoped
    job=jobs["visible"]
    before=expected(job)
    ready,release=Event(),Event()
    lock=Lock()
    calls=[]
    original=api.audit
    def interleaved(log_dir,event,**fields):
        original(log_dir,event,**fields)
        if event=="export_selected":
            with lock:
                calls.append(fields)
                first=len(calls)==1
            if first:
                ready.set()
                assert release.wait(30),"premier export non libéré"
    monkeypatch.setattr(api,"audit",interleaved)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first=pool.submit(selected,scoped)
        try:
            assert ready.wait(30),"premier export non arrivé à l'audit"
            response=client.patch(f"/api/jobs/{job}/fields/sample",headers=auth("a"),
                                  json={"confirmed_value":"AFTER90"})
            assert response.status_code==200
            after=expected(job)
            assert after!=before
            second=selected(scoped)
        finally:
            release.set()
        first_response=first.result(timeout=30)
    # Vérifier les corps avant les en-têtes pour prouver la course avec l'ancien handler.
    assert first_response.json()==before
    assert second.json()==after
    success(first_response,before)
    success(second,after)
    assert len(calls)==2 and all(c["fields"]==["sample"] for c in calls)
