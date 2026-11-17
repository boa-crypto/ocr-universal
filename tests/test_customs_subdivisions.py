"""Subdivisions de fixtures NON OFFICIELLES, jamais reconstituées par préfixe."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from tests import test_customs_review
from tests.test_customs_reference import fichiers, jeu, snapshot, valider
from unocr.cli import main
from unocr.customs_reference.comparison import charger_lot, comparer_lots
from unocr.customs_reference.coverage import diagnostiquer_couverture
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.models import SubdivisionNationale
from unocr.customs_reference.tariff_detail import consulter_code

revue = test_customs_review.revue
ADMIN, BASE = test_customs_review.ADMIN, test_customs_review.BASE


def subdivisions():
    ref = {"source_id": "TEST_NON_OFFICIEL", "localisateur": "FIXTURE NON OFFICIELLE"}
    return [{"code": code, "code_parent": parent, "designation": "FIXTURE NON OFFICIELLE", "reference": ref}
            for code, parent in [("0101000", "010100"), ("01010000", "0101000"), ("010100000", "01010000")]]


def lot_declare(tmp_path, csv=False):
    source, metadata = fichiers(tmp_path, csv=csv)
    meta = json.loads(metadata.read_text())
    meta["lot"]["subdivisions_nationales"] = subdivisions()
    if csv:
        lignes = source.read_text().splitlines()
        source.write_text(lignes[0] + ";Subdivision\n" + lignes[1] + ";010100000\n")
        meta["colonnes"]["code_subdivision_nationale"] = "Subdivision"
    else:
        lignes = json.loads(source.read_text())
        lignes[0]["code_subdivision_nationale"] = "010100000"
        source.write_text(json.dumps(lignes))
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    return source, metadata


@pytest.mark.parametrize("csv", [False, True])
def test_import_rejeu_fiche_chaine_et_aucune_inference(tmp_path, csv):
    source, metadata = lot_declare(tmp_path, csv)
    avant = snapshot(tmp_path)
    assert preparer_tarif(source, metadata)["lignes_importables"] == 1
    assert snapshot(tmp_path) == avant
    lot = tmp_path / "lot"
    preparer_tarif(source, metadata, lot)
    avant = snapshot(lot)
    modele, _ = charger_lot(lot)
    assert modele.lignes[0].code_subdivision_nationale == "010100000"
    rep = consulter_code(lot, "0101000000")
    chaine = rep["hierarchie_declaree"]["subdivisions_nationales"]
    assert [v["code"] for v in chaine] == ["0101000", "01010000", "010100000"]
    assert rep["hierarchie_declaree"]["subdivision_nationale_intermediaire"] == chaine[-1]
    assert all(v["reference"]["source_id"] == rep["source_declaree"]["id"] for v in chaine)
    assert rep["fiscalite_applicable_etablie"] is False
    couverture = diagnostiquer_couverture(lot, "tarif")["indicateurs"]
    assert couverture["compteurs"]["subdivisions_nationales"] == 3
    assert couverture["lignes_sans_subdivision_nationale_declaree"] == 0
    assert snapshot(lot) == avant


@pytest.mark.parametrize("code", [1010000, "010100", "0101000000", "٠١٠١٠٠٠", " 0101000", "0101000\n"])
def test_codes_intermediaires_stricts(code):
    brut = subdivisions()[0]
    brut["code"] = code
    with pytest.raises(ValueError):
        SubdivisionNationale.model_validate(brut)


@pytest.mark.parametrize("defaut", ["parent_absent", "parent_sans_sh6", "parent_plus_long", "parent_incoherent", "doublon", "source", "localisateur", "designation", "ligne_absente", "ligne_incoherente"])
def test_integrite_modeles_avant_ecriture(defaut):
    brut = jeu()
    brut["subdivisions_nationales"] = subdivisions()
    brut["lignes"][0]["code_subdivision_nationale"] = "010100000"
    if defaut == "parent_absent":
        brut["subdivisions_nationales"].pop(1)
    elif defaut == "parent_sans_sh6":
        brut["sous_positions"] = []
    elif defaut == "parent_plus_long":
        brut["subdivisions_nationales"][0]["code_parent"] = "01010000"
    elif defaut == "parent_incoherent":
        brut["subdivisions_nationales"][0]["code_parent"] = "020100"
    elif defaut == "doublon":
        brut["subdivisions_nationales"].append(copy.deepcopy(brut["subdivisions_nationales"][0]))
    elif defaut == "source":
        brut["subdivisions_nationales"][0]["reference"]["source_id"] = "AUTRE"
    elif defaut == "localisateur":
        brut["subdivisions_nationales"][0]["reference"]["localisateur"] = " "
    elif defaut == "designation":
        brut["subdivisions_nationales"][0]["designation"] = " "
    elif defaut == "ligne_absente":
        brut["lignes"][0]["code_subdivision_nationale"] = "0101001"
    elif defaut == "ligne_incoherente":
        brut["lignes"][0]["code_subdivision_nationale"] = "01010001"
        brut["subdivisions_nationales"].append({**subdivisions()[1], "code": "01010001"})
    with pytest.raises(ValueError):
        valider(brut)


def test_niveau_non_fourni_pas_invente_et_sauts_explicitement_permis():
    brut = jeu()
    brut["subdivisions_nationales"] = [{**subdivisions()[2], "code_parent": "010100"}]
    lot = valider(brut)
    assert lot.lignes[0].code_subdivision_nationale is None
    brut["lignes"][0]["code_subdivision_nationale"] = "010100000"
    assert valider(brut).lignes[0].code_subdivision_nationale == "010100000"


def test_archive_ancienne_sans_nouveaux_champs_reste_lisible_sans_recriture(tmp_path):
    source, metadata = fichiers(tmp_path)
    lot = tmp_path / "ancien"
    preparer_tarif(source, metadata, lot)
    normalise = json.loads((lot / "lot.json").read_text())
    normalise.pop("subdivisions_nationales")
    for ligne in normalise["lignes"]:
        ligne.pop("code_subdivision_nationale")
    (lot / "lot.json").write_text(json.dumps(normalise))
    manifest = json.loads((lot / "manifest.json").read_text())
    manifest["fichiers_sha256"]["lot.json"] = hashlib.sha256((lot / "lot.json").read_bytes()).hexdigest()
    (lot / "manifest.json").write_text(json.dumps(manifest))
    avant = snapshot(lot)
    charge, _ = charger_lot(lot)
    assert charge.subdivisions_nationales == []
    rep = consulter_code(lot, "0101000000")
    assert rep["hierarchie_declaree"]["subdivision_nationale_intermediaire"] is None
    assert rep["hierarchie_declaree"]["subdivisions_nationales"] == []
    assert snapshot(lot) == avant


def test_diff_contenu_et_provenance_subdivision(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    source_a, meta_a = lot_declare(a)
    source_b, meta_b = lot_declare(b)
    meta = json.loads(meta_b.read_text())
    meta["lot"]["subdivisions_nationales"][0]["designation"] = "AUTRE FIXTURE NON OFFICIELLE"
    meta["lot"]["subdivisions_nationales"][1]["reference"] = {"source_id": "TEST_NON_OFFICIEL", "localisateur": "AUTRE LOCALISATEUR NON OFFICIEL"}
    meta_b.write_text(json.dumps(meta))
    preparer_tarif(source_a, meta_a, a / "lot")
    preparer_tarif(source_b, meta_b, b / "lot")
    rep = comparer_lots(a / "lot", b / "lot")
    assert len(rep["hierarchie"]["subdivisions_nationales"]["modifies"]) == 1
    assert len(rep["provenances_modifiees"]["hierarchie"]["subdivisions_nationales"]) == 1


def test_schema_et_cli(tmp_path, capsys):
    schema = Path(__file__).resolve().parents[1] / "docs/customs/schemas/SubdivisionNationale.schema.json"
    assert json.loads(schema.read_text()) == SubdivisionNationale.model_json_schema()
    source, metadata = lot_declare(tmp_path)
    assert main(["customs-prepare", str(source), "--metadata", str(metadata)]) == 0
    assert json.loads(capsys.readouterr().out)["ecrit"] is False


def test_fiche_api_subdivisions_protegee(revue):
    client, racine, registre, cfg = revue
    entrees = cfg.root / "subdivisions_entrees"
    entrees.mkdir()
    source, metadata = lot_declare(entrees)
    lot = racine / "tarif_sub"
    preparer_tarif(source, metadata, lot)
    contenu = json.loads(registre.read_text())
    contenu["lots"].append({"id": "tarif_sub", "dossier": "tarif_sub", "type_lot": "tarif",
                            "manifest_sha256": hashlib.sha256((lot / "manifest.json").read_bytes()).hexdigest()})
    registre.write_text(json.dumps(contenu))
    avant = snapshot(racine)
    r = client.get(BASE + "/lots/tarif_sub/tariff/0101000000", headers=ADMIN)
    assert r.status_code == 200, r.text
    assert len(r.json()["resultat"]["hierarchie_declaree"]["subdivisions_nationales"]) == 3
    assert r.json()["publication_active"] is False
    assert snapshot(racine) == avant


@pytest.mark.parametrize("format_source", ["xlsx", "xml"])
def test_mapping_subdivision_xlsx_xml(tmp_path, format_source):
    if format_source == "xlsx":
        from openpyxl import load_workbook

        from tests.test_customs_xlsx import xlsx_fichiers
        source, metadata = xlsx_fichiers(tmp_path)
        classeur = load_workbook(source)
        table = classeur["Nomenclature"]
        table.cell(1, 8, "Subdivision")
        table.cell(2, 8, "010100000")
        classeur.save(source)
        classeur.close()
    else:
        from tests.test_customs_xml import xml_fichiers
        source, metadata = xml_fichiers(tmp_path)
        source.write_text(source.read_text().replace("</Ligne>", "<Subdivision>010100000</Subdivision></Ligne>"))
    meta = json.loads(metadata.read_text())
    meta["lot"]["subdivisions_nationales"] = subdivisions()
    meta["colonnes"]["code_subdivision_nationale"] = "Subdivision"
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    sortie = tmp_path / "lot"
    preparer_tarif(source, metadata, sortie)
    assert charger_lot(sortie)[0].lignes[0].code_subdivision_nationale == "010100000"
