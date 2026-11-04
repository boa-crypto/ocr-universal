import pytest
from unocr.ocr_engines import EngineRegistry

def test_registry_includes_baidu():
    registry = EngineRegistry()
    engine = registry.get("baidu")
    assert engine is not None
    # Check if Baidu OCR is correctly identified as not available
    # (since BAIDU_API_KEY env var is likely missing in the test environment)
    assert not engine.is_available()
    assert "Clés API Baidu manquantes" in engine.unavailable_reason
