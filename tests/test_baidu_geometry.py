"""Coordonnées distantes synthétiques : pas qualification géométrique fournisseur."""
import json
from dataclasses import asdict

import pytest
from PIL import Image, ImageDraw

from unocr import baidu_http
from unocr.baidu_response import InvalidLocation, bbox_from_location
from unocr.ingest import LoadedPage
from unocr.models import DocumentResult, JobOptions
from unocr.ocr_engines import BaiduOCREngine
from unocr.pipeline import Pipeline
from unocr.quality import build_quality_report

LOCATION = {"left": 1, "top": 2, "width": 10, "height": 5}
PRIVATE = "FAKE69-PRIVATE"


@pytest.fixture
def recognize(monkeypatch):
    for key in ("BAIDU_OCR_API_KEY", "BAIDU_API_KEY", "BAIDU_OCR_SECRET_KEY", "BAIDU_SECRET_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("BAIDU_API_KEY", "FAKE69")
    monkeypatch.setenv("BAIDU_SECRET_KEY", "FAKE69")
    engine = BaiduOCREngine()

    def setup(items):
        def post(url, **kwargs):
            if url == baidu_http.TOKEN_URL:
                return {"access_token": "FAKE69"}
            return {"words_result": items}
        monkeypatch.setattr(baidu_http, "post_json", post)
        return engine.recognize(Image.new("RGB", (100, 30), "white"), page_num=7)
    return setup


@pytest.mark.parametrize("location,expected", [
    (LOCATION, [1, 2, 11, 7]),
    ({"left": 0, "top": 0, "width": 100, "height": 30}, [0, 0, 100, 30]),
    ({"left": 1.25, "top": 2.5, "width": 0.5, "height": 0.25}, [1.25, 2.5, 1.75, 2.75]),
    ({"left": 99, "top": 29, "width": 1, "height": 1}, [99, 29, 100, 30]),
    ({**LOCATION, "ignored": PRIVATE}, [1, 2, 11, 7]),
])
def test_declared_valid_box_preserved_without_clipping(recognize, location, expected):
    out = recognize([{"words": "texte", "location": location, "probability": {"average": 0.8}}])
    assert out.ok and out.words[0].bbox.as_list() == expected
    assert out.words[0].page_num == 7
    assert out.words[0].confidence == out.mean_confidence == 0.8
    assert PRIVATE not in json.dumps(asdict(out), default=lambda value: value.model_dump())


@pytest.mark.parametrize("location", [None, False, 0, "", [], {}, PRIVATE])
def test_present_falsy_or_non_object_location_is_not_missing(recognize, location, caplog):
    out = recognize([{"words": PRIVATE, "location": location}])
    assert not out.ok and out.text == "" and out.words == [] and out.raw == {}
    assert out.error == "Baidu : localisation invalide"
    assert PRIVATE not in json.dumps(asdict(out)) + caplog.text


@pytest.mark.parametrize("key", list(LOCATION))
def test_each_coordinate_is_required(recognize, key):
    loc = dict(LOCATION)
    del loc[key]
    out = recognize([{"words": "texte", "location": loc}])
    assert not out.ok and out.words == []


@pytest.mark.parametrize("key,value", [
    ("left", True), ("top", False), ("width", "10"), ("height", None),
    ("left", PRIVATE), ("top", []), ("height", {}),
    ("left", float("nan")), ("top", float("inf")), ("width", float("-inf")),
    ("height", float("nan")), ("left", -1), ("top", -1), ("width", -1),
    ("height", -1), ("width", 0), ("height", 0),
    ("left", 100), ("top", 30), ("left", 101), ("top", 31),
    ("width", 100), ("height", 30), ("width", 101), ("height", 31),
    ("left", 10**1000), ("width", 10**1000),
    ("width", 5e-324),  # Un ajout arrondi à x ne doit pas produire largeur nulle.
])
def test_invalid_coordinate_rejects_entire_response_privately(recognize, key, value, caplog):
    loc = {**LOCATION, key: value}
    out = recognize([
        {"words": "valid-first", "location": LOCATION, "probability": {"average": 1}},
        {"words": PRIVATE, "location": loc},
    ])
    assert not out.ok and out.words == [] and out.text == "" and out.raw == {}
    assert out.mean_confidence == 0
    assert out.error == "Baidu : localisation invalide"
    assert PRIVATE not in json.dumps(asdict(out)) + caplog.text


def test_float_area_underflow_is_refused(recognize):
    loc = {"left": 0, "top": 0, "width": 5e-324, "height": 5e-324}
    assert not recognize([{"words": "texte", "location": loc}]).ok


def test_absent_location_keeps_legacy_approximation_and_score_policy(recognize):
    out = recognize([{"words": "texte"}])
    assert out.ok and out.words[0].bbox.as_list() == [0, 0, 100, 30]
    assert out.mean_confidence == 0
    assert out.raw["confidence"]["missing"] == 1


@pytest.mark.parametrize("width,height", [(0, 30), (-1, 30), (True, 30), (100.0, 30),
                                         (100, 0), (100, 2**31), (10**1000, 30)])
def test_helper_rejects_invalid_image_dimensions(width, height):
    with pytest.raises(InvalidLocation):
        bbox_from_location(LOCATION, width, height)


def test_failed_geometry_reaches_run_and_review_without_partial_words(recognize, tmp_cfg):
    recognize([{"words": PRIVATE, "location": {**LOCATION, "width": "10"}}])
    engine = BaiduOCREngine()

    class Registry:
        def get(self, name):
            return engine if name == "baidu" else None

        def select(self, **kwargs):
            return [engine]

    image = Image.new("RGB", (400, 150), "white")
    ImageDraw.Draw(image).rectangle((20, 30, 300, 55), fill="black")
    result = Pipeline(tmp_cfg, Registry())._process_page(
        LoadedPage(page_num=1, width=400, height=150, image=image),
        JobOptions(quality_mode="fast", preprocess=False), 0, 1)
    assert result.words == [] and result.text == ""
    assert len(result.engine_runs) == 1
    run = result.engine_runs[0]
    assert not run.ok and run.error == "Baidu : localisation invalide"
    assert run.confidence_provenance is None
    assert PRIVATE not in result.model_dump_json()
    report = build_quality_report(DocumentResult(pages=[result]))
    assert report.mean_global_confidence == 0
    assert any(anomaly.code == "OCR_FAILED" and anomaly.page_num == 1 for anomaly in report.anomalies)
    # La liste existante ne comprend pas les pages sans mots/texte : pas corrigé ici.
    assert report.pages_low_confidence == []
