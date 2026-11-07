"""Mesures XLSX de fixtures NON OFFICIELLES ; aucun document fiscal national."""
import hashlib
import json
from datetime import datetime

import pytest
from openpyxl import Workbook, load_workbook

from tests import test_customs_review
from tests.test_customs_fiscal_csv import MAPPING, actualiser
from tests.test_customs_fiscal_csv import fichiers as fichiers_csv
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from tests.test_customs_xlsx import modifier_archive
from unocr.cli import main
from unocr.customs_reference.fiscal_importer import charger_lot_mesures, preparer_mesures_autonomes

revue = test_customs_review.revue


def fichiers(root):
    _,metadata = fichiers_csv(root)
    mesures = json.loads((root / "MESURES_NON_OFFICIELLES.json").read_text())
    mesures[0]["description"] = "Équipement; مُعَـدَّات\nFIXTURE NON OFFICIELLE"
    classeur = Workbook()
    feuille = classeur.active
    feuille.title = "Mesures déclarées"
    feuille.append(["FIXTURE NON OFFICIELLE — pas de source fiscale nationale"])
    feuille.append([*MAPPING.values(),"Non importée"])
    for m in mesures:
        feuille.append([m.get(c) if m.get(c) is not None else "" for c in MAPPING]+[42])
    classeur.create_sheet("Notes exclues").append(["FIXTURE NON OFFICIELLE"])
    source = root / "MESURES_NON_OFFICIELLES.xlsx"
    classeur.save(source)
    classeur.close()
    meta = json.loads(metadata.read_text())
    meta.pop("delimiteur")
    meta.update(feuille="Mesures déclarées",ligne_entete=2)
    meta["source"].update(format="xlsx")
    metadata.write_text(json.dumps(meta))
    actualiser(source,metadata)
    return source,metadata


def test_plan_octets_precision_references_et_rejeu(tmp_path):
    source,metadata = fichiers(tmp_path)
    avant = snapshot(tmp_path)
    rapport = preparer_mesures_autonomes(source,metadata)
    assert snapshot(tmp_path) == avant and rapport["ecrit"] is False
    assert rapport["perimetre_lecture"]["feuilles_non_importees"] == ["Notes exclues"]
    assert rapport["perimetre_lecture"]["colonnes_non_importees"] == ["Non importée"]
    assert rapport["mesures_importables"] == 6
    preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    lot,controle = charger_lot_mesures(tmp_path / "lot")
    assert lot.source.format == "xlsx" and lot.mesures[0].code_tarifaire_10 == "0000000001"
    assert str(lot.mesures[0].taux) == "1.230000000000000000000000001"
    assert lot.mesures[1].taux == 0 and lot.mesures[2].taux is None
    assert lot.mesures[0].reference.localisateur == "XLSX, feuille Mesures déclarées, ligne 3"
    assert lot.mesures[0].description == "Équipement; مُعَـدَّات\nFIXTURE NON OFFICIELLE"
    assert (tmp_path / "lot/source_mesures_recue.xlsx").read_bytes() == source.read_bytes()
    assert (tmp_path / "lot/metadata_original.json").read_bytes() == metadata.read_bytes()
    assert not {"colonnes","delimiteur","feuille","ligne_entete"} & set(lot.model_dump())
    assert controle["fiscalite_applicable_etablie"] is False


@pytest.mark.parametrize("cellule,valeur",[("B3",1),("E3",1.23),("E3",0),("A3",True),("G3",datetime(2026,1,1)),
    ("D3","=1+1"),("I3","=1+1"),("A2",42),("B2","ID"),("J3","HORS ENTÊTE"),("D3",""),("A4","M_0")])
def test_cellules_ambigues_numeriques_dates_formules_et_structure_refusees(tmp_path,cellule,valeur):
    source,metadata = fichiers(tmp_path)
    classeur = load_workbook(source)
    classeur["Mesures déclarées"][cellule] = valeur
    if cellule == "B3":
        classeur["Mesures déclarées"][cellule].number_format = "0000000000"
    classeur.save(source)
    classeur.close()
    actualiser(source,metadata)
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("champ,valeur",[("feuille",None),("feuille","ABSENTE"),("feuille"," "),("ligne_entete",True),
    ("ligne_entete",0),("ligne_entete",51),("ligne_entete",1),("delimiteur",";"),("colonnes",None),
    ("colonnes",{"id":"ID"}),("colonnes",{**MAPPING,"description":"ABSENTE"}),("colonnes",{**MAPPING,"reference":"Non importée"})])
