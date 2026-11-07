"""Mesures autonomes de fixtures NON OFFICIELLES ; aucun tarif/taux national."""
import copy
import hashlib
import json

import pytest

from tests.test_customs_reference import snapshot
from unocr.cli import main
from unocr.customs_reference.comparison import charger_lot
from unocr.customs_reference.fiscal_importer import charger_lot_mesures, preparer_mesures_autonomes
from unocr.customs_reference.fiscal_models import MesuresAutonomesBatch, MetadataMesuresAutonomes
from unocr.customs_reference.importer import ImportRefuse
from unocr.customs_reference.legal_comparison import charger_lot_code
from unocr.customs_reference.measure_search import TYPES_MESURES
from unocr.customs_reference.review_registry import RegistreRevue


def fichiers(root):
    source,metadata = root / "MESURES_NON_OFFICIELLES.json",root / "metadata.json"
    sid = "SOURCE_MESURES_NON_OFFICIELLE"
    mesures = [{"id":"M_"+str(i),"code_tarifaire_10":"0000000001" if i<3 else "9999999999",
        "type_mesure":t,"description":"Équipement مُعَـدَّات NON OFFICIEL",
        "reference":{"source_id":sid,"localisateur":"JSON, mesure déclarée "+str(i)},
        "taux":["1.230000000000000000000000001","0"][i] if i<2 else None,
        "unite_taux":"pourcent" if i<2 else None,
        "date_entree_vigueur":"2001-02-03" if i == 0 else None}
        for i,t in enumerate(TYPES_MESURES)]
    source.write_text(json.dumps(mesures,ensure_ascii=False))
    metadata.write_text(json.dumps({"source":{"id":sid,"titre":"FIXTURE MESURES NON OFFICIELLE",
        "url":"https://www.douane.gov.dz/TEST_NON_OFFICIEL/mesures.json","organisme":"FIXTURE NON OFFICIELLE",
        "version_source":"TEST_MESURES","format":"json","date_publication":"2002-01-01",
        "sha256":hashlib.sha256(source.read_bytes()).hexdigest()}}))
    return source,metadata


