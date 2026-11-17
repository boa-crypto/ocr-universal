"""Relations de versions NON OFFICIELLES, sans inférence ou validation juridique."""
import json

import pytest

from tests import test_customs_review
from tests.test_customs_legal import fichiers_code
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.article_relations import (
    ParamRelationsArticleInvalide,
    consulter_relations_article,
)
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.review_export import analyser_export
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue


def preparer(root):
    t,m = fichiers_code(root)
    donnees = json.loads(t.read_text())
    for identifiant,origine,cible,source in [("A","TEST_O_A","TEST_C_A","TEST_O"),
                                             ("B","TEST_C_A","TEST_O_A","TEST_C"),
                                             ("C","TEST_M_A","TEST_C_A","TEST_M")]:
        donnees["relations"].append({"id":identifiant,"origine_id":origine,"cible_id":cible,"type_relation":"renvoie_a",
            "justification":"FIXTURE NON OFFICIELLE <b>justification</b>",
            "reference":{"source_id":source,"localisateur":"FIXTURE page 9 imprimée, pas page physique"}})
    t.write_text(json.dumps(donnees))
    lot = root / "lot"
    preparer_code(t,m,lot)
    return lot


def test_version_exacte_un_saut_sources_et_aucune_mutation(tmp_path):
    lot = preparer(tmp_path)
    avant = snapshot(lot)
    rep = consulter_relations_article(lot,"TEST_O_A")
    assert [v["relation_declaree"]["id"] for v in rep["relations_declarees"]] == ["A","B","TEST_RELATION"]
    assert rep["totaux_incidents_par_sens"] == {"entrantes":2,"sortantes":1}
    assert rep["total_relations_incidentes"] == rep["total_relations_filtrees"] == 3
    assert {d["id"] for d in rep["documents_declares_page"]} == {"TEST_O","TEST_M","TEST_C"}
    assert rep["relations_declarees"][0]["sens_par_rapport_a_version"] == "sortante"
    assert rep["relations_declarees"][0]["autre_version_declaree"]["id"] == "TEST_C_A"
    assert "texte_integral" not in rep["relations_declarees"][0]["autre_version_declaree"]
    assert rep["preuve_rapprochee_pdf"] is False and rep["relation_juridique_etablie"] is False
    # C et O portent le même numéro : cela n'élargit pas la sélection O à la relation C (M→C).
    assert rep["version_declaree"]["numero_article"] == "5 bis" and snapshot(lot) == avant


@pytest.mark.parametrize("sens,type_relation,ids", [
    ("tous",None,["A","B","TEST_RELATION"]), ("entrantes",None,["B","TEST_RELATION"]),
    ("sortantes",None,["A"]), ("entrantes","modifie",["TEST_RELATION"]),
    ("tous","renvoie_a",["A","B"]), ("sortantes","abroge",[]),
])
def test_filtres_declares(tmp_path,sens,type_relation,ids):
    lot = preparer(tmp_path)
    rep = consulter_relations_article(lot,"TEST_O_A",sens,type_relation)
    assert [v["relation_declaree"]["id"] for v in rep["relations_declarees"]] == ids
    assert rep["total_relations_incidentes"] == 3 and rep["total_relations_filtrees"] == len(ids)


def test_pagination_sources_limitees_page_et_inconnu(tmp_path):
    lot = preparer(tmp_path)
    rep = consulter_relations_article(lot,"TEST_O_A",limite=1,decalage=1)
    assert rep["decalage_suivant"] == 2 and rep["relations_declarees"][0]["relation_declaree"]["id"] == "B"
    assert {d["id"] for d in rep["documents_declares_page"]} == {"TEST_O","TEST_C"}
    assert consulter_relations_article(lot,"TEST_O_A",decalage=3)["decalage_suivant"] is None
    absent = consulter_relations_article(lot,"ABSENT")
    assert absent["article_trouve"] is False and absent["documents_declares_page"] == []
    assert absent["total_relations_incidentes"] == 0


@pytest.mark.parametrize("kwargs", [{"article_id":""},{"article_id":True},{"article_id":"A\n"},
    {"article_id":"x"*257},{"article_id":"\ud800"},{"sens":"entrant"},{"sens":True},
    {"type_relation":"similaire"},{"type_relation":True},{"limite":0},{"limite":101},{"limite":True},
    {"decalage":-1},{"decalage":True},{"decalage":1000001}])
