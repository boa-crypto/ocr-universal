"""Écarts de transcriptions NON OFFICIELLES, sans succession juridique déduite."""
import json

import pytest

from tests import test_customs_review
from tests.test_customs_legal import fichiers_code
from tests.test_customs_reference import snapshot
from unocr.cli import main
from unocr.customs_reference.article_diff import ParamDiffArticleInvalide, comparer_versions_article
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.review_export import analyser_export
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue
ADMIN, BASE = test_customs_review.ADMIN, test_customs_review.BASE


def lot_textes(root, a, b):
    transcription, metadata = fichiers_code(root)
    donnees = json.loads(transcription.read_text())
    donnees["articles"][0]["texte_integral"] = a
    donnees["articles"][1]["texte_integral"] = b
    transcription.write_text(json.dumps(donnees))
    lot = root / "lot"
    preparer_code(transcription, metadata, lot)
    return lot


@pytest.mark.parametrize("a,b,prefixe,suffixe,ma,mb", [
    ("avant X fin", "avant Y fin", 6, 4, "X", "Y"),
    ("abc", "abc", 3, 0, "", ""), ("abc", "abcd", 3, 0, "", "d"),
    ("abcd", "abc", 3, 0, "d", ""), ("Xabc", "Yabc", 0, 3, "X", "Y"),
    ("abc", "XYZ", 0, 0, "abc", "XYZ"), ("أ😀éX", "أ😀éY", 4, 0, "X", "Y"),
    ("A\r\nB", "A\nB", 1, 2, "\r", ""), ("é", "é", 0, 0, "é", "é"),
])
def test_ecart_exact_unicode_sans_normalisation(tmp_path, a, b, prefixe, suffixe, ma, mb):
    lot = lot_textes(tmp_path, a, b)
    avant = snapshot(lot)
    rep = comparer_versions_article(lot, "TEST_O_A", "TEST_M_A")
    assert rep["prefixe_commun_caracteres"] == prefixe
    assert rep["suffixe_commun_caracteres"] == suffixe
    assert rep["avant"]["fragment_bloc_different"] == ma
    assert rep["apres"]["fragment_bloc_different"] == mb
    assert rep["textes_identiques"] == (a == b)
    assert rep["relation_juridique_etablie"] is False
    assert len(rep["relations_directes_declarees"]) == 1
    assert snapshot(lot) == avant


def test_pagination_independante_et_sans_repli(tmp_path):
    lot = lot_textes(tmp_path, "ABCDEF", "uvwxyz")
    rep = comparer_versions_article(lot, "TEST_O_A", "TEST_M_A", limite=2, decalage_avant=1, decalage_apres=3)
    assert rep["avant"]["fragment_bloc_different"] == "BC"
    assert rep["apres"]["fragment_bloc_different"] == "xy"
    assert rep["avant"]["decalage_suivant"] == 3 and rep["apres"]["decalage_suivant"] == 5
    absent = comparer_versions_article(lot, "TEST_O_A", "TEST_M_A", "texte_francais")
    assert absent["champs_comparables"] is False and absent["textes_identiques"] is None
    assert absent["avant"]["fragment_bloc_different"] is None
    assert comparer_versions_article(lot, "TEST_O_A", "INCONNU")["apres"]["article_trouve"] is False
    assert comparer_versions_article(lot, "TEST_O_A", "TEST_M_A", decalage_avant=99)["avant"]["fragment_bloc_different"] == ""


@pytest.mark.parametrize("kwargs", [{"avant_id":""}, {"apres_id":"X\n"}, {"avant_id":"x"*257},
    {"champ":"INVALIDE"}, {"limite": True}, {"limite":0}, {"limite":16001},
    {"decalage_avant": -1}, {"decalage_apres": True}, {"decalage_apres":67108865}])
def test_parametres_avant_lecture(tmp_path, kwargs):
    valeurs = {"avant_id":"A", "apres_id":"B", **kwargs}
    with pytest.raises(ParamDiffArticleInvalide):
        comparer_versions_article(tmp_path / "absent", **valeurs)


def test_cli_sans_ecriture(tmp_path, capsys):
    lot = lot_textes(tmp_path, "NON OFFICIEL A", "NON OFFICIEL B")
    avant = snapshot(lot)
    assert main(["customs-code-article-diff", str(lot), "--before-id", "TEST_O_A", "--after-id", "TEST_M_A"]) == 0
    assert json.loads(capsys.readouterr().out)["publication_active"] is False
    assert snapshot(lot) == avant


def test_api_audit_epingle_export_et_panne(revue, monkeypatch):
    from unocr import api
    client, racine, registre, cfg = revue
    chemin = BASE + "/lots/code_a/article-diff?avant_id=TEST_O_A&apres_id=TEST_M_A"
    avant = snapshot(racine)
    r = client.get(chemin, headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert r.json()["resultat"]["relation_juridique_etablie"] is False
    corps = {"schema_version":"1", "type_export":"rapport_revue_documentaire_non_valide",
             "lecture_seule":True, "publication_active":False, "validation_juridique":"non_validee",
             "perimetre":"rapport_ou_page_uniquement_pas_corpus_complet", "horodatage_client_non_certifie":"2026-11-06T12:30:45.123Z",
             "requete_relative":chemin, "resultat":r.json()["resultat"]}
    assert analyser_export(json.dumps(corps).encode())["statut"] == "structure_compatible"
    events = [json.loads(ligne) for ligne in (cfg.log_dir / "audit.log").read_text().splitlines()]
    succes = [e for e in events if e["event"] == "revue_douaniere" and e["operation"] == "diff_articles"][-1]
    assert succes["manifestes"].keys() == {"code_a"}
    assert "TEST_O_A" not in json.dumps(succes)
    def panne(*a, **kw):
        raise AuditIndisponible("SECRET_TEST")
    monkeypatch.setattr(api, "audit_obligatoire", panne)
    refuse = client.get(chemin, headers=ADMIN)
    assert refuse.status_code == 503 and "resultat" not in refuse.json()
    assert snapshot(racine) == avant


@pytest.mark.parametrize("route,headers,statut", [
    ("/lots/code_a/article-diff?avant_id=A&apres_id=B", {}, 401),
    ("/lots/tarif_a/article-diff?avant_id=A&apres_id=B", ADMIN, 422),
    ("/lots/code_a/article-diff?avant_id=A&apres_id=B&field=INVALIDE", ADMIN, 422),
])
def test_refus_api(revue, route, headers, statut):
    client, racine, registre, cfg = revue
    assert client.get(BASE + route, headers=headers).status_code == statut
