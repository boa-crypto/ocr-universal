"""Paquet de données (étape 13) — Excel, JSON, ZIP + manifeste.

**Pourquoi ces tests.** Le paquet est ce qui sort d'UniOCR vers un autre
système. Ce qui est vérifié : les champs **validés ne sont pas mélangés** aux
propositions ; les identifiants gardent leurs zéros initiaux ; le manifeste dit
ce qui est dedans et ce qui manque ; et les documents originaux ne sont
**jamais** embarqués sans demande explicite.
"""
from __future__ import annotations

import json
import zipfile

import pytest

from unocr.packaging import (
    SCHEMA_VERSION,
    DocumentPaquet,
    genere_json,
    genere_xlsx,
    genere_zip,
)


@pytest.fixture()
def documents(tmp_path) -> list[DocumentPaquet]:
    (tmp_path / "facture.pdf").write_bytes(b"%PDF-1.4\n")
    return [
        DocumentPaquet(
            "j1", "facture.pdf", "invoice", "Facture commerciale",
            champs={
                "invoice_number": {"valeur": "2024-118", "origine": "brut",
                                   "valide": True, "page": 1, "confiance": 0.9,
                                   "label": "N° de facture"},
                "total_amount": {"valeur": "1250.50", "origine": "normalise",
                                 "valide": False, "page": 1, "confiance": 0.7,
                                 "label": "Total"},
            },
            fichiers=[tmp_path / "facture.pdf"], sha256="abc"),
        DocumentPaquet(
            "j2", "bl.pdf", "bill_of_lading", "Connaissement maritime",
            champs={
                "bl_number": {"valeur": "007", "origine": "brut", "valide": True,
                              "page": 1, "confiance": 0.95, "label": "N° de BL"},
            }),
    ]


ANOMALIES = [{
    "rule": "poids_divergent:gross_weight", "severity": "anomalie",
    "documents": ["bl.pdf"], "champs": [{"key": "gross_weight"}],
    "valeurs": [12000, 13500], "resultat": "divergent",
    "explication": "écart de 11,8 %", "status": "a_trancher",
}]

MANQUANTS = [{"category": "packing_list", "label": "Liste de colisage",
              "required": False, "expected": 1, "present": 0}]


# ───────────────────────────── Excel ─────────────────────────────

def test_xlsx_a_les_feuilles_attendues(documents, tmp_path) -> None:
    from openpyxl import load_workbook
    out = genere_xlsx(documents, tmp_path / "p.xlsx", "dos_1", "Import",
                      ANOMALIES, MANQUANTS)
    wb = load_workbook(out)
    for attendue in ("Synthèse", "Champs validés", "Champs en attente",
                     "Anomalies", "Pièces manquantes", "Métadonnées"):
        assert attendue in wb.sheetnames, f"feuille manquante : {attendue}"
    # une feuille par catégorie
    assert "Facture commerciale" in wb.sheetnames
    assert "Connaissement maritime" in wb.sheetnames


def test_xlsx_separe_valides_et_attente(documents, tmp_path) -> None:
    from openpyxl import load_workbook
    out = genere_xlsx(documents, tmp_path / "p.xlsx", "dos_1", "Import")
    wb = load_workbook(out)

    def cles(feuille):
        ws = wb[feuille]
        return {str(r[2].value) for r in ws.iter_rows(min_row=2) if r[2].value}

    assert cles("Champs validés") == {"invoice_number", "bl_number"}
    assert cles("Champs en attente") == {"total_amount"}, (
        "un champ non validé ne doit pas apparaître parmi les validés"
    )


def test_xlsx_preserve_les_zeros_initiaux(documents, tmp_path) -> None:
    """Un identifiant reste du texte : 007 ne devient pas 7."""
    from openpyxl import load_workbook
    out = genere_xlsx(documents, tmp_path / "p.xlsx", "dos_1", "Import")
    ws = load_workbook(out)["Champs validés"]
    valeurs = [str(r[4].value) for r in ws.iter_rows(min_row=2)]
    assert "007" in valeurs, f"zéro initial perdu : {valeurs}"


