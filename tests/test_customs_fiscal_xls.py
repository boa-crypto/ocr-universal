"""Sous-ensemble XLS autonome : fixtures BIFF8 NON OFFICIELLES exclusivement."""
import hashlib
import json
from datetime import datetime

import pytest

from tests import test_customs_review
from tests.test_customs_fiscal_csv import MAPPING, actualiser
from tests.test_customs_fiscal_csv import fichiers as fichiers_csv
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.fiscal_importer import charger_lot_mesures, preparer_mesures_autonomes

revue = test_customs_review.revue


def fichiers(root,defaut=None):
    xlwt = pytest.importorskip("xlwt",reason="Dépendance dev nécessaire aux fixtures BIFF8")
    _,metadata = fichiers_csv(root)
    mesures = json.loads((root / "MESURES_NON_OFFICIELLES.json").read_text())
    mesures[0]["description"] = "Équipement; مُعَـدَّات\nFIXTURE NON OFFICIELLE"
    rows = [["FIXTURE NON OFFICIELLE"],[*MAPPING.values(),"Non importée"]]
    rows.extend([[m.get(c) if m.get(c) is not None else "" for c in MAPPING]+["Texte non importé"] for m in mesures])
    if defaut == "entete_duplique":
        rows[1][1] = "ID"
    if defaut == "entete_numerique":
        rows[1][1] = 1
    mutations = {"code_numerique":(2,1,1),"taux_numerique":(2,4,1.23),"zero_numerique":(3,4,0),
                 "date_excel":(2,6,datetime(2026,1,1)),"booleen":(2,0,True),"doublon_id":(3,0,"M_0"),
                 "formule":(2,3,xlwt.Formula('"NON OFFICIEL"')),
                 "formule_non_importee":(2,8,xlwt.Formula("1+1")),"nombre_non_importe":(2,8,42)}
    if defaut in mutations:
        ligne,colonne,valeur = mutations[defaut]
        rows[ligne][colonne] = valeur
    if defaut == "hors_entete":
        rows[2].append("SURPLUS")
    if defaut == "ligne_vide":
        rows.insert(2,[])
    if defaut == "vide":
        rows = rows[:2]
    if defaut == "fusion":
        rows[1].append("Deuxième colonne exclue")
    wb = xlwt.Workbook()
    feuille = wb.add_sheet("Mesures déclarées",cell_overwrite_ok=True)
    notes = wb.add_sheet("Notes exclues")
    notes.write(0,0,xlwt.Formula("1+1") if defaut=="formule_autre_feuille" else "NON OFFICIEL")
    if defaut == "cachee":
        feuille.visibility = 1
    for numero,row in enumerate(rows):
        for colonne,valeur in enumerate(row):
            style = xlwt.easyxf(num_format_str="0000000000") if defaut=="code_numerique" and (numero,colonne)==(2,1) else xlwt.Style.default_style
            feuille.write(numero,colonne,valeur,style)
    if defaut == "fusion":
        feuille.write_merge(2,2,8,9,"Texte non importé fusionné")
    source = root / "MESURES_NON_OFFICIELLES.xls"
    wb.save(str(source))
    meta = json.loads(metadata.read_text())
    meta.pop("delimiteur")
    meta.update(feuille="Mesures déclarées",ligne_entete=2)
    meta["source"]["format"] = "xls"
    metadata.write_text(json.dumps(meta))
    actualiser(source,metadata)
    return source,metadata


def test_plan_archive_source_exacte_precision_et_rejeu(tmp_path):
    source,metadata = fichiers(tmp_path)
    avant = snapshot(tmp_path)
    rapport = preparer_mesures_autonomes(source,metadata)
    assert snapshot(tmp_path) == avant and rapport["ecrit"] is False
    perimetre = rapport["perimetre_lecture"]
    assert perimetre["feuilles_non_importees"] == ["Notes exclues"]
    assert perimetre["colonnes_non_importees"] == ["Non importée"]
    assert perimetre["contrat_xls"] == "ole_biff8_textuel_records_actifs_refuses"
    assert rapport["mesures_importables"] == 6
    preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    lot,controle = charger_lot_mesures(tmp_path / "lot")
    assert lot.source.format == "xls" and lot.mesures[0].code_tarifaire_10 == "0000000001"
    assert str(lot.mesures[0].taux) == "1.230000000000000000000000001"
    assert lot.mesures[1].taux == 0 and lot.mesures[2].taux is None
    assert lot.mesures[0].reference.localisateur == "XLS, feuille Mesures déclarées, ligne 3"
    assert lot.mesures[0].description == "Équipement; مُعَـدَّات\nFIXTURE NON OFFICIELLE"
    assert (tmp_path / "lot/source_mesures_recue.xls").read_bytes() == source.read_bytes()
    assert (tmp_path / "lot/metadata_original.json").read_bytes() == metadata.read_bytes()
    assert not {"colonnes","delimiteur","feuille","ligne_entete"} & set(lot.model_dump())
    assert controle["fiscalite_applicable_etablie"] is False


