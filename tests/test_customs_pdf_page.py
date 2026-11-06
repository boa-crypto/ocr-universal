"""PDF ReportLab NON OFFICIELS, texte natif ; aucune preuve réglementaire."""
import hashlib
import io
import json
import subprocess
from types import SimpleNamespace

import pytest
from reportlab.pdfgen import canvas

from tests import test_customs_review
from tests.test_customs_legal import fichiers_code
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.pdf_page import LecturePDFRefusee, ParamPDFInvalide, lire_page_pdf
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue


def preparer_pdf(root, destination, chiffre=False):
    root.mkdir(exist_ok=True)
    transcription, metadata = fichiers_code(root)
    meta = json.loads(metadata.read_text())
    for doc in meta["documents"]:
        sortie = io.BytesIO()
        pdf = canvas.Canvas(sortie, encrypt="TEST_NON_OFFICIEL" if chiffre else None)
        pdf.drawString(40, 700, "FIXTURE NON OFFICIELLE PAGE UNE")
        pdf.showPage()
        pdf.drawString(40, 700, "FIXTURE NON OFFICIELLE PAGE DEUX")
        pdf.showPage()
        pdf.showPage()  # page blanche explicite, pas OCR
        pdf.save()
        contenu = sortie.getvalue()
        (root / doc["fichier_recu"]).write_bytes(contenu)
        doc["document"]["sha256"] = hashlib.sha256(contenu).hexdigest()
    metadata.write_text(json.dumps(meta))
    preparer_code(transcription, metadata, destination)
    return destination


def test_page_native_fragments_unicode_et_octets_preserves(tmp_path):
    lot = preparer_pdf(tmp_path / "entrees", tmp_path / "lot")
    avant = snapshot(tmp_path)
    rep = lire_page_pdf(lot, "TEST_O")
    assert "PAGE UNE" in rep["fragment"] and rep["nombre_pages_pdf"] == 3
    assert rep["page_physique_suivante"] == 2
    assert rep["validation_juridique"] == "non_validee"
    assert rep["transcription_verification"] == "non_verifiee"
    assert rep["sha256_pdf_lu"] == hashlib.sha256((lot / "document_0001.pdf").read_bytes()).hexdigest()
    a = lire_page_pdf(lot, "TEST_O", limite=10)
    b = lire_page_pdf(lot, "TEST_O", decalage=10)
    assert a["fragment"] + b["fragment"] == rep["fragment"]
    assert a["decalage_suivant"] == 10
    assert "PAGE DEUX" in lire_page_pdf(lot, "TEST_O", page=2)["fragment"]
    assert lire_page_pdf(lot, "TEST_O", decalage=1000)["fragment"] == ""
    vide = lire_page_pdf(lot, "TEST_O", page=3)
    assert vide["texte_natif_non_vide"] is False and vide["fragment"] == ""
    assert vide["page_physique_suivante"] is None
    assert snapshot(tmp_path) == avant


@pytest.mark.parametrize("kwargs", [{"document_id": ""}, {"document_id": "x\n"}, {"document_id": "x"*257},
    {"page": 0}, {"page": True}, {"page": 10001}, {"limite": 0}, {"limite": True}, {"limite": 16001},
    {"decalage": -1}, {"decalage": True}, {"decalage": 67108865}])
def test_parametres_avant_acces_disque(tmp_path, kwargs):
    valeurs = {"document_id": "TEST_O", **kwargs}
    with pytest.raises(ParamPDFInvalide):
        lire_page_pdf(tmp_path / "absent", **valeurs)


@pytest.mark.parametrize("document,page", [("INCONNU", 1), ("TEST_O", 4)])
def test_document_ou_page_absent_refuse(tmp_path, document, page):
    lot = preparer_pdf(tmp_path / "entrees", tmp_path / "lot")
    with pytest.raises(LecturePDFRefusee):
        lire_page_pdf(lot, document, page)


@pytest.mark.parametrize("defaut", ["absent", "corrompu", "symlink"])
def test_integrite_avant_parseur(tmp_path, defaut):
    lot = preparer_pdf(tmp_path / "entrees", tmp_path / "lot")
    cible = lot / "document_0001.pdf"
    if defaut == "absent":
        cible.unlink()
    elif defaut == "corrompu":
        cible.write_bytes(b"%PDF-1.7 NON OFFICIEL INVALIDE")
    else:
        autre = tmp_path / "original.pdf"
        autre.write_bytes(cible.read_bytes())
        cible.unlink()
        cible.symlink_to(autre)
    with pytest.raises(ValueError):
        lire_page_pdf(lot, "TEST_O")


