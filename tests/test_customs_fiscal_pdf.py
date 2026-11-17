"""PDF opaque et transcription déclarée NON OFFICIELS, sans extraction fiscale."""
import hashlib
import json

import pytest
from reportlab.pdfgen import canvas

from tests import test_customs_review
from tests.test_customs_fiscal_import import fichiers as fichiers_json
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.fiscal_importer import charger_lot_mesures, preparer_mesures_autonomes

revue = test_customs_review.revue


def fichiers(root):
    original,metadata = fichiers_json(root)
    mesures = json.loads(original.read_text())
    mesures[0]["description"] = "Équipement; مُعَـدَّات\nFIXTURE NON OFFICIELLE"
    for m in mesures:
        m["reference"]["localisateur"] = "PDF, page physique 1 déclarée, mesure "+m["id"]
    transcription = root / "TRANSCRIPTION_NON_OFFICIELLE.json"
    transcription.write_text(json.dumps(mesures,ensure_ascii=False))
    source = root / "SOURCE_FISCALE_NON_OFFICIELLE.pdf"
    c = canvas.Canvas(str(source))
    c.drawString(30,750,"FIXTURE PDF NON OFFICIELLE - aucun taux national")
    c.showPage()
    c.drawString(30,750,"Page technique 2 - pas de transcription verifiee")
    c.save()
    meta = json.loads(metadata.read_text())
    meta["source"].update(format="pdf",sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                          url="https://www.douane.gov.dz/TEST_NON_OFFICIEL/mesures.pdf")
    metadata.write_text(json.dumps(meta))
    return source,metadata,transcription


def preparer(root,sortie=True):
    source,metadata,transcription = fichiers(root)
    return source,metadata,transcription,preparer_mesures_autonomes(
        source,metadata,root / "lot" if sortie else None,transcription=transcription)


def test_plan_et_archive_pdf_transcription_exactes_sans_extraction(tmp_path):
    source,metadata,transcription = fichiers(tmp_path)
    avant = snapshot(tmp_path)
    rep = preparer_mesures_autonomes(source,metadata,transcription=transcription)
    assert snapshot(tmp_path) == avant and rep["ecrit"] is False
    assert rep["mesures_source_lues"] is None and rep["mesures_transcription_lues"] == rep["mesures_importables"] == 6
    assert rep["lecture_pdf_effectuee"] is rep["structure_pdf_verifiee"] is False
    assert rep["transcription_verification"] == "non_verifiee"
    assert rep["transcription_sha256"] == hashlib.sha256(transcription.read_bytes()).hexdigest()
    preparer_mesures_autonomes(source,metadata,tmp_path / "lot",transcription=transcription)
    lot,rapport = charger_lot_mesures(tmp_path / "lot")
    assert len(list((tmp_path / "lot").iterdir())) == 6
    for nom,original in [("source_mesures_recue.pdf",source),("metadata_original.json",metadata),
                          ("transcription_mesures_recue.json",transcription)]:
        assert (tmp_path / "lot" / nom).read_bytes() == original.read_bytes()
    assert lot.source.format == "pdf" and lot.mesures[0].code_tarifaire_10 == "0000000001"
    assert str(lot.mesures[0].taux) == "1.230000000000000000000000001"
    assert lot.mesures[1].taux == 0 and lot.mesures[2].taux is None
    assert lot.mesures[0].reference.localisateur == "PDF, page physique 1 déclarée, mesure M_0"
    assert lot.mesures[0].description == "Équipement; مُعَـدَّات\nFIXTURE NON OFFICIELLE"
    assert lot.mesures[0].date_entree_vigueur.isoformat() == "2001-02-03"
    assert lot.source.date_publication.isoformat() == "2002-01-01" and lot.mesures[1].date_entree_vigueur is None
    assert rapport["transcription_verification"] == "non_verifiee" and rapport["fiscalite_applicable_etablie"] is False


@pytest.mark.parametrize("option,valeur",[("colonnes",{}),("delimiteur",";"),("feuille",None),("ligne_entete",1)])
def test_options_tabulees_interdites_sur_pdf(tmp_path,option,valeur):
    source,metadata,transcription = fichiers(tmp_path)
    meta = json.loads(metadata.read_text())
    meta[option] = valeur
    metadata.write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot",transcription=transcription)
    assert not (tmp_path / "lot").exists()


