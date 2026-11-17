"""Navigation de fixtures NON OFFICIELLES uniquement, sans règle applicable."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests import test_customs_review
from tests.test_customs_reference import fichiers, snapshot
from tests.test_customs_search import lot_tarif
from unocr.cli import main
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.tariff_tree import ParamArbreTarifInvalide, parcourir_tarif

revue = test_customs_review.revue
ADMIN, BASE = test_customs_review.ADMIN, test_customs_review.BASE


def test_parcours_complet_et_references_sans_ecriture(tmp_path):
    lot = lot_tarif(tmp_path)
    avant = snapshot(tmp_path)
    rep = parcourir_tarif(lot)
    assert rep["parent_trouve"] is None and rep["parent_declare"] is None
    assert rep["niveau_suivant"] == "chapitres"
    section = rep["enfants_declares"][0]["id"]
    for niveau, parent, attendu in [("chapitres", section, "01"), ("positions", "01", "0101"), ("sh6", "0101", "010100")]:
        rep = parcourir_tarif(lot, niveau, parent)
        assert rep["parent_trouve"] is True
        assert rep["enfants_declares"][0]["code"] == attendu
        assert rep["enfants_declares"][0]["reference"]["source_id"] == rep["source_declaree"]["id"]
    codes = parcourir_tarif(lot, "codes", "010100")
    assert codes["total_enfants_declares"] == 5
    assert [v["code_tarifaire_10"] for v in codes["enfants_declares"]] == ["010100000" + str(i) for i in range(5)]
    assert codes["enfants_declares"][0]["designation_officielle_ar"] == "مُعَـدَّات اختبار غير رسمية"
    assert codes["enfants_declares"][0]["taux_droits_douane"] is None
    assert codes["niveau_suivant"] is None
    assert codes["publication_active"] is False and codes["fiscalite_applicable_etablie"] is False
    assert codes["completude_reglementaire"] == "non_etablie"
    assert codes["archive"]["manifest_sha256"]
    assert snapshot(tmp_path) == avant


def test_pagination_exacte_et_fin(tmp_path):
    lot = lot_tarif(tmp_path)
    rep = parcourir_tarif(lot, "codes", "010100", 2, 0)
    assert len(rep["enfants_declares"]) == 2 and rep["decalage_suivant"] == 2
    dernier = parcourir_tarif(lot, "codes", "010100", 2, 4)
    assert dernier["total_enfants_declares"] == 5 and len(dernier["enfants_declares"]) == 1
    assert dernier["decalage_suivant"] is None
    loin = parcourir_tarif(lot, "codes", "010100", 100, 1_000_000)
    assert loin["total_enfants_declares"] == 5 and loin["enfants_declares"] == []
    assert loin["parent_trouve"] is True


def test_parent_present_vide_distinct_absent_et_id_unicode(tmp_path):
    source, metadata = fichiers(tmp_path)
    meta = json.loads(metadata.read_text())
    section = dict(meta["lot"]["sections"][0], id="قسم تجريبي غير رسمي")
    meta["lot"]["sections"].append(section)
    metadata.write_text(json.dumps(meta, ensure_ascii=False))
    lot = tmp_path / "lot"
    preparer_tarif(source, metadata, lot)
    vide = parcourir_tarif(lot, "chapitres", section["id"])
    assert vide["parent_trouve"] is True
    assert vide["total_enfants_declares"] == 0
    absent = parcourir_tarif(lot, "chapitres", "INCONNU")
    assert absent["parent_trouve"] is False and absent["parent_declare"] is None
    assert absent["enfants_declares"] == []
    assert absent["completude_reglementaire"] == "non_etablie"


@pytest.mark.parametrize("niveau,parent", [("positions", "99"), ("sh6", "9999"), ("codes", "999999")])
def test_parent_numerique_absent_non_invente(tmp_path, niveau, parent):
    rep = parcourir_tarif(lot_tarif(tmp_path), niveau, parent)
    assert rep["parent_trouve"] is False
    assert rep["total_enfants_declares"] == 0 and rep["enfants_declares"] == []


@pytest.mark.parametrize("niveau,parent", [(None, None), (True, None), ("chapters", None), ("", None),
                                          ("sections", ""), ("sections", "S"), ("chapitres", None),
                                          ("chapitres", " "), ("chapitres", "S\n"), ("chapitres", "x" * 257),
                                          ("positions", "1"), ("positions", "０１"), ("positions", "٠١"),
                                          ("sh6", "0101 "), ("codes", "010100\n"), ("codes", 10100)])
def test_parametres_stricts_avant_lecture(tmp_path, niveau, parent):
    with pytest.raises(ParamArbreTarifInvalide):
        parcourir_tarif(tmp_path / "absent", niveau, parent)


@pytest.mark.parametrize("limite,decalage", [(False, 0), (0, 0), (101, 0), (1.0, 0), (20, True), (20, -1), (20, 1_000_001)])
def test_pagination_stricte_avant_lecture(tmp_path, limite, decalage):
    with pytest.raises(ParamArbreTarifInvalide):
        parcourir_tarif(tmp_path / "absent", limite=limite, decalage=decalage)


def test_corruption_et_symlink_refuses(tmp_path):
    lot = lot_tarif(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(lot, target_is_directory=True)
    with pytest.raises(ValueError):
        parcourir_tarif(alias)
    (lot / "lot.json").write_text('{}')
    with pytest.raises(ValueError):
        parcourir_tarif(lot)


def test_cli_et_processus_reel_isole(tmp_path, capsys):
    lot = lot_tarif(tmp_path)
    avant = snapshot(lot)
    assert main(["customs-tariff-tree", str(lot), "--level", "codes", "--parent", "010100", "--limit", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["enfants_declares"][0]["code_tarifaire_10"] == "0101000000"
    assert main(["customs-tariff-tree", str(lot), "--level", "codes"]) == 2
    assert json.loads(capsys.readouterr().out)["statut"] == "refuse"
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
               UNOCR_DATA_DIR=str(tmp_path / "data"), UNOCR_LOG_DIR=str(tmp_path / "logs"))
    p = subprocess.run([sys.executable, "-m", "unocr.cli", "customs-tariff-tree", str(lot)], env=env,
                       capture_output=True, text=True, timeout=20)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout)["niveau"] == "sections"
    assert snapshot(lot) == avant


def test_api_parcours_epingle_et_parent_absent(revue):
    client, racine, registre, cfg = revue
    avant = snapshot(racine)
    r = client.get(BASE + "/lots/tarif_a/tree?level=codes&parent=010100&limit=2", headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert len(r.json()["resultat"]["enfants_declares"]) == 2
    assert r.json()["resultat"]["parent_trouve"] is True
    absent = client.get(BASE + "/lots/tarif_a/tree?level=codes&parent=999999", headers=ADMIN)
    assert absent.status_code == 200 and absent.json()["resultat"]["parent_trouve"] is False
    assert str(racine) not in r.text and snapshot(racine) == avant


@pytest.mark.parametrize("headers,statut", [({}, 401), ({"Authorization": "Bearer INCONNU"}, 401),
                                            ({"Authorization": "Bearer TEST_LECTEUR_NON_PRODUCTION"}, 403)])
def test_api_habilitations(revue, headers, statut):
    client, *_ = revue
    assert client.get(BASE + "/lots/tarif_a/tree", headers=headers).status_code == statut


@pytest.mark.parametrize("suffixe,statut", [('/lots/code_a/tree', 422), ('/lots/inconnu/tree', 404),
                                           ('/lots/tarif_a/tree?level=codes', 422), ('/lots/tarif_a/tree?level=inconnu', 422),
                                           ('/lots/tarif_a/tree?parent=S', 422), ('/lots/tarif_a/tree?limit=101', 422)])
def test_api_types_et_parametres(revue, suffixe, statut):
    client, *_ = revue
    assert client.get(BASE + suffixe, headers=ADMIN).status_code == statut


def test_api_epingle_et_mode_ouvert(revue, monkeypatch):
    from unocr import api
    from unocr.rbac import RegistreRBAC
    from unocr.routes import customs_review
    client, *_ = revue
    reel = customs_review.parcourir_tarif

    def remplace(*args):
        rep = reel(*args)
        rep["archive"]["manifest_sha256"] = "0" * 64
        return rep
    monkeypatch.setattr(customs_review, "parcourir_tarif", remplace)
    assert client.get(BASE + "/lots/tarif_a/tree", headers=ADMIN).status_code == 409
    monkeypatch.setattr(api, "_rbac", RegistreRBAC(actif=False))
    assert client.get(BASE + "/lots/tarif_a/tree").status_code == 403
