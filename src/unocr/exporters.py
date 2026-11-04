"""Export des résultats : TXT, JSON, CSV, XLSX, XML, PDF consultable.

Sécurité : échappement XML systématique, protection CSV/XLSX contre l'injection
de formules, jamais d'exécution de contenu extrait.
"""
from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

from .logging_setup import get_logger
from .models import DocumentResult, ExportRecord
from .security import sanitize_for_csv

log = get_logger("export")


# ---------------------------------------------------------------- TXT
def export_txt(result: DocumentResult, out: Path) -> Path:
    parts = []
    for page in result.pages:
        parts.append(f"--- Page {page.page_num} ---\n{page.text}")
    out.write_text("\n\n".join(parts), encoding="utf-8")
    return out


# ---------------------------------------------------------------- JSON
def export_json(result: DocumentResult, out: Path) -> Path:
    data = result.model_dump(mode="json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


# ---------------------------------------------------------------- CSV
#: ce que `value_origin` veut dire, en clair. Un export doit être lisible par
#: quelqu'un qui n'a pas le code sous les yeux : « corrected » seul ne dit pas
#: si c'est une règle métier ou une faute de frappe du concepteur.
LIBELLES_ORIGINE = {
    "raw": "transcription moteur",
    "normalized": "normalisation automatique",
    "corrected": "règle métier",
    "confirmed": "validé par un humain",
}


def _origine(fv) -> str:
    """Origine de la valeur affichée, en clair.

    C'est la colonne qui distingue une donnée **extraite** d'une donnée
    **interprétée** : sans elle, un export présente sur le même plan une
    transcription OCR et une valeur tranchée par un humain.
    """
    valeur = getattr(fv.value_origin, "value", fv.value_origin)
    return LIBELLES_ORIGINE.get(str(valeur), str(valeur))


def _zone(fv) -> str:
    """Zone source du champ, ou chaîne vide si elle n'est pas connue.

    Une alerte sans zone source oblige à relire tout le document pour la
    vérifier. La zone est donc exportée quand le moteur l'a fournie — et
    laissée vide, jamais inventée, quand il ne l'a pas fait.
    """
    bbox = getattr(fv, "bbox", None)
    if bbox is None:
        return ""
    try:
        return "x0=%s y0=%s x1=%s y1=%s" % (bbox.x0, bbox.y0, bbox.x1, bbox.y1)
    except AttributeError:
        return ""


def export_csv(result: DocumentResult, out_dir: Path,
              champs_seulement: bool = False) -> list[Path]:
    """Écrit les champs en CSV, puis un CSV par tableau.

    `champs_seulement` ne produit que le fichier des champs : c'est le bon
    comportement pour un export *d'une sélection de champs*, où les
    tableaux du document n'ont rien à y faire. Sans ce drapeau, l'export
    ciblé CSV devait emballer le tout dans un ZIP — une archive que ni
    l'utilisateur ni un tableur n'attendent, et qui casse le format « un
    CSV = une sélection ».
    """
    paths: list[Path] = []

    fields_path = out_dir / "fields.csv"
    with fields_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["name", "label", "raw_value", "normalized_value", "corrected_value",
                    "confirmed_value", "origine", "source", "zone",
                    "confidence", "engine_confidence", "status", "page"])
        for name, fv in result.fields.items():
            w.writerow([
                sanitize_for_csv(name), sanitize_for_csv(fv.label),
                sanitize_for_csv(fv.raw_value), sanitize_for_csv(fv.normalized_value),
                sanitize_for_csv(fv.corrected_value), sanitize_for_csv(fv.confirmed_value),
                sanitize_for_csv(_origine(fv)), sanitize_for_csv(fv.source),
                sanitize_for_csv(_zone(fv)),
                fv.confidence, fv.engine_confidence, fv.status.value,
                fv.page_num,
            ])
    paths.append(fields_path)

    if champs_seulement:
        return paths

    for i, table in enumerate(result.tables):
        p = out_dir / f"table_{i + 1}_p{table.page_num}.csv"
        with p.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            for row in table.to_matrix():
                w.writerow([sanitize_for_csv(c) for c in row])
        paths.append(p)
    return paths


