"""Deux fiches NON OFFICIELLES, aucun rapprochement fiscal ou droit applicable."""
import json

import pytest

from tests import test_customs_review
from tests.test_customs_reference import fichiers, snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.review_export import ExportRefuse, analyser_export
from unocr.customs_reference.tariff_detail import ParamFicheTarifInvalide
from unocr.customs_reference.tariff_pair import juxtaposer_fiches_tarifaires
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue
CODE = "0101000000"


def preparer(root,taux,titre,date):
    root.mkdir()
    source,metadata = fichiers(root)
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"].update(titre=titre,date_publication=date)
    ref = {"source_id":meta["lot"]["source"]["id"],"localisateur":"FIXTURE NON OFFICIELLE mesures"}
    meta["lot"]["mesures"] = [{"id":"M_"+str(i),"code_tarifaire_10":CODE,"type_mesure":"droit",
        "description":"NON OFFICIELLE "+titre,"taux":valeur,"unite_taux":"pourcent" if valeur is not None else None,
        "date_entree_vigueur":date,"reference":ref} for i,valeur in enumerate([taux,None,"0"])]
    metadata.write_text(json.dumps(meta))
    lot = root / "lot"
    preparer_tarif(source,metadata,lot)
    return lot


def test_sources_dates_taux_et_ids_locaux_non_fusionnes(tmp_path):
    a = preparer(tmp_path / "a","1.230000000000000000001","A NON OFFICIELLE","2001-01-01")
    b = preparer(tmp_path / "b","2.5","B NON OFFICIELLE","2000-01-01")
    avant = snapshot(tmp_path)
    rep = juxtaposer_fiches_tarifaires(a,b,CODE)
    assert rep["avant"]["source_declaree"]["titre"] == "A NON OFFICIELLE"
    assert rep["apres"]["source_declaree"]["date_publication"] == "2000-01-01"  # Aucun tri chronologique.
    assert rep["avant"]["mesures_declarees"][0]["taux"] == "1.230000000000000000001"
    assert rep["apres"]["mesures_declarees"][0]["taux"] == "2.5"
    assert rep["avant"]["mesures_declarees"][1]["taux"] is None
    assert rep["avant"]["mesures_declarees"][2]["taux"] == "0"
    assert rep["avant"]["ligne_declaree"]["taux_droits_douane"] is None
    assert rep["archives"]["avant"] != rep["archives"]["apres"] and "archive" not in rep
    assert rep["mesures_fusionnees"] is rep["identites_mesures_rapprochees"] is False
    assert rep["fiscalite_applicable_etablie"] is rep["utilisable_pour_calcul_douanier"] is False
    assert snapshot(tmp_path) == avant


def test_paginations_independantes_absences_et_meme_lot(tmp_path):
    a = preparer(tmp_path / "a","1","A NON OFFICIELLE","2000-01-01")
    b = preparer(tmp_path / "b","2","B NON OFFICIELLE","2001-01-01")
    rep = juxtaposer_fiches_tarifaires(a,b,CODE,1,0,1,1)
    assert rep["avant"]["decalage_mesures_suivant"] == 1 and rep["apres"]["decalage_mesures_suivant"] == 2
    assert rep["avant"]["mesures_declarees"][0]["taux"] == "1" and rep["apres"]["mesures_declarees"][0]["taux"] is None
    assert juxtaposer_fiches_tarifaires(a,b,CODE,1,99)["avant"]["mesures_declarees"] == []
    absent = juxtaposer_fiches_tarifaires(a,b,"9999999999")
    assert absent["avant"]["ligne_trouvee"] is absent["apres"]["ligne_trouvee"] is False
    assert absent["avant"]["ligne_declaree"] is None
    meme = juxtaposer_fiches_tarifaires(a,a,CODE)
    assert meme["archives"]["avant"] == meme["archives"]["apres"]


@pytest.mark.parametrize("kwargs",[{"code10":1010000000},{"code10":"٠١٠١٠٠٠٠٠٠"},{"code10":"101000000"},
    {"code10":"0101000000 "},{"code10":True},{"limite_avant":0},{"limite_avant":True},
    {"limite_apres":101},{"limite_apres":True},{"decalage_avant":-1},{"decalage_apres":1000001},{"decalage_apres":True}])
def test_tous_parametres_avant_les_deux_lectures(tmp_path,kwargs):
    with pytest.raises(ParamFicheTarifInvalide):
        juxtaposer_fiches_tarifaires(tmp_path / "absent",tmp_path / "autre",**{"code10":CODE,**kwargs})


