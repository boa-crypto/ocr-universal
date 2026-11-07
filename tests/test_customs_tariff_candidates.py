"""Pistes documentaires NON OFFICIELLES : aucun classement IA/juridique simulé."""
import json

import pytest

from tests.test_customs_reference import snapshot
from tests.test_customs_search import lot_tarif
from unocr.cli import main
from unocr.customs_reference.comparison import LotRefuse
from unocr.customs_reference.search import ParamRechercheInvalide
from unocr.customs_reference.tariff_candidates import rechercher_pistes_tarifaires
from unocr.customs_reference.tariff_criteria import rechercher_tarif_criteres


def codes(rapport):
    return [r['ligne']['code_tarifaire_10'] for r in rapport['resultats']]


def test_pistes_partielles_explicitement_distinctes_du_and(tmp_path):
    lot = lot_tarif(tmp_path)
    avant = snapshot(tmp_path)
    criteres = {'designation':'équipement','matiere':'acier','usage':'contrôle'}
    assert rechercher_tarif_criteres(lot,**criteres)['total_correspondances'] == 0
    r = rechercher_pistes_tarifaires(lot,**criteres)
    assert codes(r) == ['0101000002','0101000000']
    assert r['resultats'][0]['criteres_documentairement_complets'] == ['designation','usage']
    assert r['resultats'][0]['termes_non_retrouves_par_critere']['matiere'] == ['acier']
    assert r['resultats'][0]['conjonction_documentaire_complete'] is False
    assert all(v['statut'] == 'piste_documentaire_non_validee' for v in r['resultats'])
    assert r['candidat_retenu_automatiquement'] is False
    assert r['classement_ia_effectue'] is r['classement_douanier_valide'] is False
    assert r['probabilite_classement_etablie'] is r['attributs_techniques_certifies'] is r['taux_calcules'] is False
    assert r['source_declaree']['verification'] == 'non_verifiee'
    assert r['publication_active'] is False and r['validation_juridique'] == 'non_validee'
    assert snapshot(tmp_path) == avant


def test_priorite_criteres_complets_puis_paires_pas_pertinence_juridique(tmp_path):
    r = rechercher_pistes_tarifaires(lot_tarif(tmp_path),designation='equipement',matiere='pompe controle technique')
    assert codes(r) == ['0101000002','0101000000','0101000003']
    assert [v['indicateurs_tri'] for v in r['resultats']] == [
        {'nombre_criteres_complets':1,'nombre_paires_critere_terme_retrouvees':2},
        {'nombre_criteres_complets':1,'nombre_paires_critere_terme_retrouvees':1},
        {'nombre_criteres_complets':0,'nombre_paires_critere_terme_retrouvees':2}]


def test_nombre_paires_et_egalites_departagees_par_code(tmp_path):
    r = rechercher_pistes_tarifaires(lot_tarif(tmp_path),designation='equipement mecanique pompe')
    assert codes(r) == ['0101000000','0101000002','0101000003']
    assert [v['indicateurs_tri']['nombre_paires_critere_terme_retrouvees'] for v in r['resultats']] == [2,1,1]
    assert [v['rang_documentaire'] for v in r['resultats']] == [1,2,3]
    assert not any(v['conjonction_documentaire_complete'] for v in r['resultats'])


def test_fr_ar_spans_originaux_sans_traduction_ni_attribut_manquant(tmp_path):
    r = rechercher_pistes_tarifaires(lot_tarif(tmp_path),designation='EQUIPEMENT مُعَـدَّات',fonction='اختبار')
    v = r['resultats'][0]
    assert v['ligne']['code_tarifaire_10'] == '0101000000'
    assert v['conjonction_documentaire_complete'] is True
    assert v['indicateurs_tri']['nombre_paires_critere_terme_retrouvees'] == 3
    assert v['termes_non_retrouves_par_critere'] == {'designation':[],'fonction':[]}
    for extrait in v['extraits_correspondants']:
        champ = extrait['champ_texte']
        assert v['ligne'][champ][extrait['decalage']:extrait['decalage']+len(extrait['fragment'])] == extrait['fragment']
    partiel = r['resultats'][1]
    assert partiel['termes_non_retrouves_par_critere'] == {'designation':['معدات'],'fonction':['اختبار']}
    assert partiel['positions_par_critere']['designation']['معدات'] == []


def test_dedup_dans_critere_mais_paires_distinctes_entre_criteres(tmp_path):
    r = rechercher_pistes_tarifaires(lot_tarif(tmp_path),designation='équipement EQUIPEMENT',matiere='equipement')
    assert r['termes_normalises_par_critere'] == {'designation':['equipement'],'matiere':['equipement']}
    assert r['resultats'][0]['indicateurs_tri']['nombre_paires_critere_terme_retrouvees'] == 2


@pytest.mark.parametrize('mode,nombre',[('sous_chaine',2),('mots_entiers',0)])
def test_mode_literal_explicite(tmp_path,mode,nombre):
    assert rechercher_pistes_tarifaires(lot_tarif(tmp_path),designation='équi',match_mode=mode)['total_correspondances'] == nombre


