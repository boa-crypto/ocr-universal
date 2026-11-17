"""Deux archives NON OFFICIELLES, IDs locaux et aucune relation juridique déduite."""
import hashlib
import json

import pytest

from tests import test_customs_review
from tests.test_customs_legal import fichiers_code
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.article_diff import ParamDiffArticleInvalide, comparer_versions_article
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.review_export import ExportRefuse, analyser_export
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue


def preparer(root, texte, titre):
    root.mkdir()
    t,m = fichiers_code(root)
    brut = json.loads(t.read_text())
    brut["articles"][0]["texte_integral"] = texte
    t.write_text(json.dumps(brut))
    meta = json.loads(m.read_text())
    meta["documents"][0]["document"]["titre"] = titre
    m.write_text(json.dumps(meta))
    sortie = root / "lot"
    preparer_code(t,m,sortie)
    return sortie


@pytest.mark.parametrize("a,b,prefixe,suffixe,ma,mb", [
    ("ABC","AXC",1,1,"B","X"), ("ABC","ABC",3,0,"",""),
    ("ABC","ABCD",3,0,"","D"), ("ABCD","ABC",3,0,"D",""),
    ("أ😀X!","أ😀Y!",2,1,"X","Y"), ("é","é",0,0,"é","é"),
])
def test_ids_identiques_isoles_et_sources_preservees(tmp_path,a,b,prefixe,suffixe,ma,mb):
    avant = preparer(tmp_path / "avant",a,"SOURCE A NON OFFICIELLE")
    apres = preparer(tmp_path / "apres",b,"SOURCE B NON OFFICIELLE")
    empreintes = snapshot(tmp_path)
    rep = comparer_versions_article(avant,"TEST_O_A","TEST_O_A",repertoire_apres=apres)
    assert "archive" not in rep and rep["archives"]["avant"] != rep["archives"]["apres"]
    assert rep["avant"]["document_declare"]["titre"] == "SOURCE A NON OFFICIELLE"
    assert rep["apres"]["document_declare"]["titre"] == "SOURCE B NON OFFICIELLE"
    assert rep["prefixe_commun_caracteres"] == prefixe and rep["suffixe_commun_caracteres"] == suffixe
    assert rep["avant"]["fragment_bloc_different"] == ma and rep["apres"]["fragment_bloc_different"] == mb
    assert rep["relation_juridique_etablie"] is False and rep["relations_inter_lots_etablies"] is False
    assert rep["relations_directes_declarees"] == [] and snapshot(tmp_path) == empreintes


def test_pagination_absences_et_aucune_relation_traversee(tmp_path):
    a = preparer(tmp_path / "a","ABCDEF","A NON OFFICIELLE")
    b = preparer(tmp_path / "b","uvwxyz","B NON OFFICIELLE")
    rep = comparer_versions_article(a,"TEST_O_A","TEST_O_A",limite=2,decalage_avant=1,decalage_apres=3,repertoire_apres=b)
    assert rep["avant"]["fragment_bloc_different"] == "BC" and rep["apres"]["fragment_bloc_different"] == "xy"
    assert rep["avant"]["decalage_suivant"] == 3 and rep["apres"]["decalage_suivant"] == 5
    absent = comparer_versions_article(a,"TEST_O_A","TEST_M_A","texte_arabe",repertoire_apres=b)
    assert absent["textes_identiques"] is None and absent["champs_comparables"] is False
    assert absent["relations_directes_declarees"] == []  # La relation locale O/M n'est pas inter-lots.
    assert comparer_versions_article(a,"TEST_O_A","ABSENT",repertoire_apres=b)["apres"]["article_trouve"] is False
    meme = comparer_versions_article(a,"TEST_O_A","TEST_O_A",repertoire_apres=a)
    assert meme["textes_identiques"] is True and "archives" in meme


def test_validation_avant_les_deux_lectures_et_cli(tmp_path,capsys):
    with pytest.raises(ParamDiffArticleInvalide):
        comparer_versions_article(tmp_path / "absent","A","B",limite=True,repertoire_apres=tmp_path / "autre")
    a = preparer(tmp_path / "a","ABC","A NON OFFICIELLE")
    b = preparer(tmp_path / "b","AXC","B NON OFFICIELLE")
    assert main(["customs-code-article-diff",str(a),"--after-lot",str(b),"--before-id","TEST_O_A","--after-id","TEST_O_A"]) == 0
    assert "archives" in json.loads(capsys.readouterr().out)
    assert main(["customs-code-article-diff",str(a),"--after-lot",str(tmp_path / "absent"),"--before-id","TEST_O_A","--after-id","TEST_O_A"]) == 2


