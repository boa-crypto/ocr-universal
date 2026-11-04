"""Prétraitement intelligent : analyse qualité, opérations adaptatives, variantes.

Règles :
- le fichier source n'est jamais modifié (les images de travail sont des copies),
- les opérations ne sont appliquées que si l'analyse les justifie,
- en mode 'accurate', deux variantes (original / prétraité) sont comparées au
  niveau OCR et la meilleure est conservée.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np
from PIL import Image

from .logging_setup import get_logger
from .models import PageQuality, PreprocessOp

#: Ratio d'encre au-delà duquel une page n'est jamais considérée comme
#: blanche. Sous ce seuil, la présence de caractères est vérifiée en plus.
_SEUIL_ENCRE_NON_BLANCHE = 0.002

log = get_logger("preprocess")


@dataclass
class PreprocessResult:
    image: Image.Image
    quality: PageQuality
    ops: list[PreprocessOp] = field(default_factory=list)
    variant_name: str = "preprocessed"


def pil_to_cv(img: Image.Image) -> np.ndarray:
    arr = np.array(img.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def cv_to_pil(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))


# ------------------------------------------------------------- analyse qualité
def _est_page_blanche(gray: np.ndarray, ink: float) -> bool:
    """Décide si une page est réellement vide.

    Le ratio de pixels sombres ne suffit pas : un document réel mais peu
    denses (trois lignes sur une grande page A4) tombe sous n'importe quel
    seuil fixe et serait traité comme une page blanche — le texte est alors
    perdu sans que rien ne le signale.

    On combine donc deux signaux :
    - le ratio d'encre, qui suffit pour un fond entièrement vide ;
    - la présence de **groupes de caractères** (composantes connexes d'une
      certaine taille), qui distingue « peu d'encre » de « pas de texte ».

    Une page contenant ne serait-ce qu'une ligne de texte n'est pas vide.
    """
    if ink >= _SEUIL_ENCRE_NON_BLANCHE:
        return False
    # une page entièrement claire : aucun pixel d'encre du tout
    if ink <= 0.0:
        return True
    # on cherche des « mots » : composantes connexes de taille plausible
    binaire = (gray < 200).astype(np.uint8)
    nb, _, stats, _ = cv2.connectedComponentsWithStats(binaire, connectivity=8)
    for i in range(1, nb):
        x, y, w, h, aire = stats[i]
        # un caractère (ou un groupe de caractères) : hauteur >= 5 px,
        # largeur >= 2 px, et une densité qui exclut le bruit isolé
        if h >= 5 and w >= 2 and aire >= 4:
            return False
    return True


def analyze_quality(img: Image.Image, reported_dpi: float = 0.0) -> PageQuality:
    gray = cv2.cvtColor(pil_to_cv(img), cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    # bruit estimé par l'écart-type médian sur des blocs 8x8 lisses
    noise = float(np.median(np.abs(cv2.Laplacian(gray, cv2.CV_64F))) * 0.5)
    ink = float(np.mean(gray < 200))
    skew = _estimate_skew(gray)
    dpi = reported_dpi or (200.0 if min(w, h) >= 1200 else 150.0)

    issues = []
    if blur < 80:
        issues.append("blurry")
    if brightness < 60:
        issues.append("dark")
    if brightness > 240 and contrast < 40:
        # page blanche avec peu d'encre : pas de « surexposition » pour un simple fond blanc
        issues.append("overexposed")
    if contrast < 35:
        issues.append("low_contrast")
    if noise > 25:
        issues.append("noisy")
    if abs(skew) > 0.6:
        issues.append("skewed")
    if dpi < 150:
        issues.append("low_resolution")
    if ink < 0.005:
        issues.append("nearly_blank")

    return PageQuality(
        brightness=brightness, contrast=contrast, blur_score=blur,
        noise_score=noise, estimated_skew_deg=skew, estimated_dpi=dpi,
        ink_ratio=ink, is_blank=_est_page_blanche(gray, ink), issues=issues,
    )


def _estimate_skew(gray: np.ndarray) -> float:
    """Estime l'inclinaison (degrés) par transformée de Hough sur les lignes de texte.

    La forme de retour de `cv2.HoughLinesP` n'est pas stable d'une version
    d'OpenCV à l'autre : jusqu'à la 4.x elle vaut `(N, 1, 4)`, la 5.x renvoie
    `(N, 4)`. On normalise donc la sortie avant de la parcourir — sinon
    *toute* l'OCR raster échoue sur une dépendance plus récente, y compris
    dans un environnement où l'on croyait la version épinglée.
    """
    try:
        h, w = gray.shape
        scale = min(1.0, 1000.0 / max(h, w))
        small = cv2.resize(gray, None, fx=scale, fy=scale) if scale < 1.0 else gray
        edges = cv2.Canny(small, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100,
                                minLineLength=small.shape[1] // 4, maxLineGap=12)
        if lines is None:
            return 0.0
        segments = _segments_de_lignes(lines)
        angles = []
        for x1, y1, x2, y2 in segments:
            ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if abs(ang) <= 30:  # on ignore les verticales
                angles.append(ang)
        if not angles:
            return 0.0
        return float(np.median(angles))
    except cv2.error:
        return 0.0


def _segments_de_lignes(lines: Any) -> list[tuple[float, float, float, float]]:
    """Normalise la sortie de `HoughLinesP` en une liste de segments.

    Accepte `(N, 1, 4)` (OpenCV ≤ 4.x), `(N, 4)` (OpenCV 5.x) et le cas
    dégénéré `(1, 4)` : la forme exacte a changé sans préavis et l'OCR ne
    doit pas dépendre de la version installée.
    """
    arr = np.asarray(lines)
    if arr.size == 0:
        return []
    # aplatit `(N, 1, 4)` comme `(N, 4)`
    arr = arr.reshape(-1, arr.shape[-1])
    if arr.shape[-1] != 4:
        return []
    return [(float(x1), float(y1), float(x2), float(y2))
            for x1, y1, x2, y2 in arr]


# ------------------------------------------------------------- opérations
def _rotate_bound(img: np.ndarray, angle_deg: float) -> np.ndarray:
    h, w = img.shape[:2]
    cx, cy = w / 2, h / 2
    m = cv2.getRotationMatrix2D((cx, cy), angle_deg, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    m[0, 2] += nw / 2 - cx
    m[1, 2] += nh / 2 - cy
    return cv2.warpAffine(img, m, (nw, nh), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def _correct_perspective(img: np.ndarray) -> tuple[np.ndarray, bool]:
    """Détecte le quadrilatère du document (photo en perspective) et le redresse."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img, False
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    if area < 0.15 * img.shape[0] * img.shape[1]:
        return img, False
    peri = cv2.arcLength(cnt, True)
    quad = cv2.approxPolyDP(cnt, 0.02 * peri, True)
    if len(quad) != 4:
        return img, False
    pts = quad.reshape(4, 2).astype("float32")
    # refuse si le quadrilatère couvre déjà presque toute l'image (pas de perspective)
    x0, y0 = pts.min(axis=0)
    x1, y1 = pts.max(axis=0)
    fill = ((x1 - x0) * (y1 - y0)) / (img.shape[0] * img.shape[1])
    if fill > 0.97:
        return img, False

    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    rect = np.array([
        pts[np.argmin(s)],      # haut-gauche
        pts[np.argmin(diff)],   # haut-droit
        pts[np.argmax(s)],      # bas-droit
        pts[np.argmax(diff)],  # bas-gauche
    ], dtype="float32")
    (tl, tr, br, bl) = rect
    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    if width < 50 or height < 50:
        return img, False
    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
                   dtype="float32")
    m = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(img, m, (width, height)), True


