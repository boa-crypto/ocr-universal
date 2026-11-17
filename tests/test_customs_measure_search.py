"""Recherche de mesures de fixtures NON OFFICIELLES, jamais fiscalité applicable."""
import copy
import hashlib
import json

import pytest

from tests import test_customs_review
from tests.test_customs_reference import fichiers, snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.measure_search import TYPES_MESURES, rechercher_mesures_tarif
from unocr.customs_reference.review_export import analyser_export
from unocr.customs_reference.search import ParamRechercheInvalide, rechercher_tarif
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue
CODE = "0101000000"


def preparer(root):
    source,metadata = fichiers(root)
    lignes = json.loads(source.read_text())
    autre = copy.deepcopy(lignes[0])
    autre.update(id="LIGNE_B",code_tarifaire_10="0101000001")
    lignes.append(autre)
    source.write_text(json.dumps(lignes))
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    textes = ["Équipement douanier NON OFFICIEL","مُعَـدَّات اختبار غير رسمية","CAS_COMMUN NON OFFICIEL",
              "RESTRICTION_A_TESTER NON OFFICIEL","CAS_COMMUN NON OFFICIEL","CAS_COMMUN NON OFFICIEL"]
    meta["lot"]["mesures"] = [{"id":"M_"+str(i),"code_tarifaire_10":CODE if i<4 else "0101000001",
        "type_mesure":t,"description":textes[i],"reference":lignes[0]["reference"],
        "taux":["1.230000000000000000001","0"][i] if i<2 else None,"unite_taux":"pourcent" if i<2 else None}
        for i,t in enumerate(TYPES_MESURES)]
    metadata.write_text(json.dumps(meta))
    lot = root / "lot"
    preparer_tarif(source,metadata,lot)
    return lot


def test_recherche_fr_ar_sans_mutation_et_taux_exacts(tmp_path):
    lot = preparer(tmp_path)
    avant = snapshot(lot)
    rep = rechercher_mesures_tarif(lot,"EQUIPEMENT douanier")
    assert rep["total_correspondances"] == 1
    m = rep["resultats"][0]["mesure_declaree"]
    assert m["description"].startswith("Équipement") and m["taux"] == "1.230000000000000000001"
    assert rep["resultats"][0]["champs_correspondants"] == {"equipement":["description"],"douanier":["description"]}
    ar = rechercher_mesures_tarif(lot,"معدات اختبار")
    assert ar["resultats"][0]["mesure_declaree"]["taux"] == "0"
    assert rep["fiscalite_applicable_etablie"] is rep["utilisable_pour_calcul_douanier"] is False
    assert snapshot(lot) == avant


@pytest.mark.parametrize("type_mesure",TYPES_MESURES)
def test_types_exacts_et_requete_vide_filtree(tmp_path,type_mesure):
    lot = preparer(tmp_path)
    rep = rechercher_mesures_tarif(lot,type_mesure=type_mesure)
    assert rep["total_correspondances"] == 1 and rep["termes_normalises"] == []
    assert rep["resultats"][0]["mesure_declaree"]["type_mesure"] == type_mesure


def test_combinaison_code_pagination_et_champs_non_recherches(tmp_path):
    lot = preparer(tmp_path)
    rep = rechercher_mesures_tarif(lot,"CAS COMMUN",limite=1,decalage=1)
    assert rep["total_correspondances"] == 3 and rep["decalage_suivant"] == 2
    assert rep["resultats"][0]["mesure_declaree"]["type_mesure"] == "autorisation"
    assert rechercher_mesures_tarif(lot,"CAS COMMUN",CODE)["total_correspondances"] == 1
    assert rechercher_mesures_tarif(lot,"CAS COMMUN",CODE,"autorisation")["total_correspondances"] == 0
    assert rechercher_mesures_tarif(lot,code10="9999999999")["total_correspondances"] == 0
    assert rechercher_mesures_tarif(lot,"CAS COMMUN",decalage=99)["resultats"] == []
    assert rechercher_mesures_tarif(lot,"1.230000000000000000001")["total_correspondances"] == 0
    assert rechercher_mesures_tarif(lot,"TECHNIQUE")["total_correspondances"] == 0  # Présent seulement dans la ligne.
    assert rechercher_tarif(lot,"RESTRICTION_A_TESTER")["total_correspondances"] == 0
    assert rechercher_mesures_tarif(lot,"RESTRICTION_A_TESTER")["total_correspondances"] == 1


