"""Tests capture photo : profils conteneur (ISO 6346) et plaque / véhicule.

Valide les validateurs `plate` et `vin`, l'application des profils sur texte,
et l'extraction de bout en bout (OCR → profil) sur photos synthétiques.

Les tests qui appellent réellement Tesseract (Pipeline.process_file sur une
image raster) sont automatiquement ignorés quand Tesseract n'est pas installé
sur la machine — exactement comme le font test_ocr.py et test_i18n.py.
"""
import json

import pytest

from unocr.models import FieldStatus, JobOptions
from unocr.ocr_engines import TesseractEngine
from unocr.pipeline import Pipeline
from unocr.profiles import (
    apply_profile,
    energy_ok,
    iso6346_check_digit_ok,
    load_profiles,
    plate_format,
    plate_number_ok,
    vin_check_ok,
    vin_ok,
)

PROFILES_DIR = __import__("pathlib").Path("profiles")

# Décorateur réutilisable : skip si Tesseract absent (binaire ou modèles manquants)
_tesseract_absent = not TesseractEngine().is_available()
requires_tesseract = pytest.mark.skipif(
    _tesseract_absent,
    reason="Tesseract absent de l'environnement — tests OCR raster ignorés",
)


@pytest.fixture(scope="module")
def profiles():
    return load_profiles(PROFILES_DIR)


# ---------------------------------------------------------------- fixture client OCR
# ---------------------------------------------------------------- validateurs
class TestPlateValidator:
    @pytest.mark.parametrize("value", [
        "AB-123-CD", "AB123CD",            # français SIV
        "A-123-BC", "AA-12-BB",            # français ancien (FNI)
        "12345 AB 16", "00123 ج 16",       # algérienne (latine / arabe)
    ])
    def test_formats_reconnus(self, value):
        assert plate_number_ok(value) is True

    def test_wilaya_hors_plage(self):
        assert plate_number_ok("12345 AB 99") is False

    @pytest.mark.parametrize("value", ["12345", "1234516", "ZZZZZ", "??"])
    def test_structure_inconnue_none(self, value):
        assert plate_number_ok(value) is None

    def test_vide(self):
        assert plate_number_ok("") is False


class TestPlateFormatsInternationaux:
    @pytest.mark.parametrize("value,fmt", [
        ("AB-123-CD", "fr_siv"), ("AB 123 CD", "fr_siv"),
        ("A-123-BC", "fr_fni"),
        ("12345 AB 16", "dz"), ("00123 ج 16", "dz"),
        ("1234 BCD", "es"),
        ("M-AB 1234", "de"), ("B MM 123", "de"),
        ("AA-11-BB", "pt_nl"), ("12-AB-34", "pt_nl"),
        ("1-ABC-123", "be"),
        ("AB12 CDE", "uk"), ("A123 BCD", "uk"),
        ("34 ABC 123", "tr"),
        ("12345 A 6", "ma"),
        ("1234 تونس 56", "tn"),
    ])
    def test_format_identifie(self, value, fmt):
        name, ok = plate_format(value)
        assert name == fmt and ok is True

    def test_es_voyelle_serie_invalide(self):
        assert plate_format("1234 AEI") == ("es", False)

    def test_tr_province_inexistante(self):
        # "99 ABC 123" n'est un match pour aucun autre format → verdict honnête
        assert plate_format("99 ABC 123") == ("tr", False)

    def test_collision_honnete(self):
        # "99AB12" est un format nl (DDLLDD) valide, même si la lecture TR dirait « province 99 »
        name, ok = plate_format("99AB12")
        assert ok is True and name == "pt_nl"

    def test_inconnu_ne_tranche_jamais(self):
        assert plate_format("XYZ-9999-QQ!") == (None, None)


class TestEnergyValidator:
    @pytest.mark.parametrize("value", [
        "DIESEL", "ESSENCE", "ESSENCE SP95", "Électrique", "Hybride", "GPL",
        "GO", "ES", "Gazole", "Éthanol E85",
    ])
    def test_energies_connues(self, value):
        assert energy_ok(value) is True

    def test_terme_inconnu_ne_tranche_pas(self):
        assert energy_ok("INCONNU") is None
        assert energy_ok("VITESSE") is None   # piège « ES » en sous-chaîne

    def test_vide(self):
        assert energy_ok("") is False


class TestVinValidator:
    def test_vin_valide(self):
        assert vin_ok("1HGBH41JXMN109186") is True

    def test_vin_partiel_none(self):
        assert vin_ok("1HGBH41JXMN10918") is None   # 16 caractères

    def test_vin_lettres_interdites(self):
        assert vin_ok("IHGBH41JXMN109186") is False  # I interdit (ISO 3779)

    def test_vide(self):
        assert vin_ok("") is False


