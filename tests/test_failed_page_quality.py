"""Pages non déclarées vides sans sortie : revue et moyenne conservatrices."""
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from unocr import api
from unocr.exporters import export_json
from unocr.models import (
    BBox,
    DocumentResult,
    EngineRun,
    JobOptions,
    JobStatus,
    PageQuality,
    PageResult,
    Word,
)
from unocr.pipeline import Pipeline
from unocr.quality import build_quality_report


def page(number=1, **kwargs):
    return PageResult(page_num=number, width=100, height=30, **kwargs)


def recognized(number=1, confidence=1):
    return page(number, text="texte", words=[Word(text="texte", confidence=confidence,
                bbox=BBox(x0=0, y0=0, x1=20, y1=10))])


@pytest.mark.parametrize("text", ["", " ", "\n\t", "\u2003"])
@pytest.mark.parametrize("threshold", [0, 0.7, 1])
def test_missing_output_requires_review_even_at_zero_threshold(text, threshold):
    report = build_quality_report(DocumentResult(pages=[page(text=text)]), threshold)
    assert report.pages_low_confidence == [1]
    assert report.mean_engine_confidence == report.mean_global_confidence == 0
    assert [(a.code, a.page_num) for a in report.anomalies] == [("OCR_FAILED", 1)]


@pytest.mark.parametrize("run", [
    None,
    EngineRun(engine="baidu", page_num=1, ok=False, error="Baidu : localisation invalide"),
    EngineRun(engine="tesseract", page_num=1, ok=True, word_count=0),
])
def test_review_depends_on_missing_output_not_engine_or_claimed_success(run):
    report = build_quality_report(DocumentResult(pages=[page(engine_runs=[run] if run else [])]))
    assert report.pages_low_confidence == [1]


@pytest.mark.parametrize("threshold", [0, 0.7, 1])
def test_mixed_document_includes_failed_zero_but_not_blank(threshold):
    document = DocumentResult(pages=[recognized(), page(2), page(3, blank=True)])
    report = build_quality_report(document, threshold)
    assert report.mean_engine_confidence == report.mean_global_confidence == 0.5
    assert report.pages_low_confidence == [2]
    assert [(a.code, a.page_num) for a in report.anomalies] == [("OCR_FAILED", 2)]


def test_multiple_failures_are_counted_once_per_page_not_per_run():
    failed = page(7, engine_runs=[EngineRun(engine=name, page_num=7, ok=False)
                                 for name in ("baidu", "tesseract", "indra")])
    document = DocumentResult(pages=[recognized(5), failed, page(2)])
    report = build_quality_report(document)
    assert report.mean_engine_confidence == report.mean_global_confidence == 0.333
    assert report.pages_low_confidence == [7, 2]


def test_declared_blank_only_keeps_zero_summary_without_ocr_failure_or_review():
    report = build_quality_report(DocumentResult(pages=[page(blank=True, quality=PageQuality(is_blank=True))]))
    assert report.mean_global_confidence == 0
    assert report.pages_low_confidence == []
    assert [a.code for a in report.anomalies] == ["EMPTY_PAGE"]


def test_recognized_words_and_quality_factor_unchanged():
    p = recognized(confidence=0.8)
    p.quality.issues = ["dark"]
    report = build_quality_report(DocumentResult(pages=[p, page(2)]))
    assert report.mean_engine_confidence == 0.4
    assert report.mean_global_confidence == 0.36
    assert report.pages_low_confidence == [2]


def test_native_text_fallback_policy_not_changed_or_attributed_to_failed_page():
    report = build_quality_report(DocumentResult(pages=[page(text="texte natif"), page(2)]))
    assert report.mean_engine_confidence == report.mean_global_confidence == 0.475
    assert report.pages_low_confidence == [2]


def test_all_failed_pages_zero_and_all_listed():
    report = build_quality_report(DocumentResult(pages=[page(3), page(6)]))
    assert report.mean_global_confidence == 0
    assert report.pages_low_confidence == [3, 6]


def test_empty_document_not_reclassified_as_failed_page():
    report = build_quality_report(DocumentResult())
    assert report.pages_low_confidence == []
    assert report.anomalies == []


def test_report_does_not_mutate_source_or_invent_word_scores():
    document = DocumentResult(pages=[recognized(), page(2)])
    before = document.model_dump()
    build_quality_report(document)
    assert document.model_dump() == before
    assert document.pages[1].words == [] and document.pages[1].engine_runs == []


def test_full_pipeline_real_image_without_available_engines(tmp_cfg, tmp_path):
    class EmptyRegistry:
        def get(self, name):
            return None

        def select(self, **kwargs):
            return []

    image = Image.new("RGB", (400, 150), "white")
    ImageDraw.Draw(image).rectangle((20, 30, 300, 55), fill="black")
    path = tmp_path / "synthetic-no-engine.png"
    image.save(path)
    result = Pipeline(tmp_cfg, EmptyRegistry()).process_file(
        path, JobOptions(profile="generic", quality_mode="fast", preprocess=False,
                         extract_tables=False, extract_barcodes=False))
    assert not result.pages[0].blank
    assert result.pages[0].text == "" and result.pages[0].words == []
    assert result.quality.pages_low_confidence == [1]
    assert result.quality.mean_global_confidence == 0
    assert any(a.code == "OCR_FAILED" for a in result.quality.anomalies)


def test_json_storage_api_export_preserve_failed_page_review(tmp_cfg):
    document = DocumentResult(pages=[recognized(), page(2)])
    document.quality = build_quality_report(document)
    job = api.store.create_job("synthetic.txt", b"synthetic non officiel")
    job.status = JobStatus.DONE
    api.store.update(job)
    api.store.save_result(job.id, document.model_dump(mode="json"))
    disk = api.store.load_result(job.id)
    assert disk["quality"]["pages_low_confidence"] == [2]
    assert disk["quality"]["mean_global_confidence"] == 0.5
    with TestClient(api.app) as client:
        for route in ("result", "export/json"):
            response = client.get(f"/api/jobs/{job.id}/{route}")
            assert response.status_code == 200
            assert response.json()["quality"] == disk["quality"]
    restored = DocumentResult.model_validate(disk)
    path = export_json(restored, tmp_cfg.data_dir / "quality-export.json")
    assert json.loads(path.read_text())["quality"] == disk["quality"]
