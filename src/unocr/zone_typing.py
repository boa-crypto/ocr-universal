"""Typage de zones — repère les zones non textuelles d'un document (E2).

**Ce que ce module fait** : segmenter un document en zones typées —

- `table` : structure de tableau, reprise du détecteur éprouvé du pipeline ;
- `checkbox` : **candidate** case à cocher, retenue uniquement si elle fait
  partie d'un groupe d'au moins trois contours alignés de taille voisine.

**Ce que ce module ne fait pas, et pourquoi** :

- **Transcrire l'écriture manuscrite.** Aucun modèle HTR n'est utilisé
  (impossible dans les contraintes matérielles de référence). Une zone
  manuscrite n'est jamais dotée d'un texte inventé.
- **Détecter les signatures.** Un détecteur géométrique de signatures a été
  écrit puis **retiré** : sur le jeu de contrôle il classait un code-barres 2D
  comme « manuscrit » et trouvait 21 « signatures » sur une carte grise qui
  n'en contient aucune. Aucun discriminateur géométrique fiable n'a été trouvé
  sans modèle appris — plutôt que de livrer un détecteur faux, la capacité
  n'est pas revendiquée (voir docs/LIMITATIONS.md).

**Avertissement de méthode.** La détection de cases est **heuristique et
géométrique**, sans modèle appris. Un anneau carré peut être une case à cocher,
une lettre creuse (« O », « 0 »), un trou de fixation ou un module de
code-barres. Les résultats portent donc une confiance et une note invitant à
la confirmation humaine ; ils ne doivent jamais être traités comme un fait.

**Mesures réelles** (jeu de contrôle `tests/fixtures/form_zones.png`, voir
`tests/test_zone_typing.py`) :

| document | cases réelles | candidats retenus |
|---|---|---|
| formulaire synthétique | 4 (2 cochées, 2 vides) | 23 → **rappel 4/4, précision 17 %** |
| conteneur, plaque FR, plaque DZ, VIN, code QR | 0 | **0 faux positif** |
| carte grise | 0 | 15 candidats (faux positifs) |

Ces chiffres décrivent des images **synthétiques**. Aucune mesure sur photo
réelle n'existe : la précision réelle sur vos documents est inconnue.

Aucune heuristique de ce module ne modifie le texte ni les champs extraits.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .logging_setup import get_logger

log = get_logger("zone_typing")

# bornes de taille d'une case à cocher, en pixels rendus
CHECKBOX_MIN = 10          # en dessous : modules de code-barres, ponctuation
CHECKBOX_MAX = 60
CHECKBOX_ASPECT = (0.75, 1.33)
CHECKBOX_GROUP_MIN = 3     # une case isolée n'est pas retenue
CHECKBOX_INTERIOR_MAX = 0.45   # intérieur peu encré (une coche = ~0,24,
                             # une lettre creuse « O » = ~0,7+)
CHECKBOX_FILL_MIN = 0.70       # le contour remplit son cadre
CHECKBOX_MARGIN = 7            # marge de vide exigée autour de la case
CHECKBOX_MARGIN_MAX_INK = 0.42 # encre tolérée dans cette marge


def _ratio(w: float, h: float) -> float:
    if h <= 0:
        return 99.0
    return w / h


def _corners_inked(mask, x: int, y: int, w: int, h: int) -> int:
    """Nombre de coins encrés. Un carré en a 4 ; une lettre creuse (ronde) 0-2.

    C'est le critère qui sépare une case à cocher d'un « O » ou d'un « 0 ».
    """
    cw, ch = max(2, w // 4), max(2, h // 4)
    hits = 0
    for cx, cy in ((x, y), (x + w - cw, y), (x, y + h - ch), (x + w - cw, y + h - ch)):
        if mask[cy:cy + ch, cx:cx + cw].any():
            hits += 1
    return hits


def _box_candidates(mask) -> list[tuple[int, int, int, int]]:
    """Contours ressemblant à une case (avant filtrage par groupe)."""
    import cv2
    import numpy as np

    out = []
    cnts, _ = cv2.findContours((mask.astype(np.uint8) * 255),
                               cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if not (CHECKBOX_MIN <= w <= CHECKBOX_MAX
                and CHECKBOX_MIN <= h <= CHECKBOX_MAX):
            continue
        if not (CHECKBOX_ASPECT[0] <= _ratio(w, h) <= CHECKBOX_ASPECT[1]):
            continue
        if cv2.contourArea(c) < CHECKBOX_FILL_MIN * w * h:
            continue                      # le contour doit remplir son cadre
        inner = mask[y + 3:y + h - 3, x + 3:x + w - 3]
        if inner.size == 0 or inner.mean() > CHECKBOX_INTERIOR_MAX:
            continue                      # intérieur quasi vide
        edges = [mask[y, x + w // 2], mask[y + h - 1, x + w // 2],
                 mask[y + h // 2, x], mask[y + h // 2, x + w - 1]]
        if sum(bool(e) for e in edges) < 4:
            continue                      # anneau fermé sur les 4 côtés
        if _corners_inked(mask, x, y, w, h) < 3:
            continue                      # anguleux, pas rond
        # vide local : une case est isolée dans du blanc, une lettre creuse
        # est entourée d'autres lettres
        m = CHECKBOX_MARGIN
        ring = mask[max(0, y - m):y + h + m, max(0, x - m):x + w + m]
        if ring.size and ring.mean() > CHECKBOX_MARGIN_MAX_INK:
            continue
        out.append((x, y, w, h))
    return out


def _dedupe(boxes) -> list:
    """Supprime les contours qui se recouvrent (marque dans une case, etc.)."""
    keep = []
    for b in sorted(boxes, key=lambda t: (t[1], t[0])):
        dup = False
        for k in keep:
            ix = max(0, min(b[0] + b[2], k[0] + k[2]) - max(b[0], k[0]))
            iy = max(0, min(b[1] + b[3], k[1] + k[3]) - max(b[1], k[1]))
            if ix * iy > 0.3 * min(b[2] * b[3], k[2] * k[3]):
                dup = True
                break
        if not dup:
            keep.append(b)
    return keep


def _peers(box, boxes) -> int:
    """Voisins alignés (même ligne ou même colonne) de taille voisine."""
    x, y, w, h = box
    n = 0
    for b in boxes:
        if b == box:
            continue
        if not (abs(w - b[2]) <= 0.25 * max(w, b[2])
                and abs(h - b[3]) <= 0.25 * max(h, b[3])):
            continue
        if abs(y - b[1]) <= 0.3 * max(h, b[3]) or abs(x - b[0]) <= 0.3 * max(w, b[2]):
            n += 1
    return n


def classify_zones(path: Path | str,
                   tables: Optional[list] = None) -> list[dict]:
    """Type les zones d'un document. Renvoie une liste (jamais d'exception).

    En cas de fichier illisible, renvoie une liste vide : mieux vaut aucune
    information qu'une fausse.
    """
    p = Path(path)
    if not p.is_file():
        return []
    try:
        import cv2  # noqa: F401  (disponibilité vérifiée ici)
    except ImportError:  # pragma: no cover - dépendances système absentes
        log.warning("opencv indisponible : typage de zones ignoré")
        return []

    zones: list[dict] = []

    # ── tableaux déjà connus (détecteur éprouvé du pipeline) ──
    for t in (tables or []):
        zones.append({"kind": "table", "page": getattr(t, "page_num", 1),
                      "bbox": _bbox_of(t), "confidence": 0.9,
                      "note": "structure de tableau détectée"})

    try:
        import cv2

        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return zones
        _, m = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        mask = (m > 0)

        cands = _dedupe(_box_candidates(mask))
        for box in cands:
            if _peers(box, cands) < CHECKBOX_GROUP_MIN - 1:
                continue      # case isolée : trop de faux positifs possibles
            x, y, w, h = box
            interior = float(mask[y + 3:y + h - 3, x + 3:x + w - 3].mean())
            zones.append({
                "kind": "checkbox", "page": 1,
                "bbox": {"x": x, "y": y, "w": w, "h": h},
                "confidence": round(max(0.3, 0.9 - interior), 2),
                "note": ("case à cocher (non cochée)" if interior < 0.02
                         else "case à cocher (contient une marque)")
                         + " — heuristique géométrique, à confirmer"})
    except Exception:
        log.exception("détection des cases à cocher impossible pour %s", p.name)

    return zones


def _bbox_of(obj) -> dict:
    bb = getattr(obj, "bbox", None)
    if bb is None:
        return {}
    return {"x": getattr(bb, "x0", None), "y": getattr(bb, "y0", None),
            "w": getattr(bb, "x1", None), "h": getattr(bb, "y1", None)}
