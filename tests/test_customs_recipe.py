"""Contrôle du lanceur de recette ; simulations de processus, pas de résultats OCR."""
import json
import subprocess
from pathlib import Path

import pytest

from scripts import customs_review_recipe as outil


def test_selection_complete_et_stable():
    selection = outil.selectionner(outil.ROOT)
    assert selection == sorted(set(selection))
    assert 'tests/test_fixture_isolation.py' in selection
    assert 'tests/test_customs_review_ui.py' in selection
    assert 'tests/test_customs_recipe.py' in selection
    assert {str(p.relative_to(outil.ROOT)) for p in (outil.ROOT/'tests').glob('test_customs*.py')} <= set(selection)
    assert 'tests/test_ocr.py' not in selection


@pytest.mark.parametrize('manquant',['customs','support'])
def test_selection_absente_ou_partielle_refusee(tmp_path,manquant):
    tests = tmp_path/'tests'
    tests.mkdir()
    if manquant != 'customs':
        (tests/'test_customs_minimal.py').touch()
    if manquant != 'support':
        for nom in outil.SUPPORT:
            (tests/nom).touch()
    with pytest.raises(ValueError):
        outil.selectionner(tmp_path)


@pytest.mark.parametrize('codes',[(0,0,0),(1,0,0),(0,1,0),(0,0,1),(2,5,127)])
def test_codes_reels_agreges_sans_masquer_et_isolation(tmp_path,monkeypatch,codes):
    appels = []
    environnements = []
    monkeypatch.setenv('UNOCR_DATA_DIR','NE_PAS_UTILISER')
    def processus(commande,**options):
        assert options['cwd'] == outil.ROOT
        assert options['check'] is False
        assert 'shell' not in options
        environnement = options['env']
        environnements.append(environnement)
        for cle in ('UNOCR_DATA_DIR','UNOCR_LOG_DIR','UNOCR_USER_PROFILES_DIR'):
            assert environnement[cle] != 'NE_PAS_UTILISER'
            assert Path(environnement[cle]).parent.is_dir()
        ecrire_junit(commande)
        appels.append(commande)
        return subprocess.CompletedProcess(commande,codes[len(appels)-1])
    monkeypatch.setattr(outil.subprocess,'run',processus)
    code = outil.recette(tmp_path)
    assert len(appels) == 3 and code == int(any(codes))
    rapport = json.loads(next(tmp_path.glob('recette-*/recette.json')).read_text())
    assert [e['code_sortie'] for e in rapport['etapes']] == list(codes)
    assert rapport['suite_complete_executee'] is False
    assert rapport['validation_juridique'] == 'non_validee'
    assert rapport['code_sortie'] == code
    assert not Path(environnements[0]['UNOCR_DATA_DIR']).parent.exists()
    assert all('NE_PAS_UTILISER' not in json.dumps(e) for e in rapport['etapes'])


def test_commande_absente_en_echec_et_journal(tmp_path,monkeypatch):
    def absent(*a,**kw):
        raise FileNotFoundError('NE_PAS_RECOPIER')
    monkeypatch.setattr(outil.subprocess,'run',absent)
    r = outil.executer('commande',['inexistante'],tmp_path,{})
    assert r['code_sortie'] == 127
    assert 'NE_PAS_RECOPIER' not in (tmp_path/r['journal']).read_text()


def test_deux_invocations_sans_reutiliser_resultats(tmp_path,monkeypatch):
    def processus(commande,**kw):
        ecrire_junit(commande)
        return subprocess.CompletedProcess(commande,0)
    monkeypatch.setattr(outil.subprocess,'run',processus)
    assert outil.recette(tmp_path) == 0
    assert outil.recette(tmp_path) == 0
    dossiers = list(tmp_path.glob('recette-*'))
    assert len(dossiers) == 2
    assert all((p/'recette.json').is_file() for p in dossiers)


def test_refus_artefacts_dans_depot():
    with pytest.raises(SystemExit) as erreur:
        outil.main(['--artifacts',str(outil.ROOT/'data')])
    assert erreur.value.code == 2


def test_erreur_destination_code_deux(tmp_path):
    fichier = tmp_path/'fichier'
    fichier.touch()
    assert outil.main(['--artifacts',str(fichier)]) == 2


def ecrire_junit(commande):
    for arg in commande:
        if arg.startswith('--junitxml='):
            Path(arg.split('=',1)[1]).write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"/></testsuites>')


@pytest.mark.parametrize('contenu',[None,'invalide','<testsuites/>',
    '<testsuite tests="1" failures="0" errors="0" skipped="1"/>',
    '<testsuite tests="1" failures="1" errors="0" skipped="0"/>',
    '<testsuite tests="0" failures="0" errors="0" skipped="0"/>'])
def test_zero_processus_ne_suffit_pas_sans_junit_complet(tmp_path,monkeypatch,contenu):
    def processus(commande,**kw):
        for arg in commande:
            if arg.startswith('--junitxml=') and contenu is not None:
                Path(arg.split('=',1)[1]).write_text(contenu)
        return subprocess.CompletedProcess(commande,0)
    monkeypatch.setattr(outil.subprocess,'run',processus)
    assert outil.recette(tmp_path) == 1
    rapport = json.loads(next(tmp_path.glob('recette-*/recette.json')).read_text())
    assert rapport['junit']['selection_sans_echec_ni_ignore'] is False
