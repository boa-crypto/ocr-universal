"""Rapprochement de fixtures NON OFFICIELLES ; aucune attestation réglementaire."""
import json
from types import SimpleNamespace

import pytest

from tests import test_customs_pdf_page, test_customs_review
from tests.test_customs_pdf_page import preparer_pdf
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.article_pdf_match import (
    ParamRapprochementInvalide,
    rapprocher_fragment_article_pdf,
)
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.pdf_page import LecturePDFRefusee
from unocr.customs_reference.review_export import analyser_export
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue
revue_pdf = test_customs_pdf_page.revue_pdf


def test_presence_absence_page_vide_provenance_et_aucune_mutation(tmp_path):
    lot = preparer_pdf(tmp_path / "entrees", tmp_path / "lot")
    avant = snapshot(lot)
    rep = rapprocher_fragment_article_pdf(lot,"TEST_O_A",1,limite=7)
    assert rep["fragment_present_litteralement"] is True
    assert rep["position_debut_pdf"] == 0 and rep["position_fin_pdf_exclusive"] == 7
    assert rep["sha256_pdf_lu"] == rep["document_declare"]["sha256"]
    assert rep["version_declaree"]["reference"]["source_id"] == "TEST_O"
    assert rep["transcription_verification"] == "non_verifiee" and rep["publication_active"] is False
    absent = rapprocher_fragment_article_pdf(lot,"TEST_O_A",2)
    assert absent["fragment_present_litteralement"] is False
    assert absent["constat"] == "correspondance_litterale_non_trouvee" and absent["position_debut_pdf"] is None
    vide = rapprocher_fragment_article_pdf(lot,"TEST_O_A",3)
    assert vide["constat"] == "texte_natif_absent" and vide["fragment_present_litteralement"] is None
    assert snapshot(lot) == avant


@pytest.mark.parametrize("article,champ,offset,constat", [
    ("INCONNU","texte_integral",0,"article_absent_du_lot"),
    ("TEST_O_A","texte_francais",0,"champ_absent"), ("TEST_O_A","texte_integral",1000,"fragment_vide"),
    ("TEST_O_A","texte_integral",7,"fragment_sans_caractere_non_blanc"),
])
def test_indisponibilite_sans_extraction(tmp_path, monkeypatch, article, champ, offset, constat):
    from unocr.customs_reference import article_pdf_match
    lot = preparer_pdf(tmp_path / "entrees", tmp_path / "lot")
    def interdit(*a, **kw):
        pytest.fail("Aucune extraction attendue")
    monkeypatch.setattr(article_pdf_match,"extraire_page_controlee",interdit)
    rep = rapprocher_fragment_article_pdf(lot,article,9999,champ,1,offset)
    assert rep["constat"] == constat and rep["extraction_effectuee"] is False
    assert rep["fragment_present_litteralement"] is None and rep["sha256_pdf_lu"] is None


@pytest.mark.parametrize("kwargs", [{"article_id":""}, {"article_id":"A\n"}, {"article_id":"X"*257},
    {"article_id":True}, {"champ":"inconnu"}, {"page":True}, {"page":0}, {"page":10001},
    {"limite":0}, {"limite":True}, {"limite":16001}, {"decalage":-1}, {"decalage":True}, {"decalage":67108865}])
def test_parametres_avant_chargement(tmp_path, kwargs):
    with pytest.raises(ParamRapprochementInvalide):
        rapprocher_fragment_article_pdf(tmp_path / "absent",**{"article_id":"A","page":1,**kwargs})


def test_recherche_page_entiere_au_dela_fragment_et_premiere_occurrence(tmp_path, monkeypatch):
    from unocr.customs_reference import article_pdf_match, pdf_page
    lot = preparer_pdf(tmp_path / "entrees", tmp_path / "lot")
    charger = article_pdf_match.charger_lot_code
    appels = []
    def charger_une_fois(*a):
        appels.append(1)
        return charger(*a)
    monkeypatch.setattr(article_pdf_match,"charger_lot_code",charger_une_fois)
    def worker(*a,**kw):
        assert kw["input"].startswith(b"%PDF-") and kw["timeout"] == 15
        return SimpleNamespace(returncode=0,stdout=json.dumps({"nombre_pages":3,"texte":"X"*17000+"FIXTURE FIXTURE"}).encode())
    monkeypatch.setattr(pdf_page.subprocess,"run",worker)
    rep = rapprocher_fragment_article_pdf(lot,"TEST_O_A",1,limite=7)
    assert rep["position_debut_pdf"] == 17000 and len(appels) == 1


