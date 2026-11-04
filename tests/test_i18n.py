"""Tests C3 : i18n de l'interface, cohérence des dictionnaires, RTL."""
import json
import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
INDEX = WEB / "index.html"
#: Le comportement de changement de langue a été extrait dans un module
#: dédié, servi par `<script src="/modules/i18n-controls.js">`. Les tests
#: doivent donc lire la coquille HTML **et** le module : chercher le
#: comportement dans le seul index.html donnerait un faux négatif.
I18N_MODULE = WEB / "modules" / "i18n-controls.js"
SRC = Path(__file__).resolve().parent.parent / "src"


def _html() -> str:
    """La coquille HTML **et** le module i18n chargé par la page.

    La page est servie telle quelle par le navigateur : le script externe
    fait partie du code exécuté. Leurs deux contenus forment donc le
    comportement réel de l'interface.
    """
    module = I18N_MODULE.read_text(encoding="utf-8") if I18N_MODULE.is_file() else ""
    return INDEX.read_text(encoding="utf-8") + "\n" + module


def _i18n_block() -> str:
    s = _html()
    start = s.find("var I18N = {")
    assert start != -1, "bloc I18N introuvable dans web/index.html"
    # découpe du littéral JS par accolades équilibrées
    i = s.find("{", start)
    depth, j = 0, i
    while j < len(s):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return s[i:j + 1]


def _dicts() -> dict:
    """Extrait les dictionnaires I18N sans exécuter de JS (JSON5 → JSON)."""
    block = _i18n_block()
    # clés entre guillemets doubles, tableaux de chaînes → JSON valide
    fixed = re.sub(r"(\w+):", r'"\1":', block)
    fixed = fixed.replace("\n", " ")
    data = json.loads(fixed)
    return data


# ───────────────────────── dictionnaires ─────────────────────────

def test_three_languages_present():
    d = _dicts()
    assert set(d) >= {"fr", "en", "ar"}, f"langues trouvées : {sorted(d)}"


def test_every_key_translated_in_every_language():
    """Aucune clé ne manque dans une langue : pas de repli silencieux."""
    d = _dicts()
    ref = set(d["fr"])
    for lang, dic in d.items():
        missing = ref - set(dic)
        assert not missing, f"{lang} : clés non traduites {sorted(missing)}"
        empty = [k for k, v in dic.items()
                 if not (isinstance(v, str) and v.strip())
                 and not (isinstance(v, list) and v and all(x.strip() for x in v))]
        assert not empty, f"{lang} : traductions vides {empty}"


def test_arabic_translations_are_arabic():
    """Garde-fou : les traductions arabes contiennent bien de l'arabe."""
    d = _dicts()
    arabic = re.compile(r"[\u0600-\u06FF]")
    for k, v in d["ar"].items():
        if k.startswith("page.") or k.startswith("nav.") or k.startswith("h."):
            text = " ".join(v) if isinstance(v, list) else v
            assert arabic.search(text), f"clé {k} : traduction arabe suspecte ({text!r})"


def test_page_entries_have_title_and_subtitle():
    d = _dicts()
    for lang, dic in d.items():
        for k, v in dic.items():
            if k.startswith("page."):
                assert isinstance(v, list) and len(v) == 2, \
                    f"{lang}/{k} doit être [titre, sous-titre]"


# ───────────────────────── câblage HTML ─────────────────────────

def _html_no_comments() -> str:
    """HTML sans commentaires JS : un exemple dans un commentaire n'est pas
    un attribut réellement posé sur un élément."""
    return re.sub(r"/\*.*?\*/", "", _html(), flags=re.S)


def test_all_data_i18n_keys_exist_in_french():
    """Chaque clé utilisée par le HTML existe au moins en français."""
    html = _html_no_comments()
    used = set(re.findall(r'data-i18n="([^"]+)"', html))
    assert used, "aucun élément data-i18n dans le HTML"
    known = set(_dicts()["fr"])
    missing = used - known
    assert not missing, f"clés utilisées sans traduction française : {sorted(missing)}"


def test_language_switcher_present():
    html = _html_no_comments()
    for lang in ("fr", "en", "ar"):
        assert f'data-lang="{lang}"' in html, f"bouton de langue {lang} absent"
    assert "setUILang" in html and "localStorage" in html