def test_options_et_mapping_refuses(tmp_path,champ,valeur):
    source,metadata = fichiers(tmp_path)
    meta = json.loads(metadata.read_text())
    meta[champ] = valeur
    metadata.write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("defaut",["cachee","dtd","macro","dimension","vide"])
def test_gardes_classeur_et_dimensions_reelles(tmp_path,defaut):
    source,metadata = fichiers(tmp_path)
    if defaut in {"cachee","vide"}:
        classeur = load_workbook(source)
        feuille = classeur["Mesures déclarées"]
        if defaut == "cachee":
            feuille.sheet_state = "hidden"
        else:
            feuille.delete_rows(3,6)
        classeur.save(source)
        classeur.close()
    elif defaut == "dtd":
        modifier_archive(source,lambda nom,b: b.replace(b'<worksheet ',b'<!DOCTYPE x [<!ENTITY x "y">]><worksheet ',1) if nom=='xl/worksheets/sheet1.xml' else b)
    elif defaut == "macro":
        import zipfile
        with zipfile.ZipFile(source,"a") as z:
            z.writestr("xl/vbaProject.bin",b"NON OFFICIEL")
    else:
        import re
        modifier_archive(source,lambda nom,b:re.sub(rb'<dimension ref="[^"]+"',b'<dimension ref="A1:A1"',b) if nom=='xl/worksheets/sheet1.xml' else b)
    actualiser(source,metadata)
    if defaut in {"cachee","dtd","macro"}:
        with pytest.raises(ValueError):
            preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
        assert not (tmp_path / "lot").exists()
    else:
        assert preparer_mesures_autonomes(source,metadata)["mesures_importables"] == (0 if defaut=='vide' else 6)


@pytest.mark.parametrize("format_source",["json","csv"])
def test_options_feuille_interdites_sur_anciens_formats(tmp_path,format_source):
    source,metadata = fichiers_csv(tmp_path)
    if format_source == "json":
        from tests.test_customs_fiscal_import import fichiers as fichiers_json
        source,metadata = fichiers_json(tmp_path)
    meta = json.loads(metadata.read_text())
    meta["ligne_entete"] = 1
    metadata.write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata)


def test_cli_et_compatibilite_archive_csv_39(tmp_path,capsys):
    source,metadata = fichiers(tmp_path)
    assert main(["customs-fiscal-prepare",str(source),"--metadata",str(metadata),"--out",str(tmp_path / "lot"),"--write"]) == 0
    assert json.loads(capsys.readouterr().out)["perimetre_lecture"]["format"] == "xlsx"
    assert main(["customs-fiscal-check",str(tmp_path / "lot")]) == 0
    capsys.readouterr()
    source,metadata = fichiers_csv(tmp_path)
    preparer_mesures_autonomes(source,metadata,tmp_path / "csv39")
    attendus = {"lot_mesures.json":"41dcb127af9ab63d9a97e553ac9623ba5c661c03339a1cf1fd06f506dd6eb3d6",
                "rapport.json":"50920537b1c15aee5e020e68fa5ec547806beb383f03d1c0e39d7c5b52a18412"}
    for nom,sha in attendus.items():
        assert hashlib.sha256((tmp_path / "csv39" / nom).read_bytes()).hexdigest() == sha
    charger_lot_mesures(tmp_path / "csv39")


@pytest.mark.parametrize("defaut",["source","lot_rehache","extension","deux_sources"])
def test_archive_alteree_refusee(tmp_path,defaut):
    source,metadata = fichiers(tmp_path)
    lot = tmp_path / "lot"
    preparer_mesures_autonomes(source,metadata,lot)
    manifeste = json.loads((lot / "manifest.json").read_text())
    if defaut == "source":
        (lot / "source_mesures_recue.xlsx").write_bytes(b"ALTERE NON OFFICIEL")
    elif defaut == "lot_rehache":
        x = json.loads((lot / "lot_mesures.json").read_text())
        x["mesures"][0]["description"] = "ALTERE NON OFFICIEL"
        (lot / "lot_mesures.json").write_text(json.dumps(x))
        manifeste["fichiers_sha256"]["lot_mesures.json"] = hashlib.sha256((lot / "lot_mesures.json").read_bytes()).hexdigest()
    elif defaut == "extension":
        (lot / "source_mesures_recue.xlsx").rename(lot / "source_mesures_recue.csv")
        manifeste["fichiers_sha256"]["source_mesures_recue.csv"] = manifeste["fichiers_sha256"].pop("source_mesures_recue.xlsx")
    else:
        (lot / "source_mesures_recue.csv").write_bytes(b"NON OFFICIEL")
        manifeste["fichiers_sha256"]["source_mesures_recue.csv"] = hashlib.sha256(b"NON OFFICIEL").hexdigest()
    (lot / "manifest.json").write_text(json.dumps(manifeste))
    with pytest.raises(ValueError):
        charger_lot_mesures(lot)