def modifier(source,metadata,fonction):
    brut = json.loads(source.read_text())
    fonction(brut)
    source.write_text(json.dumps(brut,ensure_ascii=False))
    m = json.loads(metadata.read_text())
    m["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(m))


def test_plan_sans_ecriture_sans_nomenclature(tmp_path):
    source,metadata = fichiers(tmp_path)
    avant = snapshot(tmp_path)
    rep = preparer_mesures_autonomes(source,metadata)
    assert rep["mesures_source_lues"] == rep["mesures_importables"] == 6
    assert rep["codes10_declares_distincts"] == 2
    assert rep["ecrit"] is False and rep["nomenclature_incluse"] is False
    assert rep["existence_codes_dans_nomenclature"] == "non_verifiee"
    assert rep["fiscalite_applicable_etablie"] is rep["utilisable_pour_calcul_douanier"] is False
    assert snapshot(tmp_path) == avant


def test_archive_octets_rejeu_decimal_dates_source_distinctes(tmp_path):
    source,metadata = fichiers(tmp_path)
    lot = tmp_path / "lot"
    rep = preparer_mesures_autonomes(source,metadata,lot)
    assert rep["ecrit"] is True
    assert (lot / "source_mesures_recue.json").read_bytes() == source.read_bytes()
    assert (lot / "metadata_original.json").read_bytes() == metadata.read_bytes()
    avant = snapshot(tmp_path)
    donnees,controle = charger_lot_mesures(lot)
    assert str(donnees.mesures[0].taux) == "1.230000000000000000000000001"
    assert donnees.mesures[0].code_tarifaire_10 == "0000000001"
    assert donnees.mesures[1].taux == 0 and donnees.mesures[2].taux is None
    assert donnees.source.date_publication.isoformat() == "2002-01-01"
    assert donnees.mesures[0].date_entree_vigueur.isoformat() == "2001-02-03"
    assert donnees.mesures[1].date_entree_vigueur is None
    assert not hasattr(donnees,"lignes")
    assert controle["archive"]["manifest_sha256"] == hashlib.sha256((lot / "manifest.json").read_bytes()).hexdigest()
    assert snapshot(tmp_path) == avant
    with pytest.raises(FileExistsError):
        preparer_mesures_autonomes(source,metadata,lot)
    assert snapshot(tmp_path) == avant


def test_source_vide_ne_signifie_pas_exoneration(tmp_path):
    source,metadata = fichiers(tmp_path)
    modifier(source,metadata,lambda x:x.clear())
    lot = tmp_path / "lot"
    rep = preparer_mesures_autonomes(source,metadata,lot)
    assert rep["mesures_importables"] == 0 and rep["completude_reglementaire"] == "non_etablie"
    assert charger_lot_mesures(lot)[0].mesures == []


@pytest.mark.parametrize("champ,valeur",[
    ("code_tarifaire_10",1),("code_tarifaire_10","000001"),("code_tarifaire_10","٠٠٠٠٠٠٠٠٠١"),
    ("id"," "),("description"," "),("type_mesure","estimation_ia"),("statut","validee"),
    ("taux",1.2),("taux",0),("taux",True),("taux","NaN"),("taux","Infinity"),("taux","-1"),("taux","1,2"),
    ("unite_taux",None),("date_fin_validite","2000-01-01"),
    ("reference",{"source_id":"ETRANGERE","localisateur":"TEST"}),
    ("reference",{"source_id":"SOURCE_MESURES_NON_OFFICIELLE","localisateur":" "}),
    ("champ_inconnu","x")])
def test_mesures_invalides_refusees_avant_creation(tmp_path,champ,valeur):
    source,metadata = fichiers(tmp_path)
    modifier(source,metadata,lambda x:x[0].__setitem__(champ,valeur))
    lot = tmp_path / "lot"
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,lot)
    assert not lot.exists()


def test_doublon_id_et_taux_sur_restriction(tmp_path):
    source,metadata = fichiers(tmp_path)
    modifier(source,metadata,lambda x:x.append(copy.deepcopy(x[0])))
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata)
    source,metadata = fichiers(tmp_path)
    modifier(source,metadata,lambda x:x[0].__setitem__("type_mesure","restriction"))
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata)


@pytest.mark.parametrize("champ,valeur",[("publication_active",True),("publication_active",0),
    ("validation_juridique","validee"),("mesures",[]),("lignes",[]),("statut","actif")])
