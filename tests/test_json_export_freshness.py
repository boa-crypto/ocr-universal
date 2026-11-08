"""Export JSON complet : snapshot de résultat, pas fichier partagé ancien."""
from copy import deepcopy

import pytest
from test_classification_actor import patch as classify
from test_field_correction_scope import auth, fingerprint, perform
from test_field_correction_scope import scoped as scoped

from unocr import api
from unocr.models import DocumentResult


def export(scoped,who="a",kind="visible",job=None,headers=None):
    client,jobs,_=scoped
    return client.get(f'/api/jobs/{job or jobs[kind]}/export/json',headers={**auth(who),**(headers or {})})


def canonical(job):
    return DocumentResult.model_validate(api.store.load_result(job)).model_dump(mode="json")


def assert_download(response,expected):
    assert response.status_code==200,response.text
    assert response.json()==expected
    assert response.headers["content-type"]=="application/json"
    assert response.headers["content-disposition"]=='attachment; filename="result.json"'
    assert response.headers["cache-control"]=="no-store"
    assert "etag" not in response.headers and "last-modified" not in response.headers


@pytest.mark.parametrize("cached",[b'{"stale":"CACHE89"}',b'[]',b'null',b'BROKEN89',b''])
def test_existing_cached_file_is_neither_served_nor_rewritten(scoped,cached):
    job=scoped[1]["visible"]
    path=api.store.export_dir(job)/"result.json"
    path.write_bytes(cached)
    before=fingerprint(job)
    assert_download(export(scoped),canonical(job))
    assert path.read_bytes()==cached and fingerprint(job)==before


@pytest.mark.parametrize("action",["confirm","correct","status","undo","manual","auto"])
def test_export_after_edit_does_not_reuse_pre_edit_file(scoped,action):
    client,jobs,_=scoped
    job=jobs["visible"]
    if action=="undo":
        assert perform(client,job,"confirm").status_code==200
    cached=api._ensure_export(job,"json")
    previous=cached.read_bytes()
    initial=export(scoped).json()
    if action=="manual":
        response=classify(scoped)
    elif action=="auto":
        response=client.post(f"/api/jobs/{job}/classify",headers=auth("a"))
    else:
        response=perform(client,job,action)
    assert response.status_code==200,response.text
    expected=canonical(job)
    assert expected!=initial
    assert_download(export(scoped),expected)
    assert cached.read_bytes()==previous


def test_fresh_download_does_not_call_file_export_or_create_export_directory(scoped,monkeypatch):
    job=scoped[1]["visible"]
    expected=canonical(job)
    root=api.store.job_dir(job)/"exports"
    assert not root.exists()
    def forbidden(*args):
        raise AssertionError("chemin d'export fichier appelé pour JSON HTTP")
    monkeypatch.setattr(api,"_ensure_export",forbidden)
    monkeypatch.setattr(api.store,"export_dir",forbidden)
    assert_download(export(scoped),expected)
    assert not root.exists()


def test_single_loaded_snapshot_is_not_reopened_after_concurrent_save(scoped,monkeypatch):
    job=scoped[1]["visible"]
    expected=canonical(job)
    original=api.store.load_result
    calls=[]
    def interleaved(job_id):
        result=original(job_id)
        calls.append(job_id)
        updated=deepcopy(result)
        updated["fields"]["sample"].update(confirmed_value="AFTER_READ89",value_origin="confirmed",status="validated")
        api.store.save_result(job_id,updated)
        return result
    monkeypatch.setattr(api.store,"load_result",interleaved)
    response=export(scoped)
    assert response.status_code==200 and response.json()==expected
    assert calls==[job]
    assert original(job)["fields"]["sample"]["confirmed_value"]=="AFTER_READ89"


@pytest.mark.parametrize("who,kind",[("a","visible"),("b","hidden"),("reader","visible"),
                                   ("admin","hidden"),("master","hidden")])
def test_allowed_principals_receive_canonical_download(scoped,who,kind):
    assert_download(export(scoped,who,kind),canonical(scoped[1][kind]))


@pytest.mark.parametrize("who,kind,status",[("a","hidden",403),("unknown","visible",401),(None,"visible",401)])
def test_denied_precedes_result_and_cache_access(scoped,monkeypatch,who,kind,status):
    job=scoped[1][kind]
    before=fingerprint(job)
    def forbidden(*args):
        raise AssertionError("résultat/cache lu avant autorisation")
    monkeypatch.setattr(api.store,"load_result",forbidden)
    monkeypatch.setattr(api,"_ensure_export",forbidden)
    assert export(scoped,who,kind).status_code==status
    assert fingerprint(job)==before


def test_missing_job_is_404_before_loading_result(scoped,monkeypatch):
    def forbidden(*args):
        raise AssertionError("lecture d'un résultat sans job")
    monkeypatch.setattr(api.store,"load_result",forbidden)
    assert export(scoped,job="missing89").status_code==404


def test_cached_file_without_result_does_not_make_document_available(scoped):
    job=api.store.create_job("no-result89.txt",b"no-result89")
    path=api.store.export_dir(job.id)/"result.json"
    path.write_bytes(b'{"old":"CACHE89"}')
    assert export(scoped,job=job.id).status_code==409
    assert path.read_bytes()==b'{"old":"CACHE89"}'


def test_invalid_result_does_not_fall_back_to_cached_json(scoped):
    job=scoped[1]["visible"]
    path=api.store.export_dir(job)/"result.json"
    path.write_bytes(b'{"old":"CACHE89"}')
    api.store.save_result(job,{"fields":{"sample":{"name":"sample","status":"UNKNOWN89"}}})
    assert export(scoped).status_code==500
    assert path.read_bytes()==b'{"old":"CACHE89"}'


def test_other_format_retains_existing_cached_file_behavior(scoped):
    client,jobs,_=scoped
    path=api.store.export_dir(jobs["visible"])/"result.txt"
    path.write_bytes(b"OTHER_FORMAT89")
    response=client.get(f'/api/jobs/{jobs["visible"]}/export/txt',headers=auth("a"))
    assert response.status_code==200 and response.content==b"OTHER_FORMAT89"


def test_old_conditional_headers_do_not_reintroduce_cached_json(scoped):
    job=scoped[1]["visible"]
    api._ensure_export(job,"json")
    response=export(scoped,headers={"If-None-Match":'"OLD89"',"If-Modified-Since":"Thu, 01 Jan 1970 00:00:00 GMT"})
    assert_download(response,canonical(job))
