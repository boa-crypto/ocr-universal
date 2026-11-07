"""Recette réelle des générateurs : aucune réécriture implicite du corpus Git."""
import hashlib
import json
from contextlib import closing
from pathlib import Path

import make_fixtures
import parcours_fixtures
import pypdfium2 as pdfium
import pytest
from docx import Document


def empreintes(dossier):
    return {str(p.relative_to(dossier)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in dossier.rglob('*') if p.is_file()}


def texte_pdf(chemin):
    with pdfium.PdfDocument(chemin) as document:
        with closing(document[0]) as page:
            with closing(page.get_textpage()) as texte:
                return texte.get_text_range()


def test_fixture_session_generee_hors_corpus_git(fixtures_dir,ground_truth):
    assert fixtures_dir.is_dir()
    assert not fixtures_dir.is_relative_to(make_fixtures.FIXTURES)
    assert ground_truth
    assert all((fixtures_dir/nom).is_file() for nom in ground_truth)
    assert ground_truth == json.loads((fixtures_dir/'ground_truth.json').read_text())
    assert 'FACTURE' in texte_pdf(fixtures_dir/'text_pdf.pdf')
    assert Document(fixtures_dir/'letter.docx').paragraphs


def test_generation_explicite_sans_fallback_ni_etat_global(tmp_path,monkeypatch):
    source = make_fixtures.FIXTURES
    avant = empreintes(source)
    interdit = tmp_path/'ne-pas-creer'
    monkeypatch.setattr(make_fixtures,'FIXTURES',interdit)
    a,b = tmp_path/'premiere',tmp_path/'seconde'
    gt_a = make_fixtures.make_all(a)
    # La modification locale d'un fichier généré ne doit pas toucher la seconde
    # génération, ni être restaurée implicitement dans la première.
    (a/'text_pdf.pdf').write_bytes(b'fixture locale volontairement modifiee')
    gt_b = make_fixtures.make_all(b)
    assert gt_a == gt_b
    assert make_fixtures.FIXTURES == interdit and not interdit.exists()
    assert (a/'text_pdf.pdf').read_bytes() == b'fixture locale volontairement modifiee'
    assert 'FACTURE' in texte_pdf(b/'text_pdf.pdf')
    assert set(empreintes(b)) == {*gt_b,'corrupt.pdf','ground_truth.json'}
    assert empreintes(source) == avant


def test_photos_destinees_au_dossier_fourni_seulement(tmp_path,monkeypatch):
    interdit = tmp_path/'interdit'
    monkeypatch.setattr(make_fixtures,'FIXTURES',interdit)
    destination = tmp_path/'photos'
    noms = make_fixtures.make_capture_images(destination)
    assert noms and all((destination/nom).is_file() for nom in noms)
    assert not interdit.exists()


@pytest.mark.parametrize('destination_explicite',[True,False])
def test_parcours_avec_destination_et_compatibilite_defaut(tmp_path,monkeypatch,destination_explicite):
    source = parcours_fixtures.FIXTURES
    avant = empreintes(source)
    defaut = tmp_path/'defaut-substitue-pour-test'
    monkeypatch.setattr(parcours_fixtures,'FIXTURES',defaut)
    destination = tmp_path/'parcours'
    documents = parcours_fixtures.creer_fixtures(destination) if destination_explicite else parcours_fixtures.creer_fixtures()
    attendu = destination if destination_explicite else defaut
    assert {p.parent for p in documents.values()} == {attendu}
    for role,marqueur in [('facture','COMMERCIAL INVOICE'),('bl','BILL OF LADING'),('colisage','PACKING LIST')]:
        assert marqueur in texte_pdf(documents[role])
    assert empreintes(source) == avant
    if destination_explicite:
        assert not defaut.exists()


@pytest.mark.parametrize('generateur',[make_fixtures.make_all,make_fixtures.make_capture_images,parcours_fixtures.creer_fixtures])
def test_destination_invalide_ne_declenche_pas_repli(tmp_path,monkeypatch,generateur):
    interdit = tmp_path/'interdit'
    monkeypatch.setattr(make_fixtures,'FIXTURES',interdit)
    monkeypatch.setattr(parcours_fixtures,'FIXTURES',interdit)
    invalide = tmp_path/'pas-un-dossier'
    invalide.write_bytes(b'conserver')
    with pytest.raises(OSError):
        generateur(invalide)
    assert invalide.read_bytes() == b'conserver' and not interdit.exists()


def test_make_all_defaut_manuel_compatible(tmp_path,monkeypatch):
    # Aucun appel sans destination dans fixtures_dir pytest. La commande manuelle
    # conserve sa destination historique ; ici elle est substituée, jamais Git.
    destination = tmp_path/'defaut-manuel'
    monkeypatch.setattr(make_fixtures,'FIXTURES',destination)
    gt = make_fixtures.make_all()
    assert gt == json.loads((destination/'ground_truth.json').read_text())
    assert make_fixtures.FIXTURES == destination
    assert Path(destination/'text_pdf.pdf').is_file()