def test_rtl_switching_logic_present():
    """Le passage en arabe doit basculer dir=rtl sur <html>."""
    html = _html()
    assert 'document.documentElement.dir = rtl' in html
    assert "rtl" in html and '[dir="rtl"]' in html      # CSS miroir présent


def test_no_external_resource_for_i18n():
    """Les traductions sont embarquées : aucun fichier de langue à charger.

    L'interface doit fonctionner hors ligne. Le seul script chargé est un
    module **de même origine** (`/modules/...`), servi par l'application
    elle-même : ce n'est pas une ressource externe. Ce qui est interdit, c'est
    une ressource distante (CDN, CDN de polices, lien http).
    """
    html = _html()
    for src in re.findall(r'src="([^"]+)"', html):
        assert src.startswith("/"), f"script distant détecté : {src}"
    assert not re.search(r'href="https?://', html), "ressource externe détectée"
    assert not re.search(r'src="//', html), "ressource protocol-relative détectée"


# ───────────────────────── détection de direction ─────────────────────────

def test_detect_direction_arabic():
    import sys
    sys.path.insert(0, str(SRC))
    from unocr.direction import detect_direction

    ar = "شهادة التسجيل رقم AB-123-CD تاريخ 12/03/2019"
    assert detect_direction(ar) == "rtl"
    assert detect_direction("CERTIFICAT D'IMMATRICULATION") == "ltr"
    assert detect_direction("") == "neutral"
    assert detect_direction("AB") == "neutral"        # trop court pour décider


def test_detect_direction_hebrew():
    import sys
    sys.path.insert(0, str(SRC))
    from unocr.direction import detect_direction

    assert detect_direction("זהו טקסט בעברית较长") == "rtl"


def test_dominant_direction():
    import sys
    sys.path.insert(0, str(SRC))
    from unocr.direction import dominant_direction

    assert dominant_direction(["rtl", "rtl", "ltr"]) == "rtl"
    assert dominant_direction(["ltr", "ltr", "rtl"]) == "ltr"
    assert dominant_direction([]) == "neutral"


def test_rtl_spans():
    import sys
    sys.path.insert(0, str(SRC))
    from unocr.direction import rtl_spans

    spans = rtl_spans("Plaque AB-123 وشهادة")
    assert spans, "aucune plage RTL trouvée"
    assert all(b > a for a, b in spans)


# ─────────────────────── intégration pipeline (RTL) ───────────────────────

def test_arabic_fixture_detected_as_rtl():
    """Bout en bout : un document arabe doit ressortir en direction RTL."""
    import sys
    sys.path.insert(0, str(SRC))
    from unocr.models import JobOptions
    from unocr.pipeline import Pipeline

    fixture = Path(__file__).resolve().parent / "fixtures" / "photo_arabe.png"
    if not fixture.is_file():
        import pytest
        pytest.skip("fixture arabe absente")

    # Le modèle arabe est une dépendance *système* (`tesseract-ocr-ara`).
    # S'il n'est pas installé, l'OCR ne peut pas reconnaître l'arabe : le
    # test est alors inapplicable, pas en échec.
    from unocr.ocr_engines import TesseractEngine
    if "ara" not in TesseractEngine().supported_languages():
        import pytest
        pytest.skip("modèle tessdata « ara » absent (paquet tesseract-ocr-ara)")

    res = Pipeline().process_file(fixture, JobOptions(languages=["ara"],
                                                     quality_mode="fast"))
    assert res.direction == "rtl"
    assert all(pg.direction == "rtl" for pg in res.pages)
    # le texte extrait contient bien de l'arabe
    assert re.search(r"[\u0600-\u06FF]", res.pages[0].text)


def test_latin_fixture_detected_as_ltr():
    import sys
    sys.path.insert(0, str(SRC))
    from unocr.models import JobOptions
    from unocr.pipeline import Pipeline

    fixture = Path(__file__).resolve().parent / "fixtures" / "text_pdf.pdf"
    if not fixture.is_file():
        import pytest
        pytest.skip("fixture absente")
    res = Pipeline().process_file(fixture, JobOptions(quality_mode="fast"))
    assert res.direction == "ltr"
