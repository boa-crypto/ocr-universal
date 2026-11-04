"""Tests des options de traitement : chaque option doit réellement agir."""
import time

import pytest

from unocr.models import FieldValue, JobOptions
from unocr.pipeline import Pipeline, parse_page_range
from unocr.quality import build_quality_report


# ---------------------------------------------------------------- helpers
def run(path, **kw):
    return Pipeline().process_file(str(path), JobOptions(**kw))


# ---------------------------------------------------------------- plage de pages
class TestParsePageRange:
    def test_vide_toutes_les_pages(self):
        assert parse_page_range("", 5) == [1, 2, 3, 4, 5]
        assert parse_page_range("  ", 3) == [1, 2, 3]

    def test_selection(self):
        assert parse_page_range("2", 5) == [2]
        assert parse_page_range("1-3,5", 6) == [1, 2, 3, 5]
        assert parse_page_range("3-1", 5) == [1, 2, 3]   # bornes inversées
        assert parse_page_range("4-99", 5) == [4, 5]      # dépassement tronqué

    def test_invalide_retombe_sur_tout(self):
        assert parse_page_range("abc", 3) == [1, 2, 3]
        assert parse_page_range("0", 3) == [1, 2, 3]

    def test_pipeline_filtre_les_pages(self):
        # text_pdf.pdf = 2 pages
        res = run("tests/fixtures/text_pdf.pdf", page_range="2", quality_mode="fast")
        assert len(res.pages) == 1
        assert res.pages[0].page_num == 2

    def test_pipeline_toutes_pages_sans_option(self):
        res = run("tests/fixtures/text_pdf.pdf", page_range="", quality_mode="fast")
        assert len(res.pages) == 2

    def test_selection_vide_securite(self):
        from unocr.security import SecurityError
        with pytest.raises(SecurityError):
            run("tests/fixtures/text_pdf.pdf", page_range="99", quality_mode="fast")


# ---------------------------------------------------------------- moteur
class TestEngineOption:
    def test_engine_native_pdf(self):
        res = run("tests/fixtures/text_pdf.pdf", engine="native")
        for p in res.pages:
            assert any("native" in er.engine for er in p.engine_runs), p.engine_runs
            assert not any("tesseract" in er.engine for er in p.engine_runs)

    def test_engine_tesseract_force(self):
        res = run("tests/fixtures/text_pdf.pdf", engine="tesseract", quality_mode="fast")
        for p in res.pages:
            assert not any("native" in er.engine for er in p.engine_runs), p.engine_runs

    def test_engine_native_repli_sur_scan(self):
        # scanned_pdf.pdf n'a pas de couche texte : repli Tesseract
        res = run("tests/fixtures/scanned_pdf.pdf", engine="native", quality_mode="fast")
        assert res.pages
        assert any("tesseract" in er.engine for er in res.pages[0].engine_runs)


# ---------------------------------------------------------------- prétraitement
class TestPreprocessOptions:
    def test_preprocess_off(self):
        res = run("tests/fixtures/skewed.png", preprocess_mode="off", quality_mode="fast")
        p = res.pages[0]
        assert any(o.name == "preprocess" and not o.applied for o in p.preprocess_ops)
        assert not any(o.applied for o in p.preprocess_ops)

    def test_standard_applique_des_ops(self):
        res = run("tests/fixtures/skewed.png", preprocess_mode="standard", quality_mode="fast")
        p = res.pages[0]
        assert any(o.applied for o in p.preprocess_ops), p.preprocess_ops

    def test_aggressive_existe(self):
        res = run("tests/fixtures/skewed.png", preprocess_mode="aggressive", quality_mode="fast")
        assert res.pages[0].text  # tourne au moins

    def test_variant_comparison_off(self):
        res = run("tests/fixtures/skewed.png", variant_comparison=False,
                  quality_mode="accurate")
        p = res.pages[0]
        # une seule variante traitée → un seul passage moteur
        assert len(p.engine_runs) == 1, p.engine_runs

    def test_variant_comparison_on(self):
        res = run("tests/fixtures/skewed.png", variant_comparison=True,
                  quality_mode="accurate")
        p = res.pages[0]
        # deux variantes (prétraitée + originale) → deux passages minimum
        assert len(p.engine_runs) >= 2, p.engine_runs


# ---------------------------------------------------------------- modules d'extraction
class TestExtractToggles:
    def test_no_tables(self):
        res = run("tests/fixtures/table_pdf.pdf", extract_tables=False)
        assert res.tables == []
        assert any(p.text for p in res.pages)

    def test_tables_on(self):
        res = run("tests/fixtures/table_pdf.pdf", extract_tables=True)
        assert len(res.tables) >= 1   # contrôle positif même fichier

    def test_no_barcodes(self):
        res = run("tests/fixtures/qr_code.png", extract_barcodes=False, quality_mode="fast")
        assert res.barcodes == []
        res2 = run("tests/fixtures/qr_code.png", extract_barcodes=True, quality_mode="fast")
        assert len(res2.barcodes) >= 1   # contrôle positif

    def test_no_fields(self):
        res = run("tests/fixtures/bl_port.pdf", extract_fields=False,
                  profile="generic", quality_mode="fast")
        assert res.fields == {}
        assert any(p.text for p in res.pages)

    def test_fields_on(self):
        res = run("tests/fixtures/bl_port.pdf", extract_fields=True,
                  profile="generic", quality_mode="fast")
        assert len(res.fields) > 0


