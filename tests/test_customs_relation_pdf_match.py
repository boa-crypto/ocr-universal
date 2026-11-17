"""Justifications de fixtures NON OFFICIELLES ; aucun lien juridique validé."""
import json
from types import SimpleNamespace

import pytest

from tests import test_customs_pdf_page, test_customs_review
from tests.test_customs_pdf_page import preparer_pdf
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.pdf_page import LecturePDFRefusee
from unocr.customs_reference.relation_pdf_match import (
    ParamJustificationPDFInvalide,
    rapprocher_justification_pdf,
)
from unocr.customs_reference.review_export import analyser_export
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue
revue_pdf = test_customs_pdf_page.revue_pdf


def test_presence_absence_source_origine_et_aucune_mutation(tmp_path):
    lot = preparer_pdf(tmp_path / "entrees",tmp_path / "lot")
    avant = snapshot(lot)
    rep = rapprocher_justification_pdf(lot,"TEST_RELATION",1,7)
    assert rep["fragment_justification"] == "FIXTURE" and rep["fragment_present_litteralement"] is True
    assert rep["document_declare"]["id"] == "TEST_M"  # Source de preuve, pas source de l'article cible O.
    assert rep["sha256_pdf_lu"] == rep["document_declare"]["sha256"]
    assert rep["position_debut_pdf"] == 0 and rep["position_fin_pdf_exclusive"] == 7
    assert "justification" not in rep["relation_declaree"]
    assert rep["preuve_juridique_verifiee"] is False and rep["relation_juridique_etablie"] is False
    assert rapprocher_justification_pdf(lot,"TEST_RELATION",2)["fragment_present_litteralement"] is False
    vide = rapprocher_justification_pdf(lot,"TEST_RELATION",3)
    assert vide["constat"] == "texte_natif_absent" and vide["fragment_present_litteralement"] is None
    assert snapshot(lot) == avant


@pytest.mark.parametrize("identifiant,offset,constat",[("ABSENT",0,"relation_absente_du_lot"),
    ("TEST_RELATION",10000,"fragment_vide"),("TEST_RELATION",7,"fragment_sans_caractere_non_blanc")])
def test_sans_extraction_si_pas_fragment_significatif(tmp_path,monkeypatch,identifiant,offset,constat):
    from unocr.customs_reference import article_pdf_match
    lot = preparer_pdf(tmp_path / "entrees",tmp_path / "lot")
    def interdit(*a,**kw):
        pytest.fail("Pas d'extraction attendue")
    monkeypatch.setattr(article_pdf_match,"extraire_page_controlee",interdit)
    rep = rapprocher_justification_pdf(lot,identifiant,9999,1,offset)
    assert rep["constat"] == constat and rep["extraction_effectuee"] is False and rep["fragment_present_litteralement"] is None


@pytest.mark.parametrize("kwargs",[{"relation_id":""},{"relation_id":True},{"relation_id":"A\n"},
    {"relation_id":"\ud800"},{"relation_id":"X"*257},{"page":0},{"page":True},{"page":10001},
    {"limite":0},{"limite":True},{"limite":16001},{"decalage":-1},{"decalage":True},{"decalage":67108865}])
def test_parametres_avant_lecture(tmp_path,kwargs):
    with pytest.raises(ParamJustificationPDFInvalide):
        rapprocher_justification_pdf(tmp_path / "absent",**{"relation_id":"R","page":1,**kwargs})


def test_unicode_page_entiere_premiere_occurrence_et_un_rejeu(tmp_path,monkeypatch):
    from unocr.customs_reference import pdf_page, relation_pdf_match
    entree = tmp_path / "entrees"
    preparer_pdf(entree,tmp_path / "ancien")
    t = entree / "transcription_NON_OFFICIELLE.json"
    brut = json.loads(t.read_text())
    brut["relations"][0]["justification"] = "أ😀éX"
    t.write_text(json.dumps(brut))
    lot = tmp_path / "lot"
    preparer_code(t,entree / "metadata_NON_OFFICIELLE.json",lot)
    charger = relation_pdf_match.charger_lot_code
    appels = []
    def charger_une_fois(*a):
        appels.append(1)
        return charger(*a)
    monkeypatch.setattr(relation_pdf_match,"charger_lot_code",charger_une_fois)
    def worker(*a,**kw):
        assert kw["timeout"] == 15
        return SimpleNamespace(returncode=0,stdout=json.dumps({"nombre_pages":3,"texte":"!"*17000+"أ😀éXأ😀éX"}).encode())
    monkeypatch.setattr(pdf_page.subprocess,"run",worker)
    rep = rapprocher_justification_pdf(lot,"TEST_RELATION",1,2,1)
    assert rep["fragment_justification"] == "😀e" and rep["position_debut_pdf"] == 17001 and rep["decalage_suivant"] == 3
    assert len(appels) == 1
    def normalise(*a,**kw):
        return SimpleNamespace(returncode=0,stdout=json.dumps({"nombre_pages":3,"texte":"أ😀éX"}).encode())
    monkeypatch.setattr(pdf_page.subprocess,"run",normalise)
    assert rapprocher_justification_pdf(lot,"TEST_RELATION",1)["fragment_present_litteralement"] is False


def test_cli_et_page_absente(tmp_path,capsys):
    lot = preparer_pdf(tmp_path / "entrees",tmp_path / "lot")
    assert main(["customs-code-relation-pdf-match",str(lot),"--id","TEST_RELATION","--page","1","--limit","7"]) == 0
    assert json.loads(capsys.readouterr().out)["preuve_juridique_verifiee"] is False
    with pytest.raises(LecturePDFRefusee):
        rapprocher_justification_pdf(lot,"TEST_RELATION",4)


def test_api_audit_export_et_panne(revue_pdf,monkeypatch):
    from unocr import api
    client,racine,registre,cfg = revue_pdf
    avant = snapshot(racine)
    url = BASE + "/lots/code_pdf/relation-pdf-match?relation_id=TEST_RELATION&page=1&limit=7"
    r = client.get(url,headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert r.json()["resultat"]["document_declare"]["id"] == "TEST_M"
    events = [json.loads(ligne) for ligne in (cfg.log_dir / "audit.log").read_text().splitlines()]
    e = [e for e in events if e.get("operation") == "rapprochement_justification_pdf"][-1]
    assert e["manifestes"].keys() == {"code_pdf"} and "TEST_RELATION" not in json.dumps(e)
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
    ("code_pdf/relation-pdf-match?relation_id=TEST_RELATION&page=1",{},401),
    ("code_pdf/relation-pdf-match?relation_id=TEST_RELATION&page=1",{"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403),
    ("tarif_a/relation-pdf-match?relation_id=TEST_RELATION&page=1",ADMIN,422),
    ("code_pdf/relation-pdf-match?relation_id=TEST_RELATION",ADMIN,422),
    ("code_pdf/relation-pdf-match?relation_id=TEST_RELATION&page=4",ADMIN,409),
])
def test_refus_api(revue_pdf,route,headers,statut):
    client,*_ = revue_pdf
    assert client.get(BASE + "/lots/"+route,headers=headers).status_code == statut
