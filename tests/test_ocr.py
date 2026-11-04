"""Tests OCR : Tesseract réel, registre, sélection, consensus (moteurs simulés)."""
from PIL import Image, ImageDraw, ImageFont

from unocr.models import BBox, Word
from unocr.ocr_engines import (
    EngineOutput,
    EngineRegistry,
    OCREngine,
    TesseractEngine,
    consensus_merge,
)


def _text_image(text: str, size=22) -> Image.Image:
    img = Image.new("RGB", (700, 80), "white")
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        f = ImageFont.load_default()
    d.text((15, 25), text, fill="black", font=f)
    return img


class FakeEngine(OCREngine):
    def __init__(self, name, words, conf):
        self.name = name
        self._words = words
        self._conf = conf

    def is_available(self):
        return True

    def supported_languages(self):
        return ["fra", "eng"]

    def recognize(self, image, languages=None, page_num=1):
        return EngineOutput(engine=self.name, text=" ".join(self._words),
                            words=[Word(text=t, bbox=BBox(x0=i * 20, y0=0, x1=i * 20 + 18, y1=20),
                                        confidence=self._conf, engine=self.name)
                                   for i, t in enumerate(self._words)],
                            mean_confidence=self._conf)


def test_tesseract_available():
    eng = TesseractEngine()
    assert eng.is_available()
    assert "fra" in eng.supported_languages()


def test_modele_arabe_installe():
    """Le modèle arabe doit être présent : sans lui, l'OCR arabe est muet.

    C'est une dépendance *système* (`tesseract-ocr-ara`). Sur une machine
    qui ne l'a pas, le test est inapplicable — pas en échec.
    """
    import pytest

    from unocr.ocr_engines import TesseractEngine
    if "ara" not in TesseractEngine().supported_languages():
        pytest.skip("modèle tessdata « ara » absent (paquet tesseract-ocr-ara)")
    assert "ara" in TesseractEngine().supported_languages()


def test_tesseract_recognize_real():
    eng = TesseractEngine()
    out = eng.recognize(_text_image("FACTURE 2024-001"), ["fra", "eng"])
    assert out.ok
    assert "FACTURE" in out.text.replace(" ", "") or "FACTURE" in out.text
    assert 0 < out.mean_confidence <= 1
    assert out.words  # boîtes géométriques présentes


def test_registry_reports_availability_honestly():
    reg = EngineRegistry()
    engines = {e["name"]: e for e in reg.list_engines()}
    assert engines["tesseract"]["available"] is True
    assert engines["native_pdf"]["available"] is True
    # Vérification dynamique basée sur l'installation réelle
    from unocr.ocr_engines import EasyOCREngine, PaddleOCREngine
    assert engines["easyocr"]["available"] == EasyOCREngine().is_available()
    assert engines["paddleocr"]["available"] == PaddleOCREngine().is_available()


def test_selection_prefers_native_when_present():
    reg = EngineRegistry()
    selected = reg.select(has_native_text=True)
    names = [e.name for e in selected]
    assert "native_pdf" in names
    # Indra is now preferred over tesseract as the first raster engine
    assert "indra" in names


def test_consensus_keeps_best_and_flags_disagreement():
    a = FakeEngine("engine_a", ["bonjour", "le", "monde"], 0.9)
    b = FakeEngine("engine_b", ["bonjour", "le", "mond"], 0.7)
    merged = consensus_merge([a.recognize(None), b.recognize(None)], page_num=1)
    assert merged.chosen_engine == "engine_a"
    assert merged.disagreements  # désaccord signalé, pas masqué
    assert "bonjour" in merged.text


def test_consensus_not_majority_vote():
    """Deux moteurs faibles ne doivent pas écraser un moteur fort."""
    weak1 = FakeEngine("weak1", ["TROU", "ECRIT"], 0.3)
    weak2 = FakeEngine("weak2", ["TROU", "ECRIT"], 0.35)
    strong = FakeEngine("strong", ["TEXTE", "EXACT"], 0.95)
    merged = consensus_merge([weak1.recognize(None), weak2.recognize(None),
                              strong.recognize(None)])
    assert merged.chosen_engine == "strong"
    assert merged.text == "TEXTE EXACT"


def test_consensus_all_failed():
    class Broken(OCREngine):
        name = "broken"
        def is_available(self): return False
        def supported_languages(self): return []
        def recognize(self, image, languages=None, page_num=1):
            return EngineOutput(engine="broken", text="", ok=False, error="boom")
    merged = consensus_merge([Broken().recognize(None)])
    assert merged.text == ""
    assert merged.words == []
