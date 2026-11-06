"""Diagnostic descriptif de fixtures NON OFFICIELLES ; aucun score officiel."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests import test_customs_review
from tests.test_customs_history import preparer
from tests.test_customs_reference import fichiers, snapshot
from tests.test_customs_search import lot_code, lot_tarif
from unocr.cli import main
from unocr.customs_reference.coverage import ParamCouvertureInvalide, diagnostiquer_couverture
from unocr.customs_reference.importer import preparer_tarif

revue = test_customs_review.revue
ADMIN, BASE = test_customs_review.ADMIN, test_customs_review.BASE


def assertions_prudence(rep):
    assert rep["publication_active"] is False
    assert rep["validation_juridique"] == "non_validee"
    assert rep["utilisable_pour_calcul_douanier"] is False
    assert rep["completude_reglementaire"] == "non_etablie"
    assert rep["nombre_officiel_attendu"] is None
    assert rep["pourcentage_completude_reglementaire"] is None
    assert rep["integrite_locale"] == "coherente_au_rejeu"
    assert rep["archive"]["manifest_sha256"]
    assert all(s["verification"] == "non_verifiee" for s in rep["sources_declarees"])


def test_compteurs_tarif_et_champs_non_renseignes_sans_ecriture(tmp_path):
    lot = lot_tarif(tmp_path)
    avant = snapshot(tmp_path)
    rep = diagnostiquer_couverture(lot, "tarif")
    assertions_prudence(rep)
    indicateurs = rep["indicateurs"]
    assert indicateurs["compteurs"]["lignes_code10"] == 5
    assert indicateurs["compteurs"]["mesures"] == 1
    assert indicateurs["lignes_champs_non_renseignes"]["designation_officielle_fr"] == 1
    assert indicateurs["lignes_champs_non_renseignes"]["designation_officielle_ar"] == 3
    assert indicateurs["lignes_champs_non_renseignes"]["taux_droits_douane"] == 5
    assert indicateurs["mesures_par_type"]["restriction"] == 1
    assert indicateurs["mesures_par_type"]["droit"] == 0
    assert indicateurs["lignes_sans_mesure_declaree"] == 4
    assert indicateurs["subdivision_nationale_intermediaire"] == "non_decrite_par_le_contrat"
    assert not any(indicateurs["parents_sans_ligne_code10"].values())
    assert snapshot(tmp_path) == avant


def test_zero_decimal_n_est_pas_non_renseigne(tmp_path):
    source, metadata = fichiers(tmp_path)
    meta = json.loads(metadata.read_text())
    ref = json.loads(source.read_text())[0]["reference"]
    meta["lot"]["mesures"] = [{"id": "TEST_ZERO_NON_OFFICIEL", "code_tarifaire_10": "0101000000",
                               "type_mesure": "droit", "description": "TAUX TEST NON APPLICABLE", "taux": "0",
                               "unite_taux": "pourcent", "reference": ref}]
    metadata.write_text(json.dumps(meta))
    lot = tmp_path / "lot"
    preparer_tarif(source, metadata, lot)
    rep = diagnostiquer_couverture(lot, "tarif")
    assert rep["indicateurs"]["mesures_champs_non_renseignes"]["taux"] == 0
    assert rep["indicateurs"]["lignes_champs_non_renseignes"]["taux_droits_douane"] == 1
    assertions_prudence(rep)


def test_compteurs_code_numeros_et_relations_declarees(tmp_path):
    lot = lot_code(tmp_path)
    avant = snapshot(tmp_path)
    rep = diagnostiquer_couverture(lot, "code")
    assertions_prudence(rep)
    ind = rep["indicateurs"]
    assert ind["compteurs"] == {"documents": 3, "articles_transcrits": 3, "numeros_article_distincts": 2, "relations_declarees": 1}
    assert ind["documents_par_nature"] == {"code_original": 1, "acte_modificatif": 1, "compilation": 1}
    assert ind["articles_par_nature"] == {"originale": 1, "modificative": 1, "consolidee_provisoire": 1}
    assert ind["articles_champs_non_renseignes"]["date_publication"] == 3
    assert ind["occurrences_niveaux_hierarchiques"]["article"] == 3
    assert ind["occurrences_niveaux_hierarchiques"]["alinea"] == 0
    assert ind["relations_par_type"]["modifie"] == 1
    assert ind["articles_sans_relation_declaree"] == 1
    assert ind["documents_sans_article_transcrit"] == []
    # Aucun texte, URL ou nom de fichier reçu dans ce diagnostic de compteurs.
    assert "DISPOSITION MODIFICATIVE NON OFFICIELLE" not in json.dumps(rep)
    assert snapshot(tmp_path) == avant


def test_zero_article_sans_conclusion_completude(tmp_path):
    def changer(brut, meta):
        brut.update(articles=[], relations=[])
        meta["documents"][0]["document"]["date_publication"] = None
    rep = diagnostiquer_couverture(preparer(tmp_path, changer), "code")
    assert rep["indicateurs"]["compteurs"]["articles_transcrits"] == 0
    assert rep["indicateurs"]["documents_sans_article_transcrit"] == ["TEST_C", "TEST_M", "TEST_O"]
    assert rep["sources_champs_non_renseignes"]["date_publication"] == 1
    assert set(rep["indicateurs"]["articles_champs_non_renseignes"].values()) == {0}
    assertions_prudence(rep)


def test_sources_memes_octets_signalees_sans_fusion(tmp_path):
    import hashlib

    def changer(brut, meta):
        original = tmp_path / meta["documents"][0]["fichier_recu"]
        copie = tmp_path / meta["documents"][2]["fichier_recu"]
        copie.write_bytes(original.read_bytes())
        meta["documents"][2]["document"]["sha256"] = hashlib.sha256(copie.read_bytes()).hexdigest()
    rep = diagnostiquer_couverture(preparer(tmp_path, changer), "code")
    assert len(rep["indicateurs"]["empreintes_documentaires_dupliquees"]) == 1
    assert rep["indicateurs"]["compteurs"]["documents"] == 3
    assert len(rep["sources_declarees"]) == 3
    assertions_prudence(rep)


@pytest.mark.parametrize("type_lot", [None, True, 0, "", "auto", "tariff", "CODE", [], {}])
def test_type_explicite_avant_lecture(tmp_path, type_lot):
    with pytest.raises(ParamCouvertureInvalide):
        diagnostiquer_couverture(tmp_path / "absent", type_lot)


@pytest.mark.parametrize("type_lot,preparer_lot", [("tarif", lot_tarif), ("code", lot_code)])
def test_mauvais_type_corruption_et_symlink_refuses(tmp_path, type_lot, preparer_lot):
    lot = preparer_lot(tmp_path)
    with pytest.raises(ValueError):
        diagnostiquer_couverture(lot, "code" if type_lot == "tarif" else "tarif")
    alias = tmp_path / "alias"
    alias.symlink_to(lot, target_is_directory=True)
    with pytest.raises(ValueError):
        diagnostiquer_couverture(alias, type_lot)
    (lot / "manifest.json").write_text('{}')
    with pytest.raises(ValueError):
        diagnostiquer_couverture(lot, type_lot)


def test_cli_json_sans_ecriture_et_processus_isole(tmp_path, capsys):
    lot = lot_tarif(tmp_path)
    avant = snapshot(lot)
    assert main(["customs-coverage", str(lot), "--type", "tarif"]) == 0
    assertions_prudence(json.loads(capsys.readouterr().out))
    assert main(["customs-coverage", str(lot), "--type", "code"]) == 2
    assert json.loads(capsys.readouterr().out)["statut"] == "refuse"
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
               UNOCR_DATA_DIR=str(tmp_path / "data"), UNOCR_LOG_DIR=str(tmp_path / "logs"))
    p = subprocess.run([sys.executable, "-m", "unocr.cli", "customs-coverage", str(lot), "--type", "tarif"],
                       env=env, capture_output=True, text=True, timeout=20)
    assert p.returncode == 0, p.stderr
    assertions_prudence(json.loads(p.stdout))
    assert snapshot(lot) == avant


@pytest.mark.parametrize("identifiant", ["code_a", "tarif_a"])
def test_api_deux_types_epingles_et_sans_ecriture(revue, identifiant):
    client, racine, registre, cfg = revue
    avant = snapshot(racine)
    r = client.get(BASE + f"/lots/{identifiant}/coverage", headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assertions_prudence(r.json()["resultat"])
    assert str(racine) not in r.text
    assert snapshot(racine) == avant


@pytest.mark.parametrize("headers,statut", [({}, 401), ({"Authorization": "Bearer INCONNU"}, 401),
                                            ({"Authorization": "Bearer TEST_LECTEUR_NON_PRODUCTION"}, 403)])
def test_api_habilitations(revue, headers, statut):
    client, *_ = revue
    assert client.get(BASE + "/lots/code_a/coverage", headers=headers).status_code == statut


def test_api_absent_et_mode_ouvert(revue, monkeypatch):
    from unocr import api
    from unocr.rbac import RegistreRBAC
    client, *_ = revue
    assert client.get(BASE + "/lots/inconnu/coverage", headers=ADMIN).status_code == 404
    monkeypatch.setattr(api, "_rbac", RegistreRBAC(actif=False))
    assert client.get(BASE + "/lots/code_a/coverage").status_code == 403


def test_api_epingle_retour_et_registre_absent(revue, monkeypatch):
    from unocr.routes import customs_review
    client, racine, registre, cfg = revue
    reel = customs_review.diagnostiquer_couverture

    def remplace(*args):
        rep = reel(*args)
        rep["archive"]["manifest_sha256"] = "0" * 64
        return rep
    monkeypatch.setattr(customs_review, "diagnostiquer_couverture", remplace)
    r = client.get(BASE + "/lots/code_a/coverage", headers=ADMIN)
    assert r.status_code == 409 and "resultat" not in r.json()
    registre.unlink()
    assert client.get(BASE + "/lots/code_a/coverage", headers=ADMIN).status_code == 503


def test_parents_sans_ligne_et_champ_blanc_restent_constats(tmp_path):
    import copy
    import hashlib

    source, metadata = fichiers(tmp_path)
    lignes = json.loads(source.read_text())
    lignes[0].update(designation_officielle_fr=" ", designation_officielle_ar="نص اختبار غير رسمي")
    source.write_text(json.dumps(lignes, ensure_ascii=False))
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    chapitre = copy.deepcopy(meta["lot"]["chapitres"][0])
    chapitre["code"] = "02"
    position = copy.deepcopy(meta["lot"]["positions"][0])
    position.update(code="0201", chapitre="02")
    sh6 = copy.deepcopy(meta["lot"]["sous_positions"][0])
    sh6.update(code="020100", position="0201")
    meta["lot"]["chapitres"].append(chapitre)
    meta["lot"]["positions"].append(position)
    meta["lot"]["sous_positions"].append(sh6)
    metadata.write_text(json.dumps(meta))
    lot = tmp_path / "lot"
    preparer_tarif(source, metadata, lot)
    rep = diagnostiquer_couverture(lot, "tarif")
    assert rep["indicateurs"]["parents_sans_ligne_code10"] == {"sections": 0, "chapitres": 1, "positions": 1, "sh6": 1}
    assert rep["indicateurs"]["lignes_champs_non_renseignes"]["designation_officielle_fr"] == 1
    assertions_prudence(rep)
