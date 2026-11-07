"""Deux archives NON OFFICIELLES explicitement ordonnées, pas fusion juridique."""
import json
import shutil
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest

from tests import test_customs_fiscal_review, test_customs_review
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.export_replay_pair import verifier_rejeu_paire
from unocr.customs_reference.review_export import MARQUEURS, ExportRefuse

revue = test_customs_review.revue
fiscal = test_customs_fiscal_review.fiscal


@pytest.fixture()
def paire(fiscal):
    client,racine,registre,cfg = fiscal
    shutil.copytree(racine/'code_a',racine/'code_b')
    reg = json.loads(registre.read_text())
    entree = next(e for e in reg['lots'] if e['id']=='code_a').copy()
    entree.update(id='code_b',dossier='code_b')
    reg['lots'].append(entree)
    registre.write_text(json.dumps(reg))
    return fiscal


def enregistrer(cfg,url,resultat):
    fichier = cfg.root/'export_paire.json'
    fichier.write_text(json.dumps({**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
        'requete_relative':url,'resultat':resultat}))
    return fichier


@pytest.mark.parametrize('route,a,b,ta,tb,params',[
    ('diff','tarif_a','tarif_b','tarif','tarif',{}),
    ('diff','code_a','code_b','code','code',{}),
    ('diff','code_a','code_a','code','code',{}),
    ('article-diff','code_a','code_b','code','code',{'avant_id':'TEST_O_A','apres_id':'TEST_M_A','limit':5,'offset_apres':1}),
    ('article-diff','code_a','code_b','code','code',{'avant_id':'TEST_O_A','apres_id':'ABSENT','offset_avant':67108864}),
    ('tariff-compare','tarif_a','tarif_b','tarif','tarif',{'code10':'0101000000','before_limit':1,'after_offset':99}),
    ('tariff-compare','tarif_a','tarif_b','tarif','tarif',{'code10':'9999999999'}),
    ('tariff-measures','tarif_a','mesures_a','tarif','mesures',{'code10':'0000000001','tariff_offset':99,'measures_limit':1}),
    ('tariff-measures','tarif_a','mesures_a','tarif','mesures',{'code10':'0101000000'}),
])
def test_paires_api_reelles_et_modifications_detectees(paire,route,a,b,ta,tb,params):
    client,racine,registre,cfg = paire
    roles = ('tarif','mesures') if route=='tariff-measures' else ('avant','apres')
    url = BASE+'/'+route+'?'+urlencode({roles[0]:a,roles[1]:b,**params})
    r = client.get(url,headers=ADMIN)
    assert r.status_code == 200 and r.headers['cache-control']=='no-store'
    fichier = enregistrer(cfg,url,r.json()['resultat'])
    avant = snapshot(racine)
    constat = verifier_rejeu_paire(fichier,racine/a,racine/b,a,b,ta,tb)
    assert constat['rapport_identique'] is constat['manifest_export_correspond'] is True
    assert constat['archives_fournies_coherentes_au_rejeu'] is True
    assert constat['authenticite_verifiee'] is constat['identite_registre_verifiee'] is False
    assert set(constat['manifestes_archives_fournies']) == {'avant','apres'}
    objet = json.loads(fichier.read_text())
    objet['resultat']['roles_inventes'] = 'SECRET_NON_RECOPIE'
    fichier.write_text(json.dumps(objet))
    different = verifier_rejeu_paire(fichier,racine/a,racine/b,a,b,ta,tb)
    assert different['rapport_identique'] is False and 'SECRET_NON_RECOPIE' not in json.dumps(different)
    assert snapshot(racine) == avant