def test_transcription_manquante_symbolique_et_borne_totale(tmp_path,monkeypatch):
    import unocr.customs_reference.fiscal_importer as module

    source,metadata,transcription = fichiers(tmp_path)
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot")
    lien = tmp_path / "lien.json"
    lien.symlink_to(transcription)
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot",transcription=lien)
    monkeypatch.setattr(module,"MAX_TOTAL_PDF",len(source.read_bytes())+len(metadata.read_bytes())+len(transcription.read_bytes())-1)
    with pytest.raises(ValueError,match="128 Mio"):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot",transcription=transcription)
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("contenu",[b"",b"[]",b"%PDF-FAUX NON OFFICIEL"])
def test_signature_seule_pas_validation_structurelle_pdf(tmp_path,contenu):
    source,metadata,transcription = fichiers(tmp_path)
    source.write_bytes(contenu)
    meta = json.loads(metadata.read_text())
    meta["source"]["sha256"] = hashlib.sha256(contenu).hexdigest()
    metadata.write_text(json.dumps(meta))
    if contenu.startswith(b"%PDF-"):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot",transcription=transcription)
        _,rapport = charger_lot_mesures(tmp_path / "lot")
        assert rapport["structure_pdf_verifiee"] is False
    else:
        with pytest.raises(ValueError):
            preparer_mesures_autonomes(source,metadata,tmp_path / "lot",transcription=transcription)
        assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("contenu",[b"{}",b'{"mesures":[]}',b"[null]",b"[NaN]",b'[{"id":"a","id":"b"}]',
    b'[{"taux":0}]',b'[{"taux":1.23}]',b"INVALID",b"\xff\xfeINVALIDE"])
def test_transcription_json_malformee_ou_ambigue_refusee(tmp_path,contenu):
    source,metadata,transcription = fichiers(tmp_path)
    transcription.write_bytes(contenu)
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot",transcription=transcription)
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("defaut",["reference_etrangere","reference_vide","reference_absente","code_numerique","id_duplique","taux_numerique","date_incoherente"])
def test_mesures_declarees_invalides_refusees(tmp_path,defaut):
    source,metadata,transcription = fichiers(tmp_path)
    mesures = json.loads(transcription.read_text())
    if defaut == "reference_etrangere":
        mesures[0]["reference"]["source_id"] = "AUTRE"
    elif defaut == "reference_vide":
        mesures[0]["reference"]["localisateur"] = " "
    elif defaut == "reference_absente":
        mesures[0].pop("reference")
    elif defaut == "code_numerique":
        mesures[0]["code_tarifaire_10"] = 1
    elif defaut == "id_duplique":
        mesures[1]["id"] = mesures[0]["id"]
    elif defaut == "taux_numerique":
        mesures[0]["taux"] = 1.23
    else:
        mesures[0]["date_fin_validite"] = "1999-01-01"
    transcription.write_text(json.dumps(mesures))
    with pytest.raises(ValueError):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot",transcription=transcription)
    assert not (tmp_path / "lot").exists()


def test_transcription_vide_et_reference_non_localisee_ne_valident_rien(tmp_path):
    source,metadata,transcription = fichiers(tmp_path)
    mesures = json.loads(transcription.read_text())
    mesures[0]["reference"]["localisateur"] = "Page déclarée 9999, à vérifier humainement"
    transcription.write_text(json.dumps(mesures))
    preparer_mesures_autonomes(source,metadata,tmp_path / "non_localise",transcription=transcription)
    lot,rapport = charger_lot_mesures(tmp_path / "non_localise")
    assert lot.mesures[0].reference.localisateur == "Page déclarée 9999, à vérifier humainement"
    assert rapport["transcription_verification"] == "non_verifiee"
    transcription.write_text("[]")
    preparer_mesures_autonomes(source,metadata,tmp_path / "vide",transcription=transcription)
    assert charger_lot_mesures(tmp_path / "vide")[1]["mesures_importables"] == 0


@pytest.mark.parametrize("format_source",["json","csv","xlsx","xls"])
def test_transcription_separee_refusee_sur_anciens_formats(tmp_path,format_source):
    from tests.test_customs_fiscal_csv import fichiers as fichiers_csv
    from tests.test_customs_fiscal_xls import fichiers as fichiers_xls
    from tests.test_customs_fiscal_xlsx import fichiers as fichiers_xlsx

    source,metadata = {"json":fichiers_json,"csv":fichiers_csv,"xlsx":fichiers_xlsx,"xls":fichiers_xls}[format_source](tmp_path)
    transcrit = tmp_path / "TRANSCRIPTION_SUPERFLUE.json"
    transcrit.write_text("[]")
    with pytest.raises(ValueError,match="hors source PDF"):
        preparer_mesures_autonomes(source,metadata,tmp_path / "lot",transcription=transcrit)
    assert not (tmp_path / "lot").exists()


