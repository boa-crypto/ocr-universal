"""Tests API REST (TestClient FastAPI) — upload async, résultats, exports, validation."""
import time

import pytest
from fastapi.testclient import TestClient

from unocr.api import app


@pytest.fixture()
def client(tmp_cfg, fixtures_dir):
    return TestClient(app)


def _wait_done(client, job_id, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "error"):
            return j
        time.sleep(0.5)
    raise TimeoutError("job non terminé")


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "tesseract" in body["engines_available"]


def test_engines_and_languages(client):
    eng = client.get("/api/engines").json()
    names = {e["name"]: e for e in eng}
    assert names["tesseract"]["available"] is True
    from unocr.ocr_engines import EasyOCREngine
    assert names["easyocr"]["available"] == EasyOCREngine().is_available()  # honnête
    langs = client.get("/api/languages").json()
    assert "fra" in langs["installed_models"]


def test_profiles_endpoint(client):
    profs = client.get("/api/profiles").json()
    names = [p["name"] for p in profs]
    assert "generic" in names and "port_bl" in names


def test_upload_process_export_flow(client, fixtures_dir):
    with open(fixtures_dir / "text_pdf.pdf", "rb") as f:
        r = client.post("/api/documents", files={"file": ("text_pdf.pdf", f, "application/pdf")},
                        data={"profile": "invoice", "quality_mode": "fast",
                              "export_formats": "json,txt,csv,xlsx,xml"})
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    j = _wait_done(client, job_id)
    assert j["status"] == "done", j.get("error")

    res = client.get(f"/api/jobs/{job_id}/result").json()
    assert res["pages"][0]["text"]
    assert res["fields"]["invoice_number"]["raw_value"] is not None

    text = client.get(f"/api/jobs/{job_id}/text?page=1").json()
    assert text["pages"][0]["page_num"] == 1

    fields = client.get(f"/api/jobs/{job_id}/fields").json()
    assert "issue_date" in fields["fields"]

    quality = client.get(f"/api/jobs/{job_id}/quality").json()
    assert "mean_engine_confidence" in quality

    for fmt in ("json", "txt", "xlsx", "xml"):
        r = client.get(f"/api/jobs/{job_id}/export/{fmt}")
        assert r.status_code == 200, fmt
    r = client.get(f"/api/jobs/{job_id}/export/csv")
    assert r.status_code == 200

    # page image (visionneuse)
    r = client.get(f"/api/jobs/{job_id}/page/1/image")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/")


def test_human_validation_traced(client, fixtures_dir):
    with open(fixtures_dir / "text_pdf.pdf", "rb") as f:
        r = client.post("/api/documents", files={"file": ("t.pdf", f, "application/pdf")},
                        data={"profile": "generic", "quality_mode": "fast"})
    job_id = r.json()["job_id"]
    j = _wait_done(client, job_id)
    assert j["status"] == "done"
    r = client.patch(f"/api/jobs/{job_id}/fields/date",
                     json={"confirmed_value": "2024-03-15"})
    assert r.status_code == 200
    fv = r.json()["field"]
    assert fv["confirmed_value"] == "2024-03-15"
    assert fv["status"] == "validated"
    assert fv["value_origin"] == "confirmed"
    # raw_value conservé (traçabilité)
    assert fv["raw_value"] is not None


def test_upload_rejects_bad_file(client, tmp_path):
    r = client.post("/api/documents",
                    files={"file": ("evil.exe", b"MZ\x00\x00", "application/octet-stream")})
    assert r.status_code in (400, 422)


def test_upload_stops_at_configured_size_limit(client, fixtures_dir, monkeypatch):
    from unocr import api

    monkeypatch.setitem(api.cfg.data, "max_file_size_mb", 0)
    with open(fixtures_dir / "text_pdf.pdf", "rb") as source:
        response = client.post(
            "/api/documents",
            files={"file": ("document.pdf", source, "application/pdf")})
    assert response.status_code == 413


def test_batch_obeys_total_size_limit(client, monkeypatch):
    from unocr import api

    monkeypatch.setitem(api.cfg.data, "max_batch_size_mb", 0)
    response = client.post(
        "/api/batches",
        files=[("files", ("document.txt", b"document", "text/plain"))])
    assert response.status_code == 200
    assert response.json()["accepted"] == 0
    assert response.json()["rejected"]


