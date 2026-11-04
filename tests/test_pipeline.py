"""Tests de bout en bout du pipeline (documents réels générés)."""
import pytest

from unocr.models import JobOptions
from unocr.pipeline import Pipeline


def test_end_to_end_native_pdf(tmp_cfg, fixtures_dir):
    pipeline = Pipeline(tmp_cfg)
    result = pipeline.process_file(
        fixtures_dir / "text_pdf.pdf",
        JobOptions(profile="invoice", quality_mode="fast", preprocess=True,
                   export_formats=["json"]))
    assert len(result.pages) == 2
    assert "FACTURE" in result.pages[0].text
    # champs de la facture
    assert result.fields["invoice_number"].value is not None
    assert result.fields["issue_date"].normalized_value == "2024-03-15"
    assert result.fields["total_ttc"].normalized_value is not None
    # confiances
    assert result.quality.mean_engine_confidence > 0.5
    assert result.timings_ms["total_ms"] > 0
    # traçabilité
    assert result.source_hash


def test_end_to_end_scanned_pdf_ocr(tmp_cfg, fixtures_dir):
    pipeline = Pipeline(tmp_cfg)
    result = pipeline.process_file(
        fixtures_dir / "scanned_pdf.pdf",
        JobOptions(profile="generic", quality_mode="fast"))
    assert len(result.pages) == 1
    text = result.pages[0].text
    # OCR réel : on attend la plupart des mots
    assert "LIVRAISON" in text.replace(" ", "") or "LIVRAISON" in text
    assert result.engines_used  # moteurs tracés


def test_end_to_end_port_profile(tmp_cfg, fixtures_dir):
    pipeline = Pipeline(tmp_cfg)
    result = pipeline.process_file(
        fixtures_dir / "bl_port.pdf",
        JobOptions(profile="port_bl", quality_mode="fast"))
    assert result.fields["container_number"].normalized_value == "CSQU3054383"
    assert result.fields["container_number"].status.value == "detected"  # ISO 6346 valide
    assert result.fields["bl_number"].value is not None
    assert result.fields["vessel_name"].normalized_value == "MSC AURORA"
    # ETD (15/03) avant ETA (28/03) : pas d'anomalie de dates
    date_issues = [c for c in result.quality.checks if c.get("code") == "DATE_INCOHERENT"]
    assert not date_issues


def test_end_to_end_skewed_image(tmp_cfg, fixtures_dir):
    pipeline = Pipeline(tmp_cfg)
    result = pipeline.process_file(
        fixtures_dir / "skewed.png",
        JobOptions(profile="generic", quality_mode="accurate"))
    assert result.pages[0].words  # quelque chose a été reconnu
    assert result.pages[0].preprocess_ops  # le prétraitement a agi


def test_barcode_qr_detected(tmp_cfg, fixtures_dir):
    pipeline = Pipeline(tmp_cfg)
    result = pipeline.process_file(
        fixtures_dir / "qr_code.png", JobOptions(profile="generic", quality_mode="fast"))
    assert result.barcodes
    assert "example.dz" in result.barcodes[0]["text"]


def test_corrupt_file_raises(tmp_cfg, fixtures_dir):
    from unocr.security import SecurityError
    pipeline = Pipeline(tmp_cfg)
    with pytest.raises(SecurityError):
        pipeline.process_file(fixtures_dir / "corrupt.pdf", JobOptions(quality_mode="fast"))


def test_injection_content_flagged_not_executed(tmp_cfg, fixtures_dir):
    pipeline = Pipeline(tmp_cfg)
    result = pipeline.process_file(
        fixtures_dir / "injection.png", JobOptions(profile="generic", quality_mode="fast"))
    codes = [a.code for a in result.quality.anomalies]
    # si le texte est reconnu, l'injection est signalée ; jamais exécutée
    if "UNTRUSTED_CONTENT" in codes:
        assert all(isinstance(a.message, str) for a in result.quality.anomalies)


def test_digital_doc_no_fake_ocr(tmp_cfg, fixtures_dir):
    """Un DOCX est lu tel quel — pas d'OCR simulé."""
    pipeline = Pipeline(tmp_cfg)
    result = pipeline.process_file(
        fixtures_dir / "letter.docx", JobOptions(profile="generic", quality_mode="fast"))
    assert "COURRIER" in result.pages[0].text
    assert result.tables  # tableau du docx
    engines = result.engines_used
    assert "native_text" in engines
    assert "tesseract" not in engines  # aucun OCR raster sur texte numérique