def test_parametres_avant_lecture(tmp_path,kwargs):
    with pytest.raises(ParamRelationsArticleInvalide):
        consulter_relations_article(tmp_path / "absent",**{"article_id":"A",**kwargs})


def test_cli(tmp_path,capsys):
    lot = preparer(tmp_path)
    assert main(["customs-code-article-relations",str(lot),"--id","TEST_O_A","--direction","entrantes","--relation-type","modifie"]) == 0
    assert json.loads(capsys.readouterr().out)["total_relations_filtrees"] == 1


def test_api_epingle_audit_export_et_panne(revue,monkeypatch):
    from unocr import api
    client,racine,registre,cfg = revue
    avant = snapshot(racine)
    url = BASE + "/lots/code_a/article-relations?article_id=TEST_O_A&direction=entrantes&relation_type=modifie"
    rep = client.get(url,headers=ADMIN)
    assert rep.status_code == 200 and rep.headers["cache-control"] == "no-store"
    assert rep.json()["resultat"]["total_relations_filtrees"] == 1
    events = [json.loads(ligne) for ligne in (cfg.log_dir / "audit.log").read_text().splitlines()]
    e = [e for e in events if e.get("operation") == "relations_article"][-1]
    assert e["manifestes"].keys() == {"code_a"} and "TEST_O_A" not in json.dumps(e)
    export = {"schema_version":"1","type_export":"rapport_revue_documentaire_non_valide","lecture_seule":True,
        "publication_active":False,"validation_juridique":"non_validee","perimetre":"rapport_ou_page_uniquement_pas_corpus_complet",
        "horodatage_client_non_certifie":"2026-11-07T10:00:00.000Z","requete_relative":url,"resultat":rep.json()["resultat"]}
    assert analyser_export(json.dumps(export).encode())["statut"] == "structure_compatible"
    def panne(*a,**kw):
        raise AuditIndisponible("SECRET_TEST")
    monkeypatch.setattr(api,"audit_obligatoire",panne)
    refus = client.get(url,headers=ADMIN)
    assert refus.status_code == 503 and "resultat" not in refus.json()
    assert snapshot(racine) == avant


@pytest.mark.parametrize("route,headers,statut", [
    ("code_a/article-relations?article_id=TEST_O_A",{},401),
    ("code_a/article-relations?article_id=TEST_O_A",{"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403),
    ("tarif_a/article-relations?article_id=TEST_O_A",ADMIN,422),
    ("code_a/article-relations?article_id=TEST_O_A&direction=inconnu",ADMIN,422),
    ("code_a/article-relations?article_id=TEST_O_A&relation_type=inconnu",ADMIN,422),
])
def test_refus_api(revue,route,headers,statut):
    client,*_ = revue
    assert client.get(BASE + "/lots/"+route,headers=headers).status_code == statut


@pytest.mark.parametrize("type_relation",["modifie","complete","abroge","rectifie","renvoie_a"])
def test_cinq_types_restent_declares_non_valides(tmp_path,type_relation):
    t,m = fichiers_code(tmp_path)
    donnees = json.loads(t.read_text())
    donnees["relations"][0]["type_relation"] = type_relation
    t.write_text(json.dumps(donnees))
    lot = tmp_path / "lot"
    preparer_code(t,m,lot)
    rep = consulter_relations_article(lot,"TEST_O_A",type_relation=type_relation)
    assert rep["total_relations_filtrees"] == 1
    assert rep["relations_declarees"][0]["relation_declaree"]["validation_juridique"] == "non_validee"
    assert rep["relation_juridique_etablie"] is False
    sans_lien = consulter_relations_article(lot,"TEST_C_A")
    assert sans_lien["article_trouve"] is True and sans_lien["total_relations_incidentes"] == 0


def test_filtres_synchronises_avec_contrat_metier():
    from unocr.customs_reference.article_relations import TYPES_RELATIONS
    from unocr.customs_reference.legal_models import RelationJuridique
    assert set(TYPES_RELATIONS) == set(RelationJuridique.model_fields["type_relation"].annotation.__args__)