class TestVinCheckDigit:
    def test_na_conforme(self):
        assert vin_check_ok("1HGBH41JXMN109186") is True   # check digit X

    def test_na_corrompu_j3(self):
        # erreur OCR mesurée au benchmark (J→3) : check digit faux → False
        assert vin_check_ok("1HGBH413XMN109186") is False

    def test_europe_non_concerne(self):
        # 1er caractère hors 1–5 : la position 9 n'est pas un check digit
        assert vin_check_ok("WBA3A5C58CF264878") is None

    def test_longueur_invalide(self):
        assert vin_check_ok("1HGBH41JXMN10918") is None

    def test_profil_ne_montre_pas_les_vin_europeens(self):
        pro = load_profiles(PROFILES_DIR)
        f = apply_profile("N° d'identification : WBA3A5C58CF264878",
                          pro["carte_grise"])["vin"]
        assert f.status == FieldStatus.DETECTED
        assert "validator:vin_check:unverifiable" not in f.anomalies

    def test_profil_flag_le_vin_corrompu(self):
        pro = load_profiles(PROFILES_DIR)
        f = apply_profile("N° d'identification : 1HGBH413XMN109186",
                          pro["carte_grise"])["vin"]
        assert f.status == FieldStatus.INVALID
        assert "validator:vin_check:failed" in f.anomalies


# ---------------------------------------------------------------- profils sur texte
class TestContainerProfile:
    def test_conteneur_valide(self, profiles):
        f = apply_profile("CSQU 3054383", profiles["container"])["container_number"]
        assert f.raw_value.replace(" ", "") == "CSQU3054383"
        assert f.status == FieldStatus.DETECTED
        assert f.anomalies == []

    def test_conteneur_chiffre_controle_faux(self, profiles):
        f = apply_profile("CSQU 3054389", profiles["container"])["container_number"]
        assert f.status == FieldStatus.INVALID
        assert "validator:iso6346:failed" in f.anomalies

    def test_absent_jamais_invente(self, profiles):
        f = apply_profile("aucun numéro ici", profiles["container"])["container_number"]
        assert f.raw_value is None
        assert f.status == FieldStatus.NOT_DETECTED


class TestVehiclePlateProfile:
    def test_plaque_fr(self, profiles):
        f = apply_profile("Plaque: AB-123-CD", profiles["vehicle_plate"])["plate_number"]
        assert f.normalized_value == "AB-123-CD"
        assert f.status == FieldStatus.DETECTED

    def test_plaque_dz(self, profiles):
        f = apply_profile("12345 AB 16", profiles["vehicle_plate"])["plate_number"]
        assert f.status == FieldStatus.DETECTED

    def test_plaque_wilaya_fausse(self, profiles):
        f = apply_profile("12345 AB 99", profiles["vehicle_plate"])["plate_number"]
        assert f.status == FieldStatus.INVALID

    def test_vin_valide(self, profiles):
        f = apply_profile("VIN 1HGBH41JXMN109186", profiles["vehicle_plate"])["vin"]
        assert f.normalized_value == "1HGBH41JXMN109186"
        assert f.status == FieldStatus.DETECTED

    def test_vin_partiel_ambigu(self, profiles):
        f = apply_profile("châssis 1HGBH41JXMN1091", profiles["vehicle_plate"])["vin"]
        assert f.status == FieldStatus.AMBIGUOUS
        assert "validator:vin:unverifiable" in f.anomalies


# ---------------------------------------------------------------- OCR de bout en bout (photos)
@pytest.fixture()
def client(tmp_cfg, fixtures_dir):
    from fastapi.testclient import TestClient

    from unocr.api import app
    return TestClient(app)


class TestCaptureOCR:
    @requires_tesseract
    def test_photo_conteneur(self):
        res = Pipeline().process_file(
            "tests/fixtures/photo_container.png",
            JobOptions(profile="container", quality_mode="fast"))
        f = res.fields["container_number"]
        assert f.raw_value.replace(" ", "") == "CSQU3054383"
        assert f.status == FieldStatus.DETECTED
        assert iso6346_check_digit_ok(f.normalized_value) is True

    @requires_tesseract
    def test_photo_plaque_fr(self):
        res = Pipeline().process_file(
            "tests/fixtures/photo_plate_fr.png",
            JobOptions(profile="vehicle_plate", quality_mode="fast"))
        f = res.fields["plate_number"]
        assert f.normalized_value == "AB-123-CD"
        assert f.status == FieldStatus.DETECTED

    @requires_tesseract
    def test_photo_plaque_dz(self):
        res = Pipeline().process_file(
            "tests/fixtures/photo_plate_dz.png",
            JobOptions(profile="vehicle_plate", quality_mode="fast"))
        f = res.fields["plate_number"]
        assert f.normalized_value == "12345 AB 16"
        assert f.status == FieldStatus.DETECTED

    @requires_tesseract
    def test_photo_vin(self):
        res = Pipeline().process_file(
            "tests/fixtures/photo_vin.png",
            JobOptions(profile="vehicle_plate", quality_mode="fast"))
        f = res.fields["vin"]
        assert f.normalized_value == "1HGBH41JXMN109186"
        assert f.status == FieldStatus.DETECTED

    def test_api_profiles_contient_les_nouveaux(self, client):
        r = client.get("/api/profiles")
        names = {p["name"] for p in r.json()}
        assert {"container", "vehicle_plate", "carte_grise"} <= names


