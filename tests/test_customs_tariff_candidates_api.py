"""Pistes HTTP/rejeu réels sur fixtures NON OFFICIELLES, sans classification."""
import hashlib
import json
from urllib.parse import urlencode

import pytest

from tests import test_customs_fiscal_review, test_customs_review
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr import api
from unocr.cli import main
from unocr.customs_reference.export_replay import verifier_rejeu_criteres, verifier_rejeu_export
from unocr.customs_reference.review_export import MARQUEURS, ExportRefuse, analyser_export
from unocr.customs_reference.tariff_candidates import rechercher_pistes_tarifaires
from unocr.logging_setup import AuditIndisponible
from unocr.rbac import RegistreRBAC

revue = test_customs_review.revue
fiscal = test_customs_fiscal_review.fiscal
ROUTE = BASE+'/lots/tarif_a/tariff-candidates'


def exporter(revue,params):
    client,racine,registre,cfg = revue
    url = ROUTE+'?'+urlencode(params)
    r = client.get(url,headers=ADMIN)
    assert r.status_code == 200 and r.headers['cache-control'] == 'no-store'
    objet = {**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
             'requete_relative':url,'resultat':r.json()['resultat']}
    fichier = cfg.root/'pistes.json'
    fichier.write_text(json.dumps(objet,ensure_ascii=False))
    return fichier,objet


@pytest.mark.parametrize('params',[
    {'designation':'equipement','matiere':'acier'},
    {'designation':'equipement mecanique pompe','limit':1,'offset':1},
    {'designation':'معدات','usage':'contrôle','match_mode':'mots_entiers'},
    {'designation':'introuvable'},{'designation':'équi','match_mode':'mots_entiers'},
])
def test_api_service_export_rejeu_identiques(revue,params):
    client,racine,registre,cfg = revue
    avant = snapshot(racine)
    fichier,objet = exporter(revue,params)
    arguments = {('limite' if k=='limit' else 'decalage' if k=='offset' else k):v for k,v in params.items()}
    assert objet['resultat'] == rechercher_pistes_tarifaires(racine/'tarif_a',**arguments)
    assert analyser_export(fichier.read_bytes())['statut'] == 'structure_compatible'
    rep = verifier_rejeu_export(fichier,racine/'tarif_a','tarif_a','tarif',
        sha256_export_attendu=hashlib.sha256(fichier.read_bytes()).hexdigest(),
        manifest_sha256_attendu=hashlib.sha256((racine/'tarif_a/manifest.json').read_bytes()).hexdigest())
    assert rep['rapport_identique'] is True
    assert rep['empreintes_attendues']['nombre_empreintes_verifiees'] == 2
    assert rep['authenticite_verifiee'] is False
    events = [json.loads(v) for v in (cfg.log_dir/'audit.log').read_text().splitlines()]
    event = [e for e in events if e.get('operation')=='recherche_pistes_tarifaires'][-1]
    assert event['statut'] == 200 and event['lots'] == ['tarif_a']
    assert 'equipement' not in json.dumps(event) and 'resultats' not in event
    assert snapshot(racine) == avant


@pytest.mark.parametrize('query',[
    '', '?code_prefix=01','?designation=','?designation=!!!','?designation=a&limit=101',
    '?designation=a&offset=-1','?designation=a&offset=1000001','?designation=a&limit=1e0',
    '?designation=a&limit=%2B1','?designation=a&limit=١','?designation=a&limit=00000001',
    '?designation=a&match_mode=IA','?designation=a&code_prefix=١',
    '?designation=a&designation=b','?designation=a&limit=1&limit=2',
    '?designation=a&path=/etc/passwd','?designation=a&source_url=https://example.org',
    '?designation='+'a'*257, '?designation=a%FF', '?designation=a%ZZ', '?designation=a&',
    '?designation=a&%64esignation=b',
])
def test_refus_parametres_api(revue,query):
    client,*_ = revue
    r = client.get(ROUTE+query,headers=ADMIN)
    assert r.status_code == 422 and 'resultat' not in r.json()
    assert '/etc/passwd' not in r.text


@pytest.mark.parametrize('headers,statut',[(None,401),({'Authorization':'Bearer INCONNU'},401),
    ({'Authorization':'Bearer TEST_LECTEUR_NON_PRODUCTION'},403),({'X-Role':'administrateur'},401)])
def test_rbac_reel_refuse(revue,headers,statut):
    client,*_ = revue
    r = client.get(ROUTE+'?designation=a',headers=headers)
    assert r.status_code == statut and 'resultat' not in r.json()


def test_allowlist_et_legacy_fermes(revue,monkeypatch):
    client,racine,registre,cfg = revue
    original = registre.read_text()
    contenu = json.loads(original)
    contenu['reviseurs']=[]
    registre.write_text(json.dumps(contenu))
    assert client.get(ROUTE+'?designation=a',headers=ADMIN).status_code == 403
    registre.write_text(original)
    monkeypatch.setattr(api,'_rbac',RegistreRBAC(actif=False))
    assert client.get(ROUTE+'?designation=a').status_code == 403


