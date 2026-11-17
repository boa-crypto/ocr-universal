"""Classeur de fixture technique NON OFFICIELLE ; aucun tarif réel fabriqué."""
import hashlib
import io
import json
import re
import zipfile

import pytest
from openpyxl import Workbook, load_workbook

from tests.test_customs_reference import fichiers, snapshot
from unocr.cli import main
from unocr.customs_reference.importer import preparer_tarif


def xlsx_fichiers(tmp_path):
    csv, metadata = fichiers(tmp_path, csv=True)
    lignes = [ligne.split(";") for ligne in csv.read_text().splitlines()]
    classeur = Workbook()
    table = classeur.active
    table.title = "Nomenclature"
    for ligne in lignes:
        table.append(ligne)
    classeur.create_sheet("Notes").append(["FIXTURE NON OFFICIELLE — pas une nomenclature nationale"])
    source = tmp_path / "fixture_NON_OFFICIELLE.xlsx"
    classeur.save(source)
    classeur.close()
    meta = json.loads(metadata.read_text())
    meta.update(feuille="Nomenclature", ligne_entete=1)
    meta["lot"]["source"].update(format="xlsx", sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    metadata.write_text(json.dumps(meta))
    return source, metadata


def actualiser_hash(source, metadata):
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))


def modifier_archive(source, changer):
    with zipfile.ZipFile(source) as original:
        membres = [(info, original.read(info)) for info in original.infolist()]
    sortie = io.BytesIO()
    with zipfile.ZipFile(sortie, "w", zipfile.ZIP_DEFLATED) as archive:
        for info, contenu in membres:
            archive.writestr(info, changer(info.filename, contenu))
    source.write_bytes(sortie.getvalue())


def test_plan_archive_xlsx_litteral_et_perimetre(tmp_path):
    source, metadata = xlsx_fichiers(tmp_path)
    avant = snapshot(tmp_path)
    rapport = preparer_tarif(source, metadata)
    assert snapshot(tmp_path) == avant
    assert rapport["lignes_source_lues"] == rapport["codes_uniques"] == 1
    assert rapport["perimetre_lecture"]["feuille"] == "Nomenclature"
    assert rapport["perimetre_lecture"]["feuilles_non_importees"] == ["Notes"]
    assert rapport["completude_reglementaire"] == "non_etablie"
    sortie = tmp_path / "lot"
    preparer_tarif(source, metadata, sortie)
    assert (sortie / "source_recue.xlsx").read_bytes() == source.read_bytes()
    ligne = json.loads((sortie / "lot.json").read_text())["lignes"][0]
    assert ligne["code_tarifaire_10"] == "0101000000"
    assert ligne["reference"]["localisateur"] == "XLSX, feuille Nomenclature, ligne 2"
    assert ligne["taux_tva"] is None


@pytest.mark.parametrize("defaut", ["code_numerique", "formule", "en_tete_duplique", "en_tete_numerique", "cellule_hors_entete", "feuille_cachee"])
def test_classeur_ambigu_refuse(tmp_path, defaut):
    source, metadata = xlsx_fichiers(tmp_path)
    classeur = load_workbook(source)
    table = classeur["Nomenclature"]
    if defaut == "code_numerique":
        table["A2"] = 101000000
        table["A2"].number_format = "0000000000"
    elif defaut == "formule":
        table["G2"] = '=CONCAT("FIXTURE", " NON OFFICIELLE")'
    elif defaut == "en_tete_duplique":
        table["B1"] = table["A1"].value
    elif defaut == "en_tete_numerique":
        table["A1"] = 10
    elif defaut == "cellule_hors_entete":
        table["H2"] = "NON DECLARE"
    elif defaut == "feuille_cachee":
        table.sheet_state = "hidden"
    classeur.save(source)
    classeur.close()
    actualiser_hash(source, metadata)
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata, tmp_path / "sortie")
    assert snapshot(tmp_path) == avant
    assert not (tmp_path / "sortie").exists()


@pytest.mark.parametrize("champ,valeur", [("feuille", None), ("feuille", "Absente"), ("ligne_entete", True), ("ligne_entete", 0), ("delimiteur", ";")])
def test_options_explicitement_controlees(tmp_path, champ, valeur):
    source, metadata = xlsx_fichiers(tmp_path)
    meta = json.loads(metadata.read_text())
    meta[champ] = valeur
    metadata.write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata)


