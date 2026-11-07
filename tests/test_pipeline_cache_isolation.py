"""Régressions de cache : doubles unitaires, pas une qualification OCR réelle."""
import io

import pytest
from PIL import Image, ImageDraw

from unocr.cache import PageCache
from unocr.ingest import LoadedPage
from unocr.models import BBox, EngineRun, JobOptions, PageResult, Word
from unocr.ocr_engines import EngineOutput, NativeTextEngine
from unocr.pipeline import Pipeline


class Raster:
    name = "tesseract"
    kind = "raster"

    def __init__(self):
        self.calls = 0
        self.available = True
        self.text = "CURRENT"

    def supported_languages(self):
        return ["eng"]

    def recognize(self, image, languages, page_num):
        self.calls += 1
        return EngineOutput(
            engine=self.name, text=self.text, mean_confidence=0.9,
            words=[Word(text=self.text, page_num=page_num, engine=self.name,
                        confidence=0.9, bbox=BBox(x0=10, y0=10, x1=100, y1=40))])


class Registry:
    def __init__(self, raster):
        self.raster = raster
        self.native = NativeTextEngine()

    def get(self, name):
        return {"tesseract": self.raster, "native_pdf": self.native}.get(name)

    def select(self, **kwargs):
        return [self.raster] if self.raster.available else []


@pytest.fixture
def context(tmp_cfg):
    image = Image.new("RGB", (400, 150), "white")
    ImageDraw.Draw(image).rectangle((20, 30, 300, 55), fill="black")
    page = LoadedPage(page_num=1, width=400, height=150, image=image)
    raster = Raster()
    return Pipeline(tmp_cfg, Registry(raster)), page, raster


def process(pipeline, page, **kwargs):
    return pipeline._process_page(page, JobOptions(**kwargs), 0, 1)


@pytest.mark.parametrize("options", [
    {}, {"engine": "tesseract"}, {"preprocess_mode": "off"},
    {"preprocess_mode": "standard"}, {"preprocess_mode": "aggressive"},
    {"variant_comparison": False}, {"languages": ["eng"]},
    {"quality_mode": "fast"},
])
def test_legacy_pixel_cache_cannot_override_request(context, options):
    pipeline, page, raster = context
    encoded = io.BytesIO()
    page.image.save(encoded, format="PNG")
    pixels = encoded.getvalue()
    cache = PageCache()
    obsolete = PageResult(page_num=99, width=400, height=150, text="OBSOLETE", engine_runs=[
        EngineRun(engine="native_pdf", page_num=99, ok=True)])
    cache.set(pixels, obsolete)
    result = process(pipeline, page, **options)
    assert raster.calls >= 1
    assert result.text == "CURRENT"
    assert all(r.engine == "tesseract" for r in result.engine_runs)
    # Pas de suppression ni d'écrasement des données historiques.
    assert cache.get(pixels).model_dump() == obsolete.model_dump()


def test_repeated_pixels_reexecute_engine(context):
    pipeline, page, raster = context
    first = process(pipeline, page, preprocess=False)
    raster.text = "UPDATED"
    second = process(pipeline, page, preprocess=False)
    assert first.text == "CURRENT"
    assert second.text == "UPDATED"
    assert raster.calls == 2


def test_page_numbers_are_not_recycled(context):
    pipeline, page, raster = context
    first = process(pipeline, page, preprocess=False)
    page.page_num = 7
    second = process(pipeline, page, preprocess=False)
    assert first.page_num == 1
    assert second.page_num == 7
    assert all(w.page_num == 7 for w in second.words)
    assert all(r.page_num == 7 for r in second.engine_runs)
    assert raster.calls == 2


def test_engine_unavailable_does_not_replay_success(context):
    pipeline, page, raster = context
    assert process(pipeline, page, preprocess=False).text == "CURRENT"
    raster.available = False
    result = process(pipeline, page, preprocess=False)
    assert result.text == ""
    assert result.engine_runs == []
    assert raster.calls == 1


def test_native_then_forced_raster_same_pixels(context):
    pipeline, page, raster = context
    page.native_text = "NATIVE"
    page.native_words = [Word(text="NATIVE", confidence=0.95,
                              bbox=BBox(x0=10, y0=10, x1=100, y1=40))]
    first = process(pipeline, page, engine="native", preprocess=False)
    assert first.text == "NATIVE"
    second = process(pipeline, page, engine="tesseract", preprocess=False)
    assert second.text == "CURRENT"
    assert all(r.engine == "tesseract" for r in second.engine_runs)
    assert raster.calls == 1