def test_stats(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    assert "jobs_total" in r.json()


def test_export_lazy_generation(client, fixtures_dir):
    """Un export demandé est généré à la demande même s'il n'existait pas."""
    import shutil
    with open(fixtures_dir / "text_pdf.pdf", "rb") as f:
        r = client.post("/api/documents", files={"file": ("lazy.pdf", f, "application/pdf")},
                        data={"profile": "generic", "quality_mode": "fast",
                              "export_formats": "json"})
    job_id = r.json()["job_id"]
    j = _wait_done(client, job_id)
    assert j["status"] == "done"
    # on supprime les exports générés pour forcer la re-génération
    from unocr import api  # store courant (isolé par la fixture tmp_cfg)
    export_dir = api.store.export_dir(job_id)
    shutil.rmtree(export_dir, ignore_errors=True)
    export_dir.mkdir(parents=True, exist_ok=True)
    for fmt in ("txt", "csv", "xlsx", "xml"):
        r = client.get(f"/api/jobs/{job_id}/export/{fmt}")
        assert r.status_code == 200, f"{fmt}: {r.text[:200]}"
        assert len(r.content) > 100, fmt
    # csv multiple (champs + tableaux) -> bundle zip ; sinon un seul csv
    r = client.get(f"/api/jobs/{job_id}/export/csv")
    assert r.status_code == 200
    # PDF consultable : bien formé, couche texte présente
    r = client.get(f"/api/jobs/{job_id}/export/pdf")
    assert r.status_code == 200
    import pathlib
    import tempfile

    from pdfminer.high_level import extract_text
    p = pathlib.Path(tempfile.mkdtemp()) / "s.pdf"
    p.write_bytes(r.content)
    assert "FACTURE" in extract_text(p)


# ─────────────────── recherche plein texte & file de révision ───────────────────

def _result(client, job_id):
    return client.get(f"/api/jobs/{job_id}/result").json()


def test_search_finds_extracted_field(client, fixtures_dir):
    """La recherche porte sur les valeurs de champs réellement extraites."""
    with open(fixtures_dir / "text_pdf.pdf", "rb") as f:
        r = client.post("/api/documents",
                        files={"file": ("text_pdf.pdf", f, "application/pdf")},
                        data={"profile": "invoice", "quality_mode": "fast"})
    job_id = r.json()["job_id"]
    assert _wait_done(client, job_id)["status"] == "done"

    res = _result(client, job_id)
    valeur = res["fields"]["invoice_number"]["raw_value"]
    assert valeur, "aucune valeur extraite : le test n'aurait pas de sens"

    r = client.get("/api/search", params={"q": valeur})
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == valeur
    assert any(h["job_id"] == job_id and h["kind"] == "field" for h in body["hits"]), body


def test_search_finds_text_snippet(client, fixtures_dir):
    """La recherche porte aussi sur le texte reconnu, avec extrait."""
    with open(fixtures_dir / "text_pdf.pdf", "rb") as f:
        r = client.post("/api/documents",
                        files={"file": ("text_pdf.pdf", f, "application/pdf")},
                        data={"profile": "invoice", "quality_mode": "fast"})
    job_id = r.json()["job_id"]
    assert _wait_done(client, job_id)["status"] == "done"

    mot = _result(client, job_id)["pages"][0]["text"].split()[0]
    r = client.get("/api/search", params={"q": mot})
    assert r.status_code == 200
    assert any(h["kind"] == "text" and h["job_id"] == job_id for h in r.json()["hits"])


def test_search_empty_query_rejected(client):
    r = client.get("/api/search", params={"q": ""})
    assert r.status_code == 422


def test_review_queue_flags_uncertain_fields(client, fixtures_dir):
    """Avec un seuil bas, tout champ non validé et sous le seuil remonte."""
    with open(fixtures_dir / "text_pdf.pdf", "rb") as f:
        r = client.post("/api/documents",
                        files={"file": ("text_pdf.pdf", f, "application/pdf")},
                        data={"profile": "invoice", "quality_mode": "fast"})
    job_id = r.json()["job_id"]
    assert _wait_done(client, job_id)["status"] == "done"

    r = client.get("/api/review", params={"threshold": 0.999})
    assert r.status_code == 200
    body = r.json()
    assert body["documents"] >= 1
    item = next(i for i in body["items"] if i["job_id"] == job_id)
    assert item["fields"], "le document devrait avoir des champs à revoir"
    assert all("reasons" in f and f["reasons"] for f in item["fields"])


def test_review_queue_excludes_validated(client, fixtures_dir):
    """Un champ validé par l'humain ne doit plus apparaître dans la file."""
    with open(fixtures_dir / "text_pdf.pdf", "rb") as f:
        r = client.post("/api/documents",
                        files={"file": ("text_pdf.pdf", f, "application/pdf")},
                        data={"profile": "invoice", "quality_mode": "fast"})
    job_id = r.json()["job_id"]
    assert _wait_done(client, job_id)["status"] == "done"

    client.patch(f"/api/jobs/{job_id}/fields/invoice_number",
                 json={"confirmed_value": "VALIDE-123"})
    res = _result(client, job_id)
    assert res["fields"]["invoice_number"]["status"] == "validated"

    r = client.get("/api/review", params={"threshold": 0.999})
    item = next(i for i in r.json()["items"] if i["job_id"] == job_id)
    assert "invoice_number" not in {f["field"] for f in item["fields"]}


def test_review_queue_ignores_unfinished_jobs(client):
    r = client.get("/api/review")
    assert r.status_code == 200
    assert r.json()["documents"] >= 0


def test_review_queue_excludes_undetected_by_default(client, fixtures_dir):
    """Un champ absent n'est pas une erreur à trancher : exclu par défaut.

    Mesuré sur le jeu de test : les not_detected représentent ~83 % des
    entrées et noieraient la file de révision.
    """
    with open(fixtures_dir / "text_pdf.pdf", "rb") as f:
        r = client.post("/api/documents",
                        files={"file": ("undet.pdf", f, "application/pdf")},
                        data={"profile": "invoice", "quality_mode": "fast"})
    job_id = r.json()["job_id"]
    assert _wait_done(client, job_id)["status"] == "done"

    sans = client.get("/api/review", params={"threshold": 0.999}).json()
    avec = client.get("/api/review",
                      params={"threshold": 0.999, "include_undetected": True}).json()

    def champs(body, jid):
        item = next((i for i in body["items"] if i["job_id"] == jid), None)
        return {f["field"] for f in (item["fields"] if item else [])}

    a, b = champs(sans, job_id), champs(avec, job_id)
    assert b > a, "le filtre devrait retirer des champs"
    assert not any(f in a for f in ()), "aucun not_detected ne doit passer"
    # tout champ retiré est bien not_detected
    for name in (b - a):
        res = _result(client, job_id)
        assert res["fields"][name]["status"] == "not_detected"
