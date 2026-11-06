"""Fiches de fixtures NON OFFICIELLES, aucun taux applicable attesté."""
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
from unocr.customs_reference.tariff_detail import ParamFicheTarifInvalide, consulter_code

revue = test_customs_review.revue
ADMIN, BASE = test_customs_review.ADMIN, test_customs_review.BASE
CODE = "0101000000"


def test_fiche_exacte_parents_et_champs_inconnus(tmp_path):
    lot = lot_tarif(tmp_path)
    avant = snapshot(tmp_path)
    rep = consulter_code(lot, CODE)
    assert rep["ligne_trouvee"] is True
    assert rep["ligne_declaree"]["code_tarifaire_10"] == CODE
    assert rep["ligne_declaree"]["designation_officielle_ar"] == "مُعَـدَّات اختبار غير رسمية"
    assert rep["ligne_declaree"]["taux_droits_douane"] is None
    assert rep["ligne_declaree"]["taux_tva"] is None
    assert rep["hierarchie_declaree"]["chapitre"]["code"] == "01"
    assert rep["hierarchie_declaree"]["position"]["code"] == "0101"
    assert rep["hierarchie_declaree"]["sh6"]["code"] == "010100"
    assert rep["hierarchie_declaree"]["subdivision_nationale_intermediaire"] is None
    assert rep["hierarchie_declaree"]["section"]["reference"]["source_id"] == rep["source_declaree"]["id"]
    assert rep["total_mesures_declarees"] == 1
    assert rep["mesures_declarees"][0]["type_mesure"] == "restriction"
    assert rep["source_declaree"]["verification"] == "non_verifiee"
    for cle in ["publication_active", "fiscalite_applicable_etablie", "classement_douanier_valide", "restitution_juridique_a_date"]:
        assert rep[cle] is False
    assert rep["validation_juridique"] == "non_validee"
    assert rep["archive"]["manifest_sha256"]
    assert snapshot(tmp_path) == avant


def test_absence_n_est_pas_un_tarif_zero(tmp_path):
    lot = lot_tarif(tmp_path)
    rep = consulter_code(lot, "9999999999")
    assert rep["ligne_trouvee"] is False
    assert rep["ligne_declaree"] is rep["hierarchie_declaree"] is None
    assert rep["mesures_declarees"] == []
    assert rep["completude_reglementaire"] == "non_etablie"
    assert rep["fiscalite_applicable_etablie"] is False
    # Une autre ligne réellement présente sans mesure ne devient pas exonérée.
    autre = consulter_code(lot, "0101000001")
    assert autre["ligne_trouvee"] is True and autre["total_mesures_declarees"] == 0
    assert autre["ligne_declaree"]["taux_droits_douane"] is None


def test_mesures_source_dates_distinctes_precision_et_pagination(tmp_path):
    source, metadata = fichiers(tmp_path)
    meta = json.loads(metadata.read_text())
    ref = json.loads(source.read_text())[0]["reference"]
    meta["lot"]["mesures"] = [
        {"id": "TEST_Z", "code_tarifaire_10": CODE, "type_mesure": "droit", "description": "TEST NON OFFICIEL",
         "taux": "12.12345678901234567890123456789", "unite_taux": "pourcent", "reference": ref,
         "date_entree_vigueur": "2005-01-01", "date_fin_validite": "2006-01-01"},
        {"id": "TEST_A", "code_tarifaire_10": CODE, "type_mesure": "tva", "description": "TEST NON OFFICIEL",
         "taux": "0", "unite_taux": "pourcent", "reference": ref},
    ]
    metadata.write_text(json.dumps(meta))
    lot = tmp_path / "tarif"
    preparer_tarif(source, metadata, lot)
    rep = consulter_code(lot, CODE, 1, 0)
    assert rep["total_mesures_declarees"] == 2
    assert rep["mesures_declarees"][0]["id"] == "TEST_A"
    assert rep["mesures_declarees"][0]["taux"] == "0"
    assert rep["decalage_mesures_suivant"] == 1
    suivant = consulter_code(lot, CODE, 1, 1)
    mesure = suivant["mesures_declarees"][0]
    assert mesure["taux"] == "12.12345678901234567890123456789"
    assert mesure["date_fin_validite"] == "2006-01-01"
    assert suivant["decalage_mesures_suivant"] is None
    assert suivant["ligne_declaree"]["taux_droits_douane"] is None
    loin = consulter_code(lot, CODE, 100, 1_000_000)
    assert loin["mesures_declarees"] == [] and loin["total_mesures_declarees"] == 2


