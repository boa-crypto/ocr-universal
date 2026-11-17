"""Références d'empreintes indépendantes de la donnée contrôlée, sans signature."""
import hashlib
import json

import pytest

from tests import test_customs_export_replay_pair
from tests.test_customs_export_replay import exporter
from tests.test_customs_export_replay_pdf import exporter as exporter_pdf
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.export_replay import verifier_rejeu_criteres, verifier_rejeu_export
from unocr.customs_reference.export_replay_pair import verifier_rejeu_paire
from unocr.customs_reference.review_export import ExportRefuse

revue = test_customs_export_replay_pair.revue
fiscal = test_customs_export_replay_pair.fiscal
paire = test_customs_export_replay_pair.paire


def sha(fichier):
    return hashlib.sha256(fichier.read_bytes()).hexdigest()


@pytest.mark.parametrize('export_pin,manifest_pin,nombre',[(False,False,0),(True,False,1),(False,True,1),(True,True,2)])
def test_references_correctes_ou_absentes_sans_mutation(tmp_path,export_pin,manifest_pin,nombre):
    fichier,lot,_ = exporter(tmp_path)
    arguments = {'sha256_export_attendu':sha(fichier) if export_pin else None,
                 'manifest_sha256_attendu':sha(lot/'manifest.json') if manifest_pin else None}
    avant = snapshot(tmp_path)
    r = verifier_rejeu_criteres(fichier,lot,'TEST',**arguments)
    assert r['rapport_identique'] is True
    assert r['empreintes_attendues']['nombre_empreintes_verifiees'] == nombre
    assert r['empreintes_attendues']['authenticite_des_references_verifiee'] is False
    r = verifier_rejeu_export(fichier,lot,'TEST','tarif',**arguments)
    assert r['empreintes_attendues']['manifestes_epingles']['unique'] is manifest_pin
    assert snapshot(tmp_path) == avant


@pytest.mark.parametrize('valeur',[True,0,[],{},'', 'A'*64,'a'*63,'g'*64])
@pytest.mark.parametrize('cle',['sha256_export_attendu','manifest_sha256_attendu'])
def test_formats_refuses_avant_export(tmp_path,cle,valeur):
    with pytest.raises(ExportRefuse,match='Empreinte attendue'):
        verifier_rejeu_export(tmp_path/'ABSENT',tmp_path/'ABSENT','TEST','tarif',**{cle:valeur})


def test_enveloppe_modifiee_identique_sans_pin_mais_refusee_avec_pin(tmp_path):
    fichier,lot,objet = exporter(tmp_path)
    reference = sha(fichier)
    objet['horodatage_client_non_certifie'] = '2000-01-01T00:00:00.000Z'
    fichier.write_text(json.dumps(objet))
    assert verifier_rejeu_export(fichier,lot,'TEST','tarif')['rapport_identique'] is True
    with pytest.raises(ExportRefuse,match="Export différent"):
        verifier_rejeu_export(fichier,lot,'TEST','tarif',sha256_export_attendu=reference)


def test_mauvaise_reference_export_avant_analyse_json(tmp_path,monkeypatch):
    from unocr.customs_reference import export_replay
    fichier = tmp_path/'invalide.json'
    fichier.write_text('SECRET_EXPORT_INVALIDE')
    def interdit(*a,**kw):
        pytest.fail('Pas de parsing JSON si empreinte des octets différente')
    monkeypatch.setattr(export_replay,'analyser_export',interdit)
    with pytest.raises(ExportRefuse,match='Export différent') as erreur:
        verifier_rejeu_export(fichier,tmp_path/'ABSENT','TEST','tarif',sha256_export_attendu='a'*64)
    assert 'SECRET_EXPORT' not in str(erreur.value)


def test_mauvais_manifeste_refuse_avant_lecteur_pdf(tmp_path,monkeypatch):
    from unocr.customs_reference import export_replay_routes
    fichier,lot,_ = exporter_pdf(tmp_path,'code','pdf',{'document_id':'TEST_O'})
    def interdit(*a,**kw):
        pytest.fail('Pas de worker/lecteur PDF avec mauvais manifeste attendu')
    monkeypatch.setattr(export_replay_routes,'lire_page_pdf',interdit)
    with pytest.raises(ExportRefuse,match='Manifeste différent'):
        verifier_rejeu_export(fichier,lot,'TEST','code',autoriser_pdf=True,manifest_sha256_attendu='a'*64)


