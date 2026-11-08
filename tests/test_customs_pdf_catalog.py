"""Catalogue physique de fixtures non officielles, y compris sans texte natif."""
import hashlib
import json

import pytest
from test_customs_pdf_index import indexe as indexe
from test_customs_review import ADMIN, BASE
from test_customs_review import revue as revue

from unocr.customs_reference.pdf_markers import cataloguer_pages
from unocr.customs_reference.search import ParamRechercheInvalide


@pytest.fixture()
def catalogue(indexe):
    r, f, _ = indexe
    data = json.loads(f.read_text())
    doc = next(d for d in data['documents'] if d['document_id'] == 'TEST_O')
    doc['pages'][1]['texte'] = ''
    doc['pages'][1]['sha256_texte_utf8'] = hashlib.sha256(b'').hexdigest()
    f.write_text(json.dumps(data, ensure_ascii=False))
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    reg = json.loads(r[2].read_text())
    next(lot for lot in reg['lots'] if lot['id'] == 'code_a')['index_pdf_sha256'] = sha
    r[2].write_text(json.dumps(reg))
    return r, f, sha


def test_catalogue_inclut_page_sans_texte_et_pagination(catalogue):
    r, f, sha = catalogue
    offset, items = 0, []
    while True:
        value = cataloguer_pages(r[1]/'code_a', f, sha, limite=1, decalage=offset)
        assert value['total_correspondances'] == 6
        assert value['requete'] == '' and value['articles_localises_automatiquement'] is False
        items.extend(value['resultats'])
        if value['decalage_suivant'] is None:
            break
        assert value['decalage_suivant'] == offset + 1
        offset = value['decalage_suivant']
    assert len({(i['document_id'], i['page_pdf']) for i in items}) == 6
    empty = next(i for i in items if i['document_id'] == 'TEST_O' and i['page_pdf'] == 2)
    assert empty['total_caracteres'] == 0 and empty['texte_indexe_present'] is False
    assert empty['sha256_texte_utf8'] == hashlib.sha256(b'').hexdigest()
    assert all('texte' not in i and 'fragment' not in i for i in items)


def test_filtre_page_et_document_exacts(catalogue):
    r, f, sha = catalogue
    value = cataloguer_pages(r[1]/'code_a', f, sha, 'TEST_O', 2)
    assert value['total_correspondances'] == 1
    assert value['resultats'][0]['page_pdf'] == 2
    assert value['resultats'][0]['nombre_pages_pdf'] == 2
    assert value['filtres'] == {'document_id_exact': 'TEST_O', 'page_physique_exacte': 2}
    assert cataloguer_pages(r[1]/'code_a', f, sha, page=2)['total_correspondances'] == 3
    assert cataloguer_pages(r[1]/'code_a', f, sha, 'ABSENT')['resultats'] == []
    assert cataloguer_pages(r[1]/'code_a', f, sha, page=3)['resultats'] == []
    assert cataloguer_pages(r[1]/'code_a', f, sha, decalage=100)['resultats'] == []


@pytest.mark.parametrize('page', [0, 10001, True, 1.5, '1'])
def test_page_invalide_avant_lecture(catalogue, page):
    r, f, sha = catalogue
    with pytest.raises(ParamRechercheInvalide):
        cataloguer_pages(r[1]/'code_a', f, sha, page=page)


@pytest.mark.parametrize('params', [{'page': 0}, {'page': 10001}, {'limit': 0}, {'offset': -1}, {'document_id': ' '}, {'document_id': '\x00'}])
def test_http_parametres_refuses(catalogue, params):
    r, _, _ = catalogue
    assert r[0].get(BASE+'/lots/code_a/pdf-index-catalog', params=params, headers=ADMIN).status_code == 422


def test_http_autorisation_integrite_et_no_store(catalogue):
    r, f, _ = catalogue
    url = BASE+'/lots/code_a/pdf-index-catalog'
    assert r[0].get(url).status_code == 401
    response = r[0].get(url, params={'document_id': 'TEST_O', 'page': 2}, headers=ADMIN)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    item = response.json()['resultat']['resultats'][0]
    page = r[0].get(BASE+'/lots/code_a/pdf-index-page', params={'document_id': item['document_id'], 'page': item['page_pdf']}, headers=ADMIN)
    assert page.status_code == 200
    assert page.json()['resultat']['fragment'] == ''
    assert page.json()['resultat']['sha256_texte_utf8'] == item['sha256_texte_utf8']
    f.write_text('{}')
    assert r[0].get(url, headers=ADMIN).status_code == 409


def test_source_modifiee_refusee(catalogue):
    r, _, _ = catalogue
    (r[1]/'code_a/document_0001.pdf').write_bytes(b'%PDF ALTERE')
    assert r[0].get(BASE+'/lots/code_a/pdf-index-catalog', headers=ADMIN).status_code == 409


def test_catalogue_reserve_au_code_et_lot_allowliste(catalogue):
    r, _, _ = catalogue
    assert r[0].get(BASE+'/lots/tarif_a/pdf-index-catalog', headers=ADMIN).status_code == 422
    assert r[0].get(BASE+'/lots/INCONNU/pdf-index-catalog', headers=ADMIN).status_code == 404


def test_reviseur_nominatif_obligatoire(catalogue):
    r, _, _ = catalogue
    url = BASE+'/lots/code_a/pdf-index-catalog'
    assert r[0].get(url, headers={'Authorization': 'Bearer TEST_LECTEUR_NON_PRODUCTION'}).status_code == 403
    reg = json.loads(r[2].read_text())
    reg['reviseurs'] = []
    r[2].write_text(json.dumps(reg))
    assert r[0].get(url, headers=ADMIN).status_code == 403


def test_audit_obligatoire_et_pas_de_fuite(catalogue, monkeypatch):
    from unocr import api
    from unocr.logging_setup import AuditIndisponible

    r, _, _ = catalogue
    def refuser(*args, **kwargs):
        raise AuditIndisponible('CHEMIN_INTERNE_TEST')
    monkeypatch.setattr(api, 'audit_obligatoire', refuser)
    response = r[0].get(BASE+'/lots/code_a/pdf-index-catalog', headers=ADMIN)
    assert response.status_code == 503
    assert response.headers['cache-control'] == 'no-store'
    assert 'resultat' not in response.json() and 'CHEMIN_INTERNE_TEST' not in response.text
