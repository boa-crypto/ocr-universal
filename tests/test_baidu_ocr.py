from unocr.ocr_engines import EngineRegistry


def test_registry_includes_baidu(monkeypatch):
    for name in ("BAIDU_OCR_API_KEY", "BAIDU_API_KEY", "BAIDU_OCR_SECRET_KEY", "BAIDU_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    registry = EngineRegistry()
    engine = registry.get("baidu")
    assert engine is not None
    # Check if Baidu OCR is correctly identified as not available
    # (since BAIDU_API_KEY env var is likely missing in the test environment)
    assert not engine.is_available()
    assert "Clés API Baidu manquantes" in engine.unavailable_reason
