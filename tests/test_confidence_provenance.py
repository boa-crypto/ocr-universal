"""Provenance typée : persistance réelle, fournisseur et OCR non exécutés."""
import copy
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from pydantic import ValidationError

from unocr import baidu_http
from unocr.confidence_provenance import attach_confidence_provenance
from unocr.exporters import export_json
from unocr.ingest import LoadedPage
from unocr.models import BBox, DocumentResult, EngineRun, JobOptions, JobStatus, Word
from unocr.ocr_engines import BaiduOCREngine, EngineOutput
from unocr.pipeline import Pipeline
from unocr.quality import build_quality_report

PROVENANCE = {"policy": "provider_average_else_zero", "calibrated": False,
              "reported": 1, "missing": 1, "invalid": 1}


def run_data(**kwargs):
    return {"engine": "baidu", "page_num": 1, "word_count": 3,
            "mean_confidence": 0.2, "confidence_provenance": copy.deepcopy(PROVENANCE), **kwargs}


@pytest.mark.parametrize("engine", ["baidu", "tesseract", "native_pdf", "indra"])
def test_legacy_run_json_remains_identical_without_provenance(engine):
    old = {"engine": engine, "page_num": 1, "languages": [], "mean_confidence": 0.0,
           "word_count": 0, "duration_ms": 0.0, "ok": True, "error": None}
    model = EngineRun.model_validate(old)
    assert model.confidence_provenance is None
    assert model.model_dump() == old
    assert json.loads(model.model_dump_json()) == old


def test_valid_provenance_roundtrip_and_include_exclude():
    model = EngineRun(**run_data())
    dump = model.model_dump(mode="json")
    assert dump["confidence_provenance"] == PROVENANCE
    assert EngineRun.model_validate_json(model.model_dump_json()).model_dump() == dump
    assert model.model_dump(include={"confidence_provenance"}) == {"confidence_provenance": PROVENANCE}
    assert "confidence_provenance" not in model.model_dump(exclude={"confidence_provenance"})


@pytest.mark.parametrize("key,value", [
    ("reported", -1), ("missing", 10001), ("invalid", True), ("reported", 1.0),
    ("missing", "1"), ("invalid", None), ("calibrated", True), ("calibrated", 0),
    ("policy", "invented"), ("private", "FAKE67-PRIVATE"),
])
def test_invalid_provenance_model_is_refused(key, value):
    data = run_data()
    data["confidence_provenance"][key] = value
    with pytest.raises(ValidationError):
        EngineRun.model_validate(data)


@pytest.mark.parametrize("changes", [
    {"word_count": 2}, {"word_count": 4}, {"engine": "tesseract"}, {"ok": False},
    {"mean_confidence": -0.1}, {"mean_confidence": 0.5},
    {"mean_confidence": float("nan")}, {"mean_confidence": float("inf")},
])
def test_incompatible_run_is_refused(changes):
    with pytest.raises(ValidationError):
        EngineRun(**run_data(**changes))


def test_combined_count_limit_is_not_three_times_individual_limit():
    data = run_data(word_count=30000)
    data["confidence_provenance"].update(reported=10000, missing=10000, invalid=10000)
    with pytest.raises(ValidationError):
        EngineRun(**data)


@pytest.mark.parametrize("reported,missing,invalid", [(1, 0, 0), (0, 1, 0), (0, 0, 1)])
def test_zero_mean_does_not_erase_score_origin(reported, missing, invalid):
    data = run_data(word_count=1, mean_confidence=0)
    data["confidence_provenance"].update(reported=reported, missing=missing, invalid=invalid)
    assert EngineRun(**data).model_dump()["confidence_provenance"] == data["confidence_provenance"]


@pytest.mark.parametrize("raw", [
    {}, None, [], {"confidence": None}, {"confidence": "FAKE67-PRIVATE"},
    {"confidence": {**PROVENANCE, "private": "FAKE67-PRIVATE"}},
    {"confidence": {**PROVENANCE, "missing": "FAKE67-PRIVATE"}},
])
def test_raw_invalid_or_missing_never_copied_or_logged(raw, caplog):
    run = EngineRun(engine="baidu", page_num=1, word_count=3, mean_confidence=0.2)
    output = EngineOutput(engine="baidu", text="", mean_confidence=0.2,
                          words=[Word(text="a", bbox=BBox(x0=0, y0=0, x1=1, y1=1))] * 3, raw=raw)
    attached = attach_confidence_provenance(run, output)
    assert attached is run
    assert "confidence_provenance" not in attached.model_dump()
    assert "FAKE67-PRIVATE" not in attached.model_dump_json() + caplog.text


@pytest.mark.parametrize("engine,ok", [("tesseract", True), ("baidu", False)])
def test_other_engine_or_failed_run_cannot_claim_provenance(engine, ok):
    run = EngineRun(engine=engine, page_num=1, ok=ok, word_count=3, mean_confidence=0.2)
    output = EngineOutput(engine=engine, text="", ok=ok, raw={"confidence": PROVENANCE})
    assert attach_confidence_provenance(run, output) is run