@pytest.mark.parametrize("defaut",["pdf","transcription","transcription_rehachee","transcription_espaces_rehachee","rapport_rehache","lot_rehache","manquante","surplus","extension","deux_sources"])
def test_archives_pdf_alterees_refusees(tmp_path,defaut):
    preparer(tmp_path)
    lot = tmp_path / "lot"
    manifeste = json.loads((lot / "manifest.json").read_text())
    if defaut == "pdf":
        (lot / "source_mesures_recue.pdf").write_bytes(b"%PDF-ALTERE")
    elif defaut == "transcription":
        (lot / "transcription_mesures_recue.json").write_bytes(b"[]")
    elif defaut == "transcription_rehachee":
        x = json.loads((lot / "transcription_mesures_recue.json").read_text())
        x[0]["description"] = "ALTERE NON OFFICIEL"
        (lot / "transcription_mesures_recue.json").write_text(json.dumps(x))
        manifeste["fichiers_sha256"]["transcription_mesures_recue.json"] = hashlib.sha256((lot / "transcription_mesures_recue.json").read_bytes()).hexdigest()
    elif defaut == "transcription_espaces_rehachee":
        p = lot / "transcription_mesures_recue.json"
        p.write_bytes(b"\n"+p.read_bytes())
        manifeste["fichiers_sha256"][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    elif defaut in {"rapport_rehache","lot_rehache"}:
        nom = "rapport.json" if defaut == "rapport_rehache" else "lot_mesures.json"
        x = json.loads((lot / nom).read_text())
        if defaut == "rapport_rehache":
            x["transcription_verification"] = "verifiee"
        else:
            x["mesures"][0]["description"] = "ALTERE NON OFFICIEL"
        (lot / nom).write_text(json.dumps(x))
        manifeste["fichiers_sha256"][nom] = hashlib.sha256((lot / nom).read_bytes()).hexdigest()
    elif defaut == "manquante":
        (lot / "transcription_mesures_recue.json").unlink()
    elif defaut == "surplus":
        (lot / "autre.pdf").write_bytes(b"%PDF-SURPLUS")
    elif defaut == "extension":
        (lot / "source_mesures_recue.pdf").rename(lot / "source_mesures_recue.json")
        manifeste["fichiers_sha256"]["source_mesures_recue.json"] = manifeste["fichiers_sha256"].pop("source_mesures_recue.pdf")
    else:
        (lot / "source_mesures_recue.json").write_bytes(b"[]")
        manifeste["fichiers_sha256"]["source_mesures_recue.json"] = hashlib.sha256(b"[]").hexdigest()
    (lot / "manifest.json").write_text(json.dumps(manifeste))
    with pytest.raises(ValueError):
        charger_lot_mesures(lot)


def test_cli_transcription_explicitement_requise(tmp_path,capsys):
    source,metadata,transcription = fichiers(tmp_path)
    args = ["customs-fiscal-prepare",str(source),"--metadata",str(metadata),"--out",str(tmp_path / "lot")]
    assert main(args+["--write"]) == 2 and not (tmp_path / "lot").exists()
    capsys.readouterr()
    assert main(args+["--transcription",str(transcription)]) == 0 and not (tmp_path / "lot").exists()
    assert json.loads(capsys.readouterr().out)["transcription_verification"] == "non_verifiee"
    assert main(args+["--transcription",str(transcription),"--write"]) == 0
    capsys.readouterr()
    assert main(["customs-fiscal-check",str(tmp_path / "lot")]) == 0
    assert json.loads(capsys.readouterr().out)["lecture_pdf_effectuee"] is False


def test_api_revue_transcription_et_consultation_sans_lecture_pdf(revue):
    client,racine,registre,cfg = revue
    entrees = cfg.root / "entrees_pdf_fiscal"
    entrees.mkdir()
    source,metadata,transcription = fichiers(entrees)
    preparer_mesures_autonomes(source,metadata,racine / "mesures_pdf",transcription=transcription)
    reg = json.loads(registre.read_text())
    reg["lots"].append({"id":"mesures_pdf","dossier":"mesures_pdf","type_lot":"mesures",
                        "manifest_sha256":hashlib.sha256((racine / "mesures_pdf/manifest.json").read_bytes()).hexdigest()})
    registre.write_text(json.dumps(reg))
    avant = snapshot(racine)
    for chemin in ("check","sources","coverage","measure-search?code10=0000000001"):
        r = client.get(BASE+"/lots/mesures_pdf/"+chemin,headers=ADMIN)
        assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
        if chemin == "check":
            assert r.json()["resultat"]["transcription_verification"] == "non_verifiee"
    for chemin in ("pdf","pdf-source"):
        r = client.get(BASE+"/lots/mesures_pdf/"+chemin+"?document_id=SOURCE_MESURES_NON_OFFICIELLE",headers=ADMIN)
        assert r.status_code == 422
    r = client.get(BASE+"/tariff-measures?tarif=tarif_a&mesures=mesures_pdf&code10=0000000001",headers=ADMIN)
    assert r.status_code == 200
    rep = r.json()["resultat"]
    assert rep["mesures_autonomes"]["source_declaree"]["format"] == "pdf"
    assert rep["mesures_autonomes"]["total_correspondances"] == 3
    assert rep["fiche_nomenclature"]["ligne_trouvee"] is False
    assert rep["mesures_fusionnees"] is rep["rattachement_juridique_etabli"] is False
    assert snapshot(racine) == avant


def test_sauvegarde_reprise_pdf_et_transcription_exactes(tmp_cfg,tmp_path):
    from types import SimpleNamespace

    from unocr import backup

    entrees = tmp_path / "entrees"
    entrees.mkdir()
    source,metadata,transcription = fichiers(entrees)
    racine = tmp_cfg.data_dir / "customs-quarantine"
    racine.mkdir(parents=True,exist_ok=True)
    preparer_mesures_autonomes(source,metadata,racine / "mesures",transcription=transcription)
    avant = snapshot(racine)
    sauvegarde = backup.creer_sauvegarde(tmp_cfg,inclure_quarantaine=True)
    cible = SimpleNamespace(data_dir=tmp_path / "reprise/data",log_dir=tmp_path / "reprise/logs")
    backup.restaurer_sauvegarde(cible,sauvegarde.chemin,inclure_quarantaine=True)
    repris = cible.data_dir / "customs-quarantine"
    assert {k:v[1] for k,v in snapshot(repris).items()} == {k:v[1] for k,v in avant.items()}
    lot,rapport = charger_lot_mesures(repris / "mesures")
    assert len(lot.mesures) == 6 and lot.source.format == "pdf"
    assert rapport["lecture_pdf_effectuee"] is False and snapshot(racine) == avant


def test_borne_transcription_et_artefacts_avant_creation(tmp_path,monkeypatch):
    from unocr.customs_reference import fiscal_importer, importer

    source,metadata,transcription = fichiers(tmp_path)
    limite = max(len(source.read_bytes()),len(metadata.read_bytes()))+1
    transcription.write_bytes(transcription.read_bytes()+b" "*(limite+1))
    with monkeypatch.context() as m:
        m.setattr(importer,"MAX_SOURCE",limite)
        with pytest.raises(ValueError,match="64 Mio"):
            preparer_mesures_autonomes(source,metadata,tmp_path / "lot",transcription=transcription)
    with monkeypatch.context() as m:
        m.setattr(fiscal_importer,"MAX_SOURCE",1)
        with pytest.raises(ValueError,match="Artefact normalisé"):
            preparer_mesures_autonomes(source,metadata,tmp_path / "lot",transcription=transcription)
    assert not (tmp_path / "lot").exists()


def test_sorties_xls_41_inchangees(tmp_path):
    from tests.test_customs_fiscal_xls import fichiers as fichiers_xls

    source,metadata = fichiers_xls(tmp_path)
    preparer_mesures_autonomes(source,metadata,tmp_path / "xls41")
    # Préparateur et adaptateur du commit 7cf11a79, fixture NON OFFICIELLE BIFF8.
    attendus = {"lot_mesures.json":"7164d57342a45fb5298f5cf372bb5f232b6e9dae5278a98bc3b06edc3636a6ed","rapport.json":"d32f81d7b9e28771c70810bc6d86bccf255741c873adff13b6bbab3dbbc27123"}
    for nom,sha in attendus.items():
        assert hashlib.sha256((tmp_path / "xls41" / nom).read_bytes()).hexdigest() == sha
    lot,_ = charger_lot_mesures(tmp_path / "xls41")
    assert lot.source.format == "xls" and len(lot.mesures) == 6