@pytest.mark.parametrize("code", [None, True, 101000000, "", "010100", "01010000000", " 0101000000", "0101000000\n",
                                  "٠١٠١٠٠٠٠٠٠", "０１０１００００００", "01010abcde", "../secret"])
def test_code_strict_avant_lecture(tmp_path, code):
    with pytest.raises(ParamFicheTarifInvalide):
        consulter_code(tmp_path / "absent", code)


@pytest.mark.parametrize("limite,decalage", [(True, 0), (0, 0), (101, 0), (1.0, 0), (20, True), (20, -1), (20, 1_000_001)])
def test_pagination_stricte_avant_lecture(tmp_path, limite, decalage):
    with pytest.raises(ParamFicheTarifInvalide):
        consulter_code(tmp_path / "absent", CODE, limite, decalage)


def test_corruption_et_symlink_refuses(tmp_path):
    lot = lot_tarif(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(lot, target_is_directory=True)
    with pytest.raises(ValueError):
        consulter_code(alias, CODE)
    (lot / "lot.json").write_text('{}')
    with pytest.raises(ValueError):
        consulter_code(lot, CODE)


def test_cli_json_et_refus_sans_ecriture(tmp_path, capsys):
    lot = lot_tarif(tmp_path)
    avant = snapshot(lot)
    assert main(["customs-tariff-show", str(lot), "--code", CODE]) == 0
    assert json.loads(capsys.readouterr().out)["ligne_declaree"]["code_tarifaire_10"] == CODE
    assert main(["customs-tariff-show", str(lot), "--code", "010100"]) == 2
    assert json.loads(capsys.readouterr().out)["statut"] == "refuse"
    assert snapshot(lot) == avant


def test_cli_processus_reel(tmp_path):
    lot = lot_tarif(tmp_path)
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
               UNOCR_DATA_DIR=str(tmp_path / "data"), UNOCR_LOG_DIR=str(tmp_path / "logs"))
    p = subprocess.run([sys.executable, "-m", "unocr.cli", "customs-tariff-show", str(lot), "--code", CODE],
                       env=env, capture_output=True, text=True, timeout=20)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout)["ligne_trouvee"] is True


def test_api_epingle_et_absence_sans_ecriture(revue):
    client, racine, registre, cfg = revue
    avant = snapshot(racine)
    rep = client.get(BASE + "/lots/tarif_a/tariff/" + CODE, headers=ADMIN)
    assert rep.status_code == 200 and rep.headers["cache-control"] == "no-store"
    assert rep.json()["resultat"]["ligne_declaree"]["code_tarifaire_10"] == CODE
    assert str(racine) not in rep.text
    absent = client.get(BASE + "/lots/tarif_a/tariff/9999999999", headers=ADMIN)
    assert absent.status_code == 200 and absent.json()["resultat"]["ligne_trouvee"] is False
    assert snapshot(racine) == avant


@pytest.mark.parametrize("headers,statut", [({}, 401), ({"Authorization": "Bearer INCONNU"}, 401),
                                            ({"Authorization": "Bearer TEST_LECTEUR_NON_PRODUCTION"}, 403)])
def test_api_habilitation(revue, headers, statut):
    client, *_ = revue
    assert client.get(BASE + "/lots/tarif_a/tariff/" + CODE, headers=headers).status_code == statut


@pytest.mark.parametrize("suffixe,statut", [('/lots/code_a/tariff/0101000000', 422),
                                           ('/lots/inconnu/tariff/0101000000', 404),
                                           ('/lots/tarif_a/tariff/010100', 422),
                                           ('/lots/tarif_a/tariff/0101000000?measures_limit=0', 422),
                                           ('/lots/tarif_a/tariff/0101000000?measures_offset=-1', 422)])
def test_api_parametres_et_types(revue, suffixe, statut):
    client, *_ = revue
    assert client.get(BASE + suffixe, headers=ADMIN).status_code == statut


def test_api_mode_ouvert_et_epingle(revue, monkeypatch):
    from unocr import api
    from unocr.rbac import RegistreRBAC
    from unocr.routes import customs_review
    client, *_ = revue
    reel = customs_review.consulter_code

    def remplace(*args):
        rep = reel(*args)
        rep["archive"]["manifest_sha256"] = "0" * 64
        return rep
    monkeypatch.setattr(customs_review, "consulter_code", remplace)
    rep = client.get(BASE + "/lots/tarif_a/tariff/" + CODE, headers=ADMIN)
    assert rep.status_code == 409 and "resultat" not in rep.json()
    monkeypatch.setattr(api, "_rbac", RegistreRBAC(actif=False))
    assert client.get(BASE + "/lots/tarif_a/tariff/" + CODE).status_code == 403
