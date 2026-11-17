"""CSV de mesures de fixtures NON OFFICIELLES, jamais fichier fiscal national."""
import csv
import hashlib
import io
import json

import pytest

from tests import test_customs_review
from tests.test_customs_fiscal_import import fichiers as fichiers_json
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.fiscal_importer import charger_lot_mesures, preparer_mesures_autonomes
from unocr.customs_reference.fiscal_models import ConfigurationMesuresAutonomes

revue = test_customs_review.revue
MAPPING = {"id":"ID","code_tarifaire_10":"Code","type_mesure":"Type","description":"Libellé",
           "taux":"Taux","unite_taux":"Unité","date_entree_vigueur":"Début","date_fin_validite":"Fin"}


def fichiers(root,delimiteur=";",bom=True):
    source_json,metadata = fichiers_json(root)
    mesures = json.loads(source_json.read_text())
    mesures[0]["description"] = "Équipement; مُعَـدَّات\nFIXTURE NON OFFICIELLE"
    tampon = io.StringIO(newline="")
    writer = csv.writer(tampon,delimiter=delimiteur,lineterminator="\r\n")
    writer.writerow([*MAPPING.values(),"Non importée"])
    for m in mesures:
        writer.writerow([m.get(c) if m.get(c) is not None else "" for c in MAPPING]+["=1+1"])
    source = root / "MESURES_NON_OFFICIELLES.csv"
    source.write_bytes(tampon.getvalue().encode("utf-8-sig" if bom else "utf-8"))
    meta = json.loads(metadata.read_text())
    meta["source"].update(format="csv",sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    meta.update(colonnes=MAPPING,delimiteur=delimiteur)
    metadata.write_text(json.dumps(meta,ensure_ascii=False))
    return source,metadata


def actualiser(source,metadata):
    m = json.loads(metadata.read_text())
    m["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(m,ensure_ascii=False))


def test_csv_bom_multiligne_precision_sources_et_rejeu(tmp_path):
    source,metadata = fichiers(tmp_path)
    avant = snapshot(tmp_path)
    rep = preparer_mesures_autonomes(source,metadata)
    assert snapshot(tmp_path) == avant and rep["ecrit"] is False
    assert rep["perimetre_lecture"]["colonnes_non_importees"] == ["Non importée"]
    assert rep["mesures_importables"] == 6
    lot = tmp_path / "lot"
    preparer_mesures_autonomes(source,metadata,lot)
    donnees,controle = charger_lot_mesures(lot)
    assert donnees.source.format == "csv" and donnees.mesures[0].code_tarifaire_10 == "0000000001"
    assert str(donnees.mesures[0].taux) == "1.230000000000000000000000001"
    assert donnees.mesures[1].taux == 0 and donnees.mesures[2].taux is None
    assert donnees.mesures[0].reference.localisateur == "CSV, fin de ligne physique 3"
    assert donnees.mesures[1].reference.localisateur == "CSV, fin de ligne physique 4"
    assert donnees.mesures[0].description == "Équipement; مُعَـدَّات\nFIXTURE NON OFFICIELLE"
    assert donnees.mesures[1].date_entree_vigueur is None
    assert (lot / "source_mesures_recue.csv").read_bytes() == source.read_bytes()
    assert (lot / "metadata_original.json").read_bytes() == metadata.read_bytes()
    assert "colonnes" not in donnees.model_dump() and "delimiteur" not in donnees.model_dump()
    assert controle["existence_codes_dans_nomenclature"] == "non_verifiee"


@pytest.mark.parametrize("delimiteur",[",","\t","|"])
def test_delimiteurs_explicites_sans_bom(tmp_path,delimiteur):
    source,metadata = fichiers(tmp_path,delimiteur,bom=False)
    assert preparer_mesures_autonomes(source,metadata)["mesures_importables"] == 6


@pytest.mark.parametrize("defaut",["absent","id_absent","champ_inconnu","reference_reservee","colonne_partagee","introuvable","type_invalide"])
def test_mapping_refuse_sans_ecriture(tmp_path,defaut):
    source,metadata = fichiers(tmp_path)
    m = json.loads(metadata.read_text())
    if defaut == "absent":
        m.pop("colonnes")
    elif defaut == "id_absent":
        m["colonnes"].pop("id")
    elif defaut in {"champ_inconnu","reference_reservee"}:
        m["colonnes"]["champ_inconnu" if defaut == "champ_inconnu" else "reference"] = "Non importée"
    elif defaut == "colonne_partagee":
        m["colonnes"]["description"] = "Code"
    elif defaut == "introuvable":
        m["colonnes"]["id"] = "ABSENT"
    else:
        m["colonnes"]["id"] = True
    metadata.write_text(json.dumps(m))
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("delimiteur",["",";;","\r","\n","\x00",'"',"\ufeff",True])
def test_delimiteurs_invalides(tmp_path,delimiteur):
    source,metadata = fichiers(tmp_path)
    m = json.loads(metadata.read_text())
    m["delimiteur"] = delimiteur
    metadata.write_text(json.dumps(m))
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("contenu",[b"",b"ID;ID\r\nA;B\r\n",b"ID;;Type\r\nA;B;C\r\n",b'ID;Code;Type;Libell\xc3\xa9\r\n"non termine',
    b"ID;Code;Type;Libell\xc3\xa9\r\nA;0000000001;droit\r\n",b"\xff\xfeINVALID"])
def test_csv_incoherent_et_encodage_refuses(tmp_path,contenu):
    source,metadata = fichiers(tmp_path)
    source.write_bytes(contenu)
    actualiser(source,metadata)
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("ancien,nouveau",[("0000000001","1"),("0000000001","1E9"),
    ("1.230000000000000000000000001","=1+1"),("1.230000000000000000000000001","1,23"),
    ("M_0","M_1")])
def test_codes_taux_et_ids_ambigus_refuses(tmp_path,ancien,nouveau):
    source,metadata = fichiers(tmp_path)
    source.write_bytes(source.read_bytes().replace(ancien.encode(),nouveau.encode(),1))
    actualiser(source,metadata)
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


def test_csv_sans_donnees_et_options_interdites_json(tmp_path):
    source,metadata = fichiers(tmp_path)
    source.write_bytes((";".join([*MAPPING.values(),"Non importée"])+"\r\n").encode())
    actualiser(source,metadata)
    assert preparer_mesures_autonomes(source,metadata)["mesures_importables"] == 0
    source,metadata = fichiers_json(tmp_path)
    m = json.loads(metadata.read_text())
    m["colonnes"] = MAPPING
    metadata.write_text(json.dumps(m))
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata)


@pytest.mark.parametrize("defaut",["fichier_modifie","lot_rehache","extension_incoherente","double_source"])
def test_archive_csv_alteree_refusee(tmp_path,defaut):
    source,metadata = fichiers(tmp_path)
    lot = tmp_path / "lot"
    preparer_mesures_autonomes(source,metadata,lot)
    p = lot / "manifest.json"
    m = json.loads(p.read_text())
    if defaut == "fichier_modifie":
        (lot / "source_mesures_recue.csv").write_bytes(b"MODIFIE")
    elif defaut == "lot_rehache":
        x = json.loads((lot / "lot_mesures.json").read_text())
        x["mesures"][0]["description"] = "ALTERE NON OFFICIEL"
        (lot / "lot_mesures.json").write_text(json.dumps(x))
        m["fichiers_sha256"]["lot_mesures.json"] = hashlib.sha256((lot / "lot_mesures.json").read_bytes()).hexdigest()
    elif defaut == "extension_incoherente":
        (lot / "source_mesures_recue.csv").rename(lot / "source_mesures_recue.json")
        m["fichiers_sha256"]["source_mesures_recue.json"] = m["fichiers_sha256"].pop("source_mesures_recue.csv")
    else:
        (lot / "source_mesures_recue.json").write_bytes(b"[]")
        m["fichiers_sha256"]["source_mesures_recue.json"] = hashlib.sha256(b"[]").hexdigest()
    p.write_text(json.dumps(m))
    with pytest.raises(ValueError):
        charger_lot_mesures(lot)


def test_cli_schema_et_ancien_rapport_json_inchange(tmp_path,capsys):
    source,metadata = fichiers(tmp_path)
    lot = tmp_path / "lot"
    assert main(["customs-fiscal-prepare",str(source),"--metadata",str(metadata),"--out",str(lot),"--write"]) == 0
    assert json.loads(capsys.readouterr().out)["perimetre_lecture"]["format"] == "csv"
    assert main(["customs-fiscal-check",str(lot)]) == 0
    capsys.readouterr()
    from pathlib import Path
    schema = json.loads(Path('docs/customs/schemas/ConfigurationMesuresAutonomes.schema.json').read_text())
    schema.pop('$schema')
    schema.pop('description')
    assert schema == ConfigurationMesuresAutonomes.model_json_schema()
    source,metadata = fichiers_json(tmp_path)
    preparer_mesures_autonomes(source,metadata,tmp_path / "ancien_json")
    # Empreintes figées par l'ancien préparateur du commit b4142425 (fixtures NON OFFICIELLES).
    attendus = {'lot_mesures.json':'133709211196748e1cea71ea4833685fa90ce9a9df1d6924e3603506d0cefc24','rapport.json':'d0b46a7cdebb1cf0951a834f0b715932049144f6ff43303a6b7d5063bd9c3ff2'}
    for nom,sha in attendus.items():
        assert hashlib.sha256((tmp_path / "ancien_json" / nom).read_bytes()).hexdigest() == sha


def test_revue_api_csv_et_consultation_tarif_sans_fusion(revue):
    client,racine,registre,cfg = revue
    entrees = cfg.root / "entrees_csv"
    entrees.mkdir()
    source,metadata = fichiers(entrees)
    preparer_mesures_autonomes(source,metadata,racine / "mesures_csv")
    reg = json.loads(registre.read_text())
    reg["lots"].append({"id":"mesures_csv","dossier":"mesures_csv","type_lot":"mesures",
                        "manifest_sha256":hashlib.sha256((racine / "mesures_csv/manifest.json").read_bytes()).hexdigest()})
    registre.write_text(json.dumps(reg))
    avant = snapshot(racine)
    for chemin in ("check","sources","coverage","measure-search?code10=0000000001"):
        r = client.get(BASE+"/lots/mesures_csv/"+chemin,headers=ADMIN)
        assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    r = client.get(BASE+"/tariff-measures?tarif=tarif_a&mesures=mesures_csv&code10=0000000001",headers=ADMIN)
    assert r.status_code == 200
    rep = r.json()["resultat"]
    assert rep["mesures_autonomes"]["source_declaree"]["format"] == "csv"
    assert rep["mesures_autonomes"]["total_correspondances"] == 3
    assert rep["fiche_nomenclature"]["ligne_trouvee"] is False
    assert rep["mesures_fusionnees"] is rep["rattachement_juridique_etabli"] is False
    assert snapshot(racine) == avant


@pytest.mark.parametrize("ligne",['"inachevé','A;0000000001;droit','A;0000000001;droit;NON OFFICIELLE;cellule de trop'])
def test_csv_malforme_apres_mapping_valide(tmp_path,ligne):
    source,metadata = fichiers(tmp_path)
    m = json.loads(metadata.read_text())
    m["colonnes"] = {k:v for k,v in MAPPING.items() if k in {"id","code_tarifaire_10","type_mesure","description"}}
    metadata.write_text(json.dumps(m))
    source.write_bytes(("ID;Code;Type;Libellé\r\n"+ligne).encode())
    actualiser(source,metadata)
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


def test_ligne_vide_non_mesure_et_localisateur_physique(tmp_path):
    source,metadata = fichiers(tmp_path)
    source.write_bytes(source.read_bytes().replace(b"\r\n",b"\r\n\r\n",1))
    actualiser(source,metadata)
    preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    lot,rapport = charger_lot_mesures(tmp_path / "lot")
    assert len(lot.mesures) == 6 and lot.mesures[0].reference.localisateur == "CSV, fin de ligne physique 4"
    assert rapport["perimetre_lecture"]["lignes_physiques_lues"] == 9


def test_sauvegarde_reprise_csv_octets_mapping_et_rejeu(tmp_cfg,tmp_path):
    from types import SimpleNamespace

    from unocr import backup

    entrees = tmp_path / "entrees_fiscales"
    entrees.mkdir()
    source,metadata = fichiers(entrees)
    racine = tmp_cfg.data_dir / "customs-quarantine"
    racine.mkdir(parents=True,exist_ok=True)
    preparer_mesures_autonomes(source,metadata,racine / "mesures")
    avant = snapshot(racine)
    with pytest.raises(backup.BackupError):
        backup.creer_sauvegarde(tmp_cfg)
    sauvegarde = backup.creer_sauvegarde(tmp_cfg,inclure_quarantaine=True)
    cible = SimpleNamespace(data_dir=tmp_path / "reprise/data",log_dir=tmp_path / "reprise/logs")
    backup.restaurer_sauvegarde(cible,sauvegarde.chemin,inclure_quarantaine=True)
    repris = cible.data_dir / "customs-quarantine"
    assert {k:v[1] for k,v in snapshot(repris).items()} == {k:v[1] for k,v in avant.items()}
    lot,rapport = charger_lot_mesures(repris / "mesures")
    assert len(lot.mesures) == 6 and lot.source.format == "csv"
    assert rapport["fiscalite_applicable_etablie"] is False and snapshot(racine) == avant
