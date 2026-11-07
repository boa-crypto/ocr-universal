"""Rejeu de provenance et relations DÉCLARÉES, sans consolidation juridique."""
import json
from urllib.parse import urlencode

import pytest

from tests import test_customs_fiscal_review, test_customs_review
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.customs_reference.export_replay import verifier_rejeu_export
from unocr.customs_reference.review_export import MARQUEURS, ExportRefuse

revue = test_customs_review.revue
fiscal = test_customs_fiscal_review.fiscal


@pytest.mark.parametrize('identite,type_lot,route,params',[
    ('code_a','code','check',{}),('tarif_a','tarif','check',{}),('mesures_a','mesures','check',{}),
    ('code_a','code','coverage',{}),('tarif_a','tarif','coverage',{}),('mesures_a','mesures','coverage',{}),
    ('code_a','code','sources',{'source_id':'TEST_O','nature_document':'code_original','limit':1}),
    ('tarif_a','tarif','sources',{}),('mesures_a','mesures','sources',{'q':'ABSENT'}),
    ('code_a','code','history',{'article':'5 bis','limit':1,'relations_limit':1}),
    ('code_a','code','history',{'article':'5 bis','offset':99,'relations_offset':99}),
    ('code_a','code','article-relations',{'article_id':'TEST_O_A','direction':'entrantes','relation_type':'modifie'}),
    ('code_a','code','article-relations',{'article_id':'ABSENT'}),
    ('code_a','code','article-diff',{'avant_id':'TEST_O_A','apres_id':'TEST_M_A','limit':5,'offset_apres':2}),
    ('code_a','code','article-diff',{'avant_id':'TEST_O_A','apres_id':'TEST_M_A','offset_avant':67108864}),
    ('code_a','code','code-tree',{}),('code_a','code','code-tree',{'source_id':'TEST_O','path':'[]'}),
    ('tarif_a','tarif','tree',{}),('tarif_a','tarif','tree',{'level':'codes','parent':'010100','limit':1,'offset':1}),
])
def test_rejeu_provenance_api_reelle(fiscal,identite,type_lot,route,params):
    client,racine,registre,cfg = fiscal
    url = BASE+'/lots/'+identite+'/'+route+('?' + urlencode(params) if params else '')
    reponse = client.get(url,headers=ADMIN)
    assert reponse.status_code == 200 and reponse.headers['cache-control'] == 'no-store'
    objet = {**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
             'requete_relative':url,'resultat':reponse.json()['resultat']}
    fichier = cfg.root/'export_provenance.json'
    fichier.write_text(json.dumps(objet))
    avant = snapshot(racine)
    r = verifier_rejeu_export(fichier,racine/identite,identite,type_lot)
    assert r['rapport_identique'] is r['manifest_export_correspond'] is True
    assert r['authenticite_verifiee'] is r['identite_registre_verifiee'] is r['audit_serveur_verifie'] is False
    objet['resultat']['champ_invente'] = 'SECRET_NON_RECOPIE'
    fichier.write_text(json.dumps(objet))
    r = verifier_rejeu_export(fichier,racine/identite,identite,type_lot)
    assert r['rapport_identique'] is False and 'SECRET_NON_RECOPIE' not in json.dumps(r)
    assert snapshot(racine) == avant


@pytest.mark.parametrize('type_lot,route',[
    ('tarif','history?article=5'),('mesures','article-relations?article_id=X'),
    ('tarif','article-diff?avant_id=X&apres_id=Y'),('code','tree'),('mesures','code-tree'),
    ('code','coverage?limit=1'),('tarif','check?file=/secret'),
    ('code','history'),('code','article-relations'),('code','article-diff?avant_id=X'),
    ('code','history?article=X&relations_limit=1&relations_limit=2'),
    ('code','code-tree?path=%ZZ'),('code','sources?q=x&q=y'),
    ('code','article-diff?avant_id=X&apres_id=Y&after_lot=/secret'),
    ('code','pdf?document_id=X'),('mesures','fiscal-pdf?page=1'),
])
def test_refus_matrice_ou_parametres_avant_archive(fiscal,type_lot,route):
    _,racine,_,cfg = fiscal
    objet = {**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
             'requete_relative':BASE+'/lots/TEST/'+route,'resultat':{'archive':{'manifest_sha256':'a'*64}}}
    fichier = cfg.root/'refus_provenance.json'
    fichier.write_text(json.dumps(objet))
    with pytest.raises(ExportRefuse,match='Route|Paramètre|Requête|Encodage|Numéro|ID|Deux|Rejeu PDF'):
        verifier_rejeu_export(fichier,racine/'ABSENT','TEST',type_lot)


def test_terme_chemin_hierarchique_ne_devient_pas_chemin_fichier(fiscal):
    client,racine,_,cfg = fiscal
    url = BASE+'/lots/code_a/code-tree?source_id=TEST_O&path='+urlencode({'v':'[{"file":"/secret"}]'}).split('=',1)[1]
    fichier = cfg.root/'faux_chemin.json'
    fichier.write_text(json.dumps({**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
        'requete_relative':url,'resultat':{'archive':{'manifest_sha256':'a'*64}}}))
    with pytest.raises(ExportRefuse) as erreur:
        verifier_rejeu_export(fichier,racine/'code_a','code_a','code')
    assert '/secret' not in str(erreur.value)
