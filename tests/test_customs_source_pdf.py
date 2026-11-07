"""Copie exacte de PDF de fixtures NON OFFICIELLES, sans authenticité déduite."""
import hashlib
import json

import pytest

from tests import test_customs_review
from tests.test_customs_legal import fichiers_code
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.pdf_page import LecturePDFRefusee, ParamPDFInvalide
from unocr.customs_reference.source_pdf import copier_pdf_source
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue


def preparer(root):
    transcription,metadata = fichiers_code(root)
    lot = root / "lot"
    preparer_code(transcription,metadata,lot)
    return lot


def test_octets_originaux_et_provenance_sans_mutation(tmp_path):
    lot = preparer(tmp_path)
    avant = snapshot(tmp_path)
    rep,contenu = copier_pdf_source(lot,"TEST_O")
    assert contenu == (tmp_path / "FIXTURE_NON_OFFICIELLE_O.pdf").read_bytes()
    assert rep["sha256_pdf_copie"] == hashlib.sha256(contenu).hexdigest()
    assert rep["taille_octets"] == len(contenu)
    assert rep["nom_telechargement"] == "uniocr-source-non-validee-"+rep["sha256_pdf_copie"]+".pdf"
    assert rep["lecture_seule"] is True and rep["publication_active"] is False
    assert rep["validation_juridique"] == "non_validee" and rep["authenticite_documentaire"] == "non_etablie"
    assert snapshot(tmp_path) == avant


@pytest.mark.parametrize("identifiant",[None,True,12,""," ","x"*257,"x\x00","x\r\n","x\ud800"])
def test_parametres_avant_lecture(tmp_path,identifiant):
    with pytest.raises(ParamPDFInvalide):
        copier_pdf_source(tmp_path / "absent",identifiant)


def test_source_absente_et_rerelecture_modifiee(tmp_path,monkeypatch):
    import unocr.customs_reference.source_pdf as module
    lot = preparer(tmp_path)
    with pytest.raises(LecturePDFRefusee):
        copier_pdf_source(lot,"ABSENT")
    monkeypatch.setattr(module,"_lire",lambda p:b"%PDF-1.7\nMODIFICATION NON OFFICIELLE")
    with pytest.raises(LecturePDFRefusee):
        copier_pdf_source(lot,"TEST_O")


def test_api_octets_headers_audit_et_absence_de_chemin(revue):
    client,racine,registre,cfg = revue
    avant = snapshot(racine)
    r = client.get(BASE+"/lots/code_a/pdf-source?document_id=TEST_O",headers=ADMIN)
    assert r.status_code == 200 and r.content == (racine / "code_a/document_0001.pdf").read_bytes()
    sha = hashlib.sha256(r.content).hexdigest()
    assert r.headers["content-type"] == "application/pdf" and r.headers["cache-control"] == "no-store"
    assert r.headers["content-disposition"] == f'attachment; filename="uniocr-source-non-validee-{sha}.pdf"'
    assert r.headers["x-content-type-options"] == "nosniff" and "sandbox" in r.headers["content-security-policy"]
    assert r.headers["x-uniocr-source-sha256"] == sha and r.headers["x-uniocr-validation"] == "non_validee"
    assert r.headers["x-uniocr-manifest-sha256"] == hashlib.sha256((racine / "code_a/manifest.json").read_bytes()).hexdigest()
    assert int(r.headers["content-length"]) == len(r.content) and str(racine) not in str(r.headers)
    events = [json.loads(v) for v in (cfg.log_dir / "audit.log").read_text().splitlines()]
    event = [e for e in events if e.get("operation") == "copie_pdf_source"][-1]
    assert event["statut"] == 200 and event["manifestes"].keys() == {"code_a"}
    assert snapshot(racine) == avant


def test_audit_503_aucun_octet_pdf(revue,monkeypatch):
    from unocr import api
    client,*_ = revue
    def panne(*a,**kw):
        raise AuditIndisponible("SECRET_TEST")
    monkeypatch.setattr(api,"audit_obligatoire",panne)
    r = client.get(BASE+"/lots/code_a/pdf-source?document_id=TEST_O",headers=ADMIN)
    assert r.status_code == 503 and r.headers["content-type"] == "application/json"
    assert not r.content.startswith(b"%PDF") and "content-disposition" not in r.headers
    assert "SECRET_TEST" not in r.text


@pytest.mark.parametrize("moment",["avant","resultat","octets"])
def test_controles_integrite_api(revue,monkeypatch,moment):
    import unocr.routes.customs_review as routes
    client,racine,*_ = revue
    if moment == "avant":
        manifeste = racine / "code_a/manifest.json"
        manifeste.write_bytes(manifeste.read_bytes()+b" ")
    else:
        original = routes.copier_pdf_source
        def changer(*a,**kw):
            rep,contenu = original(*a,**kw)
            if moment == "resultat":
                rep["archive"]["manifest_sha256"] = "0"*64
            else:
                contenu += b"MODIFIE"
            return rep,contenu
        monkeypatch.setattr(routes,"copier_pdf_source",changer)
    r = client.get(BASE+"/lots/code_a/pdf-source?document_id=TEST_O",headers=ADMIN)
    assert r.status_code == 409 and not r.content.startswith(b"%PDF")


@pytest.mark.parametrize("route,headers,statut",[
    ("code_a/pdf-source?document_id=TEST_O",{},401),
    ("code_a/pdf-source?document_id=TEST_O",{"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403),
    ("tarif_a/pdf-source?document_id=TEST_O",ADMIN,422),("code_a/pdf-source?document_id=ABSENT",ADMIN,409),
    ("code_a/pdf-source",ADMIN,422),("absent/pdf-source?document_id=TEST_O",ADMIN,404)])
def test_refus_api(revue,route,headers,statut):
    client,*_ = revue
    r = client.get(BASE+"/lots/"+route,headers=headers)
    assert r.status_code == statut and r.headers["content-type"] == "application/json"
    assert "content-disposition" not in r.headers
