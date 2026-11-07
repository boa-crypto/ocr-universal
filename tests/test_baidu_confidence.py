"""Scores Baidu : réponses synthétiques locales, pas précision OCR mesurée."""
import pytest
from PIL import Image

from unocr import baidu_http
from unocr.models import BBox, DocumentResult, PageResult, Word
from unocr.ocr_engines import BaiduOCREngine, EngineOutput, consensus_merge
from unocr.quality import build_quality_report


@pytest.fixture
def output(monkeypatch):
    for name in ("BAIDU_OCR_API_KEY", "BAIDU_API_KEY", "BAIDU_OCR_SECRET_KEY", "BAIDU_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("BAIDU_API_KEY", "FAKE66")
    monkeypatch.setenv("BAIDU_SECRET_KEY", "FAKE66")

    def recognize(items):
        calls = []

        def post(url, **kwargs):
            calls.append(url)
            if url == baidu_http.TOKEN_URL:
                return {"access_token": "FAKE66-TOKEN"}
            return {"words_result": items}

        monkeypatch.setattr(baidu_http, "post_json", post)
        result = BaiduOCREngine().recognize(Image.new("RGB", (100, 30), "white"))
        assert calls == [baidu_http.TOKEN_URL, baidu_http.OCR_URL]
        assert result.ok
        return result

    return recognize


def provenance(result, reported=0, missing=0, invalid=0):
    assert result.raw == {"confidence": {
        "policy": "provider_average_else_zero", "calibrated": False,
        "reported": reported, "missing": missing, "invalid": invalid}}


@pytest.mark.parametrize("score", [0, 1, 0.2, 0.95, 1.0])
def test_reported_numeric_score_preserved_without_promotion(output, score):
    result = output([{"words": "texte", "probability": {"average": score}}])
    assert result.words[0].confidence == score
    assert result.mean_confidence == score
    provenance(result, reported=1)


@pytest.mark.parametrize("probability", [
    None, True, False, "0.99", 0.99, [], {},
    {"average": None}, {"average": True}, {"average": False},
    {"average": "0.99"}, {"average": -0.1}, {"average": 1.01},
    {"average": float("nan")}, {"average": float("inf")},
    {"average": float("-inf")}, {"average": []}, {"average": {}},
    {"average": 10 ** 1000},
])
def test_invalid_score_never_becomes_high_confidence(output, probability):
    result = output([{"words": "texte", "probability": probability}])
    assert result.text == "texte"
    assert result.words[0].confidence == 0
    assert result.mean_confidence == 0
    provenance(result, invalid=1)


def test_absent_score_is_conservative_not_095(output):
    result = output([{"words": "texte"}])
    assert result.words[0].confidence == result.mean_confidence == 0
    provenance(result, missing=1)


def test_all_items_count_in_mean_including_missing_invalid_and_zero(output):
    result = output([
        {"words": "a", "probability": {"average": 1}},
        {"words": "b", "probability": {"average": 0}},
        {"words": "c"}, {"words": "d", "probability": {"average": "0.99"}},
    ])
    assert [word.confidence for word in result.words] == [1, 0, 0, 0]
    assert result.mean_confidence == 0.25
    provenance(result, reported=2, missing=1, invalid=1)


def test_empty_result_has_zero_mean_and_no_fabricated_count(output):
    result = output([])
    assert result.text == "" and result.words == [] and result.mean_confidence == 0
    provenance(result)


def test_unknown_baidu_score_cannot_outrank_reported_competitor(output):
    baidu = output([{"words": "Baidu"}])
    other = EngineOutput(engine="unit-test", text="autre", mean_confidence=0.7,
                         words=[Word(text="autre", bbox=BBox(x0=0, y0=0, x1=10, y1=10),
                                     confidence=0.7, engine="unit-test")])
    merged = consensus_merge([baidu, other])
    assert merged.chosen_engine == "unit-test"
    assert merged.mean_confidence == 0.7
    assert merged.disagreements


def test_unknown_score_reaches_quality_report_and_review_list(output):
    baidu = output([{"words": "texte"}])
    merged = consensus_merge([baidu])
    page = PageResult(page_num=1, width=100, height=30, words=merged.words, text=merged.text)
    document = DocumentResult(pages=[page])
    report = build_quality_report(document, review_threshold=0.7)
    assert report.mean_engine_confidence == 0
    assert report.mean_global_confidence == 0
    assert report.pages_low_confidence == [1]


def test_pipeline_keeps_unknown_score_zero_in_runs_words_and_quality(output, tmp_cfg):
    from PIL import ImageDraw

    from unocr.ingest import LoadedPage
    from unocr.models import JobOptions
    from unocr.pipeline import Pipeline

    # Installe la réponse distante factice, pas un moteur OCR de remplacement.
    output([{"words": "texte"}])
    engine = BaiduOCREngine()

    class Registry:
        def get(self, name):
            return engine if name == "baidu" else None

        def select(self, **kwargs):
            return [engine]

    image = Image.new("RGB", (400, 150), "white")
    ImageDraw.Draw(image).rectangle((20, 30, 300, 55), fill="black")
    page = LoadedPage(page_num=1, width=400, height=150, image=image)
    result = Pipeline(tmp_cfg, Registry())._process_page(
        page, JobOptions(quality_mode="fast", preprocess=False), 0, 1)
    assert result.text == "texte"
    assert result.words[0].confidence == 0
    assert len(result.engine_runs) == 1
    assert result.engine_runs[0].mean_confidence == 0
    assert result.engine_runs[0].ok
    report = build_quality_report(DocumentResult(pages=[result]))
    assert report.mean_global_confidence == 0
    assert report.pages_low_confidence == [1]
