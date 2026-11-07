"""Corrections/annulations conditionnelles : ne pas écraser un résultat plus récent."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_field_correction_scope import auth
from test_field_correction_scope import scoped as scoped

from unocr import api
from unocr.storage import JobStore


def action(client, job, kind, who="a"):
    path = f"/api/jobs/{job}/fields/sample"
    if kind == "undo":
        return client.post(path+"/undo", headers=auth(who), json={})
    return client.patch(path, headers=auth(who), json={"corrected_value":"FIRST81"})


def successes(cfg, job):
    events = [json.loads(line) for line in (cfg.log_dir/"audit.log").read_text().splitlines()]
    return [e for e in events if e.get("job_id") == job and e.get("event") in {"field_validated","field_correction_annulee"}]


def seed(scoped, kind):
    client, jobs, _ = scoped
    job = jobs["visible"]
    if kind == "undo":
        assert client.patch(f"/api/jobs/{job}/fields/sample", headers=auth("a"), json={"confirmed_value":"SEED81"}).status_code == 200
    return job


@pytest.mark.parametrize("kind", ["patch","undo"])
@pytest.mark.parametrize("change", ["classification","same_field","other_field","delete"])
def test_changed_result_refused_without_lost_update(scoped, monkeypatch, kind, change):
    client, _, cfg = scoped
    job = seed(scoped, kind)
    newer = JobStore(cfg).load_result(job)
    if change == "classification":
        newer["classification"] = {"category":"invoice","manual":True}
    elif change == "same_field":
        newer["fields"]["sample"]["confirmed_value"] = "NEW81"
    elif change == "other_field":
        newer["fields"]["other81"] = {"name":"other81","raw_value":"NEW81"}
    path = api.store.job_dir(job)/"result.json"
    name = "_etat_champ" if kind == "patch" else "_derniere_correction"
    original = getattr(api, name)
    def concurrent(*args):
        before = original(*args)
        if change == "delete":
            path.unlink()
        else:
            JobStore(cfg).save_result(job, newer)
        return before
    monkeypatch.setattr(api, name, concurrent)
    before_events = successes(cfg, job)
    response = action(client, job, kind)
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "résultat modifié pendant la correction : relisez avant de réessayer"
    assert (JobStore(cfg).load_result(job) if path.exists() else None) == (None if change == "delete" else newer)
    assert successes(cfg, job) == before_events


@pytest.mark.parametrize("kind", ["patch","undo"])
@pytest.mark.parametrize("who,scope,status", [("reader","visible",403),("a","hidden",403),
                                             ("unknown","visible",401),(None,"visible",401)])
def test_guard_precedes_revision_access(scoped, monkeypatch, kind, who, scope, status):
    client, jobs, _ = scoped
    def forbidden(*args):
        raise AssertionError("accès révision avant autorisation")
    monkeypatch.setattr(api.store,"load_result_revision",forbidden)
    monkeypatch.setattr(api.store,"replace_result_revision",forbidden)
    assert action(client,jobs[scope],kind,who).status_code == status


@pytest.mark.parametrize("kind", ["patch","undo"])
def test_save_exception_does_not_emit_success(scoped, monkeypatch, kind):
    client, _, cfg = scoped
    job = seed(scoped,kind)
    before = JobStore(cfg).load_result(job)
    before_events = successes(cfg,job)
    def fail(*args):
        raise OSError("SYNTHETIC81 save failure")
    monkeypatch.setattr(api.store,"save_result",fail)
    with pytest.raises(OSError,match="SYNTHETIC81"):
        action(client,job,kind)
    assert JobStore(cfg).load_result(job) == before
    assert successes(cfg,job) == before_events


@pytest.mark.parametrize("kind", ["patch","undo"])
def test_paused_operation_cannot_erase_second_http_correction(scoped, monkeypatch, kind):
    client, _, cfg = scoped
    job = seed(scoped,kind)
    entered,release = threading.Event(),threading.Event()
    gate = threading.Lock()
    first = True
    name = "_etat_champ" if kind == "patch" else "_derniere_correction"
    original = getattr(api,name)
    def pause(*args):
        nonlocal first
        state = original(*args)
        with gate:
            wait = first
            first = False
        if wait:
            entered.set()
            assert release.wait(10),"seconde correction non terminée"
        return state
    monkeypatch.setattr(api,name,pause)
    before_events = successes(cfg,job)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(action,client,job,kind)
        try:
            assert entered.wait(10),"première opération non démarrée"
            second = client.patch(f"/api/jobs/{job}/fields/sample",headers=auth("a"),json={"confirmed_value":"SECOND81"})
            assert second.status_code == 200,second.text
        finally:
            release.set()
        response = future.result(timeout=15)
    assert response.status_code == 409
    assert JobStore(cfg).load_result(job)["fields"]["sample"] == second.json()["field"]
    after = successes(cfg,job)
    assert len(after) == len(before_events)+1 and after[-1]["confirmed"] == "SECOND81"