def test_dimensions_fausses_ne_masquent_pas_les_lignes(tmp_path):
    source, metadata = xlsx_fichiers(tmp_path)
    def changer(nom, contenu):
        if nom == "xl/worksheets/sheet1.xml":
            return re.sub(rb'<dimension ref="[^"]+"', b'<dimension ref="A1"', contenu)
        return contenu
    modifier_archive(source, changer)
    actualiser_hash(source, metadata)
    assert preparer_tarif(source, metadata)["lignes_source_lues"] == 1


def test_ligne_cachee_lue_et_ligne_vide_comptee(tmp_path):
    source, metadata = xlsx_fichiers(tmp_path)
    classeur = load_workbook(source)
    table = classeur["Nomenclature"]
    table.row_dimensions[2].hidden = True
    table.append([None] * 7)
    classeur.save(source)
    classeur.close()
    actualiser_hash(source, metadata)
    rapport = preparer_tarif(source, metadata)
    assert rapport["lignes_source_lues"] == 1
    assert rapport["perimetre_lecture"]["lignes_vides_ignorees"] == 1


@pytest.mark.parametrize("limite", ["MAX_MEMBRES", "MAX_DECOMPRESSE", "MAX_RATIO", "MAX_LIGNES", "MAX_COLONNES", "MAX_CELLULES"])
def test_bornes_refus_sans_sortie(tmp_path, monkeypatch, limite):
    from unocr.customs_reference import tabular

    source, metadata = xlsx_fichiers(tmp_path)
    monkeypatch.setattr(tabular, limite, 1)
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata, tmp_path / "sortie")
    assert not (tmp_path / "sortie").exists()


@pytest.mark.parametrize("contenu", [b'<!DOCTYPE worksheet [<!ENTITY x "TEST">]>', b'<!DOCTYPE worksheet>'.decode().encode('utf-16')])
def test_dtd_refuse_avant_parseur(tmp_path, contenu):
    source, metadata = xlsx_fichiers(tmp_path)
    modifier_archive(source, lambda nom, b: contenu + b if nom == "xl/worksheets/sheet1.xml" else b)
    actualiser_hash(source, metadata)
    with pytest.raises(ValueError, match="DTD"):
        preparer_tarif(source, metadata)


@pytest.mark.parametrize("nom", ["../intrus.xml", "xl/vbaProject.bin", "xl/externalLinks/externalLink1.xml",
                                 "xl/macrosheets/sheet1.xml", "xl/dialogsheets/sheet1.xml",
                                 "xl/activeX/activeX1.xml", "xl/embeddings/oleObject1.bin"])
def test_archives_actives_ou_chemins_refuses(tmp_path, nom):
    source, metadata = xlsx_fichiers(tmp_path)
    with zipfile.ZipFile(source, "a") as archive:
        archive.writestr(nom, b"FIXTURE")
    actualiser_hash(source, metadata)
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata)


def test_membre_zip_duplique_refuse(tmp_path):
    source, metadata = xlsx_fichiers(tmp_path)
    with pytest.warns(UserWarning, match="Duplicate"):
        with zipfile.ZipFile(source, "a") as archive:
            archive.writestr("xl/workbook.xml", b"FIXTURE")
    actualiser_hash(source, metadata)
    with pytest.raises(ValueError, match="dupliqué"):
        preparer_tarif(source, metadata)


def test_cli_classeur_invalide_pas_de_traceback(tmp_path, capsys):
    source, metadata = xlsx_fichiers(tmp_path)
    source.write_bytes(b"pas un ZIP XLSX")
    actualiser_hash(source, metadata)
    assert main(["customs-prepare", str(source), "--metadata", str(metadata)]) == 2
    assert json.loads(capsys.readouterr().out)["statut"] == "refuse"


@pytest.mark.parametrize("membre", ["xl/workbook.xml", "xl/worksheets/sheet1.xml"])
def test_xml_mal_forme_cli_refuse(tmp_path, capsys, membre):
    source, metadata = xlsx_fichiers(tmp_path)
    modifier_archive(source, lambda nom, contenu: b"<xml><non-termine>" if nom == membre else contenu)
    actualiser_hash(source, metadata)
    assert main(["customs-prepare", str(source), "--metadata", str(metadata)]) == 2
    assert json.loads(capsys.readouterr().out)["statut"] == "refuse"
