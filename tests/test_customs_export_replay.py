"""Rejeu indépendant d'exports NON OFFICIELS ; aucune identité authentifiée."""
import json
import os
from urllib.parse import urlencode

import pytest

from tests.test_customs_reference import snapshot
from tests.test_customs_search import lot_tarif
from unocr.cli import main
from unocr.customs_reference.export_replay import verifier_rejeu_criteres
from unocr.customs_reference.review_export import MARQUEURS, ExportRefuse
from unocr.customs_reference.tariff_criteria import rechercher_tarif_criteres


def exporter(tmp_path,params=None):
    lot = lot_tarif(tmp_path)
    params = {'designation':'ÉQUIPEMENT','match_mode':'mots_entiers','limit':'1'} if params is None else params
    arguments = {('limite' if k=='limit' else 'decalage' if k=='offset' else k):int(v) if k in ('limit','offset') else v
                 for k,v in params.items()}
    objet = {**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z',
        'requete_relative':'/api/v1/customs-review/lots/TEST/tariff-criteria?'+urlencode(params),
        'resultat':rechercher_tarif_criteres(lot,**arguments)}
    fichier = tmp_path / 'export.json'
    fichier.write_text(json.dumps(objet,ensure_ascii=False))
    return fichier,lot,objet


@pytest.mark.parametrize('params',[
    {'designation':'معدات','fonction':'mécanique'},
    {'designation':'équipement','limit':'1','offset':'1','match_mode':'mots_entiers'},
    {'designation':'pompe','usage':'معدات'},
    {'code_prefix':'99'}, {'code_prefix':'0101'},
])
def test_rejeu_integral_lecture_seule_sans_authenticite(tmp_path,params):
    fichier,lot,_ = exporter(tmp_path,params)
    avant = snapshot(tmp_path)
    r = verifier_rejeu_criteres(fichier,lot,'TEST')
    assert r['statut'] == 'rejeu_identique' and r['rapport_identique'] is True
    assert r['archive_fournie_coherente_au_rejeu'] is r['manifest_export_correspond'] is True
    assert r['authenticite_verifiee'] is r['identite_registre_verifiee'] is r['audit_serveur_verifie'] is False
    assert r['sha256_resultat_export_canonique'] == r['sha256_resultat_rejoue_canonique']
    assert 'ÉQUIPEMENT' not in json.dumps(r) and 'requete_relative' not in r
    assert snapshot(tmp_path) == avant


@pytest.mark.parametrize('mutation',[
    lambda o:o['resultat'].update(total_correspondances=999),
    lambda o:o['resultat']['resultats'][0]['positions_par_critere']['designation']['equipement'][0].update(correspondance_debut=9),
    lambda o:o['resultat'].update(occurrences_denombrees=0),  # false != 0 JSON
    lambda o:o['resultat'].update(total_correspondances=2.0),  # 2 != 2.0 JSON
    lambda o:o['resultat'].update(champ_ajoute='SECRET_NON_RECOPIE'),
    lambda o:o['resultat']['diagnostic_recherche']['par_critere']['designation'].update(lignes_tous_termes=0),
    lambda o:o['resultat'].pop('diagnostic_recherche'),  # ancienne version != rejeu courant
])
def test_modifications_detectees_sans_copier_contenu(tmp_path,mutation):
    fichier,lot,objet = exporter(tmp_path)
    mutation(objet)
    fichier.write_text(json.dumps(objet))
    r = verifier_rejeu_criteres(fichier,lot,'TEST')
    assert r['statut'] == 'rejeu_different' and r['rapport_identique'] is False
    assert r['manifest_export_correspond'] is True
    assert r['sha256_resultat_export_canonique'] != r['sha256_resultat_rejoue_canonique']
    assert 'SECRET_NON_RECOPIE' not in json.dumps(r)


def test_cle_ordonnee_indifferente_horodatage_non_rejoue(tmp_path):
    fichier,lot,objet = exporter(tmp_path)
    objet['horodatage_client_non_certifie'] = '2000-01-01T12:00:00.000Z'
    objet['resultat'] = dict(reversed(list(objet['resultat'].items())))
    fichier.write_text(json.dumps(objet,indent=4))
    assert verifier_rejeu_criteres(fichier,lot,'TEST')['rapport_identique'] is True


def test_liste_reordonnee_est_difference(tmp_path):
    fichier,lot,objet = exporter(tmp_path,{'designation':'équipement'})
    objet['resultat']['resultats'].reverse()
    fichier.write_text(json.dumps(objet))
    assert verifier_rejeu_criteres(fichier,lot,'TEST')['rapport_identique'] is False


