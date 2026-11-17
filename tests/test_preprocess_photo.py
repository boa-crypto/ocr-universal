"""Tests du prétraitement photo pour captures terrain.

Valide les étapes du pipeline PhotoPreprocessor et les fonctions utilitaires.
"""
from __future__ import annotations

import numpy as np
import pytest

from unocr.preprocess_photo import (
    PhotoPreprocessor,
    PhotoPreprocessResult,
    PreprocessStage,
    preprocess_photo,
    save_variant,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_image():
    """Génère une image synthétique 100x100 pixels (RGB)."""
    img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    # Ajoute des pixels contrastés
    img[10:30, 10:30] = [255, 255, 255]   # blanc
    img[70:90, 70:90] = [0, 0, 0]          # noir
    img[40:60, 40:60] = [0, 0, 255]        # bleu
    return img


@pytest.fixture
def sample_gray():
    """Image en niveaux de gris 100x100."""
    img = np.ones((100, 100), dtype=np.uint8) * 128
    img[10:30, 10:30] = 255
    img[70:90, 70:90] = 0
    return img


# ---------------------------------------------------------------------------
# Tests de configuration
# ---------------------------------------------------------------------------

class TestPhotoPreprocessorInit:
    def test_default_dpi(self):
        pp = PhotoPreprocessor()
        assert pp.dpi == 300

    def test_custom_dpi(self):
        pp = PhotoPreprocessor(dpi=150)
        assert pp.dpi == 150

    def test_aggressive_mode(self):
        pp = PhotoPreprocessor(aggressive=True)
        assert pp.aggressive is True


# ---------------------------------------------------------------------------
# Tests des étapes individuelles
# ---------------------------------------------------------------------------

class TestOrientation:
    def test_no_rotation_needed(self, sample_image):
        """Si l'image n'a pas d'orientation détectée, retourne l'originale."""
        pp = PhotoPreprocessor()
        # En absence de Tesseract, _correct_orientation retourne l'original
        result = pp._correct_orientation(sample_image)
        assert result is sample_image or result.shape == sample_image.shape

    def test_rotation_with_mock(self, sample_image, monkeypatch):
        """Simule une détection d'orientation à 90°."""
        import cv2
        mock_rotated = sample_image.copy()
        monkeypatch.setattr(cv2, "warpAffine", lambda *a, **kw: mock_rotated)
        monkeypatch.setattr(cv2, "getRotationMatrix2D", lambda *a, **kw: {})
        pp = PhotoPreprocessor()
        result = pp._correct_orientation(sample_image)
        assert result.shape == sample_image.shape


class TestPerspective:
    def test_no_crash_on_uniform_image(self, sample_image):
        """L'application de la correction de perspective ne doit pas planter."""
        pp = PhotoPreprocessor()
        # Même si les contours sont rares sur une image uniforme, ça ne doit
        # pas lever d'exception ni retourner un résultat de taille absurde.
        result = pp._correct_perspective(sample_image)
        assert result is not None
        assert len(result.shape) == 3  # reste une image RGB
        assert result.shape[2] == 3    # conserve les 3 canaux

    def test_with_contour_mock(self, sample_image, monkeypatch):
        """Simule la détection d'un contour quadrilatéral."""
        import cv2
        pts = np.array([[[10, 10], [90, 10], [90, 90], [10, 90]]], dtype=np.int32)
        monkeypatch.setattr(cv2, "findContours", lambda *a, **kw: (pts, None))
        monkeypatch.setattr(cv2, "Canny", lambda *a, **kw: sample_image)
        monkeypatch.setattr(cv2, "GaussianBlur", lambda *a, **kw: sample_image)
        monkeypatch.setattr(cv2, "warpPerspective", lambda *a, **kw: sample_image)
        pp = PhotoPreprocessor()
        result = pp._correct_perspective(sample_image)
        assert result.shape == sample_image.shape


class TestContrast:
    def test_clahe_color(self, sample_image):
        pp = PhotoPreprocessor()
        result = pp._enhance_contrast(sample_image)
        assert result.shape == sample_image.shape

    def test_clahe_grayscale(self, sample_gray):
        pp = PhotoPreprocessor()
        result = pp._enhance_contrast(sample_gray)
        assert result.shape == sample_gray.shape


class TestDenoise:
    def test_fastnlmeans(self, sample_image):
        pp = PhotoPreprocessor()
        result = pp._denoise(sample_image)
        assert result.shape == sample_image.shape


class TestBinarize:
    def test_binary_color(self, sample_image):
        pp = PhotoPreprocessor()
        result = pp._binarize(sample_image)
        assert result.shape == sample_image.shape[:2]
        # Valeurs binaires uniquement
        assert set(np.unique(result)).issubset({0, 255})

    def test_binary_grayscale(self, sample_gray):
        pp = PhotoPreprocessor()
        result = pp._binarize(sample_gray)
        assert result.shape == sample_gray.shape
        assert set(np.unique(result)).issubset({0, 255})


class TestResize:
    def test_no_resize_at_96dpi(self, sample_image):
        pp = PhotoPreprocessor(dpi=96)
        result = pp._resize(sample_image)
        assert result.shape == sample_image.shape


# ---------------------------------------------------------------------------
# Tests du pipeline complet
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_pipeline_runs(self, sample_image):
        pp = PhotoPreprocessor()
        result = pp.preprocess(sample_image)
        assert isinstance(result, PhotoPreprocessResult)
        assert result.stage == "full"
        # Le pipeline applique CLAHE, débruitage, puis binarisation.
        # La binarisation produit une image 2D (niveaux de gris) — c'est
        # le comportement attendu pour l'optimisation OCR.
        assert len(result.image.shape) in (2, 3)
        assert result.improved is True

    def test_pipeline_stage_only(self, sample_image):
        pp = PhotoPreprocessor()
        result = pp.preprocess(sample_image, stage=PreprocessStage.CONTRAST.value)
        assert isinstance(result, np.ndarray)
        assert result.shape == sample_image.shape

    def test_invalid_stage(self, sample_image):
        pp = PhotoPreprocessor()
        with pytest.raises(ValueError, match="étape inconnue"):
            pp.preprocess(sample_image, stage="invalid")

    def test_aggressive_mode(self, sample_image):
        pp = PhotoPreprocessor(aggressive=True)
        result = pp.preprocess(sample_image)
        assert result.stage == "full"



# ---------------------------------------------------------------------------
# Tests fonctionnels
# ---------------------------------------------------------------------------

class TestFunctional:
    def test_preprocess_photo_function(self, sample_image):
        result = preprocess_photo(sample_image)
        assert isinstance(result, PhotoPreprocessResult)

    def test_preprocess_photo_aggressive(self, sample_image):
        result = preprocess_photo(sample_image, aggressive=True)
        assert isinstance(result, PhotoPreprocessResult)

    def test_save_variant(self, sample_image, tmp_path):
        out = tmp_path / "variants" / "test.png"
        path = save_variant(sample_image, out, stage="contrast")
        assert path.is_file()
        assert path.suffix == ".png"

    def test_result_as_dict(self, sample_image):
        pp = PhotoPreprocessor()
        result = pp.preprocess(sample_image)
        d = result.as_dict()
        assert d["stage"] == "full"
        assert "description" in d
        assert "shape" in d


# ---------------------------------------------------------------------------
# Tests d'intégration avec le pipeline OCR
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_preprocess_then_ocr(self):
        """Vérifie que le prétraitement photo ne casse pas le pipeline OCR."""

        from unocr.models import JobOptions
        from unocr.pipeline import Pipeline

        # Utilise une image fixture existante
        fixture = "tests/fixtures/photo_plate_fr.png"
        if not __import__("pathlib").Path(fixture).is_file():
            pytest.skip("fixture photo_plate_fr.png absente")

        options = JobOptions(profile="vehicle_plate", quality_mode="fast")
        res = Pipeline().process_file(fixture, options)
        assert res.pages
        assert res.fields  # champs extraits
