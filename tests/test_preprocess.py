"""Tests prétraitement : analyse qualité, deskew, pipeline adaptatif."""
from PIL import Image, ImageDraw

from unocr.preprocess import analyze_quality, detect_columns_projection, preprocess_page


def _doc_image(w=800, h=400, bg="white"):
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    for i in range(6):
        d.rectangle([60, 50 + i * 50, w - 60, 50 + i * 50 + 8], fill="black")
    return img


def test_analyze_quality_clean():
    q = analyze_quality(_doc_image())
    assert q.brightness > 150
    assert not q.is_blank
    assert q.blur_score > 0


def test_analyze_quality_detects_dark():
    q = analyze_quality(_doc_image(bg=(25, 25, 25)))
    assert "dark" in q.issues


def test_analyze_quality_detects_blank():
    q = analyze_quality(Image.new("RGB", (400, 300), "white"))
    assert q.is_blank
    assert "nearly_blank" in q.issues


def test_deskew_corrects_rotation():
    base = _doc_image()
    skewed = base.rotate(8, expand=True, fillcolor="white")
    q = analyze_quality(skewed)
    assert abs(q.estimated_skew_deg) > 2
    res = preprocess_page(skewed, q)
    assert any(op.name == "deskew" and op.applied for op in res.ops)


def test_preprocess_preserves_clean_image():
    """Une image propre ne doit pas subir de transformations inutiles."""
    img = _doc_image()
    q = analyze_quality(img)
    res = preprocess_page(img, q)
    aggressive = [op for op in res.ops if op.name in ("binarize", "denoise", "shadow_removal")]
    assert not aggressive


def test_column_detection():
    img = Image.new("RGB", (800, 400), "white")
    d = ImageDraw.Draw(img)
    for i in range(8):
        d.rectangle([40, 30 + i * 40, 360, 30 + i * 40 + 8], fill="black")
        d.rectangle([440, 30 + i * 40, 760, 30 + i * 40 + 8], fill="black")
    cols = detect_columns_projection(img)
    assert len(cols) == 2