def test_inconsistent_local_raw_is_omitted_not_logged(caplog):
    run = EngineRun(engine="baidu", page_num=1, word_count=1, mean_confidence=0.2)
    output = EngineOutput(engine="baidu", text="", raw={"confidence": PROVENANCE})
    assert attach_confidence_provenance(run, output).confidence_provenance is None
    assert not caplog.records


@pytest.fixture
def document(tmp_cfg, monkeypatch):
    for name in ("BAIDU_OCR_API_KEY", "BAIDU_API_KEY", "BAIDU_OCR_SECRET_KEY", "BAIDU_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("BAIDU_API_KEY", "FAKE67")
    monkeypatch.setenv("BAIDU_SECRET_KEY", "FAKE67")

    def post(url, **kwargs):
        if url == baidu_http.TOKEN_URL:
            return {"access_token": "FAKE67"}
        return {"words_result": [
            {"words": "declared-zero", "probability": {"average": 0}},
            {"words": "missing"}, {"words": "invalid", "probability": {"average": "0.9"}},
        ]}

    monkeypatch.setattr(baidu_http, "post_json", post)
    engine = BaiduOCREngine()

    class Registry:
        def get(self, name):
            return engine if name == "baidu" else None

        def select(self, **kwargs):
            return [engine]

    image = Image.new("RGB", (400, 150), "white")
    ImageDraw.Draw(image).rectangle((20, 30, 300, 55), fill="black")
    page = Pipeline(tmp_cfg, Registry())._process_page(
        LoadedPage(page_num=1, width=400, height=150, image=image),
        JobOptions(quality_mode="fast", preprocess=False), 0, 1)
    result = DocumentResult(pages=[page])
    result.quality = build_quality_report(result)
    return result


def test_pipeline_keeps_counts_separate_from_scores_and_review(document):
    run = document.pages[0].engine_runs[0]
    assert run.confidence_provenance.model_dump() == PROVENANCE
    assert run.mean_confidence == 0
    assert all(word.confidence == 0 for word in document.pages[0].words)
    assert document.quality.pages_low_confidence == [1]


def test_json_export_persists_only_typed_metadata(document, tmp_path):
    path = export_json(document, tmp_path / "result.json")
    data = json.loads(path.read_text())
    assert data["pages"][0]["engine_runs"][0]["confidence_provenance"] == PROVENANCE
    assert "FAKE67" not in path.read_text()
    assert DocumentResult.model_validate(data).model_dump(mode="json") == data


def test_store_api_and_download_roundtrip(document, tmp_cfg):
    from unocr import api

    job = api.store.create_job("synthetic.txt", b"synthetic non officiel")
    job.status = JobStatus.DONE
    api.store.update(job)
    path = api.store.save_result(job.id, document.model_dump(mode="json"))
    assert json.loads(path.read_text())["pages"][0]["engine_runs"][0]["confidence_provenance"] == PROVENANCE
    with TestClient(api.app) as client:
        response = client.get(f"/api/jobs/{job.id}/result")
        assert response.status_code == 200
        assert response.json()["pages"][0]["engine_runs"][0]["confidence_provenance"] == PROVENANCE
        export = client.get(f"/api/jobs/{job.id}/export/json")
        assert export.status_code == 200
        assert export.json()["pages"][0]["engine_runs"][0]["confidence_provenance"] == PROVENANCE
    assert "FAKE67" not in export.text


@pytest.mark.parametrize("word_count,mean", [(1, 0.2), (3, 0.7)])
def test_projection_rejects_mismatch_with_output(word_count, mean):
    run = EngineRun(engine="baidu", page_num=1, word_count=word_count, mean_confidence=mean)
    output = EngineOutput(engine="baidu", text="", mean_confidence=0.2,
                          words=[Word(text="a", bbox=BBox(x0=0, y0=0, x1=1, y1=1))] * 3,
                          raw={"confidence": PROVENANCE})
    assert attach_confidence_provenance(run, output) is run


def test_projection_attaches_only_validated_metadata():
    run = EngineRun(engine="baidu", page_num=1, word_count=3, mean_confidence=0.2)
    output = EngineOutput(engine="baidu", text="", mean_confidence=0.2,
                          words=[Word(text="a", bbox=BBox(x0=0, y0=0, x1=1, y1=1))] * 3,
                          raw={"confidence": PROVENANCE, "private": "FAKE67-PRIVATE"})
    projected = attach_confidence_provenance(run, output)
    assert projected.confidence_provenance.model_dump() == PROVENANCE
    assert run.confidence_provenance is None  # Projection sans mutation du run source.
    assert "FAKE67-PRIVATE" not in projected.model_dump_json()
