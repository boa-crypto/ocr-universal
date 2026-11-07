"""Revue réelle de mesures NON OFFICIELLES ; aucun rattachement fiscal établi."""
import hashlib
import json

import pytest

from tests import test_customs_review
from tests.test_customs_fiscal_import import fichiers
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.coverage import diagnostiquer_couverture
from unocr.customs_reference.fiscal_importer import preparer_mesures_autonomes
from unocr.customs_reference.measure_search import rechercher_mesures_tarif
from unocr.customs_reference.review_registry import RegistreRevue
from unocr.customs_reference.source_catalog import inventorier_sources
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue


@pytest.fixture()
def fiscal(revue):
    client,racine,registre,cfg = revue
    entrees = cfg.root / "entrees_mesures"
    entrees.mkdir()
    source,metadata = fichiers(entrees)
    lot = racine / "mesures_a"
    preparer_mesures_autonomes(source,metadata,lot)
    reg = json.loads(registre.read_text())
    reg["lots"].append({"id":"mesures_a","dossier":"mesures_a","type_lot":"mesures",
                        "manifest_sha256":hashlib.sha256((lot / "manifest.json").read_bytes()).hexdigest()})
    registre.write_text(json.dumps(reg))
    return revue


def test_registre_et_quatre_operations_autorisees_sans_mutation(fiscal):
    client,racine,registre,cfg = fiscal
    avant = snapshot(racine)
    assert RegistreRevue.model_validate_json(registre.read_text()).lots[-1].type_lot == "mesures"
    assert client.get(BASE+"/lots",headers=ADMIN).json()["resultat"]["lots"][-1]["type_lot"] == "mesures"
    controle = client.get(BASE+"/lots/mesures_a/check",headers=ADMIN)
    assert controle.status_code == 200 and controle.json()["resultat"]["mesures_importables"] == 6
    r = client.get(BASE+"/lots/mesures_a/measure-search?q=معدات&code10=0000000001",headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    rep = r.json()["resultat"]
    assert rep["type_recherche"] == "mesures_autonomes_documentaires" and rep["total_correspondances"] == 3
    assert all(v["ligne_declaree"] is None for v in rep["resultats"])
    assert rep["existence_codes_dans_nomenclature"] == "non_verifiee"
    assert rep["resultats"][0]["mesure_declaree"]["taux"] == "1.230000000000000000000000001"
    assert rep["resultats"][1]["mesure_declaree"]["taux"] == "0"
    src = client.get(BASE+"/lots/mesures_a/sources",headers=ADMIN).json()["resultat"]
    assert src["type_lot"] == "mesures" and src["resultats"][0]["compteurs_lot"] == {"mesures":6}
    couverture = client.get(BASE+"/lots/mesures_a/coverage",headers=ADMIN).json()["resultat"]
    assert couverture["indicateurs"]["compteurs"]["codes10_declares_distincts"] == 2
    assert couverture["pourcentage_completude_reglementaire"] is None
    assert couverture["indicateurs"]["nomenclature_incluse"] is False
    assert snapshot(racine) == avant


def test_service_pagination_cli_sources_et_couverture(fiscal,capsys):
    _,racine,*_ = fiscal
    lot = racine / "mesures_a"
    rep = rechercher_mesures_tarif(lot,"equipement",limite=1,decalage=1,type_lot="mesures")
    assert rep["total_correspondances"] == 6 and rep["decalage_suivant"] == 2
    assert rep["resultats"][0]["mesure_declaree"]["id"] == "M_1"
    assert rechercher_mesures_tarif(lot,code10="1234567890",type_lot="mesures")["resultats"] == []
    assert main(["customs-fiscal-search",str(lot),"--type","restriction"]) == 0
    assert json.loads(capsys.readouterr().out)["total_correspondances"] == 1
    assert main(["customs-sources",str(lot),"--type","mesures"]) == 0
    assert json.loads(capsys.readouterr().out)["type_lot"] == "mesures"
    assert main(["customs-coverage",str(lot),"--type","mesures"]) == 0
    assert json.loads(capsys.readouterr().out)["type_lot"] == "mesures"
    assert inventorier_sources(lot,"mesures")["total_sources_lot"] == 1
    assert diagnostiquer_couverture(lot,"mesures")["indicateurs"]["mesures_champs_non_renseignes"]["taux"] == 4


@pytest.mark.parametrize("route",[
    "/lots/mesures_a/search?q=a","/lots/mesures_a/history?article=1","/lots/mesures_a/tariff/0000000001",
    "/lots/mesures_a/tree","/lots/mesures_a/article?article_id=A","/lots/mesures_a/article-diff?avant_id=A&apres_id=B",
    "/lots/mesures_a/article-pdf-match?article_id=A&page=1","/lots/mesures_a/article-relations?article_id=A",
    "/lots/mesures_a/relation-pdf-match?relation_id=R&page=1","/lots/mesures_a/code-tree",
    "/lots/mesures_a/pdf?document_id=D","/lots/mesures_a/pdf-source?document_id=D",
    "/diff?avant=mesures_a&apres=mesures_a","/diff?avant=mesures_a&apres=tarif_a",
    "/tariff-compare?avant=mesures_a&apres=mesures_a&code10=0000000001",
    "/article-diff?avant=mesures_a&apres=mesures_a&avant_id=A&apres_id=B"])
def test_operations_incompatibles_refusees_avant_chargeur(fiscal,monkeypatch,route):
    import unocr.routes.customs_review as module
    client,*_ = fiscal
    def interdit(*a,**kw):
        raise AssertionError("Chargeur incompatible appelé")
    monkeypatch.setattr(module,"charger_lot",interdit)
    monkeypatch.setattr(module,"charger_lot_code",interdit)
    r = client.get(BASE+route,headers=ADMIN)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "operation_non_applicable_aux_mesures_autonomes"
    assert "resultat" not in r.json()


@pytest.mark.parametrize("route",["check","coverage","sources","measure-search?measure_type=tva"])
def test_audit_obligatoire_et_503(fiscal,monkeypatch,route):
    from unocr import api
    client,racine,registre,cfg = fiscal
    url = BASE+"/lots/mesures_a/"+route
    r = client.get(url,headers=ADMIN)
    assert r.status_code == 200
    events = [json.loads(v) for v in (cfg.log_dir / "audit.log").read_text().splitlines()]
    assert events[-1]["manifestes"].keys() == {"mesures_a"}
    def panne(*a,**kw):
        raise AuditIndisponible("SECRET_TEST")
    monkeypatch.setattr(api,"audit_obligatoire",panne)
    r = client.get(url,headers=ADMIN)
    assert r.status_code == 503 and "resultat" not in r.json() and "SECRET_TEST" not in r.text


@pytest.mark.parametrize("route,headers,statut",[("check",{},401),
    ("check",{"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403),
    ("sources?nature_document=compilation",ADMIN,422),("measure-search?code10=000001",ADMIN,422),
    ("measure-search?measure_type=inconnu",ADMIN,422),("measure-search",ADMIN,422)])
def test_droits_et_parametres(fiscal,route,headers,statut):
    client,*_ = fiscal
    assert client.get(BASE+"/lots/mesures_a/"+route,headers=headers).status_code == statut


@pytest.mark.parametrize("moment",["avant","resultat"])
def test_epingle_et_resultat_recontroles(fiscal,monkeypatch,moment):
    import unocr.routes.customs_review as module
    client,racine,*_ = fiscal
    if moment == "avant":
        p = racine / "mesures_a/manifest.json"
        p.write_bytes(p.read_bytes()+b" ")
    else:
        original = module.rechercher_mesures_tarif
        def modifier(*a,**kw):
            rep = original(*a,**kw)
            rep["archive"]["manifest_sha256"] = "0"*64
            return rep
        monkeypatch.setattr(module,"rechercher_mesures_tarif",modifier)
    r = client.get(BASE+"/lots/mesures_a/measure-search?measure_type=tva",headers=ADMIN)
    assert r.status_code == 409 and "resultat" not in r.json()