def test_pagination_stable_et_prefixe_filtre_seulement(tmp_path):
    lot = lot_tarif(tmp_path)
    r = rechercher_pistes_tarifaires(lot,designation='equipement mecanique pompe',limite=1)
    page = rechercher_pistes_tarifaires(lot,designation='equipement mecanique pompe',limite=1,decalage=r['decalage_suivant'])
    assert r['total_correspondances'] == page['total_correspondances'] == 3
    assert page['resultats'][0]['rang_documentaire'] == 2
    assert codes(page) == ['0101000002']
    dernier = rechercher_pistes_tarifaires(lot,designation='equipement mecanique pompe',limite=1,decalage=2)
    assert dernier['decalage_suivant'] is None
    assert rechercher_pistes_tarifaires(lot,designation='equipement',decalage=20)['resultats'] == []
    assert rechercher_pistes_tarifaires(lot,designation='equipement',code_prefix='99')['total_correspondances'] == 0
    assert codes(rechercher_pistes_tarifaires(lot,designation='equipement',code_prefix='0101000002')) == ['0101000002']


@pytest.mark.parametrize('terme',['acier','equipment','TERME_MESURE_EXCLU','0101000000'])
def test_aucune_inference_synonyme_code_ou_mesure(tmp_path,terme):
    r = rechercher_pistes_tarifaires(lot_tarif(tmp_path),designation=terme)
    assert r['total_correspondances'] == 0 and not r['resultats']
    assert r['decalage_suivant'] is None


@pytest.mark.parametrize('arguments',[
    {},{'code_prefix':'01'},{'designation':''},{'designation':' '},{'designation':'!!!'},
    {'designation':False},{'designation':[]},{'designation':'a'*257},{'designation':'\ud800'},
    {'designation':'a\x00b'},{'designation':' '.join('t'+str(i) for i in range(17))},
    {'designation':'x','code_prefix':'٠١'},{'designation':'x','code_prefix':'1'*11},
    {'designation':'x','limite':True},{'designation':'x','limite':101},
    {'designation':'x','decalage':False},{'designation':'x','decalage':-1},
    {'designation':'x','decalage':1000001},{'designation':'x','match_mode':'IA'},
    {'designation':'x','match_mode':[]},
])
def test_parametres_refuses_avant_lecture(tmp_path,arguments):
    with pytest.raises(ParamRechercheInvalide):
        rechercher_pistes_tarifaires(tmp_path/'ABSENT',**arguments)


def test_lot_altere_refuse_sans_piste_partielle(tmp_path):
    lot = lot_tarif(tmp_path)
    (lot/'lot.json').write_text('{}')
    with pytest.raises(LotRefuse):
        rechercher_pistes_tarifaires(lot,designation='equipement')


def test_cli_succes_vide_et_refus_pas_fallback_and(tmp_path,capsys):
    lot = lot_tarif(tmp_path)
    args = ['customs-tariff-candidates',str(lot),'--designation','equipement','--matiere','acier','--limit','1']
    assert main(args) == 0
    r = json.loads(capsys.readouterr().out)
    assert r['type_recherche'] == 'pistes_tarifaires_documentaires_non_validees'
    assert len(r['resultats']) == 1 and r['total_correspondances'] == 2
    assert main(['customs-tariff-criteria',str(lot),'--designation','equipement','--matiere','acier']) == 0
    assert json.loads(capsys.readouterr().out)['total_correspondances'] == 0
    assert main(['customs-tariff-candidates',str(lot),'--designation','inexistant']) == 0
    assert json.loads(capsys.readouterr().out)['resultats'] == []
    assert main(['customs-tariff-candidates',str(lot),'--code-prefix','01']) == 2
    assert json.loads(capsys.readouterr().out)['statut'] == 'refuse'


def test_extraits_bornes_et_positions_conservees_pour_toutes_paires(tmp_path):
    termes = 'equipement mecanique non officiel معدات اختبار غير رسمية'
    r = rechercher_pistes_tarifaires(lot_tarif(tmp_path),designation=termes,matiere=termes,
                                    fonction=termes,usage=termes,caracteristiques=termes)
    v = r['resultats'][0]
    assert v['conjonction_documentaire_complete'] is True
    assert v['indicateurs_tri']['nombre_criteres_complets'] == 5
    assert v['indicateurs_tri']['nombre_paires_critere_terme_retrouvees'] == 40
    assert v['total_extraits_disponibles'] == 40 and v['extraits_tronques'] is True
    assert len(v['extraits_correspondants']) == r['maximum_extraits_par_ligne'] == 16
    assert sum(len(mots) for mots in v['positions_par_critere'].values()) == 40


def test_tri_independant_ordre_source_json(tmp_path):
    import hashlib

    from unocr.customs_reference.importer import preparer_tarif

    lot = lot_tarif(tmp_path)
    original = rechercher_pistes_tarifaires(lot,designation='equipement mecanique pompe')
    source = tmp_path/'source_inversee.json'
    source.write_text(json.dumps(list(reversed(json.loads((lot/'source_recue.json').read_text()))),ensure_ascii=False))
    metadata = tmp_path/'metadata_inversee.json'
    m = json.loads((lot/'metadata_original.json').read_text())
    m['lot']['source']['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(m))
    inverse = tmp_path/'inverse'
    preparer_tarif(source,metadata,inverse)
    assert codes(rechercher_pistes_tarifaires(inverse,designation='equipement mecanique pompe')) == codes(original)
