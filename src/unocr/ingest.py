"""Ingestion : détection de format, validation, chargement en pages.

Formats supportés : PDF natif/scanné/hybride/multipage, PNG/JPG/TIFF/BMP/WEBP,
DOCX, ODT, TXT, RTF, CSV, XLSX, XLS.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Optional

from PIL import Image, ImageOps

from .logging_setup import get_logger
from .models import BBox, Cell, Table, Word
from .security import SecurityError, sanitize_text, validate_file

log = get_logger("ingest")

# PDFium ne permet pas les appels concurrents entre threads, même sur des
# documents distincts. Toute vie native (création, rendu, fermeture) reste sous
# ce verrou de processus ; les images détachées sortent seules de cette zone.
_PDFIUM_LOCK = RLock()

# Évite le decompression bomb PIL
Image.MAX_IMAGE_PIXELS = 200_000_000


@dataclass
class LoadedPage:
    page_num: int
    width: float
    height: float
    image: Optional[Image.Image] = None       # None pour les pages purement numériques
    native_text: str = ""
    native_words: list[Word] = field(default_factory=list)
    kind: str = "image"                       # pdf_native | pdf_scan | pdf_hybrid | image | digital_text
    estimated_dpi: float = 0.0


@dataclass
class LoadedDocument:
    path: Path
    format: str
    pages: list[LoadedPage] = field(default_factory=list)
    digital_tables: list[Table] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ------------------------------------------------------------- détection
def detect_format(path: Path) -> str:
    ext = path.suffix.lower()
    header = path.open("rb").read(16)
    if header.startswith(b"%PDF-"):
        return "pdf"
    if header.startswith(b"\x89PNG"):
        return "png"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    if header.startswith(b"BM") and ext == ".bmp":
        return "bmp"
    if header.startswith(b"RIFF") and ext == ".webp":
        return "webp"
    if header.startswith(b"PK\x03\x04"):
        if ext == ".docx":
            return "docx"
        if ext == ".odt":
            return "odt"
        if ext == ".xlsx":
            return "xlsx"
    if header.startswith(b"\xd0\xcf\x11\xe0"):
        return "xls"
    if header.startswith(b"{\\rtf"):
        return "rtf"
    if ext in {".txt", ".csv"}:
        return "txt" if ext == ".txt" else "csv"
    return ext.lstrip(".") or "unknown"


# ------------------------------------------------------------- PDF
def _pdf_native_words(page_layout, page_height_pt: float, scale: float) -> tuple[str, list[Word], list]:
    """Regroupe les LTChar pdfminer en mots avec boîtes (pixels, origine haut-gauche)."""
    from pdfminer.layout import LTAnno, LTChar, LTTextContainer

    chars: list[tuple[str, float, float, float, float]] = []
    text_parts: list[str] = []
    for el in page_layout:
        if not isinstance(el, LTTextContainer):
            continue
        for line in el:
            for obj in line:
                if isinstance(obj, LTChar):
                    x0, y0, x1, y1 = obj.bbox
                    # conversion PDF (y bas) -> pixels (y haut)
                    chars.append((
                        obj.get_text(),
                        x0 * scale,
                        (page_height_pt - y1) * scale,
                        x1 * scale,
                        (page_height_pt - y0) * scale,
                    ))
                elif isinstance(obj, LTAnno):
                    pass
            text_parts.append(line.get_text())

    words: list[Word] = []
    cur_text = ""
    cur_box: Optional[list[float]] = None
    prev_x1: Optional[float] = None
    for ch, x0, y0, x1, y1 in chars:
        if ch.strip() == "":
            if cur_text and cur_box:
                words.append(_mk_word(cur_text, cur_box, scale))
            cur_text, cur_box, prev_x1 = "", None, x1
            continue
        # rupture de mot si écart horizontal important ou changement de ligne
        if cur_text and cur_box is not None:
            gap = x0 - prev_x1 if prev_x1 is not None else 0
            line_h = cur_box[3] - cur_box[1]
            if gap > max(2.0, 0.35 * line_h) or abs(y0 - cur_box[1]) > max(3.0, 0.6 * line_h):
                words.append(_mk_word(cur_text, cur_box, scale))
                cur_text, cur_box = "", None
        if not cur_text:
            cur_box = [x0, y0, x1, y1]
        else:
            cur_box[0] = min(cur_box[0], x0)
            cur_box[1] = min(cur_box[1], y0)
            cur_box[2] = max(cur_box[2], x1)
            cur_box[3] = max(cur_box[3], y1)
        cur_text += ch
        prev_x1 = x1
    if cur_text and cur_box:
        words.append(_mk_word(cur_text, cur_box, scale))
    return sanitize_text("".join(text_parts)), words, []


def _mk_word(text: str, box: list[float], scale: float) -> Word:
    return Word(
        text=text,
        bbox=BBox(x0=box[0], y0=box[1], x1=box[2], y1=box[3]),
        confidence=0.95,   # texte natif : caractères issus du fichier (documenté)
        engine="native_pdf",
    )


def _load_pdf(path: Path, dpi: int, max_pages: int = 500) -> LoadedDocument:
    import pypdfium2 as pdfium
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LAParams

    scale = dpi / 72.0
    doc = LoadedDocument(path=path, format="pdf")
    with _PDFIUM_LOCK, pdfium.PdfDocument(str(path)) as pdf:
        n_pages = len(pdf)
        if n_pages > max_pages:
            raise SecurityError(f"trop de pages ({n_pages} > {max_pages})")
        layouts = list(extract_pages(str(path), laparams=LAParams()))

        for i in range(n_pages):
            with closing(pdf[i]) as page:
                w_pt, h_pt = page.get_size()
                width, height = w_pt * scale, h_pt * scale
                native_text, native_words, _ = ("", [], [])
                if i < len(layouts):
                    native_text, native_words, _ = _pdf_native_words(layouts[i], h_pt, scale)
                for w in native_words:
                    w.page_num = i + 1

                with closing(page.render(scale=scale)) as bitmap:
                    # convert() copie les pixels avant de libérer le bitmap.
                    pil = bitmap.to_pil().convert("RGB")
                has_text = len(native_text.strip()) >= 5
                kind = "pdf_native" if has_text else "pdf_scan"
                doc.pages.append(LoadedPage(
                    page_num=i + 1,
                    width=width,
                    height=height,
                    image=pil,
                    native_text=native_text,
                    native_words=native_words,
                    kind=kind,
                    estimated_dpi=float(dpi),
                ))
    # hybride : pages mixtes dans un même document
    kinds = {p.kind for p in doc.pages}
    if kinds == {"pdf_native", "pdf_scan"}:
        for p in doc.pages:
            p.kind = "pdf_hybrid"
    return doc


# ------------------------------------------------------------- images
def _load_image(path: Path, fmt: str) -> LoadedDocument:
    doc = LoadedDocument(path=path, format=fmt)
    img = Image.open(path)
    frames = []
    if fmt == "tiff" and getattr(img, "n_frames", 1) > 1:
        for i in range(img.n_frames):
            img.seek(i)
            frames.append(ImageOps.exif_transpose(img).convert("RGB"))
    else:
        frames = [ImageOps.exif_transpose(img).convert("RGB")]

    for i, frame in enumerate(frames):
        w, h = frame.size
        # résolution estimée : DPI EXIF si présent, sinon heuristique taille
        dpi = float(frame.info.get("dpi", (0, 0))[0] or 0) or (200.0 if min(w, h) >= 1000 else 150.0)
        doc.pages.append(LoadedPage(
            page_num=i + 1, width=w, height=h, image=frame,
            kind="image", estimated_dpi=dpi,
        ))
    return doc


# ------------------------------------------------------------- texte numérique
def _virtual_text_pages(text: str, kind: str = "digital_text") -> list[LoadedPage]:
    """Découpe un texte numérique en pages logiques avec géométrie estimée.

    La géométrie est SYNTHÉTIQUE (grille de caractères) : elle sert à localiser
    les champs, pas à prétendre à une mise en page réelle.
    """
    text = sanitize_text(text)
    lines = text.splitlines() or [""]
    lines_per_page = 60
    char_w, line_h = 8.0, 18.0
    pages: list[LoadedPage] = []
    for p in range(0, max(1, len(lines)), lines_per_page):
        chunk = lines[p:p + lines_per_page]
        page_num = p // lines_per_page + 1
        width = max((len(ln) for ln in chunk), default=1) * char_w + 40
        height = (len(chunk) + 1) * line_h + 20
        words: list[Word] = []
        page_text_lines = []
        for li, line in enumerate(chunk):
            y0 = 10 + li * line_h
            x = 20.0
            page_text_lines.append(line)
            for wtxt in line.split(" "):
                if not wtxt:
                    x += char_w
                    continue
                wbox = BBox(x0=x, y0=y0, x1=x + len(wtxt) * char_w, y1=y0 + line_h - 4)
                words.append(Word(text=wtxt, bbox=wbox, confidence=0.95,
                                  engine="native_text", page_num=page_num))
                x += (len(wtxt) + 1) * char_w
        pages.append(LoadedPage(
            page_num=page_num, width=width, height=height, image=None,
            native_text="\n".join(page_text_lines), native_words=words, kind=kind,
        ))
    return pages


def _load_txt(path: Path) -> LoadedDocument:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    doc = LoadedDocument(path=path, format="txt")
    doc.pages = _virtual_text_pages(text)
    return doc


def _load_rtf(path: Path) -> LoadedDocument:
    from striprtf.striprtf import rtf_to_text
    text = rtf_to_text(path.read_text(encoding="utf-8", errors="replace"))
    doc = LoadedDocument(path=path, format="rtf")
    doc.pages = _virtual_text_pages(text)
    return doc


def _load_docx(path: Path) -> LoadedDocument:
    import docx
    d = docx.Document(str(path))
    parts: list[str] = []
    for para in d.paragraphs:
        parts.append(para.text)
    doc = LoadedDocument(path=path, format="docx")
    doc.pages = _virtual_text_pages("\n".join(parts))
    for ti, t in enumerate(d.tables):
        rows = [[c.text.strip() for c in row.cells] for row in t.rows]
        doc.digital_tables.append(_matrix_to_table(rows, page_num=1, method="digital"))
    return doc


def _load_odt(path: Path) -> LoadedDocument:
    from odf import table as odf_table
    from odf import teletype
    from odf import text as odf_text
    from odf.opendocument import load as odf_load

    odoc = odf_load(str(path))
    parts: list[str] = []
    for el in odoc.getElementsByType(odf_text.P) + odoc.getElementsByType(odf_text.H):
        parts.append(teletype.extractText(el))
    doc = LoadedDocument(path=path, format="odt")
    doc.pages = _virtual_text_pages("\n".join(parts))
    for t in odoc.getElementsByType(odf_table.Table):
        rows = []
        for tr in t.getElementsByType(odf_table.TableRow):
            row = []
            for tc in tr.getElementsByType(odf_table.TableCell):
                row.append(teletype.extractText(tc).strip())
            rows.append(row)
        if rows:
            doc.digital_tables.append(_matrix_to_table(rows, page_num=1, method="digital"))
    return doc


def _matrix_to_table(rows: list[list[str]], page_num: int, method: str = "digital") -> Table:
    n_rows = len(rows)
    n_cols = max((len(r) for r in rows), default=0)
    cells = []
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cells.append(Cell(row=ri, col=ci, text=sanitize_text(str(val)),
                              confidence=1.0, engine="native_text",
                              is_header=(ri == 0)))
    return Table(page_num=page_num, n_rows=n_rows, n_cols=n_cols,
                 cells=cells, method=method, confidence=1.0,
                 page_nums=[page_num], header_rows=1 if n_rows else 0)


def _load_tabular(path: Path, fmt: str) -> LoadedDocument:
    import pandas as pd
    doc = LoadedDocument(path=path, format=fmt)
    if fmt == "csv":
        sheets = {"Sheet1": pd.read_csv(path, dtype=str, keep_default_na=False)}
    elif fmt == "xls":
        sheets = pd.read_excel(path, sheet_name=None, dtype=str)
    else:
        sheets = pd.read_excel(path, sheet_name=None, dtype=str)
    text_parts = []
    for name, df in sheets.items():
        df = df.fillna("")
        rows = [list(map(str, df.columns))] + [list(map(str, r)) for r in df.values.tolist()]
        doc.digital_tables.append(_matrix_to_table(rows, page_num=1, method="digital"))
        text_parts.append(f"# {name}\n" + "\n".join("\t".join(r) for r in rows))
    doc.pages = _virtual_text_pages("\n\n".join(text_parts), kind="digital_text")
    return doc


# ------------------------------------------------------------- entrée principale
def load_document(path: Path | str, dpi: int = 200,
                  max_pages: int = 500,
                  max_size_mb: int = 50,
                  max_zip_uncompressed_mb: int = 200,
                  max_zip_ratio: int = 100) -> LoadedDocument:
    """Valide et charge un document en pages. Ne modifie jamais le fichier source."""
    p = Path(path)
    validate_file(p, max_size_mb=max_size_mb,
                  max_zip_uncompressed_mb=max_zip_uncompressed_mb,
                  max_zip_ratio=max_zip_ratio)
    fmt = detect_format(p)
    try:
        if fmt == "pdf":
            doc = _load_pdf(p, dpi, max_pages=max_pages)
        elif fmt in {"png", "jpeg", "tiff", "bmp", "webp"}:
            doc = _load_image(p, fmt)
        elif fmt == "docx":
            doc = _load_docx(p)
        elif fmt == "odt":
            doc = _load_odt(p)
        elif fmt == "rtf":
            doc = _load_rtf(p)
        elif fmt in {"csv", "xls", "xlsx"}:
            doc = _load_tabular(p, fmt)
        elif fmt == "txt":
            doc = _load_txt(p)
        else:
            raise SecurityError(f"format non géré: {fmt}")
    except SecurityError:
        raise
    except Exception as exc:
        log.exception("échec de chargement de %s", p.name)
        raise SecurityError(f"document illisible ou corrompu: {exc}") from exc

    if not doc.pages:
        raise SecurityError("aucune page exploitable dans le document")
    if len(doc.pages) > max_pages:
        raise SecurityError(f"trop de pages ({len(doc.pages)} > {max_pages})")
    return doc


def page_images(path: Path | str, dpi: int = 200) -> dict[int, Image.Image]:
    """Images des pages, pour l'export PDF consultable.

    **Pourquoi un helper dédié.** Le même bloc `try: load_document(…)
    except Exception: pass` existait en triple (CLI, pipeline, fonction morte) :
    trois copies dont l'échec était silencieux — un export PDF perdait ses pages
    image sans le dire. Ici l'échec est journalisé avec la raison, et l'appelant
    reçoit un dictionnaire vide qu'il peut assumer.

    Ne relance pas l'OCR : ne sert qu'à récupérer les images déjà rendues.
    """
    p = Path(path)
    out: dict[int, Image.Image] = {}
    try:
        loaded = load_document(p, dpi=dpi)
    except Exception as exc:
        log.warning("images de page indisponibles pour %s : %s", p.name, exc)
        return out
    for lp in loaded.pages:
        if lp.image is not None:
            out[lp.page_num] = lp.image
    return out