def test_metadata_activations_et_mesures_inline_refusees(tmp_path,champ,valeur):
    source,metadata = fichiers(tmp_path)
    m = json.loads(metadata.read_text())
    m[champ] = valeur
    metadata.write_text(json.dumps(m))
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("defaut",["sha","url","format","source_blanche","json_duplique","json_constante","objet_source"])
def test_provenance_et_json_refuses(tmp_path,defaut):
    source,metadata = fichiers(tmp_path)
    m = json.loads(metadata.read_text())
    if defaut in {"sha","url","format","source_blanche"}:
        k,v = {"sha":("sha256","0"*64),"url":("url","https://prive.invalid/mesures"),
               "format":("format","pdf"),"source_blanche":("titre"," ")}[defaut]
        m["source"][k] = v
    else:
        source.write_bytes({"json_duplique":b'[{"id":"A","id":"B"}]',"json_constante":b'[NaN]',"objet_source":b'{}'}[defaut])
        m["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(m))
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("defaut",["source","lot_rehache","rapport_rehache","surplus","symbolique","date","type","manifeste_duplique"])
def test_archive_altérée_et_rejeu_refuses(tmp_path,defaut):
    source,metadata = fichiers(tmp_path)
    lot = tmp_path / "lot"
    preparer_mesures_autonomes(source,metadata,lot)
    manifest = json.loads((lot / "manifest.json").read_text())
    if defaut == "source":
        (lot / "source_mesures_recue.json").write_bytes(b"[]")
    elif defaut in {"lot_rehache","rapport_rehache"}:
        nom = "lot_mesures.json" if defaut == "lot_rehache" else "rapport.json"
        x = json.loads((lot / nom).read_text())
        if defaut == "lot_rehache":
            x["mesures"][0]["description"] = "ALTÉRÉ NON OFFICIEL"
        else:
            x["mesures_importables"] = True
        (lot / nom).write_text(json.dumps(x))
        manifest["fichiers_sha256"][nom] = hashlib.sha256((lot / nom).read_bytes()).hexdigest()
    elif defaut == "surplus":
        (lot / "autre.json").write_text("{}")
    elif defaut == "symbolique":
        (lot / "source_mesures_recue.json").unlink()
        (lot / "source_mesures_recue.json").symlink_to(source)
    elif defaut == "date":
        manifest["date_importation"] = "2026-11-07T12:00:00"
    elif defaut == "type":
        manifest["type_lot"] = "tarif"
    elif defaut == "manifeste_duplique":
        (lot / "manifest.json").write_text('{"type_lot":"x","type_lot":"y"}')
    if defaut != "manifeste_duplique":
        (lot / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises((ValueError,OSError)):
        charger_lot_mesures(lot)


def test_types_anciens_et_registre_refusent_sans_mauvais_routage(tmp_path):
    source,metadata = fichiers(tmp_path)
    lot = tmp_path / "lot"
    preparer_mesures_autonomes(source,metadata,lot)
    for chargeur in (charger_lot,charger_lot_code):
        with pytest.raises((ValueError,KeyError)):
            chargeur(lot)
    with pytest.raises(ValueError):
        RegistreRevue.model_validate_json(json.dumps({"reviseurs":["TEST"],"lots":[
            {"id":"TEST_FISCAL","dossier":"lot","type_lot":"mesures","manifest_sha256":"a"*64}]}))


def test_cli_plan_ecriture_check_refus_et_schema(tmp_path,capsys):
    source,metadata = fichiers(tmp_path)
    lot = tmp_path / "lot"
    args = ["customs-fiscal-prepare",str(source),"--metadata",str(metadata),"--out",str(lot)]
    assert main(args) == 0 and not lot.exists()
    assert json.loads(capsys.readouterr().out)["ecrit"] is False
    assert main(args+["--write"]) == 0
    assert json.loads(capsys.readouterr().out)["ecrit"] is True
    assert main(["customs-fiscal-check",str(lot)]) == 0
    assert json.loads(capsys.readouterr().out)["archive"]["manifest_sha256"]
    assert main(args+["--write"]) == 2
    capsys.readouterr()
    assert main(["customs-fiscal-prepare",str(source),"--metadata",str(metadata),"--write"]) == 2
    capsys.readouterr()
    assert main(["customs-fiscal-check",str(tmp_path / "absent")]) == 2
    capsys.readouterr()
    from pathlib import Path
    for cls in (MesuresAutonomesBatch,MetadataMesuresAutonomes):
        s = json.loads(Path('docs/customs/schemas/'+cls.__name__+'.schema.json').read_text())
        s.pop('$schema')
        s.pop('description')
        assert s == cls.model_json_schema()


def test_source_symbolique_sortie_existante_et_borne_artefact(tmp_path,monkeypatch):
    import unocr.customs_reference.fiscal_importer as module
    source,metadata = fichiers(tmp_path)
    lien = tmp_path / "lien.json"
    lien.symlink_to(source)
    with pytest.raises(ImportRefuse):
        preparer_mesures_autonomes(lien,metadata)
    monkeypatch.setattr(module,"MAX_SOURCE",32)
    with pytest.raises(ImportRefuse):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    assert not (tmp_path / "lot").exists()


def test_sauvegarde_reprise_existante_conserve_lot_autonome(tmp_cfg,tmp_path):
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
    assert len(lot.mesures) == 6 and rapport["fiscalite_applicable_etablie"] is False
    assert snapshot(racine) == avant
