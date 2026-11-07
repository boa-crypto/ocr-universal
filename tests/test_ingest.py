"""Tests ingestion : formats variés, multipage, corrompu."""
import pytest

from unocr.ingest import detect_format, load_document
from unocr.security import SecurityError


def test_detect_format(fixtures_dir):
    assert detect_format(fixtures_dir / "text_pdf.pdf") == "pdf"
    assert detect_format(fixtures_dir / "skewed.png") == "png"
    assert detect_format(fixtures_dir / "letter.docx") == "docx"
    assert detect_format(fixtures_dir / "data.csv") == "csv"


def test_load_native_pdf_multipage(fixtures_dir):
    doc = load_document(fixtures_dir / "text_pdf.pdf", dpi=150)
    assert doc.format == "pdf"
    assert len(doc.pages) == 2
    assert "FACTURE" in doc.pages[0].native_text
    assert any(w.text == "FACTURE" for w in doc.pages[0].native_words)
    # boîtes géométriques cohérentes
    w = next(w for w in doc.pages[0].native_words if w.text == "FACTURE")
    assert w.bbox.x1 > w.bbox.x0
    assert w.confidence > 0.9


def test_load_scanned_pdf_has_image(fixtures_dir):
    doc = load_document(fixtures_dir / "scanned_pdf.pdf", dpi=150)
    assert len(doc.pages) == 1
    assert doc.pages[0].image is not None
    assert doc.pages[0].kind == "pdf_scan"


def test_load_image(fixtures_dir):
    doc = load_document(fixtures_dir / "skewed.png")
    assert doc.pages[0].image is not None
    assert doc.pages[0].width > 0


def test_load_docx(fixtures_dir):
    doc = load_document(fixtures_dir / "letter.docx")
    assert doc.format == "docx"
    assert "COURRIER" in doc.pages[0].native_text
    assert doc.digital_tables  # tableau du docx


def test_load_csv(fixtures_dir):
    doc = load_document(fixtures_dir / "data.csv")
    assert doc.digital_tables
    t = doc.digital_tables[0]
    assert t.n_rows == 3
    assert t.to_matrix()[0] == ["ref", "designation", "quantite", "prix"]


def test_corrupt_pdf_raises(fixtures_dir):
    with pytest.raises(SecurityError):
        load_document(fixtures_dir / "corrupt.pdf")


def test_page_limit_est_verifie_avant_extraction_et_rendu_pdf(fixtures_dir,
                                                              monkeypatch):
    import pdfminer.high_level
    import pypdfium2

    class Pdf:
        closed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

        def __len__(self):
            return 2

        def __getitem__(self, index):
            pytest.fail("page demandée avant refus de limite")

    pdf = Pdf()
    monkeypatch.setattr(pypdfium2, "PdfDocument", lambda _path: pdf)
    monkeypatch.setattr(pdfminer.high_level, "extract_pages",
                        lambda *args, **kwargs: pytest.fail("extraction trop tôt"))
    with pytest.raises(SecurityError, match="trop de pages"):
        load_document(fixtures_dir / "text_pdf.pdf", max_pages=1)
    assert pdf.closed