# ---------------------------------------------------------------- XLSX
def export_xlsx(result: DocumentResult, out: Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Champs"
    # La provenance fait partie des données exportées, pas d'un détail optionnel :
    # `origine` dit si la valeur est extraite ou interprétée, `source` quel
    # chemin l'a produite, `zone` où la relire sur le document. Sans ces trois
    # colonnes, un export présente sur le même plan une transcription OCR et
    # une valeur tranchée par un humain — et une alerte ne peut pas être
    # vérifiée sans relire tout le document.
    headers = ["name", "label", "raw_value", "normalized_value", "corrected_value",
               "confirmed_value", "origine", "source", "zone",
               "confidence", "engine_confidence", "status", "page"]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)
    for name, fv in result.fields.items():
        ws.append([
            sanitize_for_csv(name), sanitize_for_csv(fv.label),
            sanitize_for_csv(fv.raw_value), sanitize_for_csv(fv.normalized_value),
            sanitize_for_csv(fv.corrected_value), sanitize_for_csv(fv.confirmed_value),
            sanitize_for_csv(_origine(fv)), sanitize_for_csv(fv.source),
            sanitize_for_csv(_zone(fv)),
            fv.confidence, fv.engine_confidence, fv.status.value, fv.page_num,
        ])

    ws2 = wb.create_sheet("Tables")
    row_cursor = 1
    for ti, table in enumerate(result.tables, 1):
        ws2.cell(row=row_cursor, column=1,
                 value=f"Table {ti} (page {table.page_num}, méthode {table.method})").font = Font(bold=True)
        row_cursor += 1
        for row in table.to_matrix():
            ws2.append([sanitize_for_csv(c) for c in row])
            row_cursor += 1
        row_cursor += 1

    ws3 = wb.create_sheet("Texte")
    ws3.append(["page", "texte"])
    for page in result.pages:
        ws3.append([page.page_num, page.text[:32000]])

    ws4 = wb.create_sheet("Anomalies")
    ws4.append(["code", "severity", "message", "page"])
    for a in result.quality.anomalies:
        ws4.append([a.code, a.severity, sanitize_for_csv(a.message), a.page_num])

    ws5 = wb.create_sheet("Métadonnées")
    ws5.append(["clé", "valeur"])
    ws5.append(["id", result.id])
    ws5.append(["source_file", result.source_file])
    ws5.append(["source_hash_sha256", result.source_hash])
    ws5.append(["profile", result.profile_used or ""])
    ws5.append(["engines", ", ".join(result.engines_used)])
    ws5.append(["mean_engine_confidence", result.quality.mean_engine_confidence])
    ws5.append(["mean_global_confidence", result.quality.mean_global_confidence])
    wb.save(out)
    return out


# ---------------------------------------------------------------- XML
def export_xml(result: DocumentResult, out: Path) -> Path:
    root = ET.Element("document", id=result.id, source=result.source_file,
                      hash=result.source_hash, profile=result.profile_used or "")
    meta = ET.SubElement(root, "meta")
    ET.SubElement(meta, "engines").text = ",".join(result.engines_used)
    ET.SubElement(meta, "mean_engine_confidence").text = str(result.quality.mean_engine_confidence)
    ET.SubElement(meta, "mean_global_confidence").text = str(result.quality.mean_global_confidence)

    pages_el = ET.SubElement(root, "pages")
    for page in result.pages:
        p_el = ET.SubElement(pages_el, "page", num=str(page.page_num),
                             width=str(int(page.width)), height=str(int(page.height)))
        # ET.escape est appliqué implicitement par tostring ; on garde le texte brut
        ET.SubElement(p_el, "text").text = page.text

    fields_el = ET.SubElement(root, "fields")
    for name, fv in result.fields.items():
        # Même exigence que pour le XLSX : sans `origin`, `source` et `zone`,
        # un export XML ne permet pas de distinguer une valeur extraite d'une
        # valeur interprétée, ni de retrouver où relire une alerte.
        ET.SubElement(fields_el, "field",
                      name=name, label=fv.label, status=fv.status.value,
                      origin=_origine(fv), source=fv.source, zone=_zone(fv),
                      confidence=str(fv.confidence),
                      engine_confidence=str(fv.engine_confidence),
                      page=str(fv.page_num or ""),
                      raw=fv.raw_value or "", normalized=fv.normalized_value or "",
                      corrected=fv.corrected_value or "", confirmed=fv.confirmed_value or "")

    tables_el = ET.SubElement(root, "tables")
    for table in result.tables:
        t_el = ET.SubElement(tables_el, "table", page=str(table.page_num),
                             rows=str(table.n_rows), cols=str(table.n_cols),
                             method=table.method, confidence=str(table.confidence))
        for row in table.to_matrix():
            r_el = ET.SubElement(t_el, "row")
            for val in row:
                ET.SubElement(r_el, "cell").text = val

    anomalies_el = ET.SubElement(root, "anomalies")
    for a in result.quality.anomalies:
        ET.SubElement(anomalies_el, "anomaly", code=a.code, severity=a.severity,
                      page=str(a.page_num or "")).text = a.message

    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write(out, encoding="utf-8", xml_declaration=True)
    return out