@pytest.mark.parametrize("defaut",["code_numerique","taux_numerique","zero_numerique","date_excel","booleen", "doublon_id",
    "formule","formule_non_importee","formule_autre_feuille","nombre_non_importe","cachee","fusion",
    "entete_duplique","entete_numerique","hors_entete"])
def test_classeurs_hors_contrat_refuses_sans_ecriture(tmp_path,defaut):
    source,metadata = fichiers(tmp_path,defaut)
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("champ,valeur",[("feuille",None),("feuille","ABSENTE"),("feuille"," "),("ligne_entete",True),
    ("ligne_entete",0),("ligne_entete",51),("ligne_entete",1),("delimiteur",";"),("colonnes",None),
    ("colonnes",{"id":"ID"}),("colonnes",{**MAPPING,"description":"ABSENTE"}),("colonnes",{**MAPPING,"reference":"Non importée"})])
def test_mapping_et_options_incoherents_refuses(tmp_path,champ,valeur):
    source,metadata = fichiers(tmp_path)
    meta = json.loads(metadata.read_text())
    meta[champ] = valeur
    metadata.write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("defaut",["vide","ligne_vide"])
def test_lignes_vides_pas_mesures_et_reference_reelle(tmp_path,defaut):
    source,metadata = fichiers(tmp_path,defaut)
    preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    lot,rapport = charger_lot_mesures(tmp_path / "lot")
    assert len(lot.mesures) == (0 if defaut=="vide" else 6)
    if defaut == "ligne_vide":
        assert lot.mesures[0].reference.localisateur == "XLS, feuille Mesures déclarées, ligne 4"
        assert rapport["perimetre_lecture"]["lignes_vides_ignorees"] == 1


