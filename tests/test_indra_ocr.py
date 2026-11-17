import pytest
from PIL import Image

from unocr.ocr_engines import EngineRegistry, IndraEngine


def test_indra_engine_availability():
    engine = IndraEngine()
    # It should be available based on pip list
    assert engine.is_available()

def test_indra_engine_recognize():
    engine = IndraEngine()
    if not engine.is_available():
        pytest.skip("Indra engine not available")

    img = Image.new('RGB', (300, 100), color=(255, 255, 255))
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    d.text((10, 10), 'Hello Indra', fill=(0,0,0))

    output = engine.recognize(img)
    assert output.ok
    assert 'Hello' in output.text
    assert len(output.words) > 0

def test_registry_includes_indra():
    registry = EngineRegistry()
    assert registry.get("indra") is not None
