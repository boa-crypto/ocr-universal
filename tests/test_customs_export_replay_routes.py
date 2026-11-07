"""Rejeu typé de sorties API réelles NON OFFICIELLES, sans deviner un type."""
import json
from urllib.parse import urlencode

import pytest

from tests import test_customs_fiscal_review, test_customs_review
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.export_replay import verifier_rejeu_criteres, verifier_rejeu_export
from unocr.customs_reference.review_export import MARQUEURS, ExportRefuse

revue = test_customs_review.revue
fiscal = test_customs_fiscal_review.fiscal


@pytest.mark.parametrize('identite,type_lot,route,params',[
    ('code_a','code','search',{'q':'equipement','limit':1}),
    ('code_a','code','search',{'article':'5 bis','source':'TEST_O','nature':'originale'}),
    ('code_a','code','article',{'article_id':'TEST_O_A','field':'texte_arabe','limit':5,'offset':1}),
    ('code_a','code','article',{'article_id':'ABSENT'}),
    ('tarif_a','tarif','search',{'q':'0101','limit':1,'offset':1}),
    ('tarif_a','tarif','search',{'q':'équipement'}),
    ('tarif_a','tarif','tariff/0101000000',{'measures_limit':1}),
    ('tarif_a','tarif','tariff/9999999999',{}),
    ('tarif_a','tarif','measure-search',{'q':'TERME_MESURE_EXCLU','measure_type':'restriction'}),
    ('mesures_a','mesures','measure-search',{'q':'معدات','code10':'0000000001','limit':1}),
    ('mesures_a','mesures','measure-search',{'measure_type':'droit','offset':99}),
    ('tarif_a','tarif','tariff-criteria',{'designation':'équipement','match_mode':'mots_entiers'}),
])
def test_rejeu_api_complet_sans_mutation(fiscal,identite,type_lot,route,params):
    client,racine,registre,cfg = fiscal
    url = BASE+'/lots/'+identite+'/'+route+('?' + urlencode(params) if params else '')
    reponse = client.get(url,headers=ADMIN)
    assert reponse.status_code == 200 and reponse.headers['cache-control'] == 'no-store'
    objet = {**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
             'requete_relative':url,'resultat':reponse.json()['resultat']}
    fichier = cfg.root/'export_typed.json'
    fichier.write_text(json.dumps(objet))
    avant = snapshot(racine)
    constat = verifier_rejeu_export(fichier,racine/identite,identite,type_lot)
    assert constat['rapport_identique'] is constat['manifest_export_correspond'] is True
    assert constat['type_lot_explicite'] == type_lot
    assert constat['authenticite_verifiee'] is constat['identite_registre_verifiee'] is False
    objet['resultat']['champ_invente'] = 'SECRET_NON_RECOPIE'
    fichier.write_text(json.dumps(objet))
    different = verifier_rejeu_export(fichier,racine/identite,identite,type_lot)
    assert different['rapport_identique'] is False and 'SECRET_NON_RECOPIE' not in json.dumps(different)
    assert snapshot(racine) == avant


@pytest.mark.parametrize('type_lot,route',[
    ('code','tariff-criteria?designation=x'),('code','tariff/0101000000'),
    ('code','measure-search?q=x'),('tarif','article?article_id=X'),
    ('tarif','search?q=x&article=5'),('mesures','search?q=x'),
    ('mesures','tariff/0101000000'),('code','article'),
    ('code','search?q=x&q=y'),('code','search?q=x&source=%FF'),
    ('code','article?article_id=X&field=texte_integral&offset=1e3'),
    ('tarif','tariff/0101000000?measures_limit=1&measures_limit=2'),
    ('code','pdf?document_id=TEST_O'),('code','fiscal-pdf?document_id=TEST_O'),
])
def test_hors_contrat_avant_archive(fiscal,type_lot,route):
    client,racine,registre,cfg = fiscal
    objet = {**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
             'requete_relative':BASE+'/lots/TEST/'+route,
             'resultat':{'archive':{'manifest_sha256':'a'*64}}}
    fichier = cfg.root/'export_refuse.json'
    fichier.write_text(json.dumps(objet))
    with pytest.raises(ExportRefuse,match='Route|Paramètre|Requête|Pagination|ID article'):
        verifier_rejeu_export(fichier,racine/'ARCHIVE_ABSENTE','TEST',type_lot)


@pytest.mark.parametrize('type_lot',[None,True,[],{},'auto','CODE',''])
def test_type_invalide_avant_export(tmp_path,type_lot):
    with pytest.raises(ExportRefuse,match='Type explicite'):
        verifier_rejeu_export(tmp_path/'ABSENT',tmp_path/'ABSENT','TEST',type_lot)


def test_cli_type_code_explicit_et_legacy_strict(fiscal,capsys):
    client,racine,registre,cfg = fiscal
    url = BASE+'/lots/code_a/article?article_id=TEST_O_A&limit=5'
    objet = {**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
             'requete_relative':url,'resultat':client.get(url,headers=ADMIN).json()['resultat']}
    fichier = cfg.root/'export_code.json'
    fichier.write_text(json.dumps(objet))
    args = ['customs-review-export-replay',str(fichier),'--lot',str(racine/'code_a'),'--lot-id','code_a']
    assert main(args+['--type-lot','code']) == 0
    assert json.loads(capsys.readouterr().out)['type_lot_explicite'] == 'code'
    assert main(args) == 2  # Défaut tarif conservé, aucun type déduit de l'export.
    capsys.readouterr()
    with pytest.raises(ExportRefuse,match='Archive fournie'):
        verifier_rejeu_export(fichier,racine/'tarif_a','code_a','code')
    with pytest.raises(ExportRefuse):
        verifier_rejeu_criteres(fichier,racine/'code_a','code_a')


def test_grand_offset_article_valide_et_non_modifie(fiscal):
    client,racine,registre,cfg = fiscal
    url = BASE+'/lots/code_a/article?article_id=TEST_O_A&offset=67108864'
    r = client.get(url,headers=ADMIN)
    assert r.status_code == 200
    fichier = cfg.root/'grand_offset.json'
    fichier.write_text(json.dumps({**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
                     'requete_relative':url,'resultat':r.json()['resultat']}))
    assert verifier_rejeu_export(fichier,racine/'code_a','code_a','code')['rapport_identique'] is True