# ---------------------------------------------------------------- carte grise
CARTE_GRISE_TXT = """CERTIFICAT D'IMMATRICULATION
Plaque : AB-123-CD
N° d'identification : 1HGBH41JXMN109186
Marque : RENAULT
Énergie : DIESEL
1ère immatriculation : 12/03/2019
"""


class TestCarteGriseProfile:
    def test_champs_cles(self, profiles):
        r = apply_profile(CARTE_GRISE_TXT, profiles["carte_grise"])
        assert r["plate_number"].status == FieldStatus.DETECTED
        assert r["plate_number"].normalized_value == "AB-123-CD"
        assert r["vin"].normalized_value == "1HGBH41JXMN109186"
        assert r["make"].normalized_value == "RENAULT"
        assert r["fuel"].normalized_value == "DIESEL"
        assert r["fuel"].status == FieldStatus.DETECTED   # énergie connue
        assert r["first_reg_date"].normalized_value == "2019-03-12"

    def test_titre_ne_fait_pas_plaque(self, profiles):
        # le mot « IMMATRICULATION » du titre ne doit pas être capturé comme plaque
        f = apply_profile("CERTIFICAT D'IMMATRICULATION\n", profiles["carte_grise"])["plate_number"]
        assert f.status == FieldStatus.NOT_DETECTED

    def test_energie_inconnue_ambigue(self, profiles):
        f = apply_profile("Énergie : FLUIDE MAGIQUE", profiles["carte_grise"])["fuel"]
        assert f.status == FieldStatus.AMBIGUOUS

    @requires_tesseract
    def test_photo_carte_grise_13_champs(self):
        res = Pipeline().process_file(
            "tests/fixtures/photo_carte_grise.png",
            JobOptions(profile="carte_grise", quality_mode="fast"))
        attendus = {
            "plate_number": "AB-123-CD",
            "vin": "1HGBH41JXMN109186",
            "make": "RENAULT",
            "fuel": "DIESEL",
            "first_reg_date": "2019-03-12",
            "fiscal_power": "7",
            "power_kw": "55",
            "ptac": "1640",
            "seats": "5",
            "color": "GRIS",
            "co2": "98",
        }
        for key, want in attendus.items():
            f = res.fields[key]
            assert f.raw_value, f"{key} absent"
            assert f.normalized_value == want, f"{key}: {f.normalized_value!r} != {want!r}"
            assert f.status == FieldStatus.DETECTED, (key, f.anomalies)
        assert res.fields["holder"].raw_value.startswith("DUPONT")
        assert res.fields["model"].raw_value.startswith("CLIO")

    @requires_tesseract
    def test_champs_carte_grise_algerienne(self):
        res = Pipeline().process_file(
            "tests/fixtures/photo_carte_grise.png",
            JobOptions(profile="carte_grise", quality_mode="fast"))
        attendus = {"engine_number": "K9K742", "cylinder": "1461",
                    "empty_weight": "1145", "genre": "TOURISME",
                    "doc_number": "1612345670"}
        for key, want in attendus.items():
            f = res.fields[key]
            assert f.raw_value, f"{key} absent"
            assert f.normalized_value == want, (key, f.normalized_value)
            assert f.status == FieldStatus.DETECTED, (key, f.anomalies)

    def test_gabarit_terrain(self, tmp_path):
        import importlib.util
        from pathlib import Path
        bench = Path(__file__).resolve().parents[1] / "benchmarks"
        spec = importlib.util.spec_from_file_location(
            "run_field_benchmark", bench / "run_field_benchmark.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        (tmp_path / "photo.jpg").write_bytes(b"x")
        gt = mod.init_template(tmp_path)
        data = json.loads(gt.read_text(encoding="utf-8"))
        assert "photo.jpg" in data and data["photo.jpg"]["fields"] == {}


# ---------------------------------------------------------------- secours variante
class TestSecoursVariantePretraitee:
    """Quand le prétraitement dégrade la page (0 mot), la variante suivante
    (l'original) doit être tentée même en mode fast."""

    @requires_tesseract
    def test_field_hard_n_est_plus_perdu(self):
        import importlib.util
        from pathlib import Path
        bench = Path(__file__).resolve().parents[1] / "benchmarks"
        spec = importlib.util.spec_from_file_location(
            "make_field_samples", bench / "make_field_samples.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.make_field_samples()
        sample = bench / "field_samples" / "container__field_hard.png"
        res = Pipeline().process_file(
            sample, JobOptions(profile="container", quality_mode="fast"))
        assert res.pages[0].text.strip(), "aucun texte après secours variante"
        f = res.fields["container_number"]
        assert f.raw_value and f.raw_value.replace(" ", "").upper() == "CSQU3054383"
