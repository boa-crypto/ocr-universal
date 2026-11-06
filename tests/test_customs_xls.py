"""Classeurs BIFF8 techniques NON OFFICIELS ; aucun tarif national fabriqué."""
import hashlib
import json
import struct
from types import SimpleNamespace

import pytest

from tests import test_customs_review
from tests.test_customs_reference import fichiers, snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.comparison import charger_lot
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.xls_table import _verifier_biff

revue = test_customs_review.revue


def xls_fichiers(tmp_path, defaut=None):
    xlwt = pytest.importorskip("xlwt", reason="Installer les dépendances dev pour les fixtures BIFF8")
    csv, metadata = fichiers(tmp_path, csv=True)
    headers, valeurs = [ligne.split(";") for ligne in csv.read_text().splitlines()]
    classeur = xlwt.Workbook()
    feuille = classeur.add_sheet("Nomenclature")
    notes = classeur.add_sheet("Notes")
    notes.write(0, 0, xlwt.Formula("1+1") if defaut == "formule_autre_feuille" else "NON OFFICIEL")
    if defaut == "cachee":
        feuille.visibility = 1
    if defaut == "en_tete_duplique":
        headers[1] = headers[0]
    if defaut == "code_numerique":
        valeurs[0] = 101000000
    if defaut == "formule":
        valeurs[0] = xlwt.Formula('"0101000000"')
    if defaut == "booleen":
        valeurs[0] = True
    for ligne, row in enumerate([headers, valeurs]):
        for colonne, valeur in enumerate(row):
            feuille.write(ligne, colonne, valeur)
    if defaut == "fusion":
        feuille.write_merge(3, 3, 0, 1, "NON OFFICIEL")
    if defaut == "hors_entete":
        feuille.write(1, 7, "NON OFFICIEL")
    source = tmp_path / "fixture_NON_OFFICIELLE.xls"
    classeur.save(str(source))
    meta = json.loads(metadata.read_text())
    meta.update(feuille="Nomenclature", ligne_entete=1)
    meta["lot"]["source"].update(format="xls", sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    metadata.write_text(json.dumps(meta))
    return source, metadata


def test_plan_archive_rejeu_et_zeros(tmp_path):
    source, metadata = xls_fichiers(tmp_path)
    avant = snapshot(tmp_path)
    rapport = preparer_tarif(source, metadata)
    assert snapshot(tmp_path) == avant
    assert rapport["perimetre_lecture"]["feuilles_non_importees"] == ["Notes"]
    sortie = tmp_path / "lot"
    preparer_tarif(source, metadata, sortie)
    assert (sortie / "source_recue.xls").read_bytes() == source.read_bytes()
    lot, _ = charger_lot(sortie)
    assert lot.lignes[0].code_tarifaire_10 == "0101000000"
    assert lot.lignes[0].taux_tva is None
    assert lot.lignes[0].reference.localisateur == "XLS, feuille Nomenclature, ligne 2"


@pytest.mark.parametrize("defaut", ["formule", "formule_autre_feuille", "code_numerique", "booleen", "cachee", "en_tete_duplique", "hors_entete", "fusion"])
def test_cellules_ou_classeurs_ambigus_refuses_sans_sortie(tmp_path, defaut):
    source, metadata = xls_fichiers(tmp_path, defaut)
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata, tmp_path / "sortie")
    assert snapshot(tmp_path) == avant


@pytest.mark.parametrize("champ,valeur", [("feuille", None), ("feuille", "ABSENTE"), ("ligne_entete", True), ("ligne_entete", 0), ("delimiteur", ";")])
def test_options_xls_explicites(tmp_path, champ, valeur):
    source, metadata = xls_fichiers(tmp_path)
    meta = json.loads(metadata.read_text())
    meta[champ] = valeur
    metadata.write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata)


def record(code, contenu=b""):
    return struct.pack("<HH", code, len(contenu)) + contenu


def biff(contenu=b""):
    def bof(typ):
        return record(0x0809, struct.pack("<HH", 0x0600, typ))
    return bof(5) + contenu + record(0x000A) + bof(0x10) + record(0x000A)


@pytest.mark.parametrize("code", [0x0006, 0x04BC, 0x0221, 0x0236, 0x0037, 0x002F, 0x01AE, 0x0023, 0x0017,
                                   0x0018, 0x00E5, 0x00D3, 0x005D, 0x00EB, 0x00EC, 0x01B6, 0x01B8])
def test_records_biff_actifs_refuses_meme_sans_cellule(code):
    with pytest.raises(ValueError):
        _verifier_biff(biff(record(code)))


