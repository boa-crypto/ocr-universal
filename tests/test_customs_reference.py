"""Fixtures techniques NON OFFICIELLES, jamais un référentiel national d'exemple."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from unocr.cli import main
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.models import ArticleVersion, Mesure, TariffBatch


def jeu():
    ref = {"source_id": "TEST_NON_OFFICIEL", "localisateur": "fixture technique uniquement"}
    return {
        "source": {"id": ref["source_id"], "titre": "FIXTURE NON OFFICIELLE",
                   "url": "https://www.douane.gov.dz/", "organisme": "TEST",
                   "version_source": "TEST", "sha256": "a" * 64, "format": "json"},
        "sections": [{"id": "TEST", "designation": "FIXTURE", "reference": ref}],
        "chapitres": [{"code": "01", "section_id": "TEST", "designation": "FIXTURE", "reference": ref}],
        "positions": [{"code": "0101", "chapitre": "01", "designation": "FIXTURE", "reference": ref}],
        "sous_positions": [{"code": "010100", "position": "0101", "designation": "FIXTURE", "reference": ref}],
        "lignes": [{"id": "TEST_LIGNE", "code_tarifaire_10": "0101000000", "code_sh_6": "010100",
                    "chapitre": "01", "position": "0101", "sous_position": "010100", "section_id": "TEST",
                    "designation_officielle_fr": "FIXTURE TECHNIQUE NON OFFICIELLE", "reference": ref}],
    }


def valider(brut):
    return TariffBatch.model_validate_json(json.dumps(brut))


def fichiers(tmp_path, csv=False):
    lot = jeu()
    if csv:
        lot["source"]["format"] = "csv"
        source = tmp_path / "fixture_NON_OFFICIELLE.csv"
        source.write_text("Code;SH;Chap;Pos;Sous;Sec;Texte\n0101000000;010100;01;0101;010100;TEST;FIXTURE NON OFFICIELLE\n", encoding="utf-8")
        mapping = dict(zip(["code_tarifaire_10", "code_sh_6", "chapitre", "position", "sous_position", "section_id", "designation_officielle_fr"], ["Code", "SH", "Chap", "Pos", "Sous", "Sec", "Texte"]))
    else:
        source = tmp_path / "fixture_NON_OFFICIELLE.json"
        source.write_text(json.dumps(lot["lignes"]), encoding="utf-8")
        mapping = {}
    lot.pop("lignes")
    lot["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps({"lot": lot, "colonnes": mapping}), encoding="utf-8")
    return source, metadata


def snapshot(root):
    return {str(p.relative_to(root)): (p.stat().st_mtime_ns, p.read_bytes())
            for p in root.rglob("*") if p.is_file() and not p.is_symlink()}


def test_modele_inconnu_pas_zero_pas_officiel():
    lot = valider(jeu())
    assert lot.statut == "quarantaine"
    assert lot.lignes[0].taux_tva is None and lot.lignes[0].restrictions is None
    assert lot.source.verification == "non_verifiee"
    assert lot.lignes[0].code_tarifaire_10.startswith("0")


@pytest.mark.parametrize("code", [101000000, "010100000", "01010000000", "٠١٠١٠٠٠٠٠٠", "0101 00000", "01.01000000", " 0101000000"])
def test_code_non_strict_refuse(code):
    lot = jeu()
    lot["lignes"][0]["code_tarifaire_10"] = code
    with pytest.raises(ValidationError):
        valider(lot)


@pytest.mark.parametrize("defaut", ["sh_absent", "position_absente", "chapitre_absent", "section_absente", "prefixe", "section_incoherente", "doublon", "designation", "taux_inline", "dates", "source_absente", "activation"])
def test_integrite_refusee(defaut):
    lot = jeu()
    ligne = lot["lignes"][0]
    if defaut == "sh_absent":
        lot["sous_positions"] = []
    elif defaut == "position_absente":
        lot["positions"] = []
    elif defaut == "chapitre_absent":
        lot["chapitres"] = []
    elif defaut == "section_absente":
        lot["sections"] = []
    elif defaut == "prefixe":
        ligne["code_sh_6"] = "020100"
    elif defaut == "section_incoherente":
        ligne["section_id"] = "INCONNU"
    elif defaut == "doublon":
        lot["lignes"].append(copy.deepcopy(ligne))
    elif defaut == "designation":
        ligne["designation_officielle_fr"] = " "
    elif defaut == "taux_inline":
        ligne["taux_tva"] = 0
    elif defaut == "dates":
        ligne.update(date_entree_vigueur="2026-02-02", date_fin_validite="2026-01-01")
    elif defaut == "source_absente":
        ligne["reference"] = {"source_id": "AUTRE", "localisateur": "test"}
    elif defaut == "activation":
        lot["statut"] = "actif"
    with pytest.raises(ValidationError):
        valider(lot)


def test_designation_arabe_pas_de_traduction_inventee():
    lot = jeu()
    lot["lignes"][0].update(designation_officielle_fr=None, designation_officielle_ar="نص اختباري غير رسمي")
    assert valider(lot).lignes[0].designation_officielle_fr is None


@pytest.mark.parametrize("url", ["https://douane.gov.dz.example.org/", "http://www.douane.gov.dz/", "https://user:secret@www.douane.gov.dz/", "https://example.org/"])
def test_domaine_non_autorise(url):
    lot = jeu()
    lot["source"]["url"] = url
    with pytest.raises(ValidationError):
        valider(lot)


@pytest.mark.parametrize("csv", [False, True])
def test_import_plan_et_archive_sans_activation(tmp_path, csv):
    source, metadata = fichiers(tmp_path, csv)
    avant = snapshot(tmp_path)
    rapport = preparer_tarif(source, metadata)
    assert rapport["lignes_source_lues"] == rapport["codes_uniques"] == 1
    assert rapport["completude_reglementaire"] == "non_etablie"
    assert snapshot(tmp_path) == avant
    sortie = tmp_path / "nouveau_lot"
    assert preparer_tarif(source, metadata, sortie)["publication_active"] is False
    assert (sortie / ("source_recue.csv" if csv else "source_recue.json")).read_bytes() == source.read_bytes()
    assert (sortie / "metadata_original.json").read_bytes() == metadata.read_bytes()
    manifeste = json.loads((sortie / "manifest.json").read_text())
    for nom, attendu in manifeste["fichiers_sha256"].items():
        assert hashlib.sha256((sortie / nom).read_bytes()).hexdigest() == attendu
    assert json.loads((sortie / "lot.json").read_text())["lignes"][0]["code_tarifaire_10"] == "0101000000"
    avant = snapshot(tmp_path)
    with pytest.raises(FileExistsError):
        preparer_tarif(source, metadata, sortie)
    assert snapshot(tmp_path) == avant


@pytest.mark.parametrize("defaut", ["hash", "parent", "doublon_json", "symlink", "format_inconnu", "mapping", "code_csv_court"])
def test_import_invalide_ne_cree_pas_de_lot(tmp_path, defaut):
    source, metadata = fichiers(tmp_path, csv=defaut in {"mapping", "code_csv_court"})
    meta = json.loads(metadata.read_text())
    if defaut == "hash":
        meta["lot"]["source"]["sha256"] = "b" * 64
    elif defaut == "parent":
        meta["lot"]["sous_positions"] = []
    elif defaut == "doublon_json":
        source.write_text('[{"id":"a","id":"b"}]')
        meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    elif defaut == "symlink":
        cible = tmp_path / "original.json"
        source.rename(cible)
        source.symlink_to(cible)
    elif defaut == "format_inconnu":
        meta["lot"]["source"]["format"] = "pdf"
    elif defaut == "mapping":
        meta["colonnes"]["code_tarifaire_10"] = "Absent"
    elif defaut == "code_csv_court":
        source.write_text(source.read_text().replace("0101000000", "101000000"))
        meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    avant = snapshot(tmp_path)
    with pytest.raises((ValueError, ValidationError)):
        preparer_tarif(source, metadata, tmp_path / "sortie")
    assert snapshot(tmp_path) == avant and not (tmp_path / "sortie").exists()


def test_cli_plan_et_ecriture_opt_in(tmp_path, capsys):
    source, metadata = fichiers(tmp_path)
    sortie = tmp_path / "sortie"
    args = ["customs-prepare", str(source), "--metadata", str(metadata), "--out", str(sortie)]
    assert main(args) == 0 and not sortie.exists()
    assert json.loads(capsys.readouterr().out)["ecrit"] is False
    assert main(args + ["--write"]) == 0 and sortie.exists()
    assert json.loads(capsys.readouterr().out)["statut"] == "quarantaine"
    assert main(args + ["--write"]) == 2


def test_mesure_non_sourcee_refusee():
    with pytest.raises(ValidationError):
        Mesure.model_validate_json(json.dumps({"id": "TEST", "code_tarifaire_10": "0101000000", "type_mesure": "tva", "description": "FIXTURE", "taux": "19", "unite_taux": "pourcent"}))


def test_article_original_modificatif_consolide_separes():
    base = {"id": "TEST", "numero_article": "1 bis", "hierarchie": [], "nature_version": "originale",
            "texte_integral": "FIXTURE NON OFFICIELLE", "reference": {"source_id": "TEST", "localisateur": "fixture"}, "version_juridique": "TEST"}
    assert ArticleVersion.model_validate_json(json.dumps(base)).validation_juridique == "non_validee"
    with pytest.raises(ValidationError):
        ArticleVersion.model_validate_json(json.dumps({**base, "texte_modificatif": "FIXTURE"}))
    provisoire = ArticleVersion.model_validate_json(json.dumps({**base, "nature_version": "consolidee_provisoire"}))
    assert provisoire.validation_juridique == "non_validee"
    with pytest.raises(ValidationError):
        ArticleVersion.model_validate_json(json.dumps({**base, "validation_juridique": "validee"}))


@pytest.mark.parametrize("endpoint", ["calculer", "complets"])
def test_api_pas_de_calcul_non_source(endpoint, monkeypatch):
    from unocr.routes import reglementation

    app = FastAPI()
    app.include_router(reglementation.router)
    audits = []
    monkeypatch.setattr(reglementation, "audit", lambda *args, **kwargs: audits.append(args))
    with TestClient(app) as client:
        rep = client.post("/api/reglementation/droits/" + endpoint, json={"code_sh": "0101000000", "valeur": 1000, "devise": "DZD"})
    assert rep.status_code == 503
    assert rep.json()["detail"]["code"] == "reference_douaniere_non_verifiee"
    assert "total_douane" not in rep.text and not audits


def test_schemas_generes_identiques():
    root = Path(__file__).resolve().parents[1] / "docs/customs/schemas"
    for modele in (TariffBatch, ArticleVersion, Mesure):
        assert json.loads((root / (modele.__name__ + ".schema.json")).read_text()) == modele.model_json_schema()


def test_nombre_de_lignes_observe_non_completude(tmp_path):
    source, metadata = fichiers(tmp_path)
    lignes = json.loads(source.read_text())
    for n in (1, 2):
        ligne = copy.deepcopy(lignes[0])
        ligne["id"] += str(n)
        ligne["code_tarifaire_10"] = "010100000" + str(n)
        lignes.append(ligne)
    source.write_text(json.dumps(lignes))
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    rapport = preparer_tarif(source, metadata)
    assert rapport["lignes_source_lues"] == rapport["lignes_importables"] == rapport["codes_uniques"] == 3
    assert rapport["completude_reglementaire"] == "non_etablie"


def test_csv_tronque_cli_refuse_sans_traceback(tmp_path, capsys):
    source, metadata = fichiers(tmp_path, csv=True)
    source.write_text('Code;SH;Chap;Pos;Sous;Sec;Texte\n"non termine')
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    assert main(["customs-prepare", str(source), "--metadata", str(metadata), "--write", "--out", str(tmp_path / "sortie")]) == 2
    assert "refuse" in capsys.readouterr().out
    assert not (tmp_path / "sortie").exists()


@pytest.mark.parametrize("defaut", ["unite", "taux_negatif", "date", "code_absent"])
def test_mesure_documentee_mais_incoherente(defaut):
    lot = jeu()
    mesure = {"id": "TEST_MESURE", "code_tarifaire_10": "0101000000", "type_mesure": "tva", "description": "FIXTURE NON OFFICIELLE", "taux": "19", "unite_taux": "pourcent", "reference": lot["lignes"][0]["reference"]}
    if defaut == "unite":
        mesure["unite_taux"] = None
    elif defaut == "taux_negatif":
        mesure["taux"] = "-1"
    elif defaut == "date":
        mesure.update(date_entree_vigueur="2026-01-01", date_fin_validite="2025-12-31")
    elif defaut == "code_absent":
        mesure["code_tarifaire_10"] = "0101000001"
    lot["mesures"] = [mesure]
    with pytest.raises(ValidationError):
        valider(lot)