def test_signature_opaque_archivee_mais_pas_pdf_lisible(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    preparer_code(transcription, metadata, tmp_path / "lot")
    with pytest.raises(LecturePDFRefusee):
        lire_page_pdf(tmp_path / "lot", "TEST_O")


@pytest.mark.parametrize("mode", ["timeout", "crash", "json", "type", "taille"])
def test_echecs_worker_generiques_sans_valeur_sensible(tmp_path, monkeypatch, mode):
    from unocr.customs_reference import pdf_page
    lot = preparer_pdf(tmp_path / "entrees", tmp_path / "lot")
    def worker(*args, **kwargs):
        assert kwargs["timeout"] == 15
        assert isinstance(kwargs["input"], bytes) and kwargs["input"].startswith(b"%PDF-")
        if mode == "timeout":
            raise subprocess.TimeoutExpired("SECRET_TEST", 15)
        stdout = {"json": b"SECRET_TEST", "type": b'{"texte":1,"nombre_pages":3}',
                  "taille": b"x" * (3*1024*1024+1)}.get(mode, b"SECRET_TEST")
        return SimpleNamespace(returncode=-9 if mode == "crash" else 0, stdout=stdout)
    monkeypatch.setattr(pdf_page.subprocess, "run", worker)
    with pytest.raises(LecturePDFRefusee) as erreur:
        lire_page_pdf(lot, "TEST_O")
    assert "SECRET_TEST" not in str(erreur.value)


def test_cli_sortie_json_et_refus(tmp_path, capsys):
    lot = preparer_pdf(tmp_path / "entrees", tmp_path / "lot")
    assert main(["customs-code-pdf-read", str(lot), "--document", "TEST_O", "--limit", "10"]) == 0
    assert json.loads(capsys.readouterr().out)["limite"] == 10
    assert main(["customs-code-pdf-read", str(lot), "--document", "ABSENT"]) == 2


@pytest.fixture()
def revue_pdf(revue):
    client, racine, registre, cfg = revue
    lot = preparer_pdf(cfg.root / "pdf_entrees", racine / "code_pdf")
    reg = json.loads(registre.read_text())
    reg["lots"].append({"id": "code_pdf", "dossier": "code_pdf", "type_lot": "code",
                        "manifest_sha256": hashlib.sha256((lot / "manifest.json").read_bytes()).hexdigest()})
    registre.write_text(json.dumps(reg))
    return client, racine, registre, cfg


def test_api_epingle_audit_no_store_et_aucune_ecriture_corpus(revue_pdf):
    client, racine, registre, cfg = revue_pdf
    avant = snapshot(racine)
    r = client.get(BASE + "/lots/code_pdf/pdf?document_id=TEST_O&page=2&limit=10", headers=ADMIN)
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    assert r.json()["resultat"]["page_physique"] == 2
    evenements = [json.loads(ligne) for ligne in (cfg.log_dir / "audit.log").read_text().splitlines()]
    succes = [v for v in evenements if v["event"] == "revue_douaniere" and v["statut"] == 200][-1]
    assert succes["operation"] == "lecture_pdf" and succes["manifestes"].keys() == {"code_pdf"}
    assert "PAGE DEUX" not in json.dumps(succes)
    assert snapshot(racine) == avant


def test_api_pdf_audit_obligatoire(revue_pdf, monkeypatch):
    from unocr import api
    client, racine, registre, cfg = revue_pdf
    def panne(*a, **kw):
        raise AuditIndisponible("SECRET_TEST")
    monkeypatch.setattr(api, "audit_obligatoire", panne)
    r = client.get(BASE + "/lots/code_pdf/pdf?document_id=TEST_O", headers=ADMIN)
    assert r.status_code == 503 and "resultat" not in r.json() and "SECRET_TEST" not in r.text


@pytest.mark.parametrize("route,headers,statut", [
    ("/lots/code_pdf/pdf?document_id=TEST_O", {}, 401),
    ("/lots/code_pdf/pdf?document_id=TEST_O", {"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"}, 403),
    ("/lots/tarif_a/pdf?document_id=TEST_O", ADMIN, 422),
    ("/lots/code_pdf/pdf?document_id=TEST_O&page=0", ADMIN, 422),
    ("/lots/code_pdf/pdf?document_id=ABSENT", ADMIN, 409),
])
def test_refus_api(revue_pdf, route, headers, statut):
    client, racine, registre, cfg = revue_pdf
    r = client.get(BASE + route, headers=headers)
    assert r.status_code == statut and "resultat" not in r.json()


def test_pdf_chiffre_refuse_sans_mot_de_passe(tmp_path):
    lot = preparer_pdf(tmp_path / "entrees", tmp_path / "lot", chiffre=True)
    avant = snapshot(tmp_path)
    with pytest.raises(LecturePDFRefusee):
        lire_page_pdf(lot, "TEST_O")
    assert snapshot(tmp_path) == avant