@pytest.fixture()
def deux_codes(revue):
    client,racine,registre,cfg = revue
    lot = preparer(cfg.root / "code_b_entrees","VERSION B NON OFFICIELLE","SOURCE B NON OFFICIELLE")
    # Répertoire neuf, aucune archive existante modifiée.
    import shutil
    shutil.copytree(lot,racine / "code_b")
    reg = json.loads(registre.read_text())
    reg["lots"].append({"id":"code_b","dossier":"code_b","type_lot":"code",
                        "manifest_sha256":hashlib.sha256((lot / "manifest.json").read_bytes()).hexdigest()})
    registre.write_text(json.dumps(reg))
    return client,racine,registre,cfg


URL = BASE + "/article-diff?avant=code_a&apres=code_b&avant_id=TEST_O_A&apres_id=TEST_O_A"


def test_api_deux_epingles_audit_et_export(deux_codes,monkeypatch):
    from unocr import api
    client,racine,registre,cfg = deux_codes
    avant = snapshot(racine)
    reponse = client.get(URL,headers=ADMIN)
    assert reponse.status_code == 200 and reponse.headers["cache-control"] == "no-store"
    rep = reponse.json()["resultat"]
    assert rep["lots_exacts"] == {"avant":"code_a","apres":"code_b"}
    assert rep["apres"]["document_declare"]["titre"] == "SOURCE B NON OFFICIELLE"
    events = [json.loads(ligne) for ligne in (cfg.log_dir / "audit.log").read_text().splitlines()]
    succes = [e for e in events if e.get("operation") == "diff_articles_inter_lots"][-1]
    assert succes["manifestes"].keys() == {"code_a","code_b"} and "TEST_O_A" not in json.dumps(succes)
    enveloppe = {"schema_version":"1","type_export":"rapport_revue_documentaire_non_valide","lecture_seule":True,
        "publication_active":False,"validation_juridique":"non_validee","perimetre":"rapport_ou_page_uniquement_pas_corpus_complet",
        "horodatage_client_non_certifie":"2026-11-07T10:00:00.000Z","requete_relative":URL,"resultat":rep}
    assert analyser_export(json.dumps(enveloppe).encode())["statut"] == "structure_compatible"
    enveloppe["resultat"] = {**rep,"archive":rep["archives"]["avant"]}
    with pytest.raises(ExportRefuse):
        analyser_export(json.dumps(enveloppe).encode())
    def panne(*a,**kw):
        raise AuditIndisponible("SECRET_TEST")
    monkeypatch.setattr(api,"audit_obligatoire",panne)
    refuse = client.get(URL,headers=ADMIN)
    assert refuse.status_code == 503 and "resultat" not in refuse.json()
    assert snapshot(racine) == avant


@pytest.mark.parametrize("cote",["code_a","code_b"])
def test_chaque_manifeste_epingle_est_verifie(deux_codes,cote):
    client,racine,registre,cfg = deux_codes
    manifeste = racine / cote / "manifest.json"
    manifeste.write_bytes(manifeste.read_bytes()+b" ")
    assert client.get(URL,headers=ADMIN).status_code == 409


def test_empreinte_du_resultat_second_lot_recontrolee(deux_codes,monkeypatch):
    from unocr.routes import customs_review
    client,*_ = deux_codes
    original = customs_review.comparer_versions_article
    def fausser(*a,**kw):
        rep = original(*a,**kw)
        rep["archives"]["apres"]["manifest_sha256"] = "0"*64
        return rep
    monkeypatch.setattr(customs_review,"comparer_versions_article",fausser)
    assert client.get(URL,headers=ADMIN).status_code == 409


@pytest.mark.parametrize("query,headers,statut", [
    ("avant=code_a&apres=code_b",{},401),
    ("avant=code_a&apres=code_b",{"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403),
    ("avant=code_a&apres=ABSENT",ADMIN,404), ("avant=code_a&apres=tarif_a",ADMIN,422),
    ("avant=tarif_a&apres=tarif_b",ADMIN,422), ("avant=code_a&apres=code_b&field=INVALIDE",ADMIN,422),
    ("avant=code_a&apres=code_b&offset_apres=-1",ADMIN,422),
])
def test_refus_api(deux_codes,query,headers,statut):
    client,*_ = deux_codes
    rep = client.get(BASE + "/article-diff?avant_id=TEST_O_A&apres_id=TEST_O_A&"+query,headers=headers)
    assert rep.status_code == statut and "resultat" not in rep.json()