@pytest.mark.parametrize('route,ta,tb',[
    ('diff?avant=A&apres=B','code','tarif'),
    ('diff?avant=A&apres=B','mesures','mesures'),
    ('article-diff?avant=A&apres=B&avant_id=X&apres_id=Y','tarif','tarif'),
    ('tariff-measures?tarif=A&mesures=B&code10=0000000001','mesures','tarif'),
    ('tariff-compare?avant=A&apres=B&code10=0000000001','tarif','mesures'),
    ('diff?avant=B&apres=A','tarif','tarif'),
    ('diff?avant=A&apres=B&avant=B','tarif','tarif'),
    ('diff?avant=A&apres=B&file=/secret','tarif','tarif'),
    ('diff?avant=A','tarif','tarif'),
    ('tariff-compare?avant=A&apres=B','tarif','tarif'),
    ('article-diff?avant=A&apres=B&avant_id=X','code','code'),
    ('article-diff?avant=A&apres=B&avant_id=X&apres_id=Y&offset_apres=1e3','code','code'),
    ('tariff-measures?tarif=A&mesures=B&code10=0000000001&measures_limit=1&measures_limit=2','tarif','mesures'),
    ('lots/A/search?q=x','tarif','tarif'),
])
def test_refus_avant_archives(tmp_path,route,ta,tb):
    fichier = enregistrer(SimpleNamespace(root=tmp_path),BASE+'/'+route,{'archives':{
        'avant':{'manifest_sha256':'a'*64},'apres':{'manifest_sha256':'b'*64}}})
    with pytest.raises(ExportRefuse,match='Route|Identités|Paramètre|Code10|Deux IDs|Pagination|Provenance|JSON'):
        verifier_rejeu_paire(fichier,tmp_path/'ABSENT_A',tmp_path/'ABSENT_B','A','B',ta,tb)


@pytest.mark.parametrize('a,b,ta,tb',[
    ('../X','B','tarif','tarif'),('A','','tarif','tarif'),('A','B',True,'tarif'),
    ('A','B','auto','code'),('A','B','code',None),('A','A','tarif','code'),
])
def test_identites_types_avant_export(tmp_path,a,b,ta,tb):
    with pytest.raises(ExportRefuse):
        verifier_rejeu_paire(tmp_path/'ABSENT',tmp_path/'A',tmp_path/'B',a,b,ta,tb)


def test_dossiers_inverses_et_archive_alteree(paire):
    client,racine,_,cfg = paire
    url = BASE+'/tariff-compare?avant=tarif_a&apres=tarif_b&code10=0101000000'
    fichier = enregistrer(cfg,url,client.get(url,headers=ADMIN).json()['resultat'])
    inverse = verifier_rejeu_paire(fichier,racine/'tarif_b',racine/'tarif_a','tarif_a','tarif_b','tarif','tarif')
    assert inverse['rapport_identique'] is inverse['manifest_export_correspond'] is False
    (racine/'tarif_b'/'source_recue.json').write_text('SECRET_ARCHIVE_ALTEREE')
    with pytest.raises(ExportRefuse,match='Archives ou paramètres') as erreur:
        verifier_rejeu_paire(fichier,racine/'tarif_a',racine/'tarif_b','tarif_a','tarif_b','tarif','tarif')
    assert 'SECRET_ARCHIVE' not in str(erreur.value)


def test_cli_codes_paire(paire,capsys):
    client,racine,_,cfg = paire
    url = BASE+'/diff?avant=tarif_a&apres=tarif_b'
    fichier = enregistrer(cfg,url,client.get(url,headers=ADMIN).json()['resultat'])
    args = ['customs-review-export-replay-pair',str(fichier),'--before-lot',str(racine/'tarif_a'),
        '--after-lot',str(racine/'tarif_b'),'--before-id','tarif_a','--after-id','tarif_b',
        '--before-type','tarif','--after-type','tarif']
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)['rapport_identique'] is True
    o = json.loads(fichier.read_text())
    o['resultat']['champ_invente']=0
    fichier.write_text(json.dumps(o))
    assert main(args) == 1
    assert json.loads(capsys.readouterr().out)['rapport_identique'] is False
    fichier.write_text('INVALIDE')
    assert main(args) == 2
    assert json.loads(capsys.readouterr().out)['statut'] == 'refuse'