@pytest.mark.parametrize("borne",["MAX_XLS","MAX_RECORDS","MAX_LIGNES","MAX_COLONNES","MAX_CELLULES"])
def test_bornes_binaires_reutilisees(tmp_path,monkeypatch,borne):
    from unocr.customs_reference import xls_table

    source,metadata = fichiers(tmp_path)
    monkeypatch.setattr(xls_table,borne,1)
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("contenu",[b"",b"<html>NON OFFICIEL</html>",b"PK\x03\x04FAUX XLS",b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1TRONQUE"])
def test_faux_xls_et_ole_corrompu_refuses(tmp_path,contenu):
    source,metadata = fichiers(tmp_path)
    source.write_bytes(contenu)
    actualiser(source,metadata)
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("defaut",["source","lot_rehache","extension","deux_sources"])
def test_archive_alteree_refusee(tmp_path,defaut):
    source,metadata = fichiers(tmp_path)
    lot = tmp_path / "lot"
    preparer_mesures_autonomes(source,metadata,lot)
    manifeste = json.loads((lot / "manifest.json").read_text())
    if defaut == "source":
        (lot / "source_mesures_recue.xls").write_bytes(b"ALTERE NON OFFICIEL")
    elif defaut == "lot_rehache":
        x = json.loads((lot / "lot_mesures.json").read_text())
        x["mesures"][0]["description"] = "ALTERE NON OFFICIEL"
        (lot / "lot_mesures.json").write_text(json.dumps(x))
        manifeste["fichiers_sha256"]["lot_mesures.json"] = hashlib.sha256((lot / "lot_mesures.json").read_bytes()).hexdigest()
    elif defaut == "extension":
        (lot / "source_mesures_recue.xls").rename(lot / "source_mesures_recue.xlsx")
        manifeste["fichiers_sha256"]["source_mesures_recue.xlsx"] = manifeste["fichiers_sha256"].pop("source_mesures_recue.xls")
    else:
        (lot / "source_mesures_recue.csv").write_bytes(b"NON OFFICIEL")
        manifeste["fichiers_sha256"]["source_mesures_recue.csv"] = hashlib.sha256(b"NON OFFICIEL").hexdigest()
    (lot / "manifest.json").write_text(json.dumps(manifeste))
    with pytest.raises(ValueError):
        charger_lot_mesures(lot)


def test_cli_plan_ecriture_check_et_refus(tmp_path,capsys):
    source,metadata = fichiers(tmp_path)
    args = ["customs-fiscal-prepare",str(source),"--metadata",str(metadata),"--out",str(tmp_path / "lot")]
    assert main(args) == 0 and not (tmp_path / "lot").exists()
    assert json.loads(capsys.readouterr().out)["perimetre_lecture"]["format"] == "xls"
    assert main(args+["--write"]) == 0
    capsys.readouterr()
    assert main(["customs-fiscal-check",str(tmp_path / "lot")]) == 0
    capsys.readouterr()
    assert main(args+["--write"]) == 2
    capsys.readouterr()


def test_api_recherche_sources_couverture_et_consultation_sans_fusion(revue):
    client,racine,registre,cfg = revue
    entrees = cfg.root / "entrees_xls"
    entrees.mkdir()
    source,metadata = fichiers(entrees)
    preparer_mesures_autonomes(source,metadata,racine / "mesures_xls")
    reg = json.loads(registre.read_text())
    reg["lots"].append({"id":"mesures_xls","dossier":"mesures_xls","type_lot":"mesures",
                        "manifest_sha256":hashlib.sha256((racine / "mesures_xls/manifest.json").read_bytes()).hexdigest()})
    registre.write_text(json.dumps(reg))
    avant = snapshot(racine)
    for chemin in ("check","sources","coverage","measure-search?code10=0000000001"):
        r = client.get(BASE+"/lots/mesures_xls/"+chemin,headers=ADMIN)
        assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    r = client.get(BASE+"/tariff-measures?tarif=tarif_a&mesures=mesures_xls&code10=0000000001",headers=ADMIN)
    assert r.status_code == 200
    rep = r.json()["resultat"]
    assert rep["mesures_autonomes"]["source_declaree"]["format"] == "xls"
    assert rep["mesures_autonomes"]["total_correspondances"] == 3
    assert rep["fiche_nomenclature"]["ligne_trouvee"] is False
    assert rep["mesures_fusionnees"] is rep["rattachement_juridique_etabli"] is False
    assert snapshot(racine) == avant


def test_sauvegarde_reprise_xls(tmp_cfg,tmp_path):
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
    assert len(lot.mesures) == 6 and lot.source.format == "xls"
    assert rapport["fiscalite_applicable_etablie"] is False and snapshot(racine) == avant


def figer_xlsx_non_officiel(source,metadata):
    """Neutraliser dates ZIP/propriétés pour le seul test d'empreinte 40→41."""
    import io
    import re
    import zipfile

    tampon = io.BytesIO()
    with zipfile.ZipFile(source) as archive, zipfile.ZipFile(tampon,"w") as sortie:
        for nom in archive.namelist():
            contenu = archive.read(nom)
            if nom == "docProps/core.xml":
                contenu = re.sub(rb'(<dcterms:(?:created|modified)[^>]*>)[^<]+',rb'\g<1>2000-01-01T00:00:00Z',contenu)
            sortie.writestr(zipfile.ZipInfo(nom,date_time=(2000,1,1,0,0,0)),contenu)
    source.write_bytes(tampon.getvalue())
    actualiser(source,metadata)


def test_sorties_xlsx_40_identiques_et_rejouables(tmp_path):
    from tests.test_customs_fiscal_xlsx import fichiers as fichiers_xlsx

    source,metadata = fichiers_xlsx(tmp_path)
    figer_xlsx_non_officiel(source,metadata)
    preparer_mesures_autonomes(source,metadata,tmp_path / "xlsx40")
    # Empreintes obtenues avec les préparateur ET adaptateur du commit e66148c2.
    attendus = {"lot_mesures.json":"18ef40249d51a35f18d56eb4136abb4cb2942b97b0926bbc70b223db64d52b7c","rapport.json":"145e1d46159d627044a27a4164222b2d1fe96ffdc941c36d9f5a7d0c83bd1285"}
    for nom,sha in attendus.items():
        assert hashlib.sha256((tmp_path / "xlsx40" / nom).read_bytes()).hexdigest() == sha
    lot,_ = charger_lot_mesures(tmp_path / "xlsx40")
    assert len(lot.mesures) == 6 and lot.source.format == "xlsx"


@pytest.mark.parametrize("format_source",["json","csv"])
def test_adaptateur_tableur_refuse_autres_formats(tmp_path,format_source):
    from unocr.customs_reference.fiscal_models import ConfigurationMesuresAutonomes
    from unocr.customs_reference.fiscal_xlsx import lire_mesures_tableur

    source,metadata = fichiers(tmp_path)
    meta = json.loads(metadata.read_text())
    meta["source"]["format"] = format_source
    cfg = ConfigurationMesuresAutonomes.model_validate_json(json.dumps(meta))
    with pytest.raises(ValueError,match="Format tableur"):
        lire_mesures_tableur(source.read_bytes(),cfg)