@pytest.mark.parametrize('requete',[
    '/api/v1/customs-review/lots/TEST/search?q=x',
    '/api/v1/customs-review/lots/AUTRE/tariff-criteria?designation=x',
    '/api/v1/customs-review/lots/TEST/tariff-criteria?designation=x&designation=y',
    '/api/v1/customs-review/lots/TEST/tariff-criteria?designation=x&%64esignation=y',
    '/api/v1/customs-review/lots/TEST/tariff-criteria?file=/secret',
    '/api/v1/customs-review/lots/TEST/tariff-criteria?designation=%ZZ',
    '/api/v1/customs-review/lots/TEST/tariff-criteria?designation=%FF',
    '/api/v1/customs-review/lots/TEST/tariff-criteria?designation',
    '/api/v1/customs-review/lots/TEST/tariff-criteria?designation=x&limit=1e2',
    '/api/v1/customs-review/lots/TEST/tariff-criteria?designation=x&limit=+1',
    '/api/v1/customs-review/lots/TEST/tariff-criteria?designation=x&offset=10000000',
])
def test_route_ou_requete_refusee_avant_archive(tmp_path,requete,monkeypatch):
    from unocr.customs_reference import export_replay
    fichier,lot,objet = exporter(tmp_path)
    objet['requete_relative'] = requete
    fichier.write_text(json.dumps(objet))
    def interdit(*a,**kw):
        pytest.fail('Archive ne doit pas être chargée pour une requête ambiguë')
    monkeypatch.setattr(export_replay,'rechercher_tarif_criteres',interdit)
    with pytest.raises(ExportRefuse):
        verifier_rejeu_criteres(fichier,lot,'TEST')


def test_archive_modifiee_refusee_et_autre_archive_coherente_differente(tmp_path):
    dossier = tmp_path / 'premier'
    dossier.mkdir()
    fichier,lot,objet = exporter(dossier)
    autre = tmp_path / 'autre'
    autre.mkdir()
    _,lot2,_ = exporter(autre)
    r = verifier_rejeu_criteres(fichier,lot2,'TEST')
    assert r['manifest_export_correspond'] is False and r['rapport_identique'] is False
    (lot / 'source_recue.json').write_text('SECRET_FICHIER_INCOHERENT')
    with pytest.raises(ExportRefuse,match='Archive fournie ou paramètres') as erreur:
        verifier_rejeu_criteres(fichier,lot,'TEST')
    assert 'SECRET_FICHIER' not in str(erreur.value)


def test_fichier_borne_doublon_symlink_fifo(tmp_path):
    fichier,lot,objet = exporter(tmp_path)
    fichier.write_text('{"x":1,"x":2}')
    with pytest.raises(ExportRefuse):
        verifier_rejeu_criteres(fichier,lot,'TEST')
    lien = tmp_path / 'lien'
    lien.symlink_to(fichier)
    with pytest.raises(ExportRefuse):
        verifier_rejeu_criteres(lien,lot,'TEST')
    if hasattr(os, 'mkfifo'):
        fifo = tmp_path / 'fifo'
        os.mkfifo(fifo)
        with pytest.raises(ExportRefuse):
            verifier_rejeu_criteres(fifo,lot,'TEST')
    with fichier.open('wb') as f:
        f.truncate(10*1024*1024+1)
    with pytest.raises(ExportRefuse):
        verifier_rejeu_criteres(fichier,lot,'TEST')


@pytest.mark.parametrize('identite',[None,True,'../TEST','', 'x'*65])
def test_identite_explicite_avant_lecture(tmp_path,identite):
    with pytest.raises(ExportRefuse):
        verifier_rejeu_criteres(tmp_path/'ABSENT',tmp_path/'ABSENT',identite)


def test_cli_codes_zero_un_deux(tmp_path,capsys):
    fichier,lot,objet = exporter(tmp_path)
    args = ['customs-review-export-replay',str(fichier),'--lot',str(lot),'--lot-id','TEST']
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)['statut'] == 'rejeu_identique'
    objet['resultat']['total_correspondances'] = 999
    fichier.write_text(json.dumps(objet))
    assert main(args) == 1
    assert json.loads(capsys.readouterr().out)['statut'] == 'rejeu_different'
    fichier.write_text('INVALIDE')
    assert main(args) == 2
    assert json.loads(capsys.readouterr().out)['statut'] == 'refuse'
