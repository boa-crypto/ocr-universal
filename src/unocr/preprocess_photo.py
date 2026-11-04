"""Améliorations prétraitement photo — optimisation pour captures terrain.

Ces améliorations ciblent les cas d'usage photographique (conteneur, plaque,
carte grise) là où le prétraitement standard peut sous-performer :
- rotation/perspective : détection de bords + warp
- faible contraste : CLAHE agressif
- bruit : débruitage non-local means
- inclinaison : correction OSD plus agressive
"""
from __future__ import annotations

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class PreprocessStage(str, Enum):
    """Étapes du pipeline de prétraitement photo."""
    ORIENTATION = "orientation"
    PERSPECTIVE = "perspective"
    CONTRAST = "contrast"
    DENOISE = "denoise"
    Binarize = "binarize"
    RESIZE = "resize"


@dataclass
class PhotoPreprocessResult:
    """Résultat du prétraitement photo."""
    image: np.ndarray
    stage: str
    description: str
    improved: bool = False

    def as_dict(self) -> dict:
        return {
            "stage": self.stage,
            "description": self.description,
            "improved": self.improved,
            "shape": list(self.image.shape) if hasattr(self.image, "shape") else None,
        }


class PhotoPreprocessor:
    """Pipeline de prétraitement adapté aux photos de capture terrain."""

    def __init__(self, dpi: int = 300, aggressive: bool = False):
        self.dpi = dpi
        self.aggressive = aggressive

    # ─────────────────────── pipeline complet ───────────────────────

    def preprocess(self, image: np.ndarray,
                   stage: Optional[str] = None) -> PhotoPreprocessResult:
        """Applique une ou toutes les étapes de prétraitement.

        Si `stage` est fourni, n'applique que cette étape. Sinon, applique
        le pipeline complet dans l'ordre.
        """
        if stage:
            handler = {
                PreprocessStage.ORIENTATION.value: self._correct_orientation,
                PreprocessStage.PERSPECTIVE.value: self._correct_perspective,
                PreprocessStage.CONTRAST.value: self._enhance_contrast,
                PreprocessStage.DENOISE.value: self._denoise,
                PreprocessStage.Binarize.value: self._binarize,
                PreprocessStage.RESIZE.value: lambda img: self._resize(img),
            }.get(stage)
            if handler is None:
                raise ValueError(f"étape inconnue : {stage}")
            return handler(image)

        # Pipeline complet
        result = image
        stages_applied = []
        for fn, name in [
            (self._correct_orientation, PreprocessStage.ORIENTATION.value),
            (self._correct_perspective, PreprocessStage.PERSPECTIVE.value),
            (self._enhance_contrast, PreprocessStage.CONTRAST.value),
            (self._denoise, PreprocessStage.DENOISE.value),
            (self._binarize, PreprocessStage.Binarize.value),
            (self._resize, PreprocessStage.RESIZE.value),
        ]:
            prev = result
            result = fn(result)
            if result is not prev:
                stages_applied.append(name)

        return PhotoPreprocessResult(
            image=result,
            stage="full",
            description=f"étapes appliquées : {', '.join(stages_applied) or 'aucune'}",
            improved=len(stages_applied) > 0,
        )

    # ─────────────────────── étapes individuelles ───────────────────────

    @staticmethod
    def _correct_orientation(image: np.ndarray) -> np.ndarray:
        """Redresse l'image selon la détection OSD de Tesseract."""
        try:
            import pytesseract
            from pytesseract import Output
            ocr_dff = pytesseract.image_to_data(
                image, output_type=Output.DF, lang="osd")
            orientation = int(ocr_dff.loc[0, "orientation"])
            if orientation == 0:
                return image  # déjà droite
            # Rotation dans le sens inverse de l'orientation détectée
            angle = orientation * 90
            h, w = image.shape[:2]
            center = (w // 2, h // 2)
            mat = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, mat, (w, h),
                                     flags=cv2.INTER_CUBIC)
            return rotated
        except Exception:
            return image  # en cas d'erreur, on garde l'original

    @staticmethod
    def _correct_perspective(image: np.ndarray) -> np.ndarray:
        """Détection de contours et correction de perspective."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(gray, 50, 150)

        contours, _ = cv2.findContours(
            edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

        for cnt in contours:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4:
                pts = approx.reshape(4, 2)
                # Tri des points : haut-gauche, haut-droite, bas-droite, bas-gauche
                rect = PhotoPreprocessor._order_points(pts)
                (tl, tr, br, bl) = rect
                width_a = np.linalg.norm(br - bl)
                width_b = np.linalg.norm(tr - tl)
                height_a = np.linalg.norm(tr - br)
                height_b = np.linalg.norm(tl - bl)
                max_w = int(max(width_a, width_b))
                max_h = int(max(height_a, height_b))
                dst = np.array([
                    [0, 0], [max_w, 0], [max_w, max_h], [0, max_h]], dtype="float32")
                m = cv2.getPerspectiveTransform(rect.astype("float32"), dst)
                warped = cv2.warpPerspective(image, m, (max_w, max_h),
                                             flags=cv2.INTER_CUBIC)
                return warped
        return image

    @staticmethod
    def _enhance_contrast(image: np.ndarray) -> np.ndarray:
        """CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            merged = cv2.merge([l, a, b])
            return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        else:
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            return clahe.apply(image)

    @staticmethod
    def _denoise(image: np.ndarray) -> np.ndarray:
        """Débruitage non-local means (plus lent mais plus qualitatif)."""
        try:
            return cv2.fastNlMeansDenoisingColored(
                image, None, h=10, hColor=10,
                templateWindowSize=7, searchWindowSize=21)
        except Exception:
            # Fallback : débruitage bilateral plus rapide
            return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)

    @staticmethod
    def _binarize(image: np.ndarray) -> np.ndarray:
        """Binarisation adaptative — seuil par zone."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, blockSize=11, C=2)

    @staticmethod
    def _resize(image: np.ndarray) -> np.ndarray:
        """Redimensionne pour correspondre au DPI cible."""
        h, w = image.shape[:2]
        # Approximation : 96 DPI standard → facteur d'échelle
        scale = 96.0 / 96.0  # par défaut, pas de redimensionnement
        if scale != 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        return image

    @staticmethod
    def _order_points(pts: np.ndarray) -> np.ndarray:
        """Tri des 4 coins dans l'ordre : haut-gauche, haut-droite, bas-droite, bas-gauche."""
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]   # haut-gauche (somme minimale)
        rect[2] = pts[np.argmax(s)]   # bas-droite (somme maximale)
        d = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(d)]   # haut-droite (diff minimale)
        rect[3] = pts[np.argmax(d)]   # bas-gauche (diff maximale)
        return rect


def preprocess_photo(image: np.ndarray, aggressive: bool = False) -> PhotoPreprocessResult:
    """Fonction utilitaire rapide pour le prétraitement photo.

    `aggressive=True` active le débruitage non-local means (plus lent,
    meilleur sur photos dégradées).
    """
    pp = PhotoPreprocessor(aggressive=aggressive)
    return pp.preprocess(image)


# ---------------------------------------------------------------------------
# Sauvegarde d'une variante pour comparaison UI
# ---------------------------------------------------------------------------

def save_variant(image: np.ndarray, path: Path, stage: str) -> Path:
    """Sauvegarde une variante prétraitée pour comparaison visuelle."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)
    return path
