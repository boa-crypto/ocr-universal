"""Reconstruction des tableaux.

Deux méthodes, choisies selon la structure détectée :
1. `ruled`  : détection des filets (OpenCV) → grille → OCR par cellule.
2. `clustering` : regroupement des mots en lignes/colonnes (tables sans bordures).

Prudence structurelle : on ne fusionne jamais deux lignes/colonnes sur la seule
proximité visuelle — l'alignement doit être cohérent sur au moins 2 lignes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from .logging_setup import get_logger
from .models import BBox, Cell, Table, Word

log = get_logger("tables")


# ---------------------------------------------------------------- filets
def detect_ruling_lines(img: Image.Image) -> tuple[list[tuple[int, int, int, int]], bool]:
    """Retourne les segments (x0,y0,x1,y1) de filets H/V et si une grille existe."""
    arr = np.array(img.convert("L"))
    binary = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY_INV, 25, 10)
    h, w = binary.shape
    h_len = max(20, w // 30)
    v_len = max(20, h // 30)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_len, 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_len))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)

    def segments(mask: np.ndarray, horizontal: bool) -> list[tuple[int, int, int, int]]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        segs = []
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            segs.append((x, y, x + cw, y + ch))
        return segs

    hs = segments(horizontal, True)
    vs = segments(vertical, False)
    grid = len(hs) >= 2 and len(vs) >= 2
    return hs + vs, grid


def _intersections(h_segs, v_segs):
    xs = sorted({s[0] for s in v_segs} | {s[2] for s in v_segs})
    ys = sorted({s[1] for s in h_segs} | {s[3] for s in h_segs})
    return xs, ys


def extract_ruled_table(img: Image.Image, page_num: int,
                        ocr_cell=None, max_cells: int = 150,
                        min_cell_px: int = 18,
                        words: list[Word] | None = None) -> Optional[Table]:
    """Reconstruit un tableau à filets.

    Remplissage des cellules par priorité :
    1. mots déjà extraits (OCR ou texte natif) dont le centre tombe dans la cellule,
    2. OCR du recadrage (`ocr_cell`, idéalement psm 7) pour les cellules restantes.

    Garde-fous structurels : grille plausible uniquement (cellules lisibles,
    nombre de cellules borné) pour éviter les fausses grilles sur codes-barres
    ou textures, et l'explosion du temps d'OCR par cellule.
    """
    segs, grid = detect_ruling_lines(img)
    if not grid:
        return None
    h_segs = [s for s in segs if (s[3] - s[1]) < (s[2] - s[0])]
    v_segs = [s for s in segs if (s[2] - s[0]) <= (s[3] - s[1])]
    xs, ys = _intersections(h_segs, v_segs)
    # filtre les coordonnées trop proches (doublons de contours)
    def dedup(vals, tol=8):
        out = []
        for v in vals:
            if not out or v - out[-1] > tol:
                out.append(v)
        return out
    xs, ys = dedup(xs), dedup(ys)
    if len(xs) < 2 or len(ys) < 2:
        return None
    n_rows, n_cols = len(ys) - 1, len(xs) - 1
    if n_rows * n_cols > max_cells:
        return None
    # cellules trop petites : probable grille parasite (QR, textures, lignes de texte)
    med_w = sorted(xs[i + 1] - xs[i] for i in range(n_cols))[n_cols // 2]
    med_h = sorted(ys[i + 1] - ys[i] for i in range(n_rows))[n_rows // 2]
    if med_w < min_cell_px or med_h < min_cell_px:
        return None

    cells: list[Cell] = []
    arr = np.array(img.convert("RGB"))
    confs = []
    for ri in range(len(ys) - 1):
        for ci in range(len(xs) - 1):
            x0, x1 = xs[ci], xs[ci + 1]
            y0, y1 = ys[ri], ys[ri + 1]
            # 1. mots déjà extraits dans cette cellule
            inside = []
            if words:
                for w in words:
                    cx = (w.bbox.x0 + w.bbox.x1) / 2
                    cy = (w.bbox.y0 + w.bbox.y1) / 2
                    if x0 <= cx <= x1 and y0 <= cy <= y1:
                        inside.append(w)
            if inside:
                inside.sort(key=lambda w: w.bbox.x0)
                text = " ".join(w.text for w in inside).replace("\n", " ").strip()
                conf = float(np.mean([w.confidence for w in inside]))
            elif ocr_cell is not None:
                # 2. secours : OCR du recadrage (ligne unique)
                crop = Image.fromarray(arr[y0:y1, x0:x1])
                text, conf = ocr_cell(crop)
                text = (text or "").replace("\n", " ").strip()
            else:
                text, conf = "", 1.0
            cells.append(Cell(row=ri, col=ci, text=text, confidence=conf,
                              bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
                              is_header=(ri == 0)))
            if text:
                confs.append(conf)
    table = Table(
        page_num=page_num,
        bbox=BBox(x0=xs[0], y0=ys[0], x1=xs[-1], y1=ys[-1]),
        n_rows=len(ys) - 1, n_cols=len(xs) - 1, cells=cells,
        method="ruled",
        confidence=float(np.mean(confs)) if confs else 0.0,
        header_rows=1,
        page_nums=[page_num],
    )
    return table


# ---------------------------------------------------------------- sans filets
@dataclass
class RowCluster:
    words: list[Word]
    y0: float
    y1: float


def cluster_rows(words: list[Word], y_tol: float = 0.7) -> list[RowCluster]:
    if not words:
        return []
    ws = sorted(words, key=lambda w: (w.bbox.y0 + w.bbox.y1) / 2)
    rows: list[RowCluster] = []
    cur = [ws[0]]
    for w in ws[1:]:
        cy = (w.bbox.y0 + w.bbox.y1) / 2
        cy_cur = sum((x.bbox.y0 + x.bbox.y1) / 2 for x in cur) / len(cur)
        h = max(w.bbox.height, 6.0)
        if abs(cy - cy_cur) <= y_tol * h:
            cur.append(w)
        else:
            rows.append(cur)
            cur = [w]
    rows.append(cur)
    return [RowCluster(words=sorted(c, key=lambda w: w.bbox.x0),
                       y0=min(w.bbox.y0 for w in c), y1=max(w.bbox.y1 for w in c))
            for c in rows]


def infer_columns(rows: list[RowCluster]) -> list[float]:
    """Frontières de colonnes déduites des écarts horizontaux récurrents.

    Un écart n'est retenu comme frontière que s'il apparaît sur ≥ 2 lignes
    (contrôle structurel, pas une simple proximité visuelle).
    """
    gap_votes: dict[int, int] = {}
    for row in rows:
        ws = row.words
        for a, b in zip(ws, ws[1:]):
            gap = int(b.bbox.x0 - a.bbox.x1)
            if gap > 12:
                mid = int((a.bbox.x1 + b.bbox.x0) / 2)
                # vote par quantification (tolérance 12 px)
                key = mid // 12
                gap_votes[key] = gap_votes.get(key, 0) + 1
    boundaries = [k * 12 + 6 for k, v in gap_votes.items() if v >= 2]
    boundaries.sort()
    # fusionne les frontières proches
    merged: list[int] = []
    for b in boundaries:
        if not merged or b - merged[-1] > 24:
            merged.append(b)
    return [float(b) for b in merged]


def extract_borderless_table(words: list[Word], page_num: int,
                             min_rows: int = 2) -> Optional[Table]:
    rows = cluster_rows(words)
    if len(rows) < min_rows:
        return None
    bounds = infer_columns(rows)
    n_cols = len(bounds) + 1
    if n_cols < 2:
        return None
    # n'exporte une table que si l'alignement est cohérent (≥ 2 lignes multi-colonnes)
    multi = sum(1 for r in rows if sum(1 for w in r.words
                if any(b > w.bbox.x0 for b in bounds)) >= 1 and len(r.words) >= n_cols - 1)
    if multi < 2:
        return None

    cells: list[Cell] = []
    confs = []
    for ri, row in enumerate(rows):
        buckets: dict[int, list[Word]] = {ci: [] for ci in range(n_cols)}
        for w in row.words:
            ci = 0
            for bi, b in enumerate(bounds):
                if w.bbox.x0 >= b - 6:
                    ci = bi + 1
            buckets[ci].append(w)
        for ci in range(n_cols):
            ws = buckets[ci]
            text = " ".join(w.text for w in ws)
            conf = float(np.mean([w.confidence for w in ws])) if ws else 1.0
            bbox = None
            if ws:
                bbox = BBox(x0=min(w.bbox.x0 for w in ws), y0=min(w.bbox.y0 for w in ws),
                            x1=max(w.bbox.x1 for w in ws), y1=max(w.bbox.y1 for w in ws))
            if text:
                cells.append(Cell(row=ri, col=ci, text=text, confidence=conf, bbox=bbox,
                                  is_header=(ri == 0)))
                confs.append(conf)
    if not cells:
        return None
    x0 = min(c.bbox.x0 for c in cells if c.bbox)
    y0 = min(c.bbox.y0 for c in cells if c.bbox)
    x1 = max(c.bbox.x1 for c in cells if c.bbox)
    y1 = max(c.bbox.y1 for c in cells if c.bbox)
    return Table(
        page_num=page_num, bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
        n_rows=len(rows), n_cols=n_cols, cells=cells, method="clustering",
        confidence=float(np.mean(confs)) if confs else 0.0,
        header_rows=1, page_nums=[page_num],
    )


# ---------------------------------------------------------------- multi-pages
def merge_multipage_tables(tables: list[Table]) -> list[Table]:
    """Fusionne les tableaux consécutifs de même largeur en tableaux multipages.

    Critère strict : nombre de colonnes identique ET continuité des pages ET
    en-têtes compatibles. Aucune fusion sur la seule ressemblance de contenu.
    """
    if not tables:
        return []
    merged: list[Table] = []
    current = tables[0].model_copy(deep=True)
    for t in tables[1:]:
        compatible = (
            t.n_cols == current.n_cols
            and t.page_num == max(current.page_nums) + 1
            and t.method == current.method
        )
        if compatible:
            offset = current.n_rows
            for c in t.cells:
                nc = c.model_copy(deep=True)
                nc.row = c.row + offset
                current.cells.append(nc)
            current.n_rows += t.n_rows
            current.page_nums.append(t.page_num)
            current.multipage = True
            current.confidence = min(current.confidence, t.confidence)
        else:
            merged.append(current)
            current = t.model_copy(deep=True)
    merged.append(current)
    return merged


def ocr_cell_factory(engine_recognize, languages: list[str] | None = None):
    """Construit le callback OCR par cellule à partir d'un moteur (interface OCREngine)."""
    def _ocr(crop: Image.Image) -> tuple[str, float]:
        out = engine_recognize(crop, languages)
        if not out.ok or not out.words:
            return out.text, out.mean_confidence
        text = " ".join(w.text for w in out.words)
        return text, out.mean_confidence
    return _ocr
