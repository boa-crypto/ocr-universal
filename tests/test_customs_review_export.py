"""Fixtures NON OFFICIELLES : contrat local, aucune validation réglementaire."""
import hashlib
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from tests import test_customs_review
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.customs_reference.review_export import (
    MAX_EXPORT,
    ExportRefuse,
    ExportRevue,
    analyser_export,
    verifier_export,
)

revue = test_customs_review.revue


def export():
    return {"schema_version": "1", "type_export": "rapport_revue_documentaire_non_valide",
            "lecture_seule": True, "publication_active": False, "validation_juridique": "non_validee",
            "perimetre": "rapport_ou_page_uniquement_pas_corpus_complet",
            "horodatage_client_non_certifie": "2026-11-06T12:30:45.123Z",
            "requete_relative": "/api/v1/customs-review/lots/TEST_NON_OFFICIEL/check",
            "resultat": {"archive": {"manifest_sha256": "a" * 64}, "texte": "NON OFFICIEL عربي 0101000000"}}


def encoder(objet):
    return json.dumps(objet, ensure_ascii=False).encode("utf-8")


def test_structure_seule_empreinte_octets_et_absence_texte():
    contenu = encoder(export())
    constat = analyser_export(contenu)
    assert constat["sha256_fichier"] == hashlib.sha256(contenu).hexdigest()
    assert constat["octets"] == len(contenu)
    assert constat["manifestes_declares"] == ["a" * 64]
    assert constat["authenticite_verifiee"] is False
    assert constat["integrite_archives_verifiee"] is False
    assert constat["audit_serveur_verifie"] is False
    assert "0101000000" not in json.dumps(constat)
    assert "requete_relative" not in constat


def test_diff_deux_provenances_et_pas_de_mutation():
    objet = export()
    objet["requete_relative"] = "/api/v1/customs-review/diff?avant=A&apres=B"
    objet["resultat"] = {"archives": {"avant": {"manifest_sha256": "a" * 64}, "apres": {"manifest_sha256": "b" * 64}}}
    avant = deepcopy(objet)
    assert analyser_export(encoder(objet))["manifestes_declares"] == ["a" * 64, "b" * 64]
    assert objet == avant


@pytest.mark.parametrize("cle,valeur", [
    ("schema_version", 1), ("schema_version", "2"), ("lecture_seule", 1), ("lecture_seule", False),
    ("publication_active", 0), ("publication_active", True), ("validation_juridique", "validee"),
    ("type_export", "officiel"), ("perimetre", "corpus_complet"), ("inconnu", "SECRET_TEST"),
    ("horodatage_client_non_certifie", "2026-02-30T12:30:45.123Z"),
    ("horodatage_client_non_certifie", "2026-11-06T12:30:45Z"),
    ("requete_relative", "https://example.invalid/api/v1/customs-review/diff"),
    ("requete_relative", "/api/v1/customs-review/lots"),
    ("requete_relative", "/api/v1/customs-review/lots/A/check#fragment"),
    ("requete_relative", "/api/v1/customs-review/lots/A/check?q=SECRET_TEST\n"),
    ("requete_relative", "/api/v1/customs-review/diff?avant=A&apres=B"),
    ("requete_relative", "/api/v1/customs-review/lots/A/tariff/١٠١٠١٠١٠١٠"),
    ("resultat", {}), ("resultat", None),
    ("resultat", {"archive": {"manifest_sha256": "INVALIDE_SECRET_TEST"}}),
    ("resultat", {"archive": {"manifest_sha256": "a"*64}, "publication_active": True}),
    ("resultat", {"archive": {"manifest_sha256": "a"*64}, "lecture_seule": 1}),
    ("resultat", {"archive": {"manifest_sha256": "a"*64}, "validation_juridique": "validee"}),
    ("resultat", {"archive": {"manifest_sha256": "a"*64}, "archives": {}}),
])
def test_contrat_refuse_sans_exposer_valeurs(cle, valeur):
    objet = export()
    objet[cle] = valeur
    with pytest.raises(ExportRefuse) as erreur:
        analyser_export(encoder(objet))
    assert "SECRET_TEST" not in str(erreur.value)


@pytest.mark.parametrize("cle", list(export()))
def test_tout_champ_enveloppe_est_requis(cle):
    objet = export()
    del objet[cle]
    with pytest.raises(ExportRefuse):
        analyser_export(encoder(objet))


