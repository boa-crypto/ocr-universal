"""Navigation sur fixtures NON OFFICIELLES, sans inférence de parent."""
import hashlib
import json

import pytest

from tests import test_customs_review
from tests.test_customs_reference import snapshot
from tests.test_customs_subdivisions import lot_declare
from unocr.cli import main
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.tariff_tree import ParamArbreTarifInvalide, parcourir_tarif

revue = test_customs_review.revue
ADMIN, BASE = test_customs_review.ADMIN, test_customs_review.BASE


def preparer(root):
    source, metadata = lot_declare(root)
    # Ligne sans parent intermédiaire malgré préfixe commun : ne pas la rattacher.
    lignes = json.loads(source.read_text())
    lignes.append({**lignes[0], "id": "TEST_DIRECT", "code_tarifaire_10": "0101000001", "code_subdivision_nationale": None})
    source.write_text(json.dumps(lignes))
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata.write_text(json.dumps(meta))
    lot = root / "lot"
    preparer_tarif(source, metadata, lot)
    return lot


def test_enfants_mixtes_et_chaine_sans_inference(tmp_path):
    lot = preparer(tmp_path)
    avant = snapshot(lot)
    rep = parcourir_tarif(lot, "subdivisions", "010100")
    assert [v["type_noeud"] for v in rep["enfants_declares"]] == ["subdivision_nationale", "code10"]
    assert rep["enfants_declares"][1]["code_tarifaire_10"] == "0101000001"
    for parent, enfant in [("0101000", "01010000"), ("01010000", "010100000")]:
        assert parcourir_tarif(lot, "subdivisions", parent)["enfants_declares"][0]["code"] == enfant
    feuille = parcourir_tarif(lot, "subdivisions", "010100000")
    assert feuille["enfants_declares"][0]["code_tarifaire_10"] == "0101000000"
    assert feuille["total_enfants_declares"] == 1
    assert parcourir_tarif(lot, "codes", "010100")["total_enfants_declares"] == 2
    assert parcourir_tarif(lot, "sh6", "0101")["niveau_suivant_detaille"] == "subdivisions"
    assert snapshot(lot) == avant


def test_pagination_mixte_et_absence(tmp_path):
    lot = preparer(tmp_path)
    a = parcourir_tarif(lot, "subdivisions", "010100", 1, 0)
    b = parcourir_tarif(lot, "subdivisions", "010100", 1, 1)
    assert a["decalage_suivant"] == 1 and b["decalage_suivant"] is None
    assert a["enfants_declares"] + b["enfants_declares"] == parcourir_tarif(lot, "subdivisions", "010100")["enfants_declares"]
    assert parcourir_tarif(lot, "subdivisions", "010100", 1, 99)["enfants_declares"] == []
    absent = parcourir_tarif(lot, "subdivisions", "9999999")
    assert absent["parent_trouve"] is False and absent["enfants_declares"] == []


@pytest.mark.parametrize("parent", [None, "", "01010", "0101000000", "٠١٠١٠٠", "010100 ", "010100\n", 10100])
def test_parametres_avant_lecture(tmp_path, parent):
    with pytest.raises(ParamArbreTarifInvalide):
        parcourir_tarif(tmp_path / "absent", "subdivisions", parent)


def test_cli_niveau_detaille(tmp_path, capsys):
    lot = preparer(tmp_path)
    assert main(["customs-tariff-tree", str(lot), "--level", "subdivisions", "--parent", "010100"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["mode_navigation"] == "enfants_directs_declares_mixtes"
    assert rep["publication_active"] is False


def test_api_niveau_detaille_epingle_et_non_modifiant(revue):
    client, racine, registre, cfg = revue
    entrees = cfg.root / "entrees_subtree"
    entrees.mkdir()
    source_lot = preparer(entrees)
    import shutil
    shutil.copytree(source_lot, racine / "subtree")
    reg = json.loads(registre.read_text())
    reg["lots"].append({"id": "subtree", "dossier": "subtree", "type_lot": "tarif",
                        "manifest_sha256": hashlib.sha256((source_lot / "manifest.json").read_bytes()).hexdigest()})
    registre.write_text(json.dumps(reg))
    avant = snapshot(racine)
    r = client.get(BASE + "/lots/subtree/tree?level=subdivisions&parent=010100", headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert r.json()["resultat"]["total_enfants_declares"] == 2
    assert snapshot(racine) == avant
