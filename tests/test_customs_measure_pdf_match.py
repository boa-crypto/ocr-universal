"""Constats littéraux sur descriptions NON OFFICIELLES, pas validation fiscale."""
import hashlib
import json

import pytest

from tests import test_customs_fiscal_pdf_page
from tests.test_customs_fiscal_pdf import fichiers
from tests.test_customs_fiscal_pdf_page import SID
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.fiscal_importer import preparer_mesures_autonomes
from unocr.customs_reference.measure_pdf_match import (
    ParamRapprochementMesureInvalide,
    rapprocher_description_mesure_pdf,
)
from unocr.customs_reference.review_export import MARQUEURS, analyser_export

revue = test_customs_fiscal_pdf_page.revue
revue_pdf = test_customs_fiscal_pdf_page.revue_pdf


def preparer(root,description="FIXTURE PDF NON OFFICIELLE"):
    source,metadata,transcription = fichiers(root)
    mesures = json.loads(transcription.read_text())
    mesures[0]["description"] = description
    transcription.write_text(json.dumps(mesures))
    preparer_mesures_autonomes(source,metadata,root / "lot",transcription=transcription)
    return root / "lot"


def test_presence_premiere_occurrence_sans_fidelite_taux_ou_reference(tmp_path):
    lot = preparer(tmp_path)
    avant = snapshot(tmp_path)
    rep = rapprocher_description_mesure_pdf(lot,"M_0",1,limite=7)
    assert rep["fragment_present_litteralement"] is True and rep["position_fin_pdf_exclusive"] == rep["position_debut_pdf"]+7
    assert rep["decalage_suivant"] == 7 and rep["fragment_description"] == "FIXTURE"
    assert rep["taux_et_periodes_verifies"] is rep["rattachement_juridique_etabli"] is False
    assert rep["transcription_verification"] == "non_verifiee"
    assert "taux" not in rep["mesure_declaree"] and rep["mesure_declaree"]["reference"]["source_id"] == SID
    assert rep["sha256_pdf_lu"] == hashlib.sha256((lot / "source_mesures_recue.pdf").read_bytes()).hexdigest()
    assert rapprocher_description_mesure_pdf(lot,"M_0",2)["fragment_present_litteralement"] is False
    assert snapshot(tmp_path) == avant


@pytest.mark.parametrize("description,limite,decalage,mesure,constat",[
    ("FIXTURE PDF NON OFFICIELLE",4,999,"M_0","fragment_vide"),
    ("   FIXTURE",3,0,"M_0","fragment_sans_caractere_non_blanc"),
    ("NON PRESENT",4000,0,"M_0","correspondance_litterale_non_trouvee"),
    ("FIXTURE PDF NON OFFICIELLE",4000,0,"ABSENT","mesure_absente_du_lot")])
def test_absence_pas_validation_et_sans_extraction_si_vide(tmp_path,description,limite,decalage,mesure,constat):
    rep = rapprocher_description_mesure_pdf(preparer(tmp_path,description),mesure,1,limite,decalage)
    assert rep["constat"] == constat
    if constat != "correspondance_litterale_non_trouvee":
        assert rep["extraction_effectuee"] is False and rep["fragment_present_litteralement"] is None


@pytest.mark.parametrize("kwargs",[{"mesure_id":""},{"mesure_id":"x\n"},{"mesure_id":"x"*257},
    {"page":0},{"page":True},{"limite":0},{"limite":True},{"limite":16001},{"decalage":-1},{"decalage":True}])
def test_parametres_avant_lecture(tmp_path,kwargs):
    with pytest.raises(ParamRapprochementMesureInvalide):
        rapprocher_description_mesure_pdf(tmp_path / "ABSENT",**{"mesure_id":"M_0","page":1,**kwargs})


def test_page_absente_pdf_altere_et_non_pdf_refuses(tmp_path):
    lot = preparer(tmp_path)
    with pytest.raises(ValueError):
        rapprocher_description_mesure_pdf(lot,"M_0",3)
    (lot / "source_mesures_recue.pdf").write_bytes(b"%PDF-ALTERE")
    with pytest.raises(ValueError):
        rapprocher_description_mesure_pdf(lot,"M_0",1)
    from tests.test_customs_fiscal_import import fichiers as fichiers_json
    source,metadata = fichiers_json(tmp_path)
    preparer_mesures_autonomes(source,metadata,tmp_path / "json")
    with pytest.raises(ValueError):
        rapprocher_description_mesure_pdf(tmp_path / "json","M_0",1)


def test_cli(tmp_path,capsys):
    lot = preparer(tmp_path)
    assert main(["customs-measure-pdf-match",str(lot),"--measure","M_0","--page","1"]) == 0
    assert json.loads(capsys.readouterr().out)["fragment_present_litteralement"] is True


def test_api_et_export_a_provenance_simple(revue_pdf):
    client,racine,registre,cfg = revue_pdf
    avant = snapshot(racine)
    route = BASE+"/lots/mesures_pdf_lu/measure-pdf-match?mesure_id=M_0&page=1"
    r = client.get(route,headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    rep = r.json()["resultat"]
    assert rep["fragment_present_litteralement"] is False
    exp = {**MARQUEURS,"horodatage_client_non_certifie":"2026-11-07T00:00:00.000Z","requete_relative":route,"resultat":rep}
    assert analyser_export(json.dumps(exp).encode())["statut"] == "structure_compatible"
    assert snapshot(racine) == avant


@pytest.mark.parametrize("lot,extra,headers,code",[("mesures_pdf_lu","",{},401),("mesures_pdf_lu","&page=0",ADMIN,422),
    ("code_a","",ADMIN,422),("tarif_a","",ADMIN,422)])
def test_refus_api(revue_pdf,lot,extra,headers,code):
    client,*_ = revue_pdf
    r = client.get(BASE+"/lots/"+lot+"/measure-pdf-match?mesure_id=M_0"+extra,headers=headers)
    assert r.status_code == code and "resultat" not in r.json()
