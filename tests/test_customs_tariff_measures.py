"""Consultation croisée de fixtures NON OFFICIELLES, jamais fiscalité applicable."""
import copy
import hashlib
import json

import pytest

from tests import test_customs_review
from tests.test_customs_fiscal_import import fichiers as fichiers_mesures
from tests.test_customs_reference import fichiers, snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.fiscal_importer import preparer_mesures_autonomes
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.review_export import ExportRefuse, analyser_export
from unocr.customs_reference.tariff_detail import ParamFicheTarifInvalide
from unocr.customs_reference.tariff_measures import juxtaposer_tarif_mesures
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue
CODE = "0101000000"


def preparer(root):
    a,b = root / "entrees_tarif",root / "entrees_mesures"
    a.mkdir()
    b.mkdir()
    source,metadata = fichiers(a)
    m = json.loads(metadata.read_text())
    ref = json.loads(source.read_text())[0]["reference"]
    m["lot"]["mesures"] = [{"id":"M_0","code_tarifaire_10":CODE,"type_mesure":"droit","description":"NATIVE NON OFFICIELLE",
        "reference":ref,"taux":"7.0000","unite_taux":"pourcent"},{"id":"M_1","code_tarifaire_10":CODE,
        "type_mesure":"restriction","description":"RESTRICTION NATIVE NON OFFICIELLE","reference":ref}]
    metadata.write_text(json.dumps(m))
    tarif = root / "tarif"
    preparer_tarif(source,metadata,tarif)
    source,metadata = fichiers_mesures(b)
    valeurs = json.loads(source.read_text())
    for v in valeurs[:3]:
        v["code_tarifaire_10"] = CODE
    source.write_text(json.dumps(valeurs,ensure_ascii=False))
    m = json.loads(metadata.read_text())
    m["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(m))
    mesures = root / "mesures"
    preparer_mesures_autonomes(source,metadata,mesures)
    return tarif,mesures


@pytest.fixture()
def mixte(revue):
    client,racine,registre,cfg = revue
    entree = cfg.root / "entrees_mixtes"
    entree.mkdir()
    tarif,mesures = preparer(entree)
    import shutil
    reg = json.loads(registre.read_text())
    for nom,lot,type_lot in (("tarif_mixte",tarif,"tarif"),("mesures_mixtes",mesures,"mesures")):
        shutil.copytree(lot,racine / nom)
        reg["lots"].append({"id":nom,"dossier":nom,"type_lot":type_lot,
                            "manifest_sha256":hashlib.sha256((lot / "manifest.json").read_bytes()).hexdigest()})
    registre.write_text(json.dumps(reg))
    return revue


def test_sources_mesures_ids_dates_separes_et_octets_intacts(tmp_path):
    tarif,mesures = preparer(tmp_path)
    avant = snapshot(tmp_path)
    rep = juxtaposer_tarif_mesures(tarif,mesures,CODE,1,0,1,0)
    n,m = rep["fiche_nomenclature"],rep["mesures_autonomes"]
    assert n["ligne_trouvee"] is True and n["total_mesures_declarees"] == 2
    assert m["total_correspondances"] == 3 and m["resultats"][0]["ligne_declaree"] is None
    assert n["mesures_declarees"][0]["id"] == m["resultats"][0]["mesure_declaree"]["id"] == "M_0"
    assert n["mesures_declarees"][0]["taux"] == "7.0000"
    assert m["resultats"][0]["mesure_declaree"]["taux"] == "1.230000000000000000000000001"
    assert n["source_declaree"]["sha256"] != m["source_declaree"]["sha256"]
    assert m["source_declaree"]["date_publication"] == "2002-01-01"
    assert m["resultats"][0]["mesure_declaree"]["date_entree_vigueur"] == "2001-02-03"
    assert n["decalage_mesures_suivant"] == m["decalage_suivant"] == 1
    assert rep["rattachement_juridique_etabli"] is rep["mesures_fusionnees"] is rep["utilisable_pour_calcul_douanier"] is False
    assert "archive" not in rep and "archive" not in n and "archive" not in m
    assert snapshot(tmp_path) == avant


def test_paginations_zero_null_absences_et_pas_exoneration(tmp_path):
    a,b = preparer(tmp_path)
    rep = juxtaposer_tarif_mesures(a,b,CODE,1,1,1,1)
    assert rep["fiche_nomenclature"]["mesures_declarees"][0]["taux"] is None
    assert rep["mesures_autonomes"]["resultats"][0]["mesure_declaree"]["taux"] == "0"
    rep = juxtaposer_tarif_mesures(a,b,"9999999999")
    assert rep["fiche_nomenclature"]["ligne_trouvee"] is False and rep["mesures_autonomes"]["total_correspondances"] == 3
    rep = juxtaposer_tarif_mesures(a,b,"1234567890")
    assert rep["fiche_nomenclature"]["ligne_trouvee"] is False and rep["mesures_autonomes"]["resultats"] == []
    assert juxtaposer_tarif_mesures(a,b,CODE,decalage_mesures=99)["mesures_autonomes"]["resultats"] == []
    with pytest.raises(ValueError):
        juxtaposer_tarif_mesures(b,a,CODE)


@pytest.mark.parametrize("kwargs",[{"code10":101},{"code10":"010100"},{"code10":"٠١٠١٠٠٠٠٠٠"},
    {"limite_tarif":0},{"limite_tarif":True},{"decalage_tarif":-1},{"limite_mesures":0},
    {"limite_mesures":101},{"limite_mesures":True},{"decalage_mesures":-1},{"decalage_mesures":1000001}])
def test_parametres_des_deux_cotes_avant_lecture(tmp_path,kwargs):
    with pytest.raises(ParamFicheTarifInvalide):
        juxtaposer_tarif_mesures(tmp_path / "absent1",tmp_path / "absent2",**{"code10":CODE,**kwargs})


def test_cli(tmp_path,capsys):
    a,b = preparer(tmp_path)
    assert main(["customs-tariff-measures",str(a),str(b),"--code",CODE,"--measures-limit","1"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["mesures_autonomes"]["limite"] == 1 and rep["fiche_nomenclature"]["ligne_trouvee"] is True


URL = BASE+"/tariff-measures?tarif=tarif_mixte&mesures=mesures_mixtes&code10="+CODE


def test_api_audit_double_export_et_refus_ambigu(mixte,monkeypatch):
    from unocr import api
    client,racine,registre,cfg = mixte
    avant = snapshot(racine)
    r = client.get(URL,headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    rep = r.json()["resultat"]
    assert rep["lots_exacts"] == {"tarif":"tarif_mixte","mesures":"mesures_mixtes"}
    events = [json.loads(v) for v in (cfg.log_dir / "audit.log").read_text().splitlines()]
    assert events[-1]["manifestes"].keys() == {"tarif_mixte","mesures_mixtes"}
    e = {"schema_version":"1","type_export":"rapport_revue_documentaire_non_valide","lecture_seule":True,
        "publication_active":False,"validation_juridique":"non_validee","perimetre":"rapport_ou_page_uniquement_pas_corpus_complet",
        "horodatage_client_non_certifie":"2026-11-07T10:00:00.000Z","requete_relative":URL,"resultat":rep}
    assert analyser_export(json.dumps(e).encode())["statut"] == "structure_compatible"
    ambigu = copy.deepcopy(e)
    ambigu["resultat"]["archive"] = rep["archives"]["avant"]
    with pytest.raises(ExportRefuse):
        analyser_export(json.dumps(ambigu).encode())
    simple = copy.deepcopy(e)
    simple["resultat"].pop("archives")
    simple["resultat"]["archive"] = rep["archives"]["avant"]
    with pytest.raises(ExportRefuse):
        analyser_export(json.dumps(simple).encode())
    def panne(*a,**kw):
        raise AuditIndisponible("SECRET_TEST")
    monkeypatch.setattr(api,"audit_obligatoire",panne)
    r = client.get(URL,headers=ADMIN)
    assert r.status_code == 503 and "resultat" not in r.json()
    assert snapshot(racine) == avant


@pytest.mark.parametrize("moment",["tarif","mesures","resultat_mesures"])
def test_epingles_des_deux_cotes_et_resultat(mixte,monkeypatch,moment):
    import unocr.routes.customs_review as routes
    client,racine,*_ = mixte
    if moment != "resultat_mesures":
        dossier = "tarif_mixte" if moment == "tarif" else "mesures_mixtes"
        p = racine / dossier / "manifest.json"
        p.write_bytes(p.read_bytes()+b" ")
    else:
        original = routes.juxtaposer_tarif_mesures
        def changer(*a,**kw):
            rep = original(*a,**kw)
            rep["archives"]["apres"]["manifest_sha256"] = "0"*64
            return rep
        monkeypatch.setattr(routes,"juxtaposer_tarif_mesures",changer)
    r = client.get(URL,headers=ADMIN)
    assert r.status_code == 409 and "resultat" not in r.json()


@pytest.mark.parametrize("tarif,mesures",[("mesures_mixtes","tarif_mixte"),("tarif_mixte","tarif_mixte"),
    ("code_a","mesures_mixtes"),("mesures_mixtes","mesures_mixtes"),("tarif_mixte","code_a")])
def test_paires_de_types_incorrectes_refusees(mixte,tarif,mesures):
    client,*_ = mixte
    r = client.get(BASE+f"/tariff-measures?tarif={tarif}&mesures={mesures}&code10={CODE}",headers=ADMIN)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "paire_tarif_mesures_requise"


@pytest.mark.parametrize("headers,statut",[({},401),({"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403)])
def test_droits(mixte,headers,statut):
    client,*_ = mixte
    assert client.get(URL,headers=headers).status_code == statut
