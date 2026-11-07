"""Revue des champs : zéro est une valeur, rapport après confiance finale."""
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from unocr import api
from unocr.exporters import export_json
from unocr.models import (
    DocumentResult,
    FieldStatus,
    FieldValue,
    JobOptions,
    JobStatus,
    PageQuality,
    ValueOrigin,
)
from unocr.pipeline import Pipeline
from unocr.quality import build_quality_report


def field(confidence=0, status=FieldStatus.DETECTED, **kwargs):
    return FieldValue(name="sample", raw_value="texte", confidence=confidence, status=status, **kwargs)


@pytest.mark.parametrize("status", list(FieldStatus))
@pytest.mark.parametrize("score", [0.0, -0.0])
def test_zero_below_positive_threshold_included_except_not_detected(status, score):
    value = field(score, status)
    document = DocumentResult(fields={"key": value})
    before = document.model_dump()
    report = build_quality_report(document)
    assert report.fields_low_confidence == ([] if status == FieldStatus.NOT_DETECTED else ["key"])
    assert document.model_dump() == before


@pytest.mark.parametrize("score,threshold,expected", [
    (0, 0, []), (0, 0.001, ["key"]), (0.2, 0.7, ["key"]),
    (0.7, 0.7, []), (1, 0.7, []), (0, 1, ["key"]),
])
def test_threshold_remains_strict_and_configurable(score, threshold, expected):
    assert build_quality_report(DocumentResult(fields={"key": field(score)}), threshold).fields_low_confidence == expected


@pytest.mark.parametrize("score", [0, 0.1, 0.9])
def test_not_detected_remains_excluded_independently_of_confidence(score):
    value = field(score, FieldStatus.NOT_DETECTED)
    assert build_quality_report(DocumentResult(fields={"key": value}), 1).fields_low_confidence == []


def test_validated_zero_is_review_signal_not_revocation_or_change_of_value():
    value = field(0, FieldStatus.VALIDATED, confirmed_value="confirmé humain",
                  value_origin=ValueOrigin.CONFIRMED)
    report = build_quality_report(DocumentResult(fields={"key": value}))
    assert report.fields_low_confidence == ["key"]
    assert value.status == FieldStatus.VALIDATED
    assert value.value == "confirmé humain" and value.value_origin == ValueOrigin.CONFIRMED
    assert report.anomalies == []


def test_key_order_not_name_alias_and_no_duplicate_per_field():
    document = DocumentResult(fields={"b": field(), "a": field(), "other": field(1)})
    assert build_quality_report(document).fields_low_confidence == ["b", "a"]


def test_zero_does_not_invent_field_or_page_or_engine_measurement():
    document = DocumentResult(fields={"key": field()})
    report = build_quality_report(document)
    assert report.pages_low_confidence == [] and document.pages == []
    assert document.fields["key"].engine_confidence == 0
    assert report.mean_engine_confidence == report.mean_global_confidence == 0


@pytest.mark.parametrize("initial,engine,expected,listed", [
    (0.9, 0.1, 0.1, True), (0.1, 1, 1, False),
    (0, 1, 1, False), (0.9, 0.0004, 0, True),
])
def test_pipeline_report_uses_final_confidence_not_pre_recalculation(
        tmp_cfg, tmp_path, monkeypatch, initial, engine, expected, listed):
    import unocr.pipeline as module

    class EmptyRegistry:
        def get(self, name):
            return None

        def select(self, **kwargs):
            return []

    def extract(pages):
        # Contrat d'extraction injecté explicitement ; pas reconnaissance simulée.
        pages[0].quality = PageQuality()
        return {"key": field(initial, engine_confidence=engine, page_num=1)}, {}

    monkeypatch.setattr(module, "extract_generic_fields", extract)
    monkeypatch.setattr(module, "load_all_profiles", lambda *args: {})
    image = Image.new("RGB", (400, 150), "white")
    ImageDraw.Draw(image).rectangle((20, 30, 300, 55), fill="black")
    path = tmp_path / "synthetic.png"
    image.save(path)
    result = Pipeline(tmp_cfg, EmptyRegistry()).process_file(path, JobOptions(
        profile="generic", quality_mode="fast", preprocess=False, auto_classify=False,
        extract_tables=False, extract_barcodes=False))
    assert result.fields["key"].confidence == expected
    assert result.quality.fields_low_confidence == (["key"] if listed else [])
    assert result.quality.model_dump() == build_quality_report(result).model_dump()
    assert result.quality.pages_low_confidence == [1]


def test_json_store_api_and_download_keep_zero_review_without_status_change(tmp_cfg):
    value = field(0, FieldStatus.VALIDATED, confirmed_value="confirmé humain",
                  value_origin=ValueOrigin.CONFIRMED)
    document = DocumentResult(fields={"key": value})
    document.quality = build_quality_report(document)
    job = api.store.create_job("synthetic.txt", b"synthetic non officiel")
    job.status = JobStatus.DONE
    api.store.update(job)
    api.store.save_result(job.id, document.model_dump(mode="json"))
    with TestClient(api.app) as client:
        for route in ("result", "export/json"):
            response = client.get(f"/api/jobs/{job.id}/{route}")
            assert response.status_code == 200
            assert response.json()["quality"]["fields_low_confidence"] == ["key"]
            assert response.json()["fields"]["key"]["status"] == "validated"
            assert response.json()["fields"]["key"]["confirmed_value"] == "confirmé humain"
    restored = DocumentResult.model_validate(api.store.load_result(job.id))
    path = export_json(restored, tmp_cfg.data_dir / "zero-export.json")
    assert json.loads(path.read_text())["quality"]["fields_low_confidence"] == ["key"]
