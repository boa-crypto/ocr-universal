"""Tests extraction : champs génériques, tableaux, profils, ISO 6346."""

from unocr.extract_fields import extract_generic_fields, locate_value
from unocr.extract_tables import (
    cluster_rows,
    extract_borderless_table,
    infer_columns,
    merge_multipage_tables,
)
from unocr.models import BBox, FieldStatus, PageResult, Word
from unocr.profiles import (
    apply_profile,
    check_required,
    iban_ok,
    iso6346_check_digit_ok,
    load_profiles,
    luhn_ok,
)


def _page_with_text(text: str, page_num=1) -> PageResult:
    words = []
    x = 10.0
    for i, w in enumerate(text.split()):
        words.append(Word(text=w, bbox=BBox(x0=x, y0=10, x1=x + 8 * len(w), y1=30),
                          confidence=0.9, page_num=page_num))
        x += 8 * len(w) + 8
    return PageResult(page_num=page_num, width=800, height=600, text=text,
                      words=words)


def test_extract_dates_and_amounts():
    page = _page_with_text("Date : 15/03/2024 Total : 1.250,50 EUR Email : a@example.dz")
    fields, cats = extract_generic_fields([page])
    assert fields["date"].normalized_value == "2024-03-15"
    assert fields["amount"].normalized_value is not None
    assert fields["email"].raw_value == "a@example.dz"
    assert "dates" in cats


def test_missing_field_returns_not_detected():
    page = _page_with_text("Aucune information utile ici")
    fields, _ = extract_generic_fields([page])
    assert fields["email"].status == FieldStatus.NOT_DETECTED
    assert fields["email"].raw_value is None  # jamais inventé


def test_locate_value_finds_bbox():
    page = _page_with_text("Le total est 1250,50 EUR pour cette commande")
    pn, bbox, score = locate_value([page], "1250,50")
    assert pn == 1
    assert bbox is not None
    assert score >= 0.75


# ------------------------------------------------------------- tableaux
def test_cluster_rows_and_columns():
    words = []
    for r in range(3):
        for c, txt in enumerate(["REF", "NOM", "QTE"]):
            words.append(Word(text=f"{txt}{r}",
                              bbox=BBox(x0=50 + c * 150, y0=20 + r * 40,
                                        x1=50 + c * 150 + 60, y1=20 + r * 40 + 20),
                              confidence=0.9))
    rows = cluster_rows(words)
    assert len(rows) == 3
    bounds = infer_columns(rows)
    assert len(bounds) == 2  # 3 colonnes -> 2 frontières
    table = extract_borderless_table(words, page_num=1)
    assert table is not None
    assert table.n_cols == 3
    assert table.n_rows == 3
    assert table.to_matrix()[0][0] == "REF0"


def test_merge_multipage_tables():
    def mk(page, offset):
        cells = []
        for r in range(2):
            for c in range(2):
                from unocr.models import Cell
                cells.append(Cell(row=r, col=c, text=f"p{page}r{r}c{c}"))
        return __import__("unocr.models", fromlist=["Table"]).Table(
            page_num=page, n_rows=2, n_cols=2, cells=cells, method="clustering",
            page_nums=[page])
    merged = merge_multipage_tables([mk(1, 0), mk(2, 0)])
    assert len(merged) == 1
    assert merged[0].multipage
    assert merged[0].n_rows == 4
    assert merged[0].page_nums == [1, 2]


# ------------------------------------------------------------- mise en page
def test_column_detection_requires_free_gutter():
    from unocr.layout import build_blocks, detect_columns, group_words_into_lines

    def mkline(words_spec, y):
        words = []
        for x0, x1, t in words_spec:
            words.append(Word(text=t, bbox=BBox(x0=x0, y0=y, x1=x1, y1=y + 18),
                              confidence=0.9))
        return words

    # 1) une seule colonne, ligne longue ne doit PAS créer une fausse colonne
    words = []
    for i in range(5):
        words += mkline([(40, 300, f"ligne{i}")], 20 + i * 30)
    words += mkline([(40, 900, "tres-longue")], 20 + 5 * 30)
    lines = group_words_into_lines(words)
    layout = detect_columns(lines, 1000)
    assert len(layout.columns) == 1

    # 2) vraie gouttière libre (aucune ligne ne croise le milieu) -> 2 colonnes
    # (y décalés pour que la fusion de lignes ne mélange pas les deux colonnes)
    words = []
    for i in range(4):
        words += mkline([(40, 300, f"gauche{i}")], 20 + i * 30)
        words += mkline([(500, 800, f"droite{i}")], 35 + i * 30)
    lines = group_words_into_lines(words)
    layout = detect_columns(lines, 1000)
    assert len(layout.columns) == 2
    blocks = build_blocks(lines, 1000, 400)
    assert {b.column for b in blocks} == {0, 1}


# ------------------------------------------------------------- profils
def test_iso6346_check_digit():
    assert iso6346_check_digit_ok("CSQU3054383") is True   # exemple canonique
    assert iso6346_check_digit_ok("CSQU3054389") is False  # chiffre faux
    assert iso6346_check_digit_ok("ABCD1234567") is None   # non vérifiable (format)


def test_luhn_and_iban():
    assert luhn_ok("4539578763621486") is True
    assert luhn_ok("4539578763621487") is False
    assert iban_ok("FR1420041010050500013M02606") is True
    assert iban_ok("FR0020041010050500013M02606") is False


def test_apply_profile_bl(tmp_cfg, fixtures_dir):
    profs = load_profiles(tmp_cfg.profiles_dir)
    assert "port_bl" in profs
    text = (fixtures_dir / "ground_truth.json").read_text(encoding="utf-8")
    import json
    bl_text = json.loads(text)["bl_port.pdf"]
    fields = apply_profile(bl_text, profs["port_bl"])
    assert fields["container_number"].normalized_value == "CSQU3054383"
    assert fields["container_number"].status == FieldStatus.DETECTED
    assert fields["bl_number"].normalized_value == "MSCU123456789"
    assert fields["vessel_name"].normalized_value == "MSC AURORA"


def test_profile_invalid_container_flagged(tmp_cfg):
    profs = load_profiles(tmp_cfg.profiles_dir)
    fields = apply_profile("Container Number: CSQU3054389", profs["port_bl"])
    assert fields["container_number"].status == FieldStatus.INVALID


def test_check_required_reports_missing(tmp_cfg):
    profs = load_profiles(tmp_cfg.profiles_dir)
    fields = apply_profile("B/L No: XX123", profs["port_bl"])
    issues = check_required(profs["port_bl"], fields)
    codes = [i["code"] for i in issues]
    assert "MISSING_REQUIRED_FIELD" in codes  # container_number obligatoire absent


def test_date_order_relation(tmp_cfg):
    profs = load_profiles(tmp_cfg.profiles_dir)
    text = "B/L No: XX123\nContainer Number: CSQU3054383\nETA: 01/01/2024\nETD: 15/03/2024"
    fields = apply_profile(text, profs["port_bl"])
    issues = check_required(profs["port_bl"], fields)
    assert any(i["code"] == "DATE_INCOHERENT" for i in issues)
