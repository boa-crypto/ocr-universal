"""Critères explicites sur fixtures NON OFFICIELLES, sans attribut technique inféré."""
import json

import pytest

from tests import test_customs_review
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from tests.test_customs_search import lot_tarif
from unocr.cli import main
from unocr.customs_reference.review_export import MARQUEURS, analyser_export
from unocr.customs_reference.search import ParamRechercheInvalide
from unocr.customs_reference.tariff_criteria import rechercher_tarif_criteres
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue


def test_conjonction_fr_ar_et_preuves_par_critere_sans_attribut_invente(tmp_path):
    lot = lot_tarif(tmp_path)
    avant = snapshot(tmp_path)
    rep = rechercher_tarif_criteres(lot,designation="EQUIPEMENT",matiere="mécanique",fonction="معدات",usage="اختبار",caracteristiques="NON OFFICIEL",code_prefix="0101")
    assert rep["total_correspondances"] == 1
    resultat = rep["resultats"][0]
    assert resultat["ligne"]["code_tarifaire_10"] == "0101000000"
    assert resultat["ligne"]["designation_officielle_ar"] == "مُعَـدَّات اختبار غير رسمية"
    assert resultat["correspondances_par_critere"]["matiere"]["mecanique"] == ["designation_officielle_fr"]
    assert resultat["correspondances_par_critere"]["fonction"]["معدات"] == ["designation_officielle_ar"]
    assert rep["attributs_techniques_certifies"] is rep["classement_ia_effectue"] is rep["taux_calcules"] is False
    assert snapshot(tmp_path) == avant


def test_pas_synonymes_traduction_mesures_ou_criteres_distribues_entre_lignes(tmp_path):
    lot = lot_tarif(tmp_path)
    for criteres in ({"matiere":"acier"},{"designation":"pompe","usage":"مضخة"},{"designation":"TERME_MESURE_EXCLU"}):
        assert rechercher_tarif_criteres(lot,**criteres)["total_correspondances"] == 0


def test_pagination_prefixe_syntaxique_et_filtres_stables(tmp_path):
    lot = lot_tarif(tmp_path)
    a = rechercher_tarif_criteres(lot,designation="équipement",limite=1)
    b = rechercher_tarif_criteres(lot,designation="équipement",limite=1,decalage=a["decalage_suivant"])
    assert a["total_correspondances"] == 2 and a["filtres"] == b["filtres"]
    assert a["resultats"][0]["ligne"]["code_tarifaire_10"] != b["resultats"][0]["ligne"]["code_tarifaire_10"]
    assert b["decalage_suivant"] is None
    assert rechercher_tarif_criteres(lot,code_prefix="010100000",decalage=99)["resultats"] == []
    assert rechercher_tarif_criteres(lot,code_prefix="0101000004")["total_correspondances"] == 1


@pytest.mark.parametrize("kwargs",[{}, {"designation":""},{"matiere":" "},{"fonction":True},{"usage":"!"},
    {"caracteristiques":"x"*257},{"designation":"x\x00"},{"designation":"x\ud800"},{"usage":" ".join('m'+str(i) for i in range(17))},
    {"code_prefix":"١٢"},{"code_prefix":"1e3"},{"code_prefix":1},{"code_prefix":" "},{"code_prefix":"0"*11},
    {"code_prefix":"0","limite":True},{"designation":"x","limite":0},{"designation":"x","decalage":-1}])
def test_parametres_avant_lecture(tmp_path,kwargs):
    with pytest.raises(ParamRechercheInvalide):
        rechercher_tarif_criteres(tmp_path / "ABSENT",**kwargs)


def test_cli_recherche_et_refus(tmp_path,capsys):
    lot = lot_tarif(tmp_path)
    assert main(["customs-tariff-criteria",str(lot),"--designation","équipement","--fonction","mécanique"]) == 0
    assert json.loads(capsys.readouterr().out)["total_correspondances"] == 1
    assert main(["customs-tariff-criteria",str(lot)]) == 2
    capsys.readouterr()


def test_api_audit_export_et_lecture_seule(revue):
    client,racine,registre,cfg = revue
    avant = snapshot(racine)
    route = BASE+"/lots/tarif_a/tariff-criteria?code_prefix=0101&limit=1"
    r = client.get(route,headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    rep = r.json()["resultat"]
    exp = {**MARQUEURS,"horodatage_client_non_certifie":"2026-11-07T00:00:00.000Z","requete_relative":route,"resultat":rep}
    assert analyser_export(json.dumps(exp).encode())["statut"] == "structure_compatible"
    events = [json.loads(v) for v in (cfg.log_dir / "audit.log").read_text().splitlines()]
    assert [e for e in events if e.get("operation")=="recherche_tarif_criteres"][-1]["statut"] == 200
    assert snapshot(racine) == avant


@pytest.mark.parametrize("route,headers,code",[("/lots/tarif_a/tariff-criteria?usage=acier",{},401),
    ("/lots/tarif_a/tariff-criteria?usage=acier",{"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403),
    ("/lots/code_a/tariff-criteria?usage=acier",ADMIN,422),("/lots/tarif_a/tariff-criteria",ADMIN,422),
    ("/lots/tarif_a/tariff-criteria?code_prefix=1e3",ADMIN,422)])
def test_refus_api(revue,route,headers,code):
    client,*_ = revue
    r = client.get(BASE+route,headers=headers)
    assert r.status_code == code and "resultat" not in r.json()


def test_api_audit_obligatoire_et_provenance_epinglee(revue,monkeypatch):
    from unocr import api
    from unocr.routes import customs_review

    client,*_ = revue
    route = BASE+"/lots/tarif_a/tariff-criteria?code_prefix=0101"
    def panne(*a,**kw):
        raise AuditIndisponible("SECRET_TEST")
    with monkeypatch.context() as m:
        m.setattr(api,"audit_obligatoire",panne)
        r = client.get(route,headers=ADMIN)
        assert r.status_code == 503 and "resultat" not in r.json()
    origine = customs_review.rechercher_tarif_criteres
    def changer(*a,**kw):
        rep = origine(*a,**kw)
        rep["archive"]["manifest_sha256"] = "f"*64
        return rep
    monkeypatch.setattr(customs_review,"rechercher_tarif_criteres",changer)
    r = client.get(route,headers=ADMIN)
    assert r.status_code == 409 and "resultat" not in r.json()