def test_unicode_strict_pas_de_normalisation_et_pagination(tmp_path, monkeypatch):
    from unocr.customs_reference import pdf_page
    entrees = tmp_path / "entrees"
    preparer_pdf(entrees,tmp_path / "ancien")
    t = entrees / "transcription_NON_OFFICIELLE.json"
    donnees = json.loads(t.read_text())
    donnees["articles"][0]["texte_integral"] = "أ😀éX"
    t.write_text(json.dumps(donnees))
    lot = tmp_path / "lot"
    preparer_code(t,entrees / "metadata_NON_OFFICIELLE.json",lot)
    def worker(*a,**kw):
        return SimpleNamespace(returncode=0,stdout=json.dumps({"nombre_pages":3,"texte":"!أ😀éX!"}).encode())
    monkeypatch.setattr(pdf_page.subprocess,"run",worker)
    rep = rapprocher_fragment_article_pdf(lot,"TEST_O_A",1,limite=2,decalage=1)
    assert rep["fragment_article"] == "😀e" and rep["position_debut_pdf"] == 2 and rep["decalage_suivant"] == 3
    def normalise(*a,**kw):
        return SimpleNamespace(returncode=0,stdout=json.dumps({"nombre_pages":3,"texte":"!أ😀éX!"}).encode())
    monkeypatch.setattr(pdf_page.subprocess,"run",normalise)
    assert rapprocher_fragment_article_pdf(lot,"TEST_O_A",1)["fragment_present_litteralement"] is False


def test_refus_page_absente_et_pdf_altere_apres_rejeu(tmp_path, monkeypatch):
    from unocr.customs_reference import article_pdf_match
    lot = preparer_pdf(tmp_path / "entrees", tmp_path / "lot")
    with pytest.raises(LecturePDFRefusee):
        rapprocher_fragment_article_pdf(lot,"TEST_O_A",4)
    charger = article_pdf_match.charger_lot_code
    def alterer(*a):
        resultat = charger(*a)
        (lot / "document_0001.pdf").write_bytes(b"%PDF-ALTERE NON OFFICIEL")
        return resultat
    monkeypatch.setattr(article_pdf_match,"charger_lot_code",alterer)
    with pytest.raises(LecturePDFRefusee):
        rapprocher_fragment_article_pdf(lot,"TEST_O_A",1)


def test_cli_constat_negatif_n_est_pas_validation(tmp_path,capsys):
    lot = preparer_pdf(tmp_path / "entrees", tmp_path / "lot")
    assert main(["customs-code-article-pdf-match",str(lot),"--id","TEST_O_A","--page","1"]) == 0
    assert json.loads(capsys.readouterr().out)["fragment_present_litteralement"] is False


def test_api_audit_export_et_503(revue_pdf,monkeypatch):
    from unocr import api
    client,racine,registre,cfg = revue_pdf
    avant = snapshot(racine)
    url = BASE + "/lots/code_pdf/article-pdf-match?article_id=TEST_O_A&page=1&limit=7"
    rep = client.get(url,headers=ADMIN)
    assert rep.status_code == 200 and rep.headers["cache-control"] == "no-store"
    assert rep.json()["resultat"]["fragment_present_litteralement"] is True
    events = [json.loads(ligne) for ligne in (cfg.log_dir / "audit.log").read_text().splitlines()]
    succes = [e for e in events if e.get("operation") == "rapprochement_article_pdf"][-1]
    assert succes["manifestes"].keys() == {"code_pdf"} and "FIXTURE" not in json.dumps(succes)
    enveloppe = {"schema_version":"1","type_export":"rapport_revue_documentaire_non_valide","lecture_seule":True,
        "publication_active":False,"validation_juridique":"non_validee","perimetre":"rapport_ou_page_uniquement_pas_corpus_complet",
        "horodatage_client_non_certifie":"2026-11-07T10:00:00.000Z","requete_relative":url,"resultat":rep.json()["resultat"]}
    assert analyser_export(json.dumps(enveloppe).encode())["statut"] == "structure_compatible"
    def panne(*a,**kw):
        raise AuditIndisponible("SECRET_TEST")
    monkeypatch.setattr(api,"audit_obligatoire",panne)
    refus = client.get(url,headers=ADMIN)
    assert refus.status_code == 503 and "resultat" not in refus.json() and "SECRET_TEST" not in refus.text
    assert snapshot(racine) == avant


@pytest.mark.parametrize("route,headers,statut", [
    ("code_pdf/article-pdf-match?article_id=TEST_O_A&page=1",{},401),
    ("code_pdf/article-pdf-match?article_id=TEST_O_A&page=1",{"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403),
    ("tarif_a/article-pdf-match?article_id=TEST_O_A&page=1",ADMIN,422),
    ("code_pdf/article-pdf-match?article_id=TEST_O_A",ADMIN,422),
    ("code_pdf/article-pdf-match?article_id=TEST_O_A&page=4",ADMIN,409),
    ("code_pdf/article-pdf-match?article_id=TEST_O_A&page=1&field=INVALIDE",ADMIN,422),
])
def test_refus_api(revue_pdf,route,headers,statut):
    client,*_ = revue_pdf
    rep = client.get(BASE + "/lots/" + route,headers=headers)
    assert rep.status_code == statut and "resultat" not in rep.json()
