"""Comptage documentaire, pas causalité métier, IA ou attribut manquant déduit."""
import hashlib
import json

import pytest

from tests import test_customs_review
from tests.test_customs_reference import fichiers, snapshot
from tests.test_customs_review import ADMIN, BASE
from tests.test_customs_search import lot_tarif
from unocr.cli import main
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.review_export import MARQUEURS, analyser_export
from unocr.customs_reference.tariff_criteria import rechercher_tarif_criteres

revue = test_customs_review.revue


@pytest.mark.parametrize('kwargs, prefixe, total, constat',[
    ({'code_prefix':'99'},0,0,'aucune_ligne_dans_prefixe'),
    ({'designation':'introuvable'},5,0,'aucune_conjonction_sur_meme_ligne'),
    ({'designation':'équipement','fonction':'pompe'},5,0,'aucune_conjonction_sur_meme_ligne'),
    ({'designation':'équipement'},5,2,'correspondances_documentaires'),
    ({'designation':'équipement','decalage':99},5,2,'page_hors_resultats'),
    ({'code_prefix':'0101'},5,5,'correspondances_documentaires'),
    ({'code_prefix':'0101000004','designation':'équipement'},1,0,'aucune_conjonction_sur_meme_ligne'),
])
def test_constats_explicitement_distingues(tmp_path,kwargs,prefixe,total,constat):
    lot = lot_tarif(tmp_path)
    avant = snapshot(tmp_path)
    r = rechercher_tarif_criteres(lot,**kwargs)
    d = r['diagnostic_recherche']
    assert d['lignes_dans_prefixe'] == prefixe
    assert d['lignes_tous_criteres'] == total == r['total_correspondances']
    assert d['constat'] == constat
    assert d['absence_de_droit_deduite'] is d['attributs_manquants_deduits'] is False
    assert snapshot(tmp_path) == avant


def test_conjonction_impossible_malgre_criteres_individuellement_trouves(tmp_path):
    r = rechercher_tarif_criteres(lot_tarif(tmp_path),designation='équipement',fonction='pompe')
    d = r['diagnostic_recherche']
    assert d['par_critere']['designation']['lignes_tous_termes'] == 2
    assert d['par_critere']['fonction']['lignes_tous_termes'] == 1
    assert d['criteres_sans_ligne_complete'] == []
    assert d['lignes_tous_criteres'] == 0


def test_termes_repartis_ne_forment_pas_critere_et_pas_synonyme(tmp_path):
    r = rechercher_tarif_criteres(lot_tarif(tmp_path),matiere='équipement pompe',usage='acier')
    d = r['diagnostic_recherche']
    assert d['par_critere']['matiere'] == {'lignes_tous_termes':0,'lignes_par_terme':{'equipement':2,'pompe':1}}
    assert d['criteres_sans_ligne_complete'] == ['matiere','usage']
    assert d['par_critere']['usage']['lignes_par_terme']['acier'] == 0


def test_chaque_ligne_comptee_une_fois_fr_ar_et_termes_dupliques(tmp_path):
    r = rechercher_tarif_criteres(lot_tarif(tmp_path),designation='NON non',fonction='معدات اختبار')
    d = r['diagnostic_recherche']
    assert d['par_critere']['designation'] == {'lignes_tous_termes':4,'lignes_par_terme':{'non':4}}
    assert d['par_critere']['fonction']['lignes_tous_termes'] == 1
    assert d['par_critere']['fonction']['lignes_par_terme'] == {'معدات':1,'اختبار':1}
    entrees = tmp_path / 'bilingue'
    entrees.mkdir()
    source,metadata = fichiers(entrees)
    lignes = json.loads(source.read_text())
    lignes[0].update(designation_officielle_fr='acier acier',designation_officielle_ar='acier acier')
    source.write_text(json.dumps(lignes))
    meta = json.loads(metadata.read_text())
    meta['lot']['source']['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    lot = entrees / 'lot'
    preparer_tarif(source,metadata,lot)
    r = rechercher_tarif_criteres(lot,matiere='acier')
    assert r['diagnostic_recherche']['par_critere']['matiere'] == {'lignes_tous_termes':1,'lignes_par_terme':{'acier':1}}



def test_compteurs_avant_pagination_dans_prefixe_et_selon_mode(tmp_path):
    lot = lot_tarif(tmp_path)
    a = rechercher_tarif_criteres(lot,designation='quipement',limite=1)
    b = rechercher_tarif_criteres(lot,designation='quipement',limite=1,decalage=1)
    assert a['diagnostic_recherche'] == b['diagnostic_recherche']
    c = rechercher_tarif_criteres(lot,designation='quipement',match_mode='mots_entiers')
    assert c['diagnostic_recherche']['par_critere']['designation']['lignes_par_terme']['quipement'] == 0
    d = rechercher_tarif_criteres(lot,designation='équipement',code_prefix='0101000002')['diagnostic_recherche']
    assert d['lignes_dans_prefixe'] == d['lignes_tous_criteres'] == 1
    assert d['par_critere']['designation']['lignes_tous_termes'] == 1


def test_prefixe_seul_et_termes_absents_du_prefixe(tmp_path):
    lot = lot_tarif(tmp_path)
    d = rechercher_tarif_criteres(lot,code_prefix='0101')['diagnostic_recherche']
    assert d['par_critere'] == {} and d['criteres_sans_ligne_complete'] == []
    e = rechercher_tarif_criteres(lot,code_prefix='99',designation='équipement')['diagnostic_recherche']
    assert e['par_critere']['designation']['lignes_tous_termes'] == 0
    assert e['constat'] == 'aucune_ligne_dans_prefixe'


def test_cli_zero_resultat_est_un_rapport_pas_erreur(tmp_path,capsys):
    lot = lot_tarif(tmp_path)
    assert main(['customs-tariff-criteria',str(lot),'--designation','acier']) == 0
    r = json.loads(capsys.readouterr().out)
    assert r['diagnostic_recherche']['constat'] == 'aucune_conjonction_sur_meme_ligne'


def test_api_audit_export_diagnostic_sans_resultat(revue):
    client,racine,registre,cfg = revue
    avant = snapshot(racine)
    route = BASE+'/lots/tarif_a/tariff-criteria?designation=equipement&fonction=pompe'
    reponse = client.get(route,headers=ADMIN)
    assert reponse.status_code == 200 and reponse.headers['cache-control'] == 'no-store'
    r = reponse.json()['resultat']
    assert r['resultats'] == []
    assert r['diagnostic_recherche']['criteres_sans_ligne_complete'] == []
    exp = {**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z','requete_relative':route,'resultat':r}
    assert analyser_export(json.dumps(exp).encode())['statut'] == 'structure_compatible'
    events = [json.loads(v) for v in (cfg.log_dir / 'audit.log').read_text().splitlines()]
    assert any(e.get('operation')=='recherche_tarif_criteres' and e['statut']==200 for e in events)
    assert snapshot(racine) == avant
