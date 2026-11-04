"""Reconstruction de la mise en page : mots → lignes → blocs, colonnes, ordre de lecture.

Gère les colonnes multiples et l'ordre RTL (arabe) : colonnes parcourues de droite
à gauche lorsque la page est majoritairement RTL.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import BBox, TextBlock, TextLine, Word

RTL_RANGES = (
    (0x0590, 0x05FF),  # hébreu
    (0x0600, 0x06FF),  # arabe
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)


def is_rtl_char(ch: str) -> bool:
    o = ord(ch)
    return any(a <= o <= b for a, b in RTL_RANGES)


def text_direction(text: str) -> str:
    rtl = sum(1 for ch in text if is_rtl_char(ch))
    return "rtl" if rtl > 0.2 * max(1, len(text.strip())) else "ltr"


def group_words_into_lines(words: list[Word], y_tol: float = 0.6) -> list[TextLine]:
    if not words:
        return []
    ordered = sorted(words, key=lambda w: (w.bbox.y0, w.bbox.x0))
    lines: list[list[Word]] = []
    cur: list[Word] = [ordered[0]]
    for w in ordered[1:]:
        ref = cur[-1]
        h = max(ref.bbox.height, w.bbox.height, 1.0)
        cy_ref = (ref.bbox.y0 + ref.bbox.y1) / 2
        cy = (w.bbox.y0 + w.bbox.y1) / 2
        if abs(cy - cy_ref) <= y_tol * h:
            cur.append(w)
        else:
            lines.append(cur)
            cur = [w]
    lines.append(cur)

    result = []
    for ln in lines:
        ln.sort(key=lambda w: w.bbox.x0)
        text = " ".join(w.text for w in ln)
        x0 = min(w.bbox.x0 for w in ln)
        y0 = min(w.bbox.y0 for w in ln)
        x1 = max(w.bbox.x1 for w in ln)
        y1 = max(w.bbox.y1 for w in ln)
        conf = sum(w.confidence for w in ln) / len(ln)
        bbox = BBox(x0=x0, y0=y0, x1=x1, y1=y1,
                    page_width=ln[0].bbox.page_width, page_height=ln[0].bbox.page_height)
        direction = text_direction(text)
        if direction == "rtl":
            ln_sorted = sorted(ln, key=lambda w: w.bbox.x0, reverse=True)
            text = " ".join(w.text for w in ln_sorted)
        result.append(TextLine(text=text, bbox=bbox, words=ln, direction=direction,
                               confidence=conf))
    return result


@dataclass
class ColumnLayout:
    columns: list[tuple[float, float]]  # (x0, x1) par colonne, ordonnées
    rtl_page: bool = False


def detect_columns(lines: list[TextLine], page_width: float) -> ColumnLayout:
    """Détecte les colonnes par gouttières verticales réellement libres.

    Une frontière n'est retenue que si AUCUNE ligne ne la croise (contrôle
    structurel) et qu'au moins 2 lignes se situent de chaque côté. La simple
    proximité visuelle ne suffit jamais à couper une page en colonnes.
    """
    if not lines or page_width <= 0:
        return ColumnLayout(columns=[(0.0, page_width or 1.0)])
    rtl_page = sum(1 for ln in lines if ln.direction == "rtl") > len(lines) / 2

    spans = sorted((ln.bbox.x0, ln.bbox.x1) for ln in lines)
    median_h = sorted(ln.bbox.height for ln in lines)[len(lines) // 2] or 10
    gutter_min = 2.5 * median_h

    # fusionne les intervalles couverts par les lignes
    merged: list[list[float]] = []
    for x0, x1 in spans:
        if merged and x0 <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], x1)
        else:
            merged.append([x0, x1])

    gutters = []
    for a, b in zip(merged, merged[1:]):
        gap = b[0] - a[1]
        if gap >= gutter_min:
            gutters.append(((a[1] + b[0]) / 2, gap))
    gutters.sort(key=lambda g: -g[1])
    for boundary, _gap in gutters:
        left = sum(1 for ln in lines if ln.bbox.x1 <= boundary + 1)
        right = sum(1 for ln in lines if ln.bbox.x0 >= boundary - 1)
        if left >= 2 and right >= 2 and left + right == len(lines):
            return ColumnLayout(columns=[(0.0, boundary), (boundary, page_width)],
                                rtl_page=rtl_page)
    return ColumnLayout(columns=[(0.0, page_width)], rtl_page=rtl_page)


def build_blocks(lines: list[TextLine], page_width: float, page_height: float) -> list[TextBlock]:
    """Découpe les lignes en blocs parallèles (paragraphes) selon l'ordre de lecture."""
    if not lines:
        return []
    layout = detect_columns(lines, page_width)
    col_assign: dict[int, int] = {}
    for i, line in enumerate(lines):
        cx = (line.bbox.x0 + line.bbox.x1) / 2
        for ci, (c0, c1) in enumerate(layout.columns):
            if c0 <= cx <= c1:
                col_assign[i] = ci
                break
        else:
            col_assign[i] = 0

    order = list(range(len(lines)))
    col_order = list(range(len(layout.columns)))
    if layout.rtl_page:
        col_order.reverse()
    order.sort(key=lambda i: (col_order.index(col_assign[i]) if col_assign[i] in col_order else 0,
                              lines[i].bbox.y0))

    # regroupement en blocs : même colonne + proximité verticale + alignement gauche
    blocks: list[TextBlock] = []
    cur_lines: list[TextLine] = []
    cur_col = -1

    def flush():
        nonlocal cur_lines
        if not cur_lines:
            return
        text = "\n".join(ln.text for ln in cur_lines)
        bbox = BBox(
            x0=min(ln.bbox.x0 for ln in cur_lines), y0=min(ln.bbox.y0 for ln in cur_lines),
            x1=max(ln.bbox.x1 for ln in cur_lines), y1=max(ln.bbox.y1 for ln in cur_lines),
            page_width=page_width, page_height=page_height,
        )
        blocks.append(TextBlock(text=text, bbox=bbox, order=len(blocks),
                                column=cur_col, lines=cur_lines, kind="paragraph"))
        cur_lines = []

    for idx in order:
        line = lines[idx]
        col = col_assign.get(idx, 0)
        if cur_lines and col != cur_col:
            flush()
        if cur_lines:
            prev = cur_lines[-1]
            gap = line.bbox.y0 - prev.bbox.y1
            left_align = abs(line.bbox.x0 - prev.bbox.x0) < 2.5 * max(1.0, line.bbox.height * 0.4)
            if gap > 1.8 * line.bbox.height or not left_align:
                flush()
        cur_col = col
        cur_lines.append(line)
    flush()
    return blocks
