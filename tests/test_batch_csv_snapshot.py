"""CSV groupé : chaque réponse garde ses octets, pas un fichier partagé."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

import pytest
from test_batch_csv_values import HEADER, download, rows, seed
from test_field_correction_scope import auth, perform
from test_field_correction_scope import scoped as scoped

from unocr import api


def success(response,retained="NORMAL72",documents=None):
    header,records=rows(response)
    assert header==HEADER
    assert [r["valeur_retenue"] for r in records]==[retained]*len(records)
    if documents is not None:
        assert [r["document"] for r in records]==documents
    assert response.headers["content-type"]=="text/csv; charset=utf-8"
    assert response.headers["content-disposition"]=='attachment; filename="lot.csv"'
    assert response.headers["cache-control"]=="no-store"
    assert "etag" not in response.headers and "last-modified" not in response.headers
    return records


def test_download_has_csv_headers_bom_and_eight_columns(scoped):
    assert len(success(download(scoped)))==1


def test_csv_does_not_call_export_directory(scoped,monkeypatch):
    def forbidden(*args):
        raise AssertionError("répertoire d'export appelé pour CSV groupé")
    monkeypatch.setattr(api.store,"export_dir",forbidden)
    success(download(scoped))


def test_existing_batch_files_are_not_rewritten_or_added(scoped):
    job=scoped[1]["visible"]
    root=api.store.export_dir("batch_"+job[:60])
    path=root/"lot_OLD93.csv"
    path.write_bytes(b"EXISTING93")
    before=set(root.iterdir())
    success(download(scoped))
    assert set(root.iterdir())==before and path.read_bytes()==b"EXISTING93"


def test_order_and_duplicates_survive_memory_serialization(scoped):
    jobs=scoped[1]
    success(download(scoped,ids=",".join(jobs[k] for k in ("shared","visible","shared"))),
            documents=["shared.txt","visible.txt","shared.txt"])


def test_unicode_quotes_and_multiline_value_round_trip(scoped):
    value='خدمة, "ÉQUIPE"\nligne2'
    seed(scoped,confirmed_value=value)
    success(download(scoped),value)


@pytest.mark.parametrize("who,kind,status",[("a","hidden",403),("unknown","visible",401),(None,"visible",401)])
def test_denied_requests_do_not_access_results_or_export_directory(scoped,monkeypatch,who,kind,status):
    def forbidden(*args):
        raise AssertionError("lecture/chemin avant autorisation")
    monkeypatch.setattr(api.store,"load_result",forbidden)
    monkeypatch.setattr(api.store,"export_dir",forbidden)
    assert download(scoped,who,kind).status_code==status


def test_missing_job_stays_404(scoped):
    assert download(scoped,ids="missing93").status_code==404


def test_missing_result_stays_409(scoped):
    job=api.store.create_job("pending93.txt",b"pending93")
    assert download(scoped,ids=job.id).status_code==409


@pytest.mark.parametrize("ids,status",[(" ",400),("x,"*201,413)])
def test_list_limits_are_unchanged(scoped,ids,status):
    assert download(scoped,ids=ids).status_code==status


def test_json_still_has_its_own_memory_response(scoped):
    client,jobs,_=scoped
    response=client.get("/api/batches/export/json",params={"ids":jobs["visible"]},headers=auth("a"))
    assert response.status_code==200 and response.json()==[api.store.load_result(jobs["visible"])]
    assert response.headers["content-type"]=="application/json"
    assert response.headers["content-disposition"]=='attachment; filename="lot.json"'


def test_txt_still_uses_file_response(scoped):
    client,jobs,_=scoped
    response=client.get("/api/batches/export/txt",params={"ids":jobs["visible"]},headers=auth("a"))
    assert response.status_code==200 and "visible.txt" in response.text
    assert response.headers["content-type"]=="application/octet-stream"


@pytest.mark.parametrize("action,retained",[("confirm","CONFIRMED72"),("undo","NORMAL72")])
def test_new_download_reflects_http_human_change(scoped,action,retained):
    client,jobs,_=scoped
    job=jobs["visible"]
    if action=="undo":
        assert perform(client,job,"confirm").status_code==200
    assert download(scoped).status_code==200
    assert perform(client,job,action).status_code==200
    success(download(scoped),retained)


def test_200_documents_still_produce_200_rows(scoped):
    job=scoped[1]["visible"]
    assert len(success(download(scoped,ids=",".join([job]*200))))==200


def test_two_http_csv_downloads_do_not_replace_each_others_body(scoped,monkeypatch):
    client,jobs,_=scoped
    job=jobs["visible"]
    before=rows(download(scoped))
    monkeypatch.setattr(api.time,"strftime",lambda *args:"FIXED93")
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
                assert release.wait(30),"premier CSV non libéré"
    monkeypatch.setattr(api,"audit",interleaved)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first=pool.submit(download,scoped)
        try:
            assert ready.wait(30),"premier CSV non arrivé à l'audit"
            response=client.patch(f"/api/jobs/{job}/fields/sample",headers=auth("a"),json={"confirmed_value":"AFTER93"})
            assert response.status_code==200
            second=download(scoped)
        finally:
            release.set()
        first_response=first.result(timeout=30)
    assert rows(first_response)==before
    assert rows(second)[1][0]["valeur_retenue"]=="AFTER93"
    success(first_response)
    success(second,"AFTER93")
    assert len(calls)==2 and all(c["fmt"]=="csv" for c in calls)
