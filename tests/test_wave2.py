"""Tests des fonctionnalités vague 2 : déduplication, lots, audit, dossier surveillé."""
import time

import pytest
from fastapi.testclient import TestClient

from unocr import api
from unocr.api import app


@pytest.fixture()
def client(tmp_cfg, fixtures_dir):
    # le surveillant est un singleton partagé : on repart d'un état propre
    api._watch.stop()
    api._watch.reset()
    yield TestClient(app)
    api._watch.stop()
    api._watch.reset()


def _wait_done(client, job_id, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "error"):
            return j
        time.sleep(0.5)
    raise TimeoutError("job non terminé")


def _upload(client, path, name, **data):
    with open(path, "rb") as f:
        base = {"profile": "invoice", "quality_mode": "fast"}
        base.update(data)
        return client.post("/api/documents",
                           files={"file": (name, f, "application/octet-stream")},
                           data=base)


# ─────────────────────────── B6 · déduplication ───────────────────────────

def test_second_upload_is_cached(client, fixtures_dir):
    """Un document déjà traité n'est pas recalculé : le job existant est rendu."""
    r1 = _upload(client, fixtures_dir / "text_pdf.pdf", "dedup.pdf")
    assert r1.status_code == 200
    first = r1.json()
    assert first["cached"] is False
    assert _wait_done(client, first["job_id"])["status"] == "done"

    r2 = _upload(client, fixtures_dir / "text_pdf.pdf", "dedup.pdf")
    assert r2.status_code == 200
    second = r2.json()
    assert second["cached"] is True
    assert second["job_id"] == first["job_id"]
    # le résultat est immédiatement disponible, sans nouveau traitement
    assert client.get(f"/api/jobs/{second['job_id']}").json()["status"] == "done"


def test_dedupe_can_be_disabled(client, fixtures_dir):
    r1 = _upload(client, fixtures_dir / "text_pdf.pdf", "nodedup.pdf")
    assert r1.status_code == 200
    assert _wait_done(client, r1.json()["job_id"])["status"] == "done"

    r2 = _upload(client, fixtures_dir / "text_pdf.pdf", "nodedup.pdf", dedupe="false")
    assert r2.json()["cached"] is False
    assert r2.json()["job_id"] != r1.json()["job_id"]


def test_file_hash_recorded(client, fixtures_dir):
    r = _upload(client, fixtures_dir / "text_pdf.pdf", "hash.pdf")
    job = client.get(f"/api/jobs/{r.json()['job_id']}").json()
    assert job["file_hash"] and len(job["file_hash"]) == 64


# ─────────────────────────── B3 · lots ───────────────────────────

def test_batch_upload_creates_jobs(client, fixtures_dir):
    files = [
        ("files", ("a.pdf", open(fixtures_dir / "text_pdf.pdf", "rb"), "application/pdf")),
        ("files", ("b.pdf", open(fixtures_dir / "bl_port.pdf", "rb"), "application/pdf")),
    ]
    r = client.post("/api/batches", files=files,
                    data={"profile": "invoice", "quality_mode": "fast"})
    assert r.status_code == 200
    body = r.json()
    assert body["batch_id"].startswith("batch_")
    assert len(body["jobs"]) == 2
    assert body["rejected"] == []
    for j in body["jobs"]:
        assert _wait_done(client, j["job_id"])["status"] == "done"


def test_batch_dedupes(client, fixtures_dir):
    """Re-déposer le même fichier dans un lot ne relance pas l'OCR."""
    r1 = _upload(client, fixtures_dir / "text_pdf.pdf", "lot.pdf")
    assert _wait_done(client, r1.json()["job_id"])["status"] == "done"

    files = [("files", ("lot.pdf", open(fixtures_dir / "text_pdf.pdf", "rb"), "application/pdf"))]
    r2 = client.post("/api/batches", files=files,
                     data={"profile": "invoice", "quality_mode": "fast"})
    assert r2.json()["jobs"][0]["cached"] is True
    assert r2.json()["jobs"][0]["job_id"] == r1.json()["job_id"]


def test_batch_rejects_bad_file_without_failing_batch(client, fixtures_dir):
    """Un fichier invalide est écarté et signalé, le lot aboutit."""
    files = [
        ("files", ("ok.pdf", open(fixtures_dir / "text_pdf.pdf", "rb"), "application/pdf")),
        ("files", ("evil.exe", b"MZ\x00\x00", "application/octet-stream")),
    ]
    r = client.post("/api/batches", files=files,
                    data={"profile": "invoice", "quality_mode": "fast"})
    body = r.json()
    assert len(body["jobs"]) == 1
    assert len(body["rejected"]) == 1
    assert "evil.exe" in body["rejected"][0]["filename"]