def test_manifeste_du_resultat_recontrole(tmp_path,monkeypatch):
    from unocr.customs_reference import export_replay_routes
    fichier,lot,_ = exporter(tmp_path)
    reference = sha(lot/'manifest.json')
    original = export_replay_routes.rechercher_tarif_criteres
    def modifier(*a,**kw):
        resultat = original(*a,**kw)
        resultat['archive']['manifest_sha256'] = 'a'*64
        return resultat
    monkeypatch.setattr(export_replay_routes,'rechercher_tarif_criteres',modifier)
    with pytest.raises(ExportRefuse,match='Manifeste du rejeu différent'):
        verifier_rejeu_export(fichier,lot,'TEST','tarif',manifest_sha256_attendu=reference)


def test_manifestes_symlink_et_dossier_symlink_refuses(tmp_path):
    fichier,lot,_ = exporter(tmp_path)
    reference = sha(lot/'manifest.json')
    lien = tmp_path/'lien_lot'
    lien.symlink_to(lot,target_is_directory=True)
    with pytest.raises(ExportRefuse):
        verifier_rejeu_export(fichier,lien,'TEST','tarif',manifest_sha256_attendu=reference)
    manifeste = lot/'manifest.json'
    copie = tmp_path/'copie_manifest.json'
    copie.write_bytes(manifeste.read_bytes())
    manifeste.unlink()
    manifeste.symlink_to(copie)
    with pytest.raises(ExportRefuse):
        verifier_rejeu_export(fichier,lot,'TEST','tarif',manifest_sha256_attendu=reference)


def test_paire_trois_pins_et_ordre_distinct(paire,capsys):
    client,racine,_,cfg = paire
    url = BASE+'/tariff-compare?avant=tarif_a&apres=tarif_b&code10=0101000000'
    fichier = test_customs_export_replay_pair.enregistrer(cfg,url,client.get(url,headers=ADMIN).json()['resultat'])
    a,b = racine/'tarif_a',racine/'tarif_b'
    pins = {'sha256_export_attendu':sha(fichier),'manifest_avant_attendu':sha(a/'manifest.json'),
            'manifest_apres_attendu':sha(b/'manifest.json')}
    r = verifier_rejeu_paire(fichier,a,b,'tarif_a','tarif_b','tarif','tarif',**pins)
    assert r['rapport_identique'] is True and r['empreintes_attendues']['nombre_empreintes_verifiees'] == 3
    args = ['customs-review-export-replay-pair',str(fichier),'--before-lot',str(a),'--after-lot',str(b),
        '--before-id','tarif_a','--after-id','tarif_b','--before-type','tarif','--after-type','tarif',
        '--expected-export-sha256',sha(fichier),'--expected-before-manifest-sha256',sha(a/'manifest.json'),
        '--expected-after-manifest-sha256',sha(b/'manifest.json')]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)['empreintes_attendues']['nombre_empreintes_verifiees'] == 3
    pins['manifest_avant_attendu'],pins['manifest_apres_attendu'] = pins['manifest_apres_attendu'],pins['manifest_avant_attendu']
    with pytest.raises(ExportRefuse,match='Manifeste différent'):
        verifier_rejeu_paire(fichier,a,b,'tarif_a','tarif_b','tarif','tarif',**pins)
    with pytest.raises(ExportRefuse,match='Empreinte attendue'):
        verifier_rejeu_paire(cfg.root/'ABSENT',a,b,'A','B','tarif','tarif',manifest_apres_attendu=True)


def test_cli_references_et_refus(tmp_path,capsys):
    fichier,lot,_ = exporter(tmp_path)
    args = ['customs-review-export-replay',str(fichier),'--lot',str(lot),'--lot-id','TEST',
            '--expected-export-sha256',sha(fichier),'--expected-manifest-sha256',sha(lot/'manifest.json')]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)['empreintes_attendues']['nombre_empreintes_verifiees'] == 2
    fichier.write_text(fichier.read_text()+'\n')
    assert main(args) == 2
    assert json.loads(capsys.readouterr().out)['statut'] == 'refuse'
