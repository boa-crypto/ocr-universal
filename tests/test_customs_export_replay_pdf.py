"""Rejeu PDFium réel de fixtures NON OFFICIELLES, uniquement sur opt-in local."""
import json
from urllib.parse import urlencode

import pytest

from tests.test_customs_fiscal_pdf_page import SID
from tests.test_customs_measure_pdf_match import preparer as preparer_mesures
from tests.test_customs_pdf_page import preparer_pdf
from tests.test_customs_reference import snapshot
from unocr.cli import main
from unocr.customs_reference.article_pdf_match import rapprocher_fragment_article_pdf
from unocr.customs_reference.export_replay import verifier_rejeu_export
from unocr.customs_reference.fiscal_pdf_page import lire_page_pdf_mesures
from unocr.customs_reference.measure_pdf_match import rapprocher_description_mesure_pdf
from unocr.customs_reference.pdf_page import lire_page_pdf
from unocr.customs_reference.relation_pdf_match import rapprocher_justification_pdf
from unocr.customs_reference.review_export import MARQUEURS, ExportRefuse


def exporter(tmp_path,type_lot,route,params):
    if type_lot == 'code':
        lot = preparer_pdf(tmp_path/'entrees',tmp_path/'lot')
    else:
        entrees = tmp_path/'entrees'
        entrees.mkdir()
        lot = preparer_mesures(entrees)
    services = {'pdf':lire_page_pdf,'fiscal-pdf':lire_page_pdf_mesures,
        'article-pdf-match':rapprocher_fragment_article_pdf,'relation-pdf-match':rapprocher_justification_pdf,
        'measure-pdf-match':rapprocher_description_mesure_pdf}
    arguments = {({'limit':'limite','offset':'decalage','field':'champ'}.get(k,k)):v for k,v in params.items()}
    resultat = services[route](lot,**arguments)
    fichier = tmp_path/'export_pdf.json'
    objet = {**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
        'requete_relative':'/api/v1/customs-review/lots/TEST/'+route+'?'+urlencode(params),'resultat':resultat}
    fichier.write_text(json.dumps(objet))
    return fichier,lot,objet


@pytest.mark.parametrize('type_lot,route,params',[
    ('code','pdf',{'document_id':'TEST_O','page':1,'limit':5,'offset':2}),
    ('code','pdf',{'document_id':'TEST_O','page':3}),  # Page native vide, pas OCR.
    ('code','pdf',{'document_id':'TEST_O','offset':67108864}),
    ('code','article-pdf-match',{'article_id':'TEST_O_A','page':1,'limit':7}),
    ('code','article-pdf-match',{'article_id':'TEST_O_A','page':2}),
    ('code','article-pdf-match',{'article_id':'ABSENT','page':1}),
    ('code','relation-pdf-match',{'relation_id':'TEST_RELATION','page':1,'limit':7}),
    ('code','relation-pdf-match',{'relation_id':'ABSENT','page':1}),
    ('mesures','fiscal-pdf',{'document_id':SID,'page':2,'limit':12}),
    ('mesures','measure-pdf-match',{'mesure_id':'M_0','page':1,'limit':7}),
    ('mesures','measure-pdf-match',{'mesure_id':'ABSENT','page':1}),
])
def test_rejeu_natif_et_rapprochements_sans_mutation(tmp_path,type_lot,route,params):
    fichier,lot,objet = exporter(tmp_path,type_lot,route,params)
    avant = snapshot(tmp_path)
    r = verifier_rejeu_export(fichier,lot,'TEST',type_lot,autoriser_pdf=True)
    assert r['rapport_identique'] is r['manifest_export_correspond'] is r['rejeu_pdf_autorise'] is True
    assert r['authenticite_verifiee'] is r['identite_registre_verifiee'] is False
    assert snapshot(tmp_path) == avant
    objet['resultat']['fragment_fabrique'] = 'SECRET_NON_RECOPIE'
    fichier.write_text(json.dumps(objet))
    r = verifier_rejeu_export(fichier,lot,'TEST',type_lot,autoriser_pdf=True)
    assert r['rapport_identique'] is False and 'SECRET_NON_RECOPIE' not in json.dumps(r)


@pytest.mark.parametrize('route',['pdf','fiscal-pdf','article-pdf-match','relation-pdf-match','measure-pdf-match'])
def test_permission_absente_refuse_avant_archive(tmp_path,route,monkeypatch):
    from unocr.customs_reference import export_replay_routes
    fichier = tmp_path/'sans_permission.json'
    fichier.write_text(json.dumps({**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
        'requete_relative':'/api/v1/customs-review/lots/TEST/'+route,'resultat':{'archive':{'manifest_sha256':'a'*64}}}))
    def interdit(*a,**kw):
        pytest.fail('Aucun lecteur PDF ne doit être appelé sans opt-in')
    for nom in ('lire_page_pdf','lire_page_pdf_mesures','rapprocher_fragment_article_pdf',
                'rapprocher_justification_pdf','rapprocher_description_mesure_pdf'):
        monkeypatch.setattr(export_replay_routes,nom,interdit)
    with pytest.raises(ExportRefuse,match='non autorisé'):
        verifier_rejeu_export(fichier,tmp_path/'ABSENT','TEST','code')


@pytest.mark.parametrize('type_lot,route',[
    ('tarif','pdf?document_id=X'),('code','fiscal-pdf?document_id=X'),
    ('mesures','article-pdf-match?article_id=X&page=1'),('code','measure-pdf-match?mesure_id=X'),
    ('code','pdf'),('code','article-pdf-match?article_id=X'),('code','relation-pdf-match?page=1'),
    ('mesures','fiscal-pdf?document_id=X&file=/secret'),
    ('code','pdf?document_id=X&page=1&page=2'),('code','pdf?document_id=X&page=1e3'),
    ('code','pdf?document_id=X&allow_pdf=true'),
])
def test_refus_type_identifiants_ou_parametres_avant_archive(tmp_path,type_lot,route):
    fichier = tmp_path/'refus_pdf.json'
    fichier.write_text(json.dumps({**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
        'requete_relative':'/api/v1/customs-review/lots/TEST/'+route,'resultat':{'archive':{'manifest_sha256':'a'*64}}}))
    with pytest.raises(ExportRefuse,match='Route PDF|ID et page|Paramètre|Pagination'):
        verifier_rejeu_export(fichier,tmp_path/'ABSENT','TEST',type_lot,autoriser_pdf=True)


@pytest.mark.parametrize('permission',[None,0,1,'true',[],{}])
def test_permission_type_strict_avant_export(tmp_path,permission):
    with pytest.raises(ExportRefuse,match='booléenne'):
        verifier_rejeu_export(tmp_path/'ABSENT',tmp_path/'ABSENT','TEST','code',autoriser_pdf=permission)


def test_cli_opt_in_et_pdf_altere_refuse(tmp_path,capsys):
    fichier,lot,objet = exporter(tmp_path,'code','pdf',{'document_id':'TEST_O'})
    args = ['customs-review-export-replay',str(fichier),'--lot',str(lot),'--lot-id','TEST','--type-lot','code']
    assert main(args) == 2
    assert json.loads(capsys.readouterr().out)['statut'] == 'refuse'
    assert main(args+['--allow-pdf']) == 0
    assert json.loads(capsys.readouterr().out)['rejeu_pdf_autorise'] is True
    (lot/'document_0001.pdf').write_bytes(b'%PDF-ALTERE')
    assert main(args+['--allow-pdf']) == 2
    r = json.loads(capsys.readouterr().out)
    assert r['statut'] == 'refuse' and '%PDF-ALTERE' not in json.dumps(r)
