"""Lecture native de fixtures PDF fiscales NON OFFICIELLES, sans validation."""
import hashlib
import json
import subprocess
from types import SimpleNamespace

import pytest
from reportlab.pdfgen import canvas

from tests import test_customs_review
from tests.test_customs_fiscal_pdf import fichiers
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.fiscal_importer import charger_lot_mesures, preparer_mesures_autonomes
from unocr.customs_reference.fiscal_pdf_page import lire_page_pdf_mesures
from unocr.customs_reference.pdf_page import LecturePDFRefusee, ParamPDFInvalide
from unocr.customs_reference.review_export import MARQUEURS, analyser_export
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue
SID = "SOURCE_MESURES_NON_OFFICIELLE"


def preparer(root):
    source,metadata,transcription = fichiers(root)
    lot = root / "lot"
    preparer_mesures_autonomes(source,metadata,lot,transcription=transcription)
    return lot


def test_texte_natif_pagination_et_transcription_non_comparee(tmp_path):
    lot = preparer(tmp_path)
    avant = snapshot(tmp_path)
    rep = lire_page_pdf_mesures(lot,SID)
    assert rep["type_rapport"] == "lecture_page_pdf_mesures_recu"
    assert "aucun taux national" in rep["fragment"] and rep["nombre_pages_pdf"] == 2
    assert rep["page_physique_suivante"] == 2 and rep["lecture_pdf_effectuee"] is True
    assert rep["transcription_verification"] == "non_verifiee" and rep["mesures_transcrites_comparees"] is False
    assert rep["sha256_pdf_lu"] == hashlib.sha256((lot / "source_mesures_recue.pdf").read_bytes()).hexdigest()
    assert rep["transcription_sha256"] == hashlib.sha256((lot / "transcription_mesures_recue.json").read_bytes()).hexdigest()
    a = lire_page_pdf_mesures(lot,SID,limite=10)
    b = lire_page_pdf_mesures(lot,SID,decalage=10)
    assert a["fragment"]+b["fragment"] == rep["fragment"] and a["decalage_suivant"] == 10
    assert "technique 2" in lire_page_pdf_mesures(lot,SID,page=2)["fragment"]
    assert lire_page_pdf_mesures(lot,SID,decalage=1000)["fragment"] == ""
    assert charger_lot_mesures(lot)[1]["lecture_pdf_effectuee"] is False
    assert snapshot(tmp_path) == avant


@pytest.mark.parametrize("kwargs",[{"document_id":""},{"document_id":"x\n"},{"document_id":"x"*257},
    {"page":0},{"page":True},{"page":10001},{"limite":0},{"limite":True},{"limite":16001},
    {"decalage":-1},{"decalage":True},{"decalage":67108865}])
def test_parametres_avant_toute_lecture(tmp_path,kwargs):
    with pytest.raises(ParamPDFInvalide):
        lire_page_pdf_mesures(tmp_path / "ABSENT",**{"document_id":SID,**kwargs})


@pytest.mark.parametrize("defaut",["id","page","autre_format","alteration","relecture"])
def test_refus_avant_ou_apres_rejeu(tmp_path,monkeypatch,defaut):
    from unocr.customs_reference import fiscal_pdf_page

    if defaut == "autre_format":
        from tests.test_customs_fiscal_import import fichiers as fichiers_json
        source,metadata = fichiers_json(tmp_path)
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
        lot = tmp_path / "lot"
    else:
        lot = preparer(tmp_path)
    if defaut == "alteration":
        (lot / "source_mesures_recue.pdf").write_bytes(b"%PDF-ALTERE")
    if defaut == "relecture":
        monkeypatch.setattr(fiscal_pdf_page,"_lire",lambda p:b"%PDF-ALTERE APRES REJEU")
    with pytest.raises(ValueError):
        lire_page_pdf_mesures(lot,"ABSENT" if defaut=="id" else SID,page=3 if defaut=="page" else 1)


@pytest.mark.parametrize("mode",["timeout","crash","json","type","taille"])
def test_echecs_worker_sans_diagnostic_sensible(tmp_path,monkeypatch,mode):
    from unocr.customs_reference import pdf_page

    lot = preparer(tmp_path)
    def worker(*args,**kwargs):
        assert kwargs["timeout"] == 15 and kwargs["input"].startswith(b"%PDF-")
        if mode == "timeout":
            raise subprocess.TimeoutExpired("SECRET_TEST",15)
        sortie = {"json":b"SECRET_TEST","type":b'{"texte":1,"nombre_pages":2}',"taille":b"x"*(3*1024*1024+1)}.get(mode,b"SECRET_TEST")
        return SimpleNamespace(returncode=-9 if mode=="crash" else 0,stdout=sortie)
    monkeypatch.setattr(pdf_page.subprocess,"run",worker)
    with pytest.raises(LecturePDFRefusee) as exc:
        lire_page_pdf_mesures(lot,SID)
    assert "SECRET_TEST" not in str(exc.value)