@pytest.mark.parametrize('identite',['code_a','mesures_a','ABSENT'])
def test_type_ou_lot_inconnu_refuse(fiscal,identite):
    client,*_ = fiscal
    r = client.get(BASE+'/lots/'+identite+'/tariff-candidates?designation=a',headers=ADMIN)
    assert r.status_code == (404 if identite=='ABSENT' else 422) and 'resultat' not in r.json()


def test_audit_et_manifestes_avant_apres_obligatoires(revue,monkeypatch):
    from unocr.routes import customs_review
    client,racine,registre,cfg = revue
    url = ROUTE+'?designation=equipement'
    def panne(*a,**kw):
        raise AuditIndisponible('SECRET_TEST')
    with monkeypatch.context() as m:
        m.setattr(api,'audit_obligatoire',panne)
        r = client.get(url,headers=ADMIN)
        assert r.status_code == 503 and 'resultat' not in r.json() and 'SECRET_TEST' not in r.text
    original = customs_review.rechercher_pistes_tarifaires
    def changer(*a,**kw):
        rep = original(*a,**kw)
        rep['archive']['manifest_sha256']='f'*64
        return rep
    with monkeypatch.context() as m:
        m.setattr(customs_review,'rechercher_pistes_tarifaires',changer)
        r = client.get(url,headers=ADMIN)
        assert r.status_code == 409 and 'resultat' not in r.json()
    manifeste = racine/'tarif_a/manifest.json'
    manifeste.write_text(manifeste.read_text()+'\n')
    r = client.get(url,headers=ADMIN)
    assert r.status_code == 409 and 'resultat' not in r.json()


@pytest.mark.parametrize('mutation',[
    lambda o:o['resultat']['resultats'][0].update(rang_documentaire=9),
    lambda o:o['resultat']['resultats'][0]['termes_non_retrouves_par_critere'].update(matiere=[]),
    lambda o:o['resultat']['resultats'][0]['indicateurs_tri'].update(nombre_criteres_complets=100),
    lambda o:o['resultat']['resultats'][0]['positions_par_critere']['designation']['equipement'][0].update(correspondance_debut=9),
    lambda o:o['resultat']['resultats'].reverse(),
    lambda o:o['resultat'].update(candidat_retenu_automatiquement=True),
])
def test_resultat_complet_compare_sans_recopier(revue,mutation):
    _,racine,*_ = revue
    fichier,objet = exporter(revue,{'designation':'equipement','matiere':'acier'})
    mutation(objet)
    fichier.write_text(json.dumps(objet))
    r = verifier_rejeu_export(fichier,racine/'tarif_a','tarif_a','tarif')
    assert r['rapport_identique'] is False
    assert 'resultats' not in r and 'termes_non_retrouves_par_critere' not in r


def test_types_parametres_et_legacy_refuses_avant_archive(revue):
    _,racine,registre,cfg = revue
    fichier,objet = exporter(revue,{'designation':'equipement'})
    for t in ('code','mesures'):
        with pytest.raises(ExportRefuse,match='Route'):
            verifier_rejeu_export(fichier,racine/'ABSENT','tarif_a',t)
    with pytest.raises(ExportRefuse,match='Route'):
        verifier_rejeu_criteres(fichier,racine/'ABSENT','tarif_a')
    for suffixe in ('designation=a&path=/etc/passwd','designation=a&designation=b','designation=a&offset=1e2'):
        objet['requete_relative']=ROUTE+'?'+suffixe
        fichier.write_text(json.dumps(objet))
        with pytest.raises(ExportRefuse):
            verifier_rejeu_export(fichier,racine/'ABSENT','tarif_a','tarif')


def test_cli_rejeu_zero_un_deux(revue,capsys):
    _,racine,*_ = revue
    fichier,objet = exporter(revue,{'designation':'equipement','matiere':'acier'})
    args=['customs-review-export-replay',str(fichier),'--lot',str(racine/'tarif_a'),'--lot-id','tarif_a']
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)['rapport_identique'] is True
    objet['resultat']['resultats'][0]['rang_documentaire']=99
    fichier.write_text(json.dumps(objet))
    assert main(args) == 1
    capsys.readouterr()
    assert main([*args,'--type-lot','code']) == 2
    assert json.loads(capsys.readouterr().out)['statut'] == 'refuse'


def test_source_archive_alteree_refusee_sans_resultat(revue):
    client,racine,*_ = revue
    source = racine/'tarif_a/source_recue.json'
    source.write_text(source.read_text()+'\n')
    r = client.get(ROUTE+'?designation=equipement',headers=ADMIN)
    assert r.status_code == 409 and 'resultat' not in r.json()