# ---------------------------------------------------------------- seuil de revue
class TestReviewThreshold:
    def _fake(self):
        from unocr.models import DocumentResult
        r = DocumentResult(source_file="x", source_hash="h")
        r.fields["a"] = FieldValue(name="a", label="A", raw_value="1",
                                   confidence=0.5, engine_confidence=0.5)
        return r

    def test_seuil_bas_peu_de_revue(self):
        q = build_quality_report(self._fake(), review_threshold=0.1)
        assert q.fields_low_confidence == []
        assert q.pages_low_confidence == []

    def test_seuil_haut_force_la_revue(self):
        q = build_quality_report(self._fake(), review_threshold=0.9)
        assert "a" in q.fields_low_confidence

    def test_option_transmise_au_pipeline(self):
        res = run("tests/fixtures/bl_port.pdf", min_confidence_review=0.99,
                  quality_mode="fast")
        # à 99 %, des pages ou des champs passent sous le seuil
        assert (res.quality.fields_low_confidence or res.quality.pages_low_confidence
                or res.quality.anomalies)


# ---------------------------------------------------------------- options API
@pytest.fixture()
def client(tmp_cfg, fixtures_dir):
    from fastapi.testclient import TestClient

    from unocr.api import app
    return TestClient(app)


class TestApiOptions:
    def test_upload_avec_nouvelles_options(self, client):
        data = open("tests/fixtures/skewed.png", "rb").read()
        r = client.post("/api/documents", files={"file": ("skewed.png", data, "image/png")},
                        data={
                            "profile": "generic", "languages": "eng",
                            "quality_mode": "fast", "preprocess": "true",
                            "preprocess_mode": "off", "variant_comparison": "false",
                            "export_formats": "json", "page_range": "",
                            "render_dpi": "150", "engine": "tesseract",
                            "extract_fields": "true", "extract_tables": "false",
                            "extract_barcodes": "false",
                            "min_confidence_review": "0.9",
                        })
        assert r.status_code == 200, r.text
        job_id = r.json()["job_id"]
        for _ in range(120):
            j = client.get(f"/api/jobs/{job_id}").json()
            if j["status"] in ("done", "done_with_warnings", "error"):
                break
            time.sleep(0.25)
        assert j["status"] in ("done", "done_with_warnings"), j
        opt = j["options"]
        assert opt["preprocess_mode"] == "off"
        assert opt["variant_comparison"] is False
        assert opt["render_dpi"] == 150
        assert opt["engine"] == "tesseract"
        assert opt["extract_tables"] is False
        assert opt["extract_barcodes"] is False
        assert opt["min_confidence_review"] == 0.9
        # les options ont agi : pas de tableaux extraits, pas de prétraitement
        res = client.get(f"/api/jobs/{job_id}/result").json()
        assert res["tables"] == []
        assert res["barcodes"] == []
        for p in res["pages"]:
            assert all(not o["applied"] for o in p["preprocess_ops"])


class TestBooléensFormulaires:
    """Les booléens absents du multipart doivent garder leur valeur par défaut.

    Piège FastAPI : une déclaration `flag: bool = Form(True)` n'aboutit pas
    à `True` quand le champ est absent — FastAPI applique
    `infer_false_if_missing` et renvoie `False` pour tout booléen absent.
    Un client qui n'envoie que le fichier obtenait alors un traitement
    *sans* extraction de champs, sans tableaux et sans codes-barres, sans
    le moindre signal d'erreur.

    Ces tests verrouillent le comportement correct : absent → `True`.
    """

    def test_absence_de_champ_booléen_vaut_vrai(self):
        from unocr.api import _form_bool

        assert _form_bool(None) is True
        assert _form_bool(None, default=False) is False

    def test_valeurs_booléennes_explicites(self):
        from unocr.api import _form_bool

        for v in ("1", "true", "TRUE", "on", "yes", "oui", "vrai", " true "):
            assert _form_bool(v) is True, v
        for v in ("0", "false", "off", "no", "non", "faux", ""):
            assert _form_bool(v) is False, v

    def test_valeur_booléenne_invalide_est_refusée(self):
        import pytest
        from fastapi import HTTPException

        from unocr.api import _form_bool

        with pytest.raises(HTTPException) as exc:
            _form_bool("peut-être")
        assert exc.value.status_code == 422

    def test_upload_sans_options_booléennes_garde_les_défauts(self, client):
        """Un envoi minimal (fichier seul) doit extraire champs et tableaux."""
        data = open("tests/fixtures/skewed.png", "rb").read()
        r = client.post("/api/documents",
                        files={"file": ("skewed.png", data, "image/png")})
        assert r.status_code == 200, r.text
        job_id = r.json()["job_id"]
        j = {}
        for _ in range(120):
            j = client.get(f"/api/jobs/{job_id}").json()
            if j["status"] in ("done", "done_with_warnings", "error"):
                break
            time.sleep(0.25)
        assert j["status"] in ("done", "done_with_warnings"), j
        opt = j["options"]
        # les booléens absents restent activés
        assert opt["preprocess"] is True
        assert opt["variant_comparison"] is True
        assert opt["extract_fields"] is True
        assert opt["extract_tables"] is True
        assert opt["extract_barcodes"] is True

