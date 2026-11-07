"""Localisations Unicode dans des libellés NON OFFICIELS ; jamais preuves PDF."""
import json
from types import SimpleNamespace

import pytest

from tests import test_customs_review
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from tests.test_customs_search import lot_tarif
from unocr.cli import main
from unocr.customs_reference.review_export import MARQUEURS, analyser_export
from unocr.customs_reference.search import _normaliser
from unocr.customs_reference.search_excerpt import localiser_termes
from unocr.customs_reference.tariff_criteria import rechercher_tarif_criteres
from unocr.customs_reference.tariff_excerpt import localiser_criteres

revue = test_customs_review.revue


@pytest.mark.parametrize("texte,termes",[
    ("😀 ÉQUIPEMENT en acier",["equipement","acier"]),
    ("😀 مُعَـدَّات اختبار غير رسمية",["معدات","اختبار"]),
    ("œuvré æther Straße ﬃ ¼ ﻻ",["oeuvre","aether","ss","fi","4","لا"]),
    ("e\u0301quipement ＡＢＣ ㍿",["equipement","abc","株式会社"]),
    ("a"+"ـ"*500+"b",["ab"]),
    ("deux UN un deux",["un","deux"]),
    ("a -- b",["a b","b"]),
])
def test_localisation_multiterme_unicode_original(texte,termes):
    spans = localiser_termes(texte,termes)
    assert list(spans) == termes
    for t,(debut,fin) in spans.items():
        assert t in _normaliser(texte[debut:fin])
        assert debut >= 0 and fin <= len(texte)
    ligne = SimpleNamespace(designation_officielle_fr=texte,designation_officielle_ar=None)
    rep = localiser_criteres(ligne,{"designation":{t:["designation_officielle_fr"] for t in termes}})
    for ex in rep["extraits_correspondants"]:
        assert ex["fragment"] == texte[ex["decalage"]:ex["decalage"]+len(ex["fragment"])]
        assert len(ex["fragment"]) <= 384
        assert ex["unite_decalage"] == "points_de_code_unicode_python"
    if len(texte)>500:
        assert rep["extraits_correspondants"][0]["correspondance_entierement_visible"] is False


def test_vide_absent_et_premiere_occurrence_pas_denombrement():
    assert localiser_termes("texte",[]) == localiser_termes("texte",["absent",""]) == {}
    assert localiser_termes("un un UN",["un"]) == {"un":(0,2)}


def test_tous_criteres_et_langues_localises_extraits_bornes():
    mots = ['mot'+str(i)+'x' for i in range(16)]
    texte = ' '.join(mots)
    ligne = SimpleNamespace(designation_officielle_fr=texte,designation_officielle_ar=texte)
    preuves = {critere:{t:["designation_officielle_ar","designation_officielle_fr"] for t in mots}
               for critere in ("designation","matiere","fonction","usage","caracteristiques")}
    rep = localiser_criteres(ligne,preuves)
    assert rep["total_extraits_disponibles"] == 160
    assert len(rep["extraits_correspondants"]) == 16 and rep["extraits_tronques"] is True
    assert rep["positions_par_critere"].keys() == preuves.keys()
    assert all(len(spans)==2 for mots in rep["positions_par_critere"].values() for spans in mots.values())
    assert localiser_criteres(ligne,{}) == {"positions_par_critere":{},"extraits_correspondants":[],
                                          "total_extraits_disponibles":0,"extraits_tronques":False}


def test_service_preuves_croisees_fr_ar_et_prefixe_seul(tmp_path):
    lot = lot_tarif(tmp_path)
    avant = snapshot(tmp_path)
    rep = rechercher_tarif_criteres(lot,designation="ÉQUIPEMENT",fonction="معدات اختبار",matiere="mécanique")
    assert rep["occurrences_denombrees"] is False and rep["maximum_extraits_par_ligne"] == 16
    r = rep["resultats"][0]
    for critere,mots in r["positions_par_critere"].items():
        for t,spans in mots.items():
            assert [s["champ_texte"] for s in spans] == r["correspondances_par_critere"][critere][t]
            for s in spans:
                texte = r["ligne"][s["champ_texte"]]
                assert t in _normaliser(texte[s["correspondance_debut"]:s["correspondance_fin"]])
    assert rechercher_tarif_criteres(lot,code_prefix="0101")["resultats"][0]["extraits_correspondants"] == []
    assert snapshot(tmp_path) == avant


def test_extraits_produits_seulement_pour_page_retenue(tmp_path,monkeypatch):
    from unocr.customs_reference import tariff_criteria
    lot = lot_tarif(tmp_path)
    origine = tariff_criteria.localiser_criteres
    appels = []
    def compter(ligne,preuves,match_mode="sous_chaine"):
        appels.append(ligne.code_tarifaire_10)
        return origine(ligne,preuves,match_mode)
    monkeypatch.setattr(tariff_criteria,"localiser_criteres",compter)
    rep = rechercher_tarif_criteres(lot,designation="équipement",limite=1,decalage=1)
    assert appels == [rep["resultats"][0]["ligne"]["code_tarifaire_10"]]
    rechercher_tarif_criteres(lot,designation="équipement",decalage=999)
    assert len(appels) == 1


def test_cli_conserve_positions_originales(tmp_path,capsys):
    lot = lot_tarif(tmp_path)
    assert main(["customs-tariff-criteria",str(lot),"--designation","معدات"]) == 0
    r = json.loads(capsys.readouterr().out)["resultats"][0]
    assert r["positions_par_critere"]["designation"]["معدات"][0]["champ_texte"] == "designation_officielle_ar"


def test_api_export_localisations_et_audit(revue):
    client,racine,registre,cfg = revue
    avant = snapshot(racine)
    route = BASE+"/lots/tarif_a/tariff-criteria?designation=معدات&fonction=mecanique"
    r = client.get(route,headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    rep = r.json()["resultat"]
    assert len(rep["resultats"][0]["extraits_correspondants"]) == 2
    exp = {**MARQUEURS,"horodatage_client_non_certifie":"2026-11-07T00:00:00.000Z","requete_relative":route,"resultat":rep}
    assert analyser_export(json.dumps(exp).encode())["statut"] == "structure_compatible"
    events = [json.loads(v) for v in (cfg.log_dir / "audit.log").read_text().splitlines()]
    assert [e for e in events if e.get("operation")=="recherche_tarif_criteres"][-1]["statut"] == 200
    assert snapshot(racine) == avant