def _crop_borders(img: np.ndarray) -> tuple[np.ndarray, bool]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(th)
    if coords is None:
        return img, False
    x, y, w, h = cv2.boundingRect(coords)
    margin = int(0.01 * max(img.shape[:2]))
    x0, y0 = max(0, x - margin), max(0, y - margin)
    x1 = min(img.shape[1], x + w + margin)
    y1 = min(img.shape[0], y + h + margin)
    if (x1 - x0) * (y1 - y0) < 0.5 * img.shape[0] * img.shape[1]:
        return img, False  # recadrage trop agressif : annulé
    return img[y0:y1, x0:x1], True


def _remove_shadows(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    norm = cv2.divide(gray, bg, scale=255)
    return cv2.cvtColor(norm, cv2.COLOR_GRAY2BGR)


def _enhance_contrast(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    ln, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return cv2.cvtColor(cv2.merge([clahe.apply(ln), a, b]), cv2.COLOR_LAB2BGR)


def _denoise(img: np.ndarray, strength: int = 7) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(img, None, strength, strength, 7, 21)


def _binarize(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 15)
    return cv2.cvtColor(th, cv2.COLOR_GRAY2BGR)


def _upscale(img: np.ndarray, factor: float) -> np.ndarray:
    if factor <= 1.05:
        return img
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w * factor), int(h * factor)), interpolation=cv2.INTER_CUBIC)