def test_api_recherche_sources_couverture_et_consultation_sans_fusion(revue):
    client,racine,registre,cfg = revue
    entrees = cfg.root / "entrees_xlsx"
    entrees.mkdir()
    source,metadata = fichiers(entrees)
    preparer_mesures_autonomes(source,metadata,racine / "mesures_xlsx")
    reg = json.loads(registre.read_text())
    reg["lots"].append({"id":"mesures_xlsx","dossier":"mesures_xlsx","type_lot":"mesures",
                        "manifest_sha256":hashlib.sha256((racine / "mesures_xlsx/manifest.json").read_bytes()).hexdigest()})
    registre.write_text(json.dumps(reg))
    avant = snapshot(racine)
    for chemin in ("check","sources","coverage","measure-search?code10=0000000001"):
        r = client.get(BASE+"/lots/mesures_xlsx/"+chemin,headers=ADMIN)
        assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    r = client.get(BASE+"/tariff-measures?tarif=tarif_a&mesures=mesures_xlsx&code10=0000000001",headers=ADMIN)
    assert r.status_code == 200
    rep = r.json()["resultat"]
    assert rep["mesures_autonomes"]["source_declaree"]["format"] == "xlsx"
    assert rep["mesures_autonomes"]["total_correspondances"] == 3
    assert rep["fiche_nomenclature"]["ligne_trouvee"] is False
    assert rep["mesures_fusionnees"] is rep["rattachement_juridique_etabli"] is False
    assert snapshot(racine) == avant


def test_sauvegarde_reprise_xlsx(tmp_cfg,tmp_path):
    from types import SimpleNamespace

    from unocr import backup

    entrees = tmp_path / "entrees"
    entrees.mkdir()
    source,metadata = fichiers(entrees)
    racine = tmp_cfg.data_dir / "customs-quarantine"
    racine.mkdir(parents=True,exist_ok=True)
    preparer_mesures_autonomes(source,metadata,racine / "mesures")
    avant = snapshot(racine)
    sauvegarde = backup.creer_sauvegarde(tmp_cfg,inclure_quarantaine=True)
    cible = SimpleNamespace(data_dir=tmp_path / "reprise/data",log_dir=tmp_path / "reprise/logs")
    backup.restaurer_sauvegarde(cible,sauvegarde.chemin,inclure_quarantaine=True)
    repris = cible.data_dir / "customs-quarantine"
    assert {k:v[1] for k,v in snapshot(repris).items()} == {k:v[1] for k,v in avant.items()}
    lot,rapport = charger_lot_mesures(repris / "mesures")
    assert len(lot.mesures) == 6 and lot.source.format == "xlsx"
    assert rapport["fiscalite_applicable_etablie"] is False and snapshot(racine) == avant


@pytest.mark.parametrize("borne",["MAX_LIGNES","MAX_COLONNES","MAX_CELLULES","MAX_MEMBRES","MAX_DECOMPRESSE","MAX_RATIO"])
def test_bornes_lecteur_reutilisees(tmp_path,monkeypatch,borne):
    from unocr.customs_reference import tabular

    source,metadata = fichiers(tmp_path)
    monkeypatch.setattr(tabular,borne,1)
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


def test_ligne_vide_comptee_et_references_physiques(tmp_path):
    source,metadata = fichiers(tmp_path)
    classeur = load_workbook(source)
    classeur["Mesures déclarées"].insert_rows(3)
    classeur.save(source)
    classeur.close()
    actualiser(source,metadata)
    preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    lot,rapport = charger_lot_mesures(tmp_path / "lot")
    assert lot.mesures[0].reference.localisateur == "XLSX, feuille Mesures déclarées, ligne 4"
    assert rapport["perimetre_lecture"]["lignes_vides_ignorees"] == 1
