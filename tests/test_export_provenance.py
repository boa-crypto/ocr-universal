"""La provenance doit survivre à l'export.

**Pourquoi ce fichier existe.** L'export Excel est un livrable explicite du
parcours (étape 9 : « fichier Excel avec données validées, références
documentaires et anomalies non résolues »). Il ne reprenait ni `value_origin`,
ni `source`, ni la zone du champ — alors que le cahier des charges exige une
« provenance complète par champ » et des « alertes expliquées avec zones
sources ».

Sans ces colonnes, un export présente sur le même plan une transcription OCR et
une valeur tranchée par un humain : le lecteur ne peut plus distinguer ce qui a
été **extrait** de ce qui a été **interprété**. Et une alerte ne peut pas être
vérifiée sans relire tout le document, faute de zone.

Le JSON, lui, exporte tout le modèle — il n'avait pas ce trou.
"""
import csv
import json

from unocr.exporters import export_csv, export_json, export_xlsx, export_xml
from unocr.models import BBox, DocumentResult, FieldValue, ValueOrigin


def _resultat():
    return DocumentResult(
        id="job1", source_file="facture.pdf", source_hash="abc123",
        pages=[], fields={
            "invoice_number": FieldValue(
                name="invoice_number", label="N° facture",
                raw_value="FA/1", normalized_value="FA-1",
                corrected_value="FA-2026-0001",
                value_origin=ValueOrigin.CORRECTED, source="rule",
                confidence=0.9, engine_confidence=0.8, page_num=1,
                bbox=BBox(x0=10, y0=20, x1=40, y1=28)),
            "montant": FieldValue(
                name="montant", label="Montant", raw_value="1200,00",
                confirmed_value="1200.00",
                value_origin=ValueOrigin.CONFIRMED, source="user",
                confidence=0.95, page_num=2),
        }, tables=[])


# ─────────────────────────────── XLSX ───────────────────────────────

def test_xlsx_porte_la_provenance(tmp_path):
    from openpyxl import load_workbook
    p = export_xlsx(_resultat(), tmp_path / "out.xlsx")
    ws = load_workbook(p)["Champs"]
    entetes = [c.value for c in ws[1]]
    for attendu in ("origine", "source", "zone"):
        assert attendu in entetes, "colonne manquante : %s" % attendu


def test_xlsx_distingue_extrait_et_interprete(tmp_path):
    """Deux champs de même valeur affichée doivent rester distinguables."""
    from openpyxl import load_workbook
    p = export_xlsx(_resultat(), tmp_path / "out.xlsx")
    ws = load_workbook(p)["Champs"]
    entetes = [c.value for c in ws[1]]
    lignes = {r[0]: r for r in ws.iter_rows(min_row=2, values_only=True)}
    i_origine = entetes.index("origine")
    assert lignes["invoice_number"][i_origine] == "règle métier"
    assert lignes["montant"][i_origine] == "validé par un humain"


def test_xlsx_exporte_la_zone_source(tmp_path):
    from openpyxl import load_workbook
    p = export_xlsx(_resultat(), tmp_path / "out.xlsx")
    ws = load_workbook(p)["Champs"]
    entetes = [c.value for c in ws[1]]
    lignes = {r[0]: r for r in ws.iter_rows(min_row=2, values_only=True)}
    i_zone = entetes.index("zone")
    assert "x0=10" in str(lignes["invoice_number"][i_zone])
    # pas de zone connue -> chaîne vide, jamais une zone inventée
    assert lignes["montant"][i_zone] in ("", None)


def test_xlsx_origine_est_en_clair(tmp_path):
    """« corrected » seul ne dit pas si c'est une règle ou une faute de frappe."""
    from openpyxl import load_workbook
    p = export_xlsx(_resultat(), tmp_path / "out.xlsx")
    ws = load_workbook(p)["Champs"]
    entetes = [c.value for c in ws[1]]
    valeurs = {r[entetes.index("origine")]
               for r in ws.iter_rows(min_row=2, values_only=True)}
    assert valeurs == {"règle métier", "validé par un humain"}