@pytest.mark.parametrize("kwargs",[{"requete":""},{"requete":"!!!"},{"requete":"X"*257},
    {"requete":" ".join(str(i) for i in range(17))},{"requete":"abc\ud800"},{"requete":"A\x00"},
    {"code10":True},{"code10":"010100"},{"code10":"٠١٠١٠٠٠٠٠٠"},{"type_mesure":"similaire"},
    {"type_mesure":True},{"limite":0},{"limite":101},{"limite":True},{"decalage":-1},{"decalage":1000001},{"decalage":True}])
def test_parametres_avant_lecture(tmp_path,kwargs):
    with pytest.raises(ParamRechercheInvalide):
        rechercher_mesures_tarif(tmp_path / "absent",**kwargs)


def test_cli(tmp_path,capsys):
    lot = preparer(tmp_path)
    assert main(["customs-tariff-measure-search",str(lot),"--type","restriction","--code",CODE]) == 0
    assert json.loads(capsys.readouterr().out)["total_correspondances"] == 1


def test_api_audit_export_et_503(revue,monkeypatch):
    from unocr import api
    client,racine,registre,cfg = revue
    avant = snapshot(racine)
    url = BASE + "/lots/tarif_a/measure-search?q=TERME_MESURE_EXCLU&code10="+CODE+"&measure_type=restriction"
    r = client.get(url,headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert r.json()["resultat"]["total_correspondances"] == 1
    events = [json.loads(ligne) for ligne in (cfg.log_dir / "audit.log").read_text().splitlines()]
    e = [e for e in events if e.get("operation") == "recherche_mesures"][-1]
    assert e["manifestes"].keys() == {"tarif_a"} and "TERME_MESURE_EXCLU" not in json.dumps(e)
    export = {"schema_version":"1","type_export":"rapport_revue_documentaire_non_valide","lecture_seule":True,
        "publication_active":False,"validation_juridique":"non_validee","perimetre":"rapport_ou_page_uniquement_pas_corpus_complet",
        "horodatage_client_non_certifie":"2026-11-07T10:00:00.000Z","requete_relative":url,"resultat":r.json()["resultat"]}
    assert analyser_export(json.dumps(export).encode())["statut"] == "structure_compatible"
    def panne(*a,**kw):
        raise AuditIndisponible("SECRET_TEST")
    monkeypatch.setattr(api,"audit_obligatoire",panne)
    r = client.get(url,headers=ADMIN)
    assert r.status_code == 503 and "resultat" not in r.json()
    assert snapshot(racine) == avant


@pytest.mark.parametrize("route,headers,statut",[
    ("tarif_a/measure-search?q=X",{},401),
    ("tarif_a/measure-search?q=X",{"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403),
    ("code_a/measure-search?q=X",ADMIN,422),("tarif_a/measure-search",ADMIN,422),
    ("tarif_a/measure-search?measure_type=inconnu",ADMIN,422),("tarif_a/measure-search?code10=010100",ADMIN,422),
])
def test_refus_api(revue,route,headers,statut):
    client,*_ = revue
    assert client.get(BASE + "/lots/"+route,headers=headers).status_code == statut


def test_types_filtres_synchronises_avec_modele():
    from unocr.customs_reference.models import Mesure
    assert set(TYPES_MESURES) == set(Mesure.model_fields["type_mesure"].annotation.__args__)
