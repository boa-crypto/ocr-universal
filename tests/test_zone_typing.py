"""Tests E2 : typage de zones — mesures réales sur le jeu de contrôle.

Ces tests ne vérifient pas un comportement idéalisé : ils mesurent ce que le
détecteur fait réellement et verrouillent les chiffres, afin qu'une régression
de précision soit visible. Les valeurs mesurées sont documentées dans
`src/unocr/zone_typing.py` et docs/LIMITATIONS.md.
"""
from pathlib import Path

import pytest

from unocr.zone_typing import (
    CHECKBOX_GROUP_MIN,
    classify_zones,
)

FIX = Path(__file__).resolve().parent / "fixtures"

# formulaire synthétique contrôlé : 4 cases dessinées à ces positions
TRUTH_BOXES = [(260, 130), (260, 182), (260, 234), (260, 286)]


def _boxes(zones):
    return [(z["bbox"]["x"], z["bbox"]["y"]) for z in zones
            if z["kind"] == "checkbox"]


# ───────────────────────── contrat de base ─────────────────────────

def test_classify_returns_well_formed_zones():
    zones = classify_zones(FIX / "form_zones.png")
    assert isinstance(zones, list)
    for z in zones:
        assert z["kind"] in ("checkbox", "table")
        assert 0.0 <= z["confidence"] <= 1.0
        assert z["page"] >= 1
        assert "bbox" in z and "note" in z


def test_missing_file_returns_empty():
    assert classify_zones(FIX / "absent.png") == []


def test_tables_are_typed():
    """Un tableau fourni est typé, en plus de l'analyse d'image."""

    class _BB:
        x0, y0, x1, y1 = 10, 20, 300, 200

    class _T:
        page_num, bbox = 2, _BB()

    zones = classify_zones(FIX / "form_zones.png", tables=[_T()])
    tables = [z for z in zones if z["kind"] == "table"]
    assert len(tables) == 1
    assert tables[0]["page"] == 2 and tables[0]["confidence"] == 0.9
    assert tables[0]["bbox"] == {"x": 10, "y": 20, "w": 300, "h": 200}


def test_no_signature_or_handwritten_kind():
    """La capacité a été retirée après mesure : elle ne doit pas réapparaître."""
    for f in FIX.glob("*.png"):
        kinds = {z["kind"] for z in classify_zones(f)}
        assert not (kinds & {"signature", "handwritten"}), \
            f"{f.name} : capacité retirée de nouveau présente {kinds}"


# ───────────────────────── mesures verrouillées ─────────────────────────

def test_controlled_form_recall():
    """Les 4 cases dessinées (2 cochées, 2 vides) doivent toutes être
    retrouvées : le seuil d'intérieur tolère une coche (~0,24 d'encre)."""
    found = _boxes(classify_zones(FIX / "form_zones.png"))
    for tx, ty in TRUTH_BOXES:
        assert any(abs(fx - tx) <= 6 and abs(fy - ty) <= 6
                   for fx, fy in found), f"case ({tx},{ty}) non détectée"


def test_controlled_form_precision_is_measured():
    """Précision mesurée = 4/23 ≈ 17 % — chiffre réel, verrouillé.

    Le détecteur est honnête sur sa faiblesse : il trouve toutes les vraies
    cases mais produit des candidats issus des lettres creuses du leurre
    (« OOO 000 DDD 888 »). C'est un générateur de candidats à confirmer,
    pas un oracle. Si ce chiffre se dégrade, le test échoue.
    """
    found = _boxes(classify_zones(FIX / "form_zones.png"))
    assert len(found) >= len(TRUTH_BOXES)
    precision = len(TRUTH_BOXES) / len(found)
    assert 0.10 <= precision <= 0.45, f"précision inattendue : {precision:.2f}"


@pytest.mark.parametrize("fixture", [
    "photo_container.png", "photo_plate_fr.png", "photo_plate_dz.png",
    "photo_vin.png", "qr_code.png",
])
def test_no_false_positive_on_documents_without_boxes(fixture):
    """Documents sans aucune case à cocher → 0 candidat retenu."""
    found = _boxes(classify_zones(FIX / fixture))
    assert found == [], f"{fixture} : {len(found)} faux positifs {found}"


def test_carte_grise_few_false_positives():
    """Carte grise : mesuré à 15 candidats pour 0 case réelle.

    Le test verrouille une borne haute largement suffisante : l'objectif est
    de détecter une explosion de faux positifs, pas de viser 0 (impossible
    sans modèle appris).
    """
    found = _boxes(classify_zones(FIX / "photo_carte_grise.png"))
    assert len(found) <= 20, f"{len(found)} faux positifs (borne : 20)"


def test_isolated_ring_is_rejected():
    """Une case isolée n'est pas retenue : le filtrage par groupe existe."""
    import cv2
    import numpy as np

    from unocr.zone_typing import _box_candidates, _peers

    img = np.full((200, 200), 255, np.uint8)
    cv2.rectangle(img, (80, 80), (110, 110), 0, 3)      # UNE seule case
    _, m = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    mask = (m > 0)
    cands = _box_candidates(mask)
    assert cands, "le candidat devrait être détecté avant filtrage"
    assert _peers(cands[0], cands) < CHECKBOX_GROUP_MIN - 1
