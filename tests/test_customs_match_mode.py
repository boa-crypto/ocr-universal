"""Mots entiers NORMALISÉS, pas morphologie ou synonymes ; fixtures NON OFFICIELLES."""
import copy
import hashlib
import json

import pytest

from tests import test_customs_review
from tests.test_customs_reference import fichiers, snapshot
from tests.test_customs_review import ADMIN, BASE
from tests.test_customs_search import lot_tarif
from unocr.cli import main
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.match_mode import indice_terme
from unocr.customs_reference.review_export import MARQUEURS, analyser_export
from unocr.customs_reference.search import ParamRechercheInvalide, _normaliser
from unocr.customs_reference.search_excerpt import localiser_termes
from unocr.customs_reference.tariff_criteria import rechercher_tarif_criteres

revue = test_customs_review.revue


@pytest.mark.parametrize("texte,terme,position",[
    ("glacier acier", "acier",8),("acier", "acier",0),("aciereux", "acier",-1),
    ("acier-inox", "acier",0),("non_acier", "acier",4),
    ("معداتهم مُعَـدَّات", "معدات",8),("المعدات", "معدات",-1),
    ("😀 ŒUVRÉ", "oeuvre",0),("ß ss", "ss",0),("ﻻ", "لا",0),("¼", "4",2),
])
def test_frontieres_et_positions_unicode(texte,terme,position):
    normalise = _normaliser(texte)
    assert indice_terme(normalise,terme,"mots_entiers") == position
    spans = localiser_termes(texte,[terme],"mots_entiers")
    if position<0:
        assert spans == {}
    else:
        debut,fin = spans[terme]
        assert terme in _normaliser(texte[debut:fin])


def test_pas_motif_regex_et_mode_inconnu():
    assert indice_terme("acier", ".*", "mots_entiers") == -1
    with pytest.raises(ValueError):
        indice_terme("acier","acier","regex")


@pytest.mark.parametrize("mode",[None,True,0,[],{},"", "REGEX", "mots_entiers "])
def test_mode_invalide_avant_lecture(tmp_path,mode):
    with pytest.raises(ParamRechercheInvalide):
        rechercher_tarif_criteres(tmp_path / "ABSENT",designation="acier",match_mode=mode)


def test_modes_distincts_et_spans_apres_faux_positif(tmp_path):
    source,metadata = fichiers(tmp_path)
    base = json.loads(source.read_text())[0]
    lignes = []
    for i,fr in enumerate(("glacier acier NON OFFICIEL","glacier NON OFFICIEL", "acier inox NON OFFICIEL")):
        ligne = copy.deepcopy(base)
        ligne.update(id='TEST_'+str(i),code_tarifaire_10='010100000'+str(i),designation_officielle_fr=fr)
        lignes.append(ligne)
    source.write_text(json.dumps(lignes))
    meta = json.loads(metadata.read_text())
    meta['lot']['source']['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    lot = tmp_path / "lot"
    preparer_tarif(source,metadata,lot)
    avant = snapshot(tmp_path)
    a = rechercher_tarif_criteres(lot,matiere="acier")
    b = rechercher_tarif_criteres(lot,matiere="acier",match_mode="mots_entiers",limite=1)
    assert a['total_correspondances'] == 3 and b['total_correspondances'] == 2
    assert a['resultats'][0]['positions_par_critere']['matiere']['acier'][0]['correspondance_debut'] == 2
    assert b['resultats'][0]['positions_par_critere']['matiere']['acier'][0]['correspondance_debut'] == 8
    assert b['resultats'][0]['extraits_correspondants'][0]['correspondance_debut'] == 8
    suite = rechercher_tarif_criteres(lot,matiere="acier",match_mode="mots_entiers",limite=1,decalage=b['decalage_suivant'])
    assert suite['filtres'] == b['filtres'] and suite['decalage_suivant'] is None
    assert b['mode'] == 'conjonction_criteres_mots_entiers'
    assert not any('Sous-chaînes littérales' in a for a in b['avertissements'])
    assert snapshot(tmp_path) == avant


def test_fr_ar_conjonction_pas_flexion_ni_traduction_et_prefixe_seul(tmp_path):
    lot = lot_tarif(tmp_path)
    r = rechercher_tarif_criteres(lot,designation="équipement",fonction="معدات اختبار",match_mode="mots_entiers")
    assert r['total_correspondances'] == 1
    for terme in ("équipements","pompes","quip"):
        assert rechercher_tarif_criteres(lot,designation=terme,match_mode="mots_entiers")['total_correspondances'] == 0
    assert rechercher_tarif_criteres(lot,code_prefix="0101",match_mode="mots_entiers")['total_correspondances'] == 5


def test_cli_mode_et_defaut(tmp_path,capsys):
    lot = lot_tarif(tmp_path)
    for args,total in (([],2),(['--match-mode','mots_entiers'],0)):
        assert main(['customs-tariff-criteria',str(lot),'--designation','quipement',*args]) == 0
        assert json.loads(capsys.readouterr().out)['total_correspondances'] == total


def test_api_modes_audit_export_et_refus(revue):
    client,racine,registre,cfg = revue
    avant = snapshot(racine)
    route = BASE+'/lots/tarif_a/tariff-criteria?designation=quipement'
    assert client.get(route,headers=ADMIN).json()['resultat']['total_correspondances'] == 2
    r = client.get(route+'&match_mode=mots_entiers',headers=ADMIN)
    assert r.status_code == 200 and r.headers['cache-control'] == 'no-store'
    rep = r.json()['resultat']
    assert rep['total_correspondances'] == 0 and rep['filtres']['match_mode'] == 'mots_entiers'
    exp = {**MARQUEURS,'horodatage_client_non_certifie':'2026-11-07T00:00:00.000Z','requete_relative':route+'&match_mode=mots_entiers','resultat':rep}
    assert analyser_export(json.dumps(exp).encode())['statut'] == 'structure_compatible'
    assert client.get(route+'&match_mode=regex',headers=ADMIN).status_code == 422
    assert client.get(route+'&match_mode=mots_entiers').status_code == 401
    events = [json.loads(v) for v in (cfg.log_dir / 'audit.log').read_text().splitlines()]
    assert any(e.get('operation')=='recherche_tarif_criteres' and e['statut']==200 for e in events)
    assert snapshot(racine) == avant
