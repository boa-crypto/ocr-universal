"""Chronologie de fixtures NON OFFICIELLES : jamais corpus applicable."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests import test_customs_review
from tests.test_customs_legal import fichiers_code
from tests.test_customs_reference import snapshot
from unocr.cli import main
from unocr.customs_reference.history import ParamHistoriqueInvalide, historique_article
from unocr.customs_reference.legal_importer import preparer_code

revue = test_customs_review.revue
ADMIN = test_customs_review.ADMIN
BASE = test_customs_review.BASE


def preparer(root, changer=None):
    transcription, metadata = fichiers_code(root)
    brut, meta = json.loads(transcription.read_text()), json.loads(metadata.read_text())
    if changer:
        changer(brut, meta)
    transcription.write_text(json.dumps(brut, ensure_ascii=False))
    metadata.write_text(json.dumps(meta, ensure_ascii=False))
    lot = root / "lot"
    preparer_code(transcription, metadata, lot)
    return lot


def test_separation_versions_et_relation_avec_autre_numero(tmp_path):
    lot = preparer(tmp_path)
    avant = snapshot(tmp_path)
    rapport = historique_article(lot, "5 bis")
    assert [a["id"] for a in rapport["versions_meme_numero"]] == ["TEST_O_A", "TEST_C_A"]
    assert [a["nature_version"] for a in rapport["versions_meme_numero"]] == ["originale", "consolidee_provisoire"]
    assert rapport["relations_declarees"][0]["origine_id"] == "TEST_M_A"
    assert rapport["relations_declarees"][0]["cible_id"] == "TEST_O_A"
    assert rapport["articles_contexte_relations"][0]["numero_article"] == "7"
    assert rapport["relations_declarees"][0]["reference"]["localisateur"]
    assert rapport["relations_declarees"][0]["justification"].startswith("FIXTURE NON OFFICIELLE")
    assert {d["id"] for d in rapport["documents_declares_page"]} == {"TEST_O", "TEST_M", "TEST_C"}
    assert rapport["succession_juridique_etablie"] is False
    assert rapport["restitution_juridique_a_date"] is False
    assert rapport["publication_active"] is False
    assert rapport["validation_juridique"] == "non_validee"
    assert rapport["completude_reglementaire"] == "non_etablie"
    assert rapport["archive"]["manifest_sha256"]
    assert snapshot(tmp_path) == avant


def test_meme_numero_ne_cree_pas_de_relation(tmp_path):
    def changer(brut, meta):
        brut["relations"] = []
        brut["articles"][1]["articles_lies"] = []
    rapport = historique_article(preparer(tmp_path, changer), "5 bis")
    assert rapport["total_versions_meme_numero"] == 2
    assert rapport["total_relations_declarees"] == 0
    assert rapport["articles_contexte_relations"] == []


def test_dates_distinctes_et_statut_declare_sans_applicabilite(tmp_path):
    def changer(brut, meta):
        brut["articles"][0].update(date_publication="2010-01-01", date_entree_vigueur="2011-01-01",
                                   date_fin_validite="2012-01-01", date_abrogation="2013-01-01",
                                   statut_juridique_declare="applicable", reference_jo="JO TEST NON OFFICIEL")
    rapport = historique_article(preparer(tmp_path, changer), "5 bis")
    version = rapport["versions_meme_numero"][0]
    assert version["id"] == "TEST_O_A"  # tri source 2000, pas date d'article 2010
    assert version["date_publication_declaree"] == "2010-01-01"
    assert version["date_entree_vigueur_declaree"] == "2011-01-01"
    assert version["date_fin_validite_declaree"] == "2012-01-01"
    assert version["date_abrogation_declaree"] == "2013-01-01"
    assert version["statut_juridique_declare"] == "applicable"
    assert version["validation_juridique"] == "non_validee"
    assert next(d for d in rapport["documents_declares_page"] if d["id"] == "TEST_O")["date_publication"] == "2000-01-01"


def test_dates_inconnues_en_fin_et_ordre_stable(tmp_path):
    def changer(brut, meta):
        meta["documents"][0]["document"]["date_publication"] = None
        brut["articles"].reverse()
        meta["documents"].reverse()
    rapport = historique_article(preparer(tmp_path, changer), "5 bis")
    assert [a["id"] for a in rapport["versions_meme_numero"]] == ["TEST_C_A", "TEST_O_A"]
    assert next(d for d in rapport["documents_declares_page"] if d["id"] == "TEST_O")["date_publication"] is None


def test_pagination_independante_versions_et_relations(tmp_path):
    lot = preparer(tmp_path)
    rapport = historique_article(lot, "5 bis", 1, 0, 1, 0)
    assert rapport["total_versions_meme_numero"] == 2
    assert len(rapport["versions_meme_numero"]) == 1
    assert rapport["decalage_suivant"] == 1
    assert rapport["total_relations_declarees"] == 1
    assert rapport["decalage_relations_suivant"] is None
    suivant = historique_article(lot, "5 bis", 1, 1, 1, 1)
    assert suivant["versions_meme_numero"][0]["id"] == "TEST_C_A"
    assert suivant["relations_declarees"] == suivant["articles_contexte_relations"] == []
    assert suivant["decalage_suivant"] is None
    loin = historique_article(lot, "5 bis", 100, 1_000_000, 100, 1_000_000)
    assert loin["total_versions_meme_numero"] == 2
    assert loin["versions_meme_numero"] == loin["relations_declarees"] == []


@pytest.mark.parametrize("numero", ["5", "05 bis", "5 BIS", " 5 bis", "٥ bis", "INCONNU"])
def test_numero_exact_sans_correction_et_aucune_absence_de_droit(tmp_path, numero):
    rapport = historique_article(preparer(tmp_path), numero)
    assert rapport["numero_article_exact"] == numero
    assert rapport["total_versions_meme_numero"] == rapport["total_relations_declarees"] == 0
    assert rapport["completude_reglementaire"] == "non_etablie"


def test_apercus_bilingues_tronques_sans_modification(tmp_path):
    def changer(brut, meta):
        brut["articles"][0].update(texte_integral="TEST NON OFFICIEL " * 100,
                                   texte_francais=None, texte_arabe="نص غير رسمي " * 100)
    lot = preparer(tmp_path, changer)
    avant = snapshot(lot)
    version = historique_article(lot, "5 bis")["versions_meme_numero"][0]
    assert len(version["apercus"]["texte_integral"]["texte"]) == 512
    assert version["apercus"]["texte_integral"]["tronque"] is True
    assert version["apercus"]["texte_francais"] is None
    assert version["apercus"]["texte_arabe"]["texte"].startswith("نص غير رسمي")
    assert snapshot(lot) == avant


def test_sans_transcription_ne_devient_pas_historique_complet(tmp_path):
    def changer(brut, meta):
        brut.update(articles=[], relations=[])
    rapport = historique_article(preparer(tmp_path, changer), "5 bis")
    assert rapport["total_versions_meme_numero"] == 0
    assert rapport["documents_sans_article_transcrit"] == ["TEST_C", "TEST_M", "TEST_O"]
    assert rapport["completude_reglementaire"] == "non_etablie"


@pytest.mark.parametrize("numero", [None, True, 5, "", " ", "x" * 257, "5\n", "5\x00"])
def test_parametres_article_avant_lecture(tmp_path, numero):
    with pytest.raises(ParamHistoriqueInvalide):
        historique_article(tmp_path / "absent", numero)


@pytest.mark.parametrize("position,valeur", [(0, True), (0, 0), (0, 101), (0, 1.0), (1, -1), (1, 1_000_001),
                                             (2, False), (2, 0), (2, 101), (3, True), (3, -1), (3, 1_000_001)])
def test_bornes_strictes_paginators_avant_lecture(tmp_path, position, valeur):
    args = [20, 0, 20, 0]
    args[position] = valeur
    with pytest.raises(ParamHistoriqueInvalide):
        historique_article(tmp_path / "absent", "5 bis", *args)


def test_lot_corrompu_ou_symbolique_refuse(tmp_path):
    lot = preparer(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(lot, target_is_directory=True)
    with pytest.raises(ValueError):
        historique_article(alias, "5 bis")
    (lot / "lot_code.json").write_text('{}')
    with pytest.raises(ValueError):
        historique_article(lot, "5 bis")


def test_cli_json_et_erreur_sans_ecriture(tmp_path, capsys):
    lot = preparer(tmp_path)
    avant = snapshot(lot)
    assert main(["customs-code-history", str(lot), "--article", "5 bis", "--limit", "1"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["total_versions_meme_numero"] == 2 and len(rep["versions_meme_numero"]) == 1
    assert main(["customs-code-history", str(lot), "--article", "5 bis", "--relations-limit", "0"]) == 2
    assert json.loads(capsys.readouterr().out)["statut"] == "refuse"
    assert snapshot(lot) == avant


def test_cli_processus_reel_isole(tmp_path):
    lot = preparer(tmp_path)
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
               UNOCR_DATA_DIR=str(tmp_path / "data"), UNOCR_LOG_DIR=str(tmp_path / "logs"))
    p = subprocess.run([sys.executable, "-m", "unocr.cli", "customs-code-history", str(lot),
                        "--article", "5 bis", "--relations-offset", "1"], env=env, capture_output=True, text=True, timeout=20)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout)["relations_declarees"] == []


def test_api_historique_epingle_sans_ecriture(revue):
    client, racine, registre, cfg = revue
    avant = snapshot(racine)
    r = client.get(BASE + "/lots/code_a/history", params={"article": "5 bis", "limit": 1}, headers=ADMIN)
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    assert r.json()["resultat"]["total_versions_meme_numero"] == 2
    assert r.json()["resultat"]["archive"]["manifest_sha256"]
    assert str(racine) not in r.text
    assert snapshot(racine) == avant


@pytest.mark.parametrize("headers,code", [({}, 401), ({"Authorization": "Bearer INCONNU"}, 401),
                                          ({"Authorization": "Bearer TEST_LECTEUR_NON_PRODUCTION"}, 403)])
def test_api_historique_habilitation(revue, headers, code):
    client, *_ = revue
    assert client.get(BASE + "/lots/code_a/history?article=5", headers=headers).status_code == code


def test_api_mode_ouvert_refuse(revue, monkeypatch):
    from unocr import api
    from unocr.rbac import RegistreRBAC
    client, *_ = revue
    monkeypatch.setattr(api, "_rbac", RegistreRBAC(actif=False))
    assert client.get(BASE + "/lots/code_a/history?article=5").status_code == 403


@pytest.mark.parametrize("suffixe,code", [('/lots/tarif_a/history?article=5', 422),
                                         ('/lots/inconnu/history?article=5', 404),
                                         ('/lots/code_a/history', 422),
                                         ('/lots/code_a/history?article=%20', 422),
                                         ('/lots/code_a/history?article=5&relations_limit=101', 422),
                                         ('/lots/code_a/history?article=5&offset=-1', 422)])
def test_api_parametres_et_types(revue, suffixe, code):
    client, *_ = revue
    assert client.get(BASE + suffixe, headers=ADMIN).status_code == code


def test_api_epingle_pre_et_post_historique(revue, monkeypatch):
    from unocr.routes import customs_review
    client, racine, registre, cfg = revue
    reel = customs_review.historique_article

    def remplace(*args):
        resultat = reel(*args)
        resultat["archive"]["manifest_sha256"] = "0" * 64
        return resultat
    monkeypatch.setattr(customs_review, "historique_article", remplace)
    r = client.get(BASE + "/lots/code_a/history?article=5", headers=ADMIN)
    assert r.status_code == 409 and "resultat" not in r.json()
    monkeypatch.setattr(customs_review, "historique_article", reel)
    brut = json.loads(registre.read_text())
    for item in brut["lots"]:
        item["manifest_sha256"] = "0" * 64
    registre.write_text(json.dumps(brut))
    assert client.get(BASE + "/lots/code_a/history?article=5", headers=ADMIN).status_code == 409


def test_relations_un_saut_seulement_et_pagination_sur_ensemble(tmp_path):
    def changer(brut, meta):
        from copy import deepcopy
        autre = deepcopy(brut["articles"][1])
        autre.update(id="TEST_M_B", numero_article="99", articles_lies=[])
        autre["hierarchie"][-1]["identifiant"] = "99"
        brut["articles"].append(autre)
        brut["relations"].extend([
            {"id": "TEST_2", "origine_id": "TEST_C_A", "cible_id": "TEST_M_A", "type_relation": "renvoie_a",
             "justification": "RENVOI TEST NON OFFICIEL", "reference": {"source_id": "TEST_C", "localisateur": "page test"}},
            {"id": "TEST_TRANSITIF_EXCLU", "origine_id": "TEST_M_A", "cible_id": "TEST_M_B", "type_relation": "renvoie_a",
             "justification": "RENVOI TEST NON OFFICIEL", "reference": {"source_id": "TEST_M", "localisateur": "page test"}},
        ])
    lot = preparer(tmp_path, changer)
    rep = historique_article(lot, "5 bis", limite=1, limite_relations=1)
    assert rep["total_relations_declarees"] == 2
    assert rep["decalage_relations_suivant"] == 1
    assert rep["relations_declarees"][0]["id"] == "TEST_2"
    # C figure en contexte de relation, même quand hors page des versions.
    assert {a["id"] for a in rep["articles_contexte_relations"]} == {"TEST_C_A", "TEST_M_A"}
    suivant = historique_article(lot, "5 bis", limite_relations=1, decalage_relations=1)
    assert suivant["relations_declarees"][0]["id"] == "TEST_RELATION"
    assert suivant["decalage_relations_suivant"] is None
    assert "TEST_M_B" not in json.dumps(rep)


def test_tri_dates_egales_ne_favorise_pas_une_version_juridique(tmp_path):
    def changer(brut, meta):
        for doc in meta["documents"]:
            doc["document"]["date_publication"] = "2000-01-01"
    rep = historique_article(preparer(tmp_path, changer), "5 bis")
    assert [a["id"] for a in rep["versions_meme_numero"]] == ["TEST_C_A", "TEST_O_A"]
    assert rep["succession_juridique_etablie"] is False
