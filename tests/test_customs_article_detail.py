"""Lectures de transcriptions NON OFFICIELLES ; aucun texte applicable attesté."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests import test_customs_review
from tests.test_customs_history import preparer
from tests.test_customs_reference import snapshot
from unocr.cli import main
from unocr.customs_reference.article_detail import ParamArticleInvalide, consulter_article

revue = test_customs_review.revue
ADMIN, BASE = test_customs_review.ADMIN, test_customs_review.BASE


def test_version_exacte_metadata_et_source_sans_ecriture(tmp_path):
    lot = preparer(tmp_path)
    avant = snapshot(tmp_path)
    rep = consulter_article(lot, "TEST_O_A")
    assert rep["article_trouve"] is True
    assert rep["fragment"] == "FIXTURE NON OFFICIELLE O"
    assert rep["version_declaree"]["numero_article"] == "5 bis"
    assert rep["version_declaree"]["nature_version"] == "originale"
    assert rep["version_declaree"]["date_publication_declaree"] is None
    assert rep["document_declare"]["date_publication"] == "2000-01-01"
    assert rep["document_declare"]["id"] == rep["version_declaree"]["reference"]["source_id"]
    assert rep["version_declaree"]["hierarchie"][-1]["identifiant"] == "5 bis"
    assert rep["champs_texte_renseignes"]["texte_arabe"] is True
    assert rep["publication_active"] is False and rep["restitution_juridique_a_date"] is False
    assert rep["validation_juridique"] == "non_validee"
    assert rep["transcription_verification"] == "non_verifiee"
    assert rep["archive"]["manifest_sha256"]
    assert snapshot(tmp_path) == avant


def test_langue_absente_sans_repli_et_arabe_exact(tmp_path):
    lot = preparer(tmp_path)
    fr = consulter_article(lot, "TEST_O_A", "texte_francais")
    assert fr["texte_renseigne"] is False and fr["fragment"] is None and fr["total_caracteres"] is None
    ar = consulter_article(lot, "TEST_O_A", "texte_arabe")
    assert ar["fragment"] == "نص تجريبي غير رسمي"
    assert ar["decalage_suivant"] is None


def test_lecture_tout_le_texte_par_points_de_code_sans_normaliser(tmp_path):
    texte = "  É\nعَ😀e\u0301\t" * 2200
    def changer(brut, meta):
        brut["articles"][0].update(texte_integral=texte, texte_francais=texte)
    lot = preparer(tmp_path, changer)
    avant = snapshot(lot)
    fragments, offset = [], 0
    while True:
        rep = consulter_article(lot, "TEST_O_A", limite=3111, decalage=offset)
        assert len(rep["fragment"]) <= 3111
        assert rep["total_caracteres"] == len(texte)
        fragments.append(rep["fragment"])
        if rep["decalage_suivant"] is None:
            break
        offset = rep["decalage_suivant"]
    assert "".join(fragments) == texte
    assert snapshot(lot) == avant


def test_plage_apres_fin_distinguee_absence_de_texte(tmp_path):
    lot = preparer(tmp_path)
    rep = consulter_article(lot, "TEST_O_A", limite=16_000, decalage=67_108_864)
    assert rep["texte_renseigne"] is True and rep["fragment"] == ""
    assert rep["total_caracteres"] > 0 and rep["decalage_suivant"] is None
    assert rep["article_trouve"] is True


@pytest.mark.parametrize("identifiant", ["5 bis", "test_o_a", " TEST_O_A", "INCONNU"])
def test_aucune_selection_par_numero_ou_correction(tmp_path, identifiant):
    rep = consulter_article(preparer(tmp_path), identifiant)
    assert rep["article_trouve"] is False
    assert rep["version_declaree"] is rep["document_declare"] is rep["fragment"] is None
    assert rep["completude_reglementaire"] == "non_etablie"


def test_versions_et_champs_origine_modificatif_separes(tmp_path):
    def changer(brut, meta):
        brut["articles"][0]["texte_origine"] = brut["articles"][0]["texte_integral"]
        brut["articles"][1]["texte_modificatif"] = brut["articles"][1]["texte_integral"]
    lot = preparer(tmp_path, changer)
    assert consulter_article(lot, "TEST_O_A", "texte_origine")["fragment"] == "FIXTURE NON OFFICIELLE O"
    assert consulter_article(lot, "TEST_M_A", "texte_modificatif")["fragment"] == "FIXTURE NON OFFICIELLE M"
    assert consulter_article(lot, "TEST_C_A", "texte_origine")["fragment"] is None
    assert consulter_article(lot, "TEST_C_A")["version_declaree"]["nature_version"] == "consolidee_provisoire"


@pytest.mark.parametrize("identifiant", [None, True, 1, "", " ", "x" * 257, "ID\n", "ID\x00"])
def test_id_invalide_avant_lecture(tmp_path, identifiant):
    with pytest.raises(ParamArticleInvalide):
        consulter_article(tmp_path / "absent", identifiant)


@pytest.mark.parametrize("champ", [None, True, "", "texte", "../secret"])
def test_champ_invalide_avant_lecture(tmp_path, champ):
    with pytest.raises(ParamArticleInvalide):
        consulter_article(tmp_path / "absent", "ID", champ)


@pytest.mark.parametrize("limite,decalage", [(True, 0), (0, 0), (16001, 0), (1.0, 0), (1, True), (1, -1), (1, 67_108_865)])
def test_plages_strictes_avant_lecture(tmp_path, limite, decalage):
    with pytest.raises(ParamArticleInvalide):
        consulter_article(tmp_path / "absent", "ID", limite=limite, decalage=decalage)


def test_corruption_et_symlink_refuses(tmp_path):
    lot = preparer(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(lot, target_is_directory=True)
    with pytest.raises(ValueError):
        consulter_article(alias, "TEST_O_A")
    (lot / "lot_code.json").write_text('{}')
    with pytest.raises(ValueError):
        consulter_article(lot, "TEST_O_A")


def test_cli_et_processus_reel_sans_ecriture(tmp_path, capsys):
    lot = preparer(tmp_path)
    avant = snapshot(lot)
    assert main(["customs-code-read", str(lot), "--id", "TEST_O_A", "--limit", "7"]) == 0
    assert json.loads(capsys.readouterr().out)["fragment"] == "FIXTURE"
    assert main(["customs-code-read", str(lot), "--id", "TEST_O_A", "--limit", "0"]) == 2
    assert json.loads(capsys.readouterr().out)["statut"] == "refuse"
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
               UNOCR_DATA_DIR=str(tmp_path / "data"), UNOCR_LOG_DIR=str(tmp_path / "logs"))
    p = subprocess.run([sys.executable, "-m", "unocr.cli", "customs-code-read", str(lot), "--id", "TEST_O_A", "--field", "texte_arabe"],
                       env=env, capture_output=True, text=True, timeout=20)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout)["fragment"] == "نص تجريبي غير رسمي"
    assert snapshot(lot) == avant


def test_api_fragments_et_id_absent_sans_ecriture(revue):
    client, racine, registre, cfg = revue
    avant = snapshot(racine)
    r = client.get(BASE + "/lots/code_a/article", params={"article_id": "TEST_O_A", "limit": 8}, headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert r.json()["resultat"]["fragment"] == "ÉQUIPEME"
    assert r.json()["resultat"]["decalage_suivant"] == 8
    absent = client.get(BASE + "/lots/code_a/article?article_id=5", headers=ADMIN)
    assert absent.status_code == 200 and absent.json()["resultat"]["article_trouve"] is False
    assert str(racine) not in r.text and snapshot(racine) == avant


@pytest.mark.parametrize("headers,statut", [({}, 401), ({"Authorization": "Bearer INCONNU"}, 401),
                                            ({"Authorization": "Bearer TEST_LECTEUR_NON_PRODUCTION"}, 403)])
def test_api_habilitations(revue, headers, statut):
    client, *_ = revue
    assert client.get(BASE + "/lots/code_a/article?article_id=TEST_O_A", headers=headers).status_code == statut


@pytest.mark.parametrize("suffixe,statut", [('/lots/tarif_a/article?article_id=ID', 422), ('/lots/inconnu/article?article_id=ID', 404),
                                           ('/lots/code_a/article', 422), ('/lots/code_a/article?article_id=%20', 422),
                                           ('/lots/code_a/article?article_id=ID&field=inconnu', 422),
                                           ('/lots/code_a/article?article_id=ID&limit=16001', 422),
                                           ('/lots/code_a/article?article_id=ID&offset=67108865', 422)])
def test_api_parametres_et_types(revue, suffixe, statut):
    client, *_ = revue
    assert client.get(BASE + suffixe, headers=ADMIN).status_code == statut


def test_api_epingle_et_mode_ouvert(revue, monkeypatch):
    from unocr import api
    from unocr.rbac import RegistreRBAC
    from unocr.routes import customs_review
    client, *_ = revue
    reel = customs_review.consulter_article

    def remplace(*args):
        rep = reel(*args)
        rep["archive"]["manifest_sha256"] = "0" * 64
        return rep
    monkeypatch.setattr(customs_review, "consulter_article", remplace)
    assert client.get(BASE + "/lots/code_a/article?article_id=TEST_O_A", headers=ADMIN).status_code == 409
    monkeypatch.setattr(api, "_rbac", RegistreRBAC(actif=False))
    assert client.get(BASE + "/lots/code_a/article?article_id=TEST_O_A").status_code == 403