def test_cli(tmp_path,capsys):
    a = preparer(tmp_path / "a","1","A NON OFFICIELLE","2000-01-01")
    b = preparer(tmp_path / "b","2","B NON OFFICIELLE","2001-01-01")
    assert main(["customs-tariff-compare",str(a),str(b),"--code",CODE,"--after-limit","1"]) == 0
    assert json.loads(capsys.readouterr().out)["apres"]["limite_mesures"] == 1


URL = BASE + "/tariff-compare?avant=tarif_a&apres=tarif_b&code10=" + CODE


def test_api_deux_epingles_audit_export_et_panne(revue,monkeypatch):
    from unocr import api
    client,racine,registre,cfg = revue
    avant = snapshot(racine)
    r = client.get(URL,headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert r.json()["resultat"]["lots_exacts"] == {"avant":"tarif_a","apres":"tarif_b"}
    events = [json.loads(ligne) for ligne in (cfg.log_dir / "audit.log").read_text().splitlines()]
    e = [e for e in events if e.get("operation") == "juxtaposition_fiches_tarifaires"][-1]
    assert e["manifestes"].keys() == {"tarif_a","tarif_b"} and CODE not in json.dumps(e)
    export = {"schema_version":"1","type_export":"rapport_revue_documentaire_non_valide","lecture_seule":True,
        "publication_active":False,"validation_juridique":"non_validee","perimetre":"rapport_ou_page_uniquement_pas_corpus_complet",
        "horodatage_client_non_certifie":"2026-11-07T10:00:00.000Z","requete_relative":URL,"resultat":r.json()["resultat"]}
    assert analyser_export(json.dumps(export).encode())["statut"] == "structure_compatible"
    export["resultat"]["archive"] = export["resultat"]["archives"]["avant"]
    with pytest.raises(ExportRefuse):
        analyser_export(json.dumps(export).encode())
    def panne(*a,**kw):
        raise AuditIndisponible("SECRET_TEST")
    monkeypatch.setattr(api,"audit_obligatoire",panne)
    r = client.get(URL,headers=ADMIN)
    assert r.status_code == 503 and "resultat" not in r.json()
    assert snapshot(racine) == avant


@pytest.mark.parametrize("cote",["tarif_a","tarif_b"])
def test_epingle_chaque_cote(revue,cote):
    client,racine,*_ = revue
    p = racine / cote / "manifest.json"
    p.write_bytes(p.read_bytes()+b" ")
    assert client.get(URL,headers=ADMIN).status_code == 409


@pytest.mark.parametrize("query,headers,statut",[
    ("avant=tarif_a&apres=tarif_b",{},401),
    ("avant=tarif_a&apres=tarif_b",{"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403),
    ("avant=tarif_a&apres=ABSENT",ADMIN,404),("avant=tarif_a&apres=code_a",ADMIN,422),
    ("avant=code_a&apres=code_a",ADMIN,422),("avant=tarif_a&apres=tarif_b&after_offset=-1",ADMIN,422),
])
def test_refus_api(revue,query,headers,statut):
    client,*_ = revue
    r = client.get(BASE + "/tariff-compare?code10="+CODE+"&"+query,headers=headers)
    assert r.status_code == statut and "resultat" not in r.json()


def test_code_absent_d_un_seul_cote_et_code_present_sans_mesure(tmp_path):
    a = preparer(tmp_path / "a","1","A NON OFFICIELLE","2000-01-01")
    entree = tmp_path / "b"
    entree.mkdir()
    source,metadata = fichiers(entree)
    lignes = json.loads(source.read_text())
    lignes[0]["code_tarifaire_10"] = "0101000001"
    source.write_text(json.dumps(lignes))
    import hashlib
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    b = entree / "lot"
    preparer_tarif(source,metadata,b)
    rep = juxtaposer_fiches_tarifaires(a,b,CODE)
    assert rep["avant"]["ligne_trouvee"] is True and rep["apres"]["ligne_trouvee"] is False
    assert rep["apres"]["ligne_declaree"] is None and rep["apres"]["mesures_declarees"] == []
    inverse = juxtaposer_fiches_tarifaires(a,b,"0101000001")
    assert inverse["apres"]["ligne_trouvee"] is True and inverse["apres"]["total_mesures_declarees"] == 0
    assert inverse["fiscalite_applicable_etablie"] is False


def test_empreinte_restituee_cote_apres_recontrolee(revue,monkeypatch):
    from unocr.routes import customs_review
    client,*_ = revue
    original = customs_review.juxtaposer_fiches_tarifaires
    def fausser(*a,**kw):
        rep = original(*a,**kw)
        rep["archives"]["apres"]["manifest_sha256"] = "0"*64
        return rep
    monkeypatch.setattr(customs_review,"juxtaposer_fiches_tarifaires",fausser)
    r = client.get(URL,headers=ADMIN)
    assert r.status_code == 409 and "resultat" not in r.json()