def test_batch_export_csv_groups_documents(client, fixtures_dir):
    # deux fichiers DISTINCTS : un même fichier serait dédupliqué (comportement voulu)
    ids = []
    for src, name in ((fixtures_dir / "text_pdf.pdf", "g1.pdf"),
                      (fixtures_dir / "bl_port.pdf", "g2.pdf")):
        r = _upload(client, src, name)
        jid = r.json()["job_id"]
        assert _wait_done(client, jid)["status"] == "done"
        ids.append(jid)

    r = client.get("/api/batches/export/csv", params={"ids": ",".join(ids)})
    assert r.status_code == 200
    text = r.content.decode("utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert lines[0].startswith("document,champ,")
    assert "g1.pdf" in text and "g2.pdf" in text


def test_batch_export_json_and_txt(client, fixtures_dir):
    r = _upload(client, fixtures_dir / "text_pdf.pdf", "gj.pdf")
    jid = r.json()["job_id"]
    assert _wait_done(client, jid)["status"] == "done"

    j = client.get("/api/batches/export/json", params={"ids": jid})
    assert j.status_code == 200
    assert isinstance(j.json(), list) and "fields" in j.json()[0]

    t = client.get("/api/batches/export/txt", params={"ids": jid})
    assert t.status_code == 200
    assert "gj.pdf" in t.content.decode("utf-8")


def test_batch_export_requires_result(client, fixtures_dir):
    # TestClient exécute les tâches de fond avant de répondre : on crée donc un
    # job sans le lancer, pour obtenir un résultat réellement absent.
    from unocr.models import JobOptions
    # api.store est le store courant (isolé par la fixture tmp_cfg)
    job = api.store.create_job("pending.pdf", b"contenu", JobOptions(profile="generic"))
    resp = client.get("/api/batches/export/json", params={"ids": job.id})
    assert resp.status_code == 409


def test_batch_export_unknown_job(client):
    assert client.get("/api/batches/export/json",
                      params={"ids": "job_absent"}).status_code == 404


def test_batch_export_xlsx_one_sheet_per_document(client, fixtures_dir):
    ids = []
    for src, name in ((fixtures_dir / "text_pdf.pdf", "x1.pdf"),
                      (fixtures_dir / "bl_port.pdf", "x2.pdf")):
        r = _upload(client, src, name)
        jid = r.json()["job_id"]
        assert _wait_done(client, jid)["status"] == "done"
        ids.append(jid)

    resp = client.get("/api/batches/export/xlsx", params={"ids": ",".join(ids)})
    assert resp.status_code == 200
    assert len(resp.content) > 1000
    import io

    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    assert len(wb.sheetnames) >= 2, wb.sheetnames
    assert all(len(s) <= 31 for s in wb.sheetnames)


# ─────────────────────────── C5 · journal d'audit ───────────────────────────

def test_audit_endpoint_returns_entries(client, fixtures_dir):
    r = _upload(client, fixtures_dir / "text_pdf.pdf", "audit.pdf")
    jid = r.json()["job_id"]
    assert _wait_done(client, jid)["status"] == "done"

    body = client.get("/api/audit", params={"limit": 200}).json()
    assert body["returned"] >= 1
    events = {e.get("event") for e in body["entries"]}
    assert "job_created" in events
    # chaque entrée est horodatée et typée
    for e in body["entries"]:
        assert "ts" in e and "event" in e


def test_audit_filters_by_event(client, fixtures_dir):
    r = _upload(client, fixtures_dir / "text_pdf.pdf", "filtre.pdf")
    assert _wait_done(client, r.json()["job_id"])["status"] == "done"

    body = client.get("/api/audit", params={"event": "job_created", "limit": 200}).json()
    assert body["returned"] >= 1
    assert all(e["event"] == "job_created" for e in body["entries"])


def test_audit_filter_no_match(client):
    body = client.get("/api/audit", params={"event": "evenement_inexistant"}).json()
    assert body["returned"] == 0


# ─────────────────────────── B4 · dossier surveillé ───────────────────────────

def test_watch_status_and_disable(client):
    body = client.get("/api/watch").json()
    assert body["enabled"] is False and body["running"] is False

    r = client.put("/api/watch", json={"enabled": False, "path": "data/watch"})
    assert r.status_code == 200
    assert r.json()["enabled"] is False


def test_watch_processes_new_file(client, tmp_path, fixtures_dir):
    """Un fichier déposé dans le dossier surveillé est traité."""
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    src = fixtures_dir / "text_pdf.pdf"
    (watch_dir / "arrive.pdf").write_bytes(src.read_bytes())

    r = client.put("/api/watch", json={
        "enabled": True, "path": str(watch_dir), "profile": "invoice",
        "quality_mode": "fast", "poll_seconds": 2.0, "move_done": False})
    assert r.json()["enabled"] is True

    try:
        # 1er balayage : mémorise la taille. 2e : taille stable → traitement.
        client.post("/api/watch/scan")
        time.sleep(1.6)
        res = client.post("/api/watch/scan").json()
        assert res["scanned"] is True
        assert res["processed"] == 1
        assert res["last_job_id"]
        assert _wait_done(client, res["last_job_id"])["status"] == "done"
    finally:
        client.put("/api/watch", json={"enabled": False})


def test_watch_dedupes_known_file(client, tmp_path, fixtures_dir):
    watch_dir = tmp_path / "watch2"
    watch_dir.mkdir()
    (watch_dir / "connu.pdf").write_bytes((fixtures_dir / "text_pdf.pdf").read_bytes())

    r = _upload(client, fixtures_dir / "text_pdf.pdf", "connu.pdf")
    known = r.json()["job_id"]
    assert _wait_done(client, known)["status"] == "done"

    client.put("/api/watch", json={"enabled": True, "path": str(watch_dir),
                                   "profile": "invoice", "quality_mode": "fast"})
    try:
        client.post("/api/watch/scan")
        time.sleep(1.6)
        res = client.post("/api/watch/scan").json()
        assert res["processed"] == 0
        assert res["skipped_duplicates"] == 1
    finally:
        client.put("/api/watch", json={"enabled": False})


def test_watch_rejects_bad_file(client, tmp_path):
    watch_dir = tmp_path / "watch3"
    watch_dir.mkdir()
    (watch_dir / "virus.exe").write_bytes(b"MZ\x00\x00")

    client.put("/api/watch", json={"enabled": True, "path": str(watch_dir),
                                   "profile": "generic", "quality_mode": "fast"})
    try:
        client.post("/api/watch/scan")
        time.sleep(1.6)
        res = client.post("/api/watch/scan").json()
        assert res["rejected"] == 1
        assert res["processed"] == 0
    finally:
        client.put("/api/watch", json={"enabled": False})


def test_watch_invalid_path(client):
    r = client.put("/api/watch", json={"enabled": True, "path": "/etc/passwd"})
    assert r.status_code == 200
    res = client.post("/api/watch/scan").json()
    assert res["scanned"] is False
    client.put("/api/watch", json={"enabled": False})


def _last_job_id() -> str:
    jobs = api.store.list_jobs(limit=1)
    assert jobs, "aucun job créé"
    return jobs[0].id


# ─────────────────────────── C2 · export ciblé ───────────────────────────

def test_export_selected_fields(client, fixtures_dir):
    """L'export ciblé ne contient que les champs demandés."""
    r = _upload(client, fixtures_dir / "text_pdf.pdf", "sel.pdf")
    jid = r.json()["job_id"]
    assert _wait_done(client, jid)["status"] == "done"

    res = client.get(f"/api/jobs/{jid}/result").json()
    names = list(res["fields"])
    assert len(names) >= 2
    keep = names[:2]

    resp = client.get(f"/api/jobs/{jid}/export/csv/selected",
                      params={"fields": ",".join(keep)})
    assert resp.status_code == 200
    text = resp.content.decode("utf-8-sig")
    header = text.splitlines()[0]
    assert "raw_value" in header
    for n in keep:
        assert n in text
    for n in names[2:]:
        assert n not in text


def test_export_selected_json(client, fixtures_dir):
    r = _upload(client, fixtures_dir / "text_pdf.pdf", "selj.pdf")
    jid = r.json()["job_id"]
    assert _wait_done(client, jid)["status"] == "done"
    res = client.get(f"/api/jobs/{jid}/result").json()
    name = list(res["fields"])[0]

    resp = client.get(f"/api/jobs/{jid}/export/json/selected", params={"fields": name})
    assert resp.status_code == 200
    body = resp.json()
    assert list(body["fields"]) == [name]


def test_export_selected_unknown_field(client, fixtures_dir):
    r = _upload(client, fixtures_dir / "text_pdf.pdf", "selu.pdf")
    jid = r.json()["job_id"]
    assert _wait_done(client, jid)["status"] == "done"
    resp = client.get(f"/api/jobs/{jid}/export/csv/selected",
                      params={"fields": "champ_qui_nexiste_pas"})
    assert resp.status_code == 400


def test_export_selected_bad_format(client, fixtures_dir):
    r = _upload(client, fixtures_dir / "text_pdf.pdf", "selb.pdf")
    jid = r.json()["job_id"]
    assert _wait_done(client, jid)["status"] == "done"
    resp = client.get(f"/api/jobs/{jid}/export/exe/selected", params={"fields": "date"})
    assert resp.status_code == 400