# ---------------------------------------------------------------- PDF consultable
def export_searchable_pdf(result: DocumentResult, out: Path,
                          page_images: dict[int, Image.Image] | None = None) -> Path:
    """PDF consultable : image de la page d'origine + couche texte invisible.

    La couche texte est positionnée sur les boîtes des mots reconnus : copier/
    rechercher dans le PDF renvoie le texte extrait, la mise en page reste celle
    de la source.
    """
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    if not page_images:
        raise ValueError("page_images requis : le PDF consultable est reconstruit depuis les rendus")

    page_list = sorted(page_images)
    first = page_images[page_list[0]]
    w0, h0 = first.size
    c = canvas.Canvas(str(out), pagesize=(w0, h0))
    for pn in page_list:
        img = page_images[pn]
        w, h = img.size
        c.setPageSize((w, h))
        c.drawImage(ImageReader(img), 0, 0, width=w, height=h)
        page_result = next((p for p in result.pages if p.page_num == pn), None)
        if page_result:
            to = c.beginText()
            to.setTextRenderMode(3)  # texte invisible
            for word in page_result.words:
                x = word.bbox.x0
                y = h - word.bbox.y1  # conversion haut-gauche -> bas-gauche PDF
                to.setTextOrigin(x, y)
                to.setFont("Helvetica", max(4.0, min(72.0, word.bbox.height * 0.85)))
                to.textOut(word.text + " ")
            c.drawText(to)
        c.showPage()
    c.save()
    return out


# ---------------------------------------------------------------- orchestration
def export_all(result: DocumentResult, out_dir: Path,
               formats: list[str],
               page_images: dict[int, Image.Image] | None = None) -> list[ExportRecord]:
    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[ExportRecord] = []

    def record(fmt: str, path: Path) -> None:
        records.append(ExportRecord(format=fmt, path=str(path),
                                    size_bytes=path.stat().st_size if path.exists() else 0))

    for fmt in formats:
        try:
            if fmt == "txt":
                record("txt", export_txt(result, out_dir / "result.txt"))
            elif fmt == "json":
                record("json", export_json(result, out_dir / "result.json"))
            elif fmt == "csv":
                for p in export_csv(result, out_dir):
                    record("csv", p)
            elif fmt == "xlsx":
                record("xlsx", export_xlsx(result, out_dir / "result.xlsx"))
            elif fmt == "xml":
                record("xml", export_xml(result, out_dir / "result.xml"))
            elif fmt == "pdf":
                if page_images:
                    record("pdf", export_searchable_pdf(result, out_dir / "searchable.pdf",
                                                        page_images))
                else:
                    result.warnings.append("export pdf consultable ignoré : images de page absentes")
            else:
                result.warnings.append(f"format d'export inconnu: {fmt}")
        except Exception as exc:
            log.exception("échec export %s", fmt)
            result.warnings.append(f"échec export {fmt}: {exc}")
    return records