@pytest.mark.parametrize("contenu", [b"", b"\x09", biff()[:-1], biff()+b"\x01", record(0x0809, struct.pack("<HH", 0x0500, 5)),
    record(0x0809, struct.pack("<HH", 0x0600, 0x40)), biff(record(0x0809, struct.pack("<HH", 0x0600, 5))),
    record(0x000A), biff(record(0x0020))+b"\x01\x00\x00\x00"])
def test_biff_incomplet_ancien_ou_macro_refuse(contenu):
    with pytest.raises(ValueError):
        _verifier_biff(contenu)


def test_biff_padding_nul_et_bornes(monkeypatch):
    from unocr.customs_reference import xls_table
    _verifier_biff(biff() + b"\0" * 10)
    monkeypatch.setattr(xls_table, "MAX_RECORDS", 1)
    with pytest.raises(ValueError):
        _verifier_biff(biff())


@pytest.mark.parametrize("borne", ["MAX_XLS", "MAX_CELLULES", "MAX_LIGNES", "MAX_COLONNES"])
def test_limites_avant_sortie(tmp_path, monkeypatch, borne):
    from unocr.customs_reference import xls_table
    source, metadata = xls_fichiers(tmp_path)
    monkeypatch.setattr(xls_table, borne, 1)
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError):
        preparer_tarif(source, metadata, tmp_path / "sortie")
    assert snapshot(tmp_path) == avant


def test_cli_et_refus_fichier_non_xls(tmp_path, capsys):
    source, metadata = xls_fichiers(tmp_path)
    assert main(["customs-prepare", str(source), "--metadata", str(metadata)]) == 0
    assert json.loads(capsys.readouterr().out)["ecrit"] is False
    source.write_bytes(b"NON OFFICIEL, PAS OLE")
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    assert main(["customs-prepare", str(source), "--metadata", str(metadata)]) == 2


def test_xls_depuis_zip_selectionne(tmp_path):
    from tests.test_customs_zip import archive
    source, metadata = xls_fichiers(tmp_path)
    contenu = source.read_bytes()
    source = tmp_path / "fixture_NON_OFFICIELLE.zip"
    source.write_bytes(archive([("tarif.xls", contenu)]))
    meta = json.loads(metadata.read_text())
    meta.update(membre_zip="tarif.xls", format_contenu="xls")
    meta["lot"]["source"].update(format="zip", sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    metadata.write_text(json.dumps(meta))
    sortie = tmp_path / "lot"
    preparer_tarif(source, metadata, sortie)
    lot, rapport = charger_lot(sortie)
    assert lot.lignes[0].code_tarifaire_10 == "0101000000"
    assert rapport["perimetre_lecture"]["format_contenu"] == "xls"


@pytest.mark.parametrize("suffixe", ["check", "search?q=010100", "tariff/0101000000", "tree?level=sections", "coverage"])
def test_xls_via_api_protegee(revue, suffixe):
    client, racine, registre, cfg = revue
    entrees = cfg.root / "xls_entrees"
    entrees.mkdir()
    source, metadata = xls_fichiers(entrees)
    lot = racine / "tarif_xls"
    preparer_tarif(source, metadata, lot)
    contenu = json.loads(registre.read_text())
    empreinte = hashlib.sha256((lot / "manifest.json").read_bytes()).hexdigest()
    contenu["lots"].append({"id": "tarif_xls", "dossier": "tarif_xls", "type_lot": "tarif", "manifest_sha256": empreinte})
    registre.write_text(json.dumps(contenu))
    avant = snapshot(racine)
    reponse = client.get(BASE + "/lots/tarif_xls/" + suffixe, headers=ADMIN)
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["resultat"]["archive"]["manifest_sha256"] == empreinte
    assert snapshot(racine) == avant


@pytest.mark.parametrize("type_entree,nom,parent", [(1, "VBA", 0), (2, "VBA", 0), (2, "Workbook", 1), (5, "AUTRE", 0)])
def test_repertoire_ole_hors_contrat_refuse(tmp_path, monkeypatch, type_entree, nom, parent):
    from unocr.customs_reference import xls_table
    source, metadata = xls_fichiers(tmp_path)
    entrees = [SimpleNamespace(DID=0, etype=5), SimpleNamespace(DID=1, etype=type_entree, name=nom, parent=parent)]
    monkeypatch.setattr(xls_table, "CompDoc", lambda *a, **kw: SimpleNamespace(dirlist=entrees))
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError, match="OLE hors contrat"):
        preparer_tarif(source, metadata, tmp_path / "sortie")
    assert snapshot(tmp_path) == avant