@pytest.mark.parametrize("mode",["blanc","chiffre","faux"])
def test_pdf_blanc_chiffre_ou_opaque_non_lisible(tmp_path,mode):
    source,metadata,transcription = fichiers(tmp_path)
    if mode == "faux":
        source.write_bytes(b"%PDF-FAUX NON OFFICIEL")
    else:
        c = canvas.Canvas(str(source),encrypt="NON_OFFICIEL" if mode=="chiffre" else None)
        c.showPage()
        c.save()
    m = json.loads(metadata.read_text())
    m["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(m))
    preparer_mesures_autonomes(source,metadata,tmp_path / "lot",transcription=transcription)
    if mode == "blanc":
        rep = lire_page_pdf_mesures(tmp_path / "lot",SID)
        assert rep["texte_natif_non_vide"] is False and rep["fragment"] == ""
    else:
        with pytest.raises(LecturePDFRefusee):
            lire_page_pdf_mesures(tmp_path / "lot",SID)


def test_cli_native_et_refus(tmp_path,capsys):
    lot = preparer(tmp_path)
    assert main(["customs-fiscal-pdf-read",str(lot),"--document",SID,"--limit","10"]) == 0
    assert json.loads(capsys.readouterr().out)["limite"] == 10
    assert main(["customs-fiscal-pdf-read",str(lot),"--document","ABSENT"]) == 2
    capsys.readouterr()


@pytest.fixture()
def revue_pdf(revue):
    client,racine,registre,cfg = revue
    entree = cfg.root / "pdf_fiscal"
    entree.mkdir()
    source,metadata,transcription = fichiers(entree)
    preparer_mesures_autonomes(source,metadata,racine / "mesures_pdf_lu",transcription=transcription)
    reg = json.loads(registre.read_text())
    reg["lots"].append({"id":"mesures_pdf_lu","dossier":"mesures_pdf_lu","type_lot":"mesures",
        "manifest_sha256":hashlib.sha256((racine / "mesures_pdf_lu/manifest.json").read_bytes()).hexdigest()})
    registre.write_text(json.dumps(reg))
    return revue


def test_api_epingle_audit_export_et_archives_inchangees(revue_pdf):
    client,racine,registre,cfg = revue_pdf
    avant = snapshot(racine)
    route = BASE+"/lots/mesures_pdf_lu/fiscal-pdf?document_id="+SID+"&page=2&limit=10"
    r = client.get(route,headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    rep = r.json()["resultat"]
    assert rep["page_physique"] == 2
    exp = {**MARQUEURS,"horodatage_client_non_certifie":"2026-11-07T00:00:00.000Z","requete_relative":route,"resultat":rep}
    assert analyser_export(json.dumps(exp).encode())["statut"] == "structure_compatible"
    events = [json.loads(v) for v in (cfg.log_dir / "audit.log").read_text().splitlines()]
    succes = [v for v in events if v.get("operation")=="lecture_pdf_mesures" and v["statut"]==200][-1]
    assert succes["manifestes"].keys() == {"mesures_pdf_lu"} and "technique 2" not in json.dumps(succes)
    assert snapshot(racine) == avant


@pytest.mark.parametrize("suffixe,headers,statut",[("",{},401),("",{"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403),
    ("&page=0",ADMIN,422),("&page=3",ADMIN,409),("&document_id=ABSENT",ADMIN,409)])
def test_refus_api(revue_pdf,suffixe,headers,statut):
    client,*_ = revue_pdf
    r = client.get(BASE+"/lots/mesures_pdf_lu/fiscal-pdf?document_id="+SID+suffixe,headers=headers)
    assert r.status_code == statut and "resultat" not in r.json()


@pytest.mark.parametrize("lot_id",["tarif_a","code_a"])
def test_types_incompatibles_restent_refuses(revue_pdf,lot_id):
    client,*_ = revue_pdf
    r = client.get(BASE+"/lots/"+lot_id+"/fiscal-pdf?document_id="+SID,headers=ADMIN)
    assert r.status_code == 422 and "resultat" not in r.json()


def test_audit_obligatoire_et_epingle_du_resultat(revue_pdf,monkeypatch):
    from unocr import api
    from unocr.routes import customs_review

    client,racine,registre,cfg = revue_pdf
    route = BASE+"/lots/mesures_pdf_lu/fiscal-pdf?document_id="+SID
    def panne(*a,**kw):
        raise AuditIndisponible("SECRET_TEST")
    with monkeypatch.context() as m:
        m.setattr(api,"audit_obligatoire",panne)
        r = client.get(route,headers=ADMIN)
        assert r.status_code == 503 and "resultat" not in r.json() and "SECRET_TEST" not in r.text
    origine = customs_review.lire_page_pdf_mesures
    def changer(*a,**kw):
        resultat = origine(*a,**kw)
        resultat["archive"]["manifest_sha256"] = "f"*64
        return resultat
    monkeypatch.setattr(customs_review,"lire_page_pdf_mesures",changer)
    r = client.get(route,headers=ADMIN)
    assert r.status_code == 409 and "resultat" not in r.json()
