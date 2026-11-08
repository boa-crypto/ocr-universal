"""JSON groupé : réponses indépendantes, lectures par document non atomiques."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

import pytest
from test_field_correction_scope import auth, perform
from test_field_correction_scope import scoped as scoped

from unocr import api


@pytest.fixture
def batch(scoped):
    for kind,job in scoped[1].items():
        result=api.store.load_result(job)
        result["batch_test_marker"]=kind
        api.store.save_result(job,result)
    return scoped


def download(batch,ids=None,who="a",fmt="json",headers=None):
    client,jobs,_=batch
    return client.get(f"/api/batches/export/{fmt}",params={"ids":ids if ids is not None else jobs["visible"]},
                      headers={**auth(who),**(headers or {})})


def success(response,expected):
    assert response.status_code==200,response.text
    assert response.json()==expected
    assert response.headers["content-type"]=="application/json"
    assert response.headers["content-disposition"]=='attachment; filename="lot.json"'
    assert response.headers["cache-control"]=="no-store"
    assert "etag" not in response.headers and "last-modified" not in response.headers


def events(cfg):
    return [json.loads(line) for line in (cfg.log_dir/"audit.log").read_text().splitlines()]


@pytest.mark.parametrize("kinds",[["visible"],["visible","shared"],["shared","visible"],["visible","visible"]])
def test_order_and_duplicates_are_preserved_without_normalizing_raw_results(batch,kinds):
    jobs=batch[1]
    ids=[jobs[k] for k in kinds]
    success(download(batch,",".join(ids)),[api.store.load_result(j) for j in ids])


def test_empty_tokens_and_spaces_keep_existing_list_policy(batch):
    jobs=batch[1]
    success(download(batch,f', {jobs["visible"]},, {jobs["shared"]}, '),
            [api.store.load_result(jobs[k]) for k in ("visible","shared")])


def test_existing_batch_files_are_not_read_or_modified(batch):
    job=batch[1]["visible"]
    root=api.store.export_dir("batch_"+job[:60])
    path=root/"lot_OLD91.json"
    path.write_bytes(b"EXISTING91")
    before=set(root.iterdir())
    success(download(batch),[api.store.load_result(job)])
    assert set(root.iterdir())==before and path.read_bytes()==b"EXISTING91"


def test_json_does_not_call_export_directory(batch,monkeypatch):
    expected=[api.store.load_result(batch[1]["visible"])]
    def forbidden(*args):
        raise AssertionError("chemin fichier groupé appelé pour JSON")
    monkeypatch.setattr(api.store,"export_dir",forbidden)
    success(download(batch),expected)


def test_old_conditional_headers_do_not_return_file_validators(batch):
    success(download(batch,headers={"If-None-Match":'"OLD91"',"If-Modified-Since":"Thu, 01 Jan 1970 00:00:00 GMT"}),
            [api.store.load_result(batch[1]["visible"])])


@pytest.mark.parametrize("action",["confirm","undo","manual","auto"])
def test_next_download_reflects_new_result(batch,action):
    client,jobs,_=batch
    job=jobs["visible"]
    if action=="undo":
        assert perform(client,job,"confirm").status_code==200
    before=download(batch).json()
    if action=="manual":
        response=client.patch(f"/api/jobs/{job}/classification",headers=auth("a"),json={"category":"invoice"})
    elif action=="auto":
        response=client.post(f"/api/jobs/{job}/classify",headers=auth("a"))
    else:
        response=perform(client,job,action)
    assert response.status_code==200
    after=[api.store.load_result(job)]
    assert before!=after
    success(download(batch),after)


@pytest.mark.parametrize("who,status",[("a",403),("unknown",401),(None,401)])
def test_denied_list_creates_no_file_or_batch_success(batch,monkeypatch,who,status):
    _,jobs,cfg=batch
    offset=len(events(cfg))
    def forbidden(*args):
        raise AssertionError("répertoire créé pour un lot refusé")
    monkeypatch.setattr(api.store,"export_dir",forbidden)
    response=download(batch,",".join([jobs["visible"],jobs["hidden"]]),who)
    assert response.status_code==status
    assert not [e for e in events(cfg)[offset:] if e["event"]=="batch_exported"]


def test_missing_job_after_valid_job_has_no_success(batch):
    cfg=batch[-1]
    offset=len(events(cfg))
    assert download(batch,batch[1]["visible"]+",missing91").status_code==404
    assert not [e for e in events(cfg)[offset:] if e["event"]=="batch_exported"]


def test_missing_result_after_valid_job_has_no_success(batch):
    job=api.store.create_job("pending91.txt",b"pending91")
    cfg=batch[-1]
    offset=len(events(cfg))
    assert download(batch,batch[1]["visible"]+","+job.id).status_code==409
    assert not [e for e in events(cfg)[offset:] if e["event"]=="batch_exported"]


@pytest.mark.parametrize("ids,status",[("",422),(" ",400),(",,",400),("x,"*201,413)])
def test_empty_and_oversized_lists_keep_rejection(batch,ids,status):
    assert download(batch,ids).status_code==status


def test_200_repeated_entries_are_still_allowed_and_counted(batch):
    job=batch[1]["visible"]
    cfg=batch[-1]
    offset=len(events(cfg))
    success(download(batch,",".join([job]*200)),[api.store.load_result(job)]*200)
    entries=[e for e in events(cfg)[offset:] if e["event"]=="batch_exported"]
    assert len(entries)==1 and entries[0]["documents"]==200 and entries[0]["fmt"]=="json"


def test_raw_result_shape_is_not_replaced_by_document_model(batch):
    job=batch[1]["visible"]
    raw={"RAW91":{"nested":"خدمة"}}
    api.store.save_result(job,raw)
    response=download(batch)
    assert response.status_code==200 and response.json()==[raw]


def test_txt_still_uses_existing_file_response(batch):
    response=download(batch,fmt="txt")
    assert response.status_code==200 and "visible.txt" in response.text
    assert response.headers["content-type"]=="application/octet-stream"
    assert '.txt' in response.headers["content-disposition"]


def test_batch_is_a_sequence_of_per_document_reads_not_atomic_snapshot(batch,monkeypatch):
    _,jobs,_=batch
    before=api.store.load_result(jobs["visible"])
    original=api.store.load_result
    calls=[]
    def interleaved(job):
        result=original(job)
        calls.append(job)
        if len(calls)==1:
            for kind in ("visible","shared"):
                updated=original(jobs[kind])
                updated["batch_test_marker"]="AFTER_READ91"
                api.store.save_result(jobs[kind],updated)
        return result
    monkeypatch.setattr(api.store,"load_result",interleaved)
    response=download(batch,",".join([jobs["visible"],jobs["shared"]]))
    assert response.status_code==200
    assert response.json()==[before,original(jobs["shared"])]
    assert calls==[jobs["visible"],jobs["shared"]]


def test_two_http_batches_with_same_stamp_do_not_replace_each_others_body(batch,monkeypatch):
    client,jobs,_=batch
    job=jobs["visible"]
    before=[api.store.load_result(job)]
    # Reproduire deux générations dans la même seconde sans hasard d'horloge.
    monkeypatch.setattr(api.time,"strftime",lambda *args:"FIXED91")
    ready,release=Event(),Event()
    lock=Lock()
    calls=[]
    original=api.audit
    def interleaved(log_dir,event,**fields):
        original(log_dir,event,**fields)
        if event=="batch_exported":
            with lock:
                calls.append(fields)
                first=len(calls)==1
            if first:
                ready.set()
                assert release.wait(30),"premier lot non libéré"
    monkeypatch.setattr(api,"audit",interleaved)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first=pool.submit(download,batch)
        try:
            assert ready.wait(30),"premier lot non arrivé à l'audit"
            response=client.patch(f"/api/jobs/{job}/fields/sample",headers=auth("a"),json={"confirmed_value":"AFTER91"})
            assert response.status_code==200
            after=[api.store.load_result(job)]
            second=download(batch)
        finally:
            release.set()
        first_response=first.result(timeout=30)
    assert first_response.json()==before
    assert second.json()==after and after!=before
    success(first_response,before)
    success(second,after)
    assert len(calls)==2