@pytest.mark.parametrize("contenu", [b"", b"\xff", b"{}{}", b"[]", b"null", b"true", b"{", b'"SECRET_TEST"',
    b'{"a":1,"a":2}', b'{"a":{"b":1,"b":2}}', b'{"n":NaN}', b'{"n":Infinity}',
    b'{"n":-Infinity}', b'{"n":1e999}', b'{"s":"\\ud800"}', b'\xef\xbb\xbf{}',
    b"[" * 1100 + b"0" + b"]" * 1100,
])
def test_json_ambigu_non_fini_ou_invalide(contenu):
    with pytest.raises(ExportRefuse):
        analyser_export(contenu)


def test_profondeur_et_taille_bornees():
    objet = export()
    objet["resultat"]["profond"] = json.loads("[" * 65 + "0" + "]" * 65)
    with pytest.raises(ExportRefuse, match="Profondeur"):
        analyser_export(encoder(objet))
    with pytest.raises(ExportRefuse):
        analyser_export(b" " * (MAX_EXPORT + 1))


def test_lecture_seule_et_types_dangereux(tmp_path):
    fichier = tmp_path / "export.json"
    fichier.write_bytes(encoder(export()))
    avant = fichier.read_bytes()
    assert verifier_export(fichier)["statut"] == "structure_compatible"
    assert fichier.read_bytes() == avant
    lien = tmp_path / "lien"
    lien.symlink_to(fichier)
    for chemin in [lien, tmp_path, tmp_path / "absent"]:
        with pytest.raises(ExportRefuse):
            verifier_export(chemin)
    if hasattr(os, "mkfifo"):
        fifo = tmp_path / "fifo"
        os.mkfifo(fifo)
        with pytest.raises(ExportRefuse):
            verifier_export(fifo)
    trop_grand = tmp_path / "grand"
    with trop_grand.open("wb") as sortie:
        sortie.truncate(MAX_EXPORT + 1)
    with pytest.raises(ExportRefuse):
        verifier_export(trop_grand)
    assert fichier.read_bytes() == avant


def test_schema_versionne_correspond_au_modele():
    chemin = Path(__file__).resolve().parents[1] / "docs/customs/schemas/ExportRevue.schema.json"
    schema = json.loads(chemin.read_text())
    schema.pop("$schema")
    schema.pop("description")
    assert schema == ExportRevue.model_json_schema()


def test_cli_succes_refus_et_aucun_magasin_cree(tmp_path):
    fichier = tmp_path / "export.json"
    fichier.write_bytes(encoder(export()))
    env = {**os.environ, "UNOCR_DATA_DIR": str(tmp_path / "data_inexistant"),
           "UNOCR_LOG_DIR": str(tmp_path / "logs_inexistants"), "PYTHONPATH": "src"}
    for entree, code in [(fichier, 0), (tmp_path / "absent", 2)]:
        p = subprocess.run([sys.executable, "-m", "unocr.cli", "customs-review-export-check", str(entree)],
                           env=env, capture_output=True, text=True, timeout=10)
        assert p.returncode == code, p.stderr
        resultat = json.loads(p.stdout)
        assert resultat["lecture_seule"] is True
        assert resultat["publication_active"] is False
        assert not p.stderr
    assert not (tmp_path / "data_inexistant").exists()
    assert not (tmp_path / "logs_inexistants").exists()


@pytest.mark.parametrize("route", [
    "/lots/tarif_a/check", "/lots/code_a/check",
    "/lots/tarif_a/search?q=010100", "/lots/code_a/search?article=5%20bis",
    "/lots/code_a/history?article=5%20bis", "/lots/tarif_a/tariff/0101000000",
    "/lots/tarif_a/coverage", "/lots/code_a/coverage", "/lots/tarif_a/tree?level=sections",
    "/lots/code_a/article?article_id=V1&field=texte_integral&limit=4&offset=0",
    "/diff?avant=tarif_a&apres=tarif_b", "/diff?avant=code_a&apres=code_a",
])
def test_tous_rapports_api_reels_acceptes_sans_ecrire_corpus(revue, route):
    client, racine, registre, cfg = revue
    avant = snapshot(racine)
    reponse = client.get(BASE + route, headers=ADMIN)
    assert reponse.status_code == 200, reponse.text
    objet = export()
    objet["requete_relative"] = BASE + route
    objet["resultat"] = reponse.json()["resultat"]
    assert analyser_export(encoder(objet))["statut"] == "structure_compatible"
    assert snapshot(racine) == avant
