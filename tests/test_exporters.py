"""Tests exports : TXT, JSON, CSV, XLSX, XML, PDF consultable."""
import json
import xml.etree.ElementTree as ET

from unocr.exporters import (
    export_all,
    export_csv,
    export_json,
    export_txt,
    export_xlsx,
    export_xml,
)
from unocr.models import (
    BBox,
    Cell,
    DocumentResult,
    FieldStatus,
    FieldValue,
    PageResult,
    QualityReport,
    Table,
    Word,
)


def _small_result() -> DocumentResult:
    res = DocumentResult(source_file="test.pdf")
    words = [Word(text="FACTURE", bbox=BBox(x0=10, y0=10, x1=100, y1=40), confidence=0.9)]
    res.pages.append(PageResult(page_num=1, width=600, height=800,
                                text="FACTURE 2024-001", words=words))
    res.fields["invoice_number"] = FieldValue(
        name="invoice_number", label="N° facture", raw_value="2024-001",
        normalized_value="2024-001", confidence=0.9, engine_confidence=0.9,
        page_num=1, status=FieldStatus.DETECTED)
    res.fields["email"] = FieldValue(name="email", label="E-mail",
                                     raw_value=None, status=FieldStatus.NOT_DETECTED)
    res.tables.append(Table(page_num=1, n_rows=2, n_cols=2,
                            cells=[Cell(row=0, col=0, text="=DANGER"),
                                   Cell(row=0, col=1, text="OK"),
                                   Cell(row=1, col=0, text="1"),
                                   Cell(row=1, col=1, text="2")]))
    res.quality = QualityReport(mean_engine_confidence=0.9, mean_global_confidence=0.85)
    return res


def test_txt_export(tmp_path):
    res = _small_result()
    p = export_txt(res, tmp_path / "out.txt")
    content = p.read_text(encoding="utf-8")
    assert "FACTURE 2024-001" in content
    assert "--- Page 1 ---" in content


def test_json_export_roundtrip(tmp_path):
    res = _small_result()
    p = export_json(res, tmp_path / "out.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["fields"]["invoice_number"]["raw_value"] == "2024-001"
    assert data["fields"]["email"]["raw_value"] is None


def test_csv_export_protects_formula(tmp_path):
    res = _small_result()
    paths = export_csv(res, tmp_path)
    table_csv = [p for p in paths if p.name.startswith("table_")][0]
    content = table_csv.read_text(encoding="utf-8-sig")
    assert "'=DANGER" in content  # neutralisé
    assert "=DANGER" not in content.replace("'=DANGER", "")


def test_xlsx_export(tmp_path):
    res = _small_result()
    p = export_xlsx(res, tmp_path / "out.xlsx")
    assert p.stat().st_size > 500
    from openpyxl import load_workbook
    wb = load_workbook(p)
    assert set(wb.sheetnames) >= {"Champs", "Tables", "Texte", "Métadonnées"}


def test_xml_export_escapes(tmp_path):
    res = _small_result()
    res.pages[0].text = 'texte avec <balise> & "guillemets"'
    p = export_xml(res, tmp_path / "out.xml")
    tree = ET.parse(p)  # doit être bien formé malgré les caractères spéciaux
    assert tree.getroot().tag == "document"


def test_export_all_with_searchable_pdf(tmp_path):
    from pdfminer.high_level import extract_text
    from PIL import Image, ImageDraw
    res = _small_result()
    img = Image.new("RGB", (600, 800), "white")
    ImageDraw.Draw(img).text((10, 10), "FACTURE 2024-001", fill="black")
    records = export_all(res, tmp_path,
                         ["txt", "json", "csv", "xlsx", "xml", "pdf"],
                         page_images={1: img})
    fmts = {r.format for r in records}
    assert {"txt", "json", "csv", "xlsx", "xml", "pdf"} <= fmts
    # le PDF consultable contient une couche texte réellement extractible
    extracted = extract_text(tmp_path / "searchable.pdf")
    assert "FACTURE" in extracted