def test_xlsx_contient_les_anomalies(documents, tmp_path) -> None:
    from openpyxl import load_workbook
    out = genere_xlsx(documents, tmp_path / "p.xlsx", "dos_1", "Import",
                      ANOMALIES, MANQUANTS)
    ws = load_workbook(out)["Anomalies"]
    regles = [str(r[0].value) for r in ws.iter_rows(min_row=2)]
    assert "poids_divergent:gross_weight" in regles


# ───────────────────────────── JSON ─────────────────────────────

def test_json_structure_complete(documents, tmp_path) -> None:
    out = genere_json(documents, tmp_path / "p.json", "dos_1", "Import",
                      ANOMALIES, MANQUANTS)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["dossier"]["id"] == "dos_1"
    assert len(data["documents"]) == 2
    assert data["champs_valides"] == 2 and data["champs_total"] == 3
    assert data["anomalies"] == ANOMALIES
    assert data["pieces_manquantes"] == MANQUANTS


def test_json_ne_divulgue_pas_les_chemins(documents, tmp_path) -> None:
    out = genere_json(documents, tmp_path / "p.json", "dos_1", "Import")
    data = json.loads(out.read_text(encoding="utf-8"))
    for doc in data["documents"]:
        assert all("/" not in f for f in doc["fichiers"]), (
            "le paquet ne doit pas embarquer de chemins absolus"
        )


# ───────────────────────────── ZIP ─────────────────────────────

def test_zip_contient_xlsx_json_et_manifeste(documents, tmp_path) -> None:
    out = genere_zip(documents, tmp_path / "p.zip", "dos_1", "Import",
                     ANOMALIES, MANQUANTS)
    with zipfile.ZipFile(out) as zf:
        noms = set(zf.namelist())
    assert {"paquet.xlsx", "paquet.json", "manifeste.json"} <= noms


def test_zip_nembarque_pas_les_documents_par_defaut(documents, tmp_path) -> None:
    out = genere_zip(documents, tmp_path / "p.zip", "dos_1", "Import")
    with zipfile.ZipFile(out) as zf:
        noms = zf.namelist()
    assert "facture.pdf" not in noms, (
        "les documents originaux ne doivent pas être embarqués sans demande"
    )


def test_zip_embarque_les_documents_si_demande(documents, tmp_path) -> None:
    out = genere_zip(documents, tmp_path / "p.zip", "dos_1", "Import",
                     inclure_documents=True)
    with zipfile.ZipFile(out) as zf:
        noms = zf.namelist()
        assert "facture.pdf" in noms
        manifeste = json.loads(zf.read("manifeste.json").decode("utf-8"))
    assert manifeste["documents_originaux_inclus"] is True


def test_manifeste_decrit_le_contenu_et_les_manques(documents, tmp_path) -> None:
    out = genere_zip(documents, tmp_path / "p.zip", "dos_1", "Import",
                     ANOMALIES, MANQUANTS)
    with zipfile.ZipFile(out) as zf:
        m = json.loads(zf.read("manifeste.json").decode("utf-8"))
    assert m["schema_version"] == SCHEMA_VERSION
    assert len(m["documents_inclus"]) == 2
    assert m["pieces_manquantes"] == MANQUANTS
    assert m["anomalies"] == ANOMALIES
    assert "paquet.xlsx" in m["fichiers"]


def test_paquet_vide_ne_plante_pas(tmp_path) -> None:
    out = genere_xlsx([], tmp_path / "vide.xlsx", "dos_x", "Vide")
    from openpyxl import load_workbook
    wb = load_workbook(out)
    assert "Synthèse" in wb.sheetnames
    ws = wb["Synthèse"]
    assert any("0" == str(r[1].value) for r in ws.iter_rows(min_row=2))