# ─────────────────────────────── CSV ───────────────────────────────

def test_csv_porte_la_provenance(tmp_path):
    p = export_csv(_resultat(), tmp_path)[0]
    with p.open(encoding="utf-8-sig") as fh:
        entetes = next(csv.reader(fh))
    for attendu in ("origine", "source", "zone"):
        assert attendu in entetes, "colonne manquante : %s" % attendu


def test_csv_alignes_sur_le_xlsx(tmp_path):
    """CSV et XLSX ne doivent pas exposer des colonnes différentes."""
    from openpyxl import load_workbook
    xlsx = [c.value for c in
            load_workbook(export_xlsx(_resultat(), tmp_path / "o.xlsx"))["Champs"][1]]
    with export_csv(_resultat(), tmp_path)[0].open(encoding="utf-8-sig") as fh:
        csv_entetes = next(csv.reader(fh))
    assert set(xlsx) == set(csv_entetes), (
        "XLSX %s vs CSV %s" % (xlsx, csv_entetes))


# ─────────────────────────────── XML ───────────────────────────────

def test_xml_porte_la_provenance(tmp_path):
    import xml.etree.ElementTree as ET
    p = export_xml(_resultat(), tmp_path / "o.xml")
    racine = ET.fromstring(p.read_text(encoding="utf-8"))
    champs = {f.attrib["name"]: f.attrib for f in racine.findall("fields/field")}
    for nom, attributs in champs.items():
        for attendu in ("origin", "source", "zone"):
            assert attendu in attributs, "%s : attribut manquant %s" % (nom, attendu)
    assert champs["montant"]["origin"] == "validé par un humain"
    assert champs["invoice_number"]["origin"] == "règle métier"


# ─────────────────────────────── JSON ───────────────────────────────

def test_json_conserve_tout_le_modele(tmp_path):
    """Le JSON sérialise le modèle entier : la provenance y est déjà."""
    p = export_json(_resultat(), tmp_path / "o.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    champs = data["fields"]
    assert champs["invoice_number"]["value_origin"] == "corrected"
    assert champs["invoice_number"]["source"] == "rule"
    assert champs["invoice_number"]["bbox"]["x0"] == 10


# ─────────────────────── pas de données inventées ───────────────────────

def test_zone_vide_quand_le_moteur_ne_l_a_pas_fournie(tmp_path):
    """Une zone absente doit rester absente, pas devenir « 0,0,0,0 »."""
    from openpyxl import load_workbook
    r = _resultat()
    r.fields["sans_zone"] = FieldValue(name="sans_zone", raw_value="x")
    p = export_xlsx(r, tmp_path / "o.xlsx")
    ws = load_workbook(p)["Champs"]
    entetes = [c.value for c in ws[1]]
    lignes = {row[0]: row for row in ws.iter_rows(min_row=2, values_only=True)}
    i_zone = entetes.index("zone")
    assert lignes["sans_zone"][i_zone] in ("", None)


def test_export_reste_lisible_avec_des_valeurs_hostiles(tmp_path):
    """Une valeur extraite est une donnée non fiable : elle ne casse pas l'export."""
    from openpyxl import load_workbook
    r = _resultat()
    r.fields["piege"] = FieldValue(
        name="piege", raw_value='=SOMME(A1:A9)" ; rm -rf /',
        confirmed_value="\t=LIGNE()")
    p = export_xlsx(r, tmp_path / "o.xlsx")
    ws = load_workbook(p)["Champs"]
    entetes = [c.value for c in ws[1]]
    lignes = {row[0]: row for row in ws.iter_rows(min_row=2, values_only=True)}
    i_conf = entetes.index("confirmed_value")
    # la valeur est neutralisée, pas exécutée
    assert not str(lignes["piege"][i_conf]).startswith(("=", "+", "-", "@"))