def _detect_orientation(img: Image.Image) -> int:
    """Orientation via Tesseract OSD ; renvoie 0 si indéterminé (échec gracieux)."""
    try:
        import pytesseract
        small = img.convert("L")
        small.thumbnail((1000, 1000))
        osd = pytesseract.image_to_osd(small)
        for line in osd.splitlines():
            if line.lower().startswith("orientation"):
                return int(line.split(":")[1].strip()) % 360
    except Exception:  # OSD échoue sur petites images / peu de texte → non bloquant
        return 0
    return 0


# ------------------------------------------------------------- pipeline
def preprocess_page(img: Image.Image, quality: PageQuality | None = None,
                    reported_dpi: float = 0.0,
                    aggressive: bool = False) -> PreprocessResult:
    """Applique uniquement les opérations justifiées par l'analyse qualité."""
    quality = quality or analyze_quality(img, reported_dpi)
    ops: list[PreprocessOp] = []
    arr = pil_to_cv(img)
    issues = set(quality.issues)

    # 1. orientation (OSD) — rotation par pas de 90° si détecté
    orient = _detect_orientation(img)
    if orient in (90, 180, 270):
        rot = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}[orient]
        arr = cv2.rotate(arr, rot)
        ops.append(PreprocessOp(name="rotate_90", applied=True, params={"deg": orient},
                                reason="orientation détectée par OSD"))

    # 2. inclinaison fine
    if "skewed" in issues or aggressive:
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        skew = _estimate_skew(gray)
        if abs(skew) > 0.3:
            arr = _rotate_bound(arr, skew)
            ops.append(PreprocessOp(name="deskew", applied=True, params={"deg": round(skew, 2)},
                                    reason=f"inclinaison estimée {skew:.2f}°"))

    # 3. perspective (photos)
    if aggressive or quality.contrast < 40:
        warped, ok = _correct_perspective(arr)
        if ok:
            arr = warped
            ops.append(PreprocessOp(name="perspective", applied=True,
                                    reason="quadrilatère de document détecté"))

    # 4. recadrage des bordures
    cropped, ok = _crop_borders(arr)
    if ok:
        arr = cropped
        ops.append(PreprocessOp(name="crop", applied=True, reason="bordures vides détectées"))

    # 5. ombres / éclairage inégal
    if "dark" in issues or "overexposed" in issues or aggressive:
        arr = _remove_shadows(arr)
        ops.append(PreprocessOp(name="shadow_removal", applied=True,
                                reason="éclairage inégal détecté"))

    # 6. contraste
    if "low_contrast" in issues:
        arr = _enhance_contrast(arr)
        ops.append(PreprocessOp(name="contrast", applied=True,
                                reason="contraste faible (écart-type luminance bas)"))

    # 7. débruitage (prudent : peut dégrader les petits caractères)
    if "noisy" in issues and not aggressive:
        arr = _denoise(arr, 5)
        ops.append(PreprocessOp(name="denoise", applied=True,
                                reason="bruit élevé estimé", params={"strength": 5}))

    # 8. agrandissement des petites résolutions
    if quality.estimated_dpi and quality.estimated_dpi < 150:
        factor = min(2.5, 200.0 / max(quality.estimated_dpi, 1.0))
        arr = _upscale(arr, factor)
        ops.append(PreprocessOp(name="upscale", applied=True,
                                params={"factor": round(factor, 2)},
                                reason=f"DPI estimé {quality.estimated_dpi:.0f} < 150"))

    # 9. binarisation adaptative — seulement si recommandé, jamais par défaut
    #    (elle peut détruire tampons, tableaux fins, écriture manuscrite)
    if "low_contrast" in issues and ("dark" in issues or "overexposed" in issues):
        arr = _binarize(arr)
        ops.append(PreprocessOp(name="binarize", applied=True,
                                reason="contraste ET éclairage dégradés"))

    return PreprocessResult(image=cv_to_pil(arr), quality=quality, ops=ops,
                            variant_name="preprocessed")


def detect_columns_projection(img: Image.Image) -> list[tuple[int, int]]:
    """Détecte les régions de colonnes par analyse de projection verticale de l'encre."""
    gray = cv2.cvtColor(pil_to_cv(img), cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    col_sum = th.sum(axis=0) / 255.0
    threshold = 0.005 * th.shape[0]
    cols = []
    in_col = False
    start = 0
    for x, v in enumerate(col_sum):
        if v > threshold and not in_col:
            in_col, start = True, x
        elif v <= threshold and in_col:
            if x - start > 20:
                cols.append((start, x))
            in_col = False
    if in_col and th.shape[1] - start > 20:
        cols.append((start, th.shape[1]))
    return cols or [(0, th.shape[1])]
