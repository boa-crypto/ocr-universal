"""Rejeu/diff de fixtures NON OFFICIELLES ; aucune conclusion réglementaire."""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_customs_legal import fichiers_code
from tests.test_customs_reference import fichiers, snapshot
from unocr.cli import main
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.legal_comparison import charger_lot_code, comparer_lots_code
from unocr.customs_reference.legal_importer import preparer_code


def lots_code(tmp_path, changer=None):
    lots = []
    for nom in ("avant", "apres"):
        entree = tmp_path / ("recu_" + nom)
        entree.mkdir()
        transcription, metadata = fichiers_code(entree)
        brut, meta = json.loads(transcription.read_text()), json.loads(metadata.read_text())
        if changer:
            changer(nom, brut, meta, entree)
        transcription.write_text(json.dumps(brut, ensure_ascii=False))
        metadata.write_text(json.dumps(meta, ensure_ascii=False))
        sortie = tmp_path / ("lot_" + nom)
        preparer_code(transcription, metadata, sortie)
        lots.append(sortie)
    return lots


def rehasher(lot, fichier):
    path = lot / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["fichiers_sha256"][fichier] = hashlib.sha256((lot / fichier).read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))


def remplacer_json(lot, fichier, changer):
    path = lot / fichier
    brut = json.loads(path.read_text())
    changer(brut)
    path.write_text(json.dumps(brut))
    rehasher(lot, fichier)


def test_identiques_check_diff_lecture_seule(tmp_path):
    a, b = lots_code(tmp_path)
    avant = snapshot(tmp_path)
    lot, controle = charger_lot_code(a)
    assert len(lot.articles) == 3
    assert controle["integrite_locale"] == "coherente_au_rejeu"
    assert controle["lecture_seule"] is True and controle["ecrit"] is False
    assert controle["transcription_verification"] == "non_verifiee"
    assert controle["publication_active"] is False
    assert controle["validation_humaine_requise"] is True
    assert controle["archive"]["date_importation"].endswith("+00:00")
    assert controle["archive"]["transcription_nom_recu"] == "transcription_NON_OFFICIELLE.json"
    rapport = comparer_lots_code(a, b)
    for categorie in ("articles", "relations", "documents"):
        assert rapport[categorie] == {"ajoutes": [], "retires": [], "modifies": []}
    assert rapport["provenances_modifiees"] == {"articles": [], "relations": []}
    assert rapport["validation_juridique"] == "non_validee"
    assert rapport["restitution_juridique_a_date"] is False
    assert rapport["completude_reglementaire"] == "non_etablie"
    assert snapshot(tmp_path) == avant


def test_lot_portable_sans_originaux_ni_resolution_du_sidecar(tmp_path):
    a, b = lots_code(tmp_path)
    shutil.rmtree(tmp_path / "recu_avant")
    shutil.rmtree(tmp_path / "recu_apres")
    deplace = tmp_path / "autre_emplacement"
    shutil.copytree(a, deplace)
    avant = snapshot(tmp_path)
    assert charger_lot_code(deplace)[1]["documents_recus"] == 3
    assert comparer_lots_code(deplace, b)["articles"]["modifies"] == []
    assert snapshot(tmp_path) == avant


def test_textes_langues_dates_hierarchie_historiques_declares(tmp_path):
    def changer(nom, brut, meta, entree):
        if nom == "apres":
            article = brut["articles"][0]
            article.update(texte_integral="  AUTRE FIXTURE NON OFFICIELLE\n", texte_arabe="نص اختباري آخر",
                           date_entree_vigueur="2000-02-01", statut_juridique_declare="modifie",
                           historique_modifications=[{"source_id": "TEST_M", "localisateur": "FIXTURE page 1"}])
            article["hierarchie"].insert(1, {"niveau": "chapitre", "identifiant": "TEST_CHAPITRE"})
    rapport = comparer_lots_code(*lots_code(tmp_path, changer))
    modification = rapport["articles"]["modifies"][0]
    assert modification["identifiant"] == "TEST_O_A"
    assert set(modification["changements"]) == {"texte_integral", "texte_arabe", "date_entree_vigueur", "statut_juridique_declare", "historique_modifications", "hierarchie"}
    assert modification["changements"]["texte_integral"]["apres"].endswith("\n")
    assert rapport["publication_active"] is False


def test_ajout_retrait_articles_et_perimetres_sans_abrogation(tmp_path):
    def changer(nom, brut, meta, entree):
        if nom == "apres":
            brut["articles"] = [a for a in brut["articles"] if a["id"] != "TEST_C_A"]
            article = copy.deepcopy(brut["articles"][0])
            article.update(id="TEST_O_B", numero_article="6")
            article["hierarchie"][-1]["identifiant"] = "6"
            brut["articles"].append(article)
    rapport = comparer_lots_code(*lots_code(tmp_path, changer))
    assert rapport["articles"]["ajoutes"] == ["TEST_O_B"]
    assert rapport["articles"]["retires"] == ["TEST_C_A"]
    assert rapport["details_ajouts_retraits"]["articles"]["ajoutes"][0]["reference"]["source_id"] == "TEST_O"
    assert rapport["details_ajouts_retraits"]["articles"]["retires"][0]["nature_version"] == "consolidee_provisoire"
    assert any("Périmètres" in message for message in rapport["avertissements"])
    assert any("aucune abrogation" in message for message in rapport["avertissements"])


def test_id_renomme_pas_d_appariement_par_numero(tmp_path):
    def changer(nom, brut, meta, entree):
        if nom == "apres":
            brut["articles"][2]["id"] = "TEST_C_AUTRE_ID"
    rapport = comparer_lots_code(*lots_code(tmp_path, changer))
    assert rapport["articles"]["ajoutes"] == ["TEST_C_AUTRE_ID"]
    assert rapport["articles"]["retires"] == ["TEST_C_A"]
    assert rapport["articles"]["modifies"] == []


def test_identite_conservee_avec_numero_ou_version_change_a_revoir(tmp_path):
    def changer(nom, brut, meta, entree):
        if nom == "apres":
            article = brut["articles"][2]
            article.update(numero_article="6", version_juridique="TEST_C_V2")
            article["hierarchie"][-1]["identifiant"] = "6"
    rapport = comparer_lots_code(*lots_code(tmp_path, changer))
    assert rapport["identites_articles_a_revoir"] == ["TEST_C_A"]
    assert any("revoir l'identité" in message for message in rapport["avertissements"])


def test_provenance_separee_texte_inchange(tmp_path):
    def changer(nom, brut, meta, entree):
        if nom == "apres":
            brut["articles"][0]["reference"]["localisateur"] = "FIXTURE autre localisateur"
            brut["relations"][0]["reference"]["localisateur"] = "FIXTURE preuve déplacée"
    rapport = comparer_lots_code(*lots_code(tmp_path, changer))
    assert rapport["articles"]["modifies"] == rapport["relations"]["modifies"] == []
    assert rapport["provenances_modifiees"]["articles"][0]["identifiant"] == "TEST_O_A"
    assert rapport["provenances_modifiees"]["relations"][0]["identifiant"] == "TEST_RELATION"


def test_relations_declares_modifiees_ajoutees_retirees(tmp_path):
    def changer(nom, brut, meta, entree):
        if nom == "avant":
            retour = copy.deepcopy(brut["relations"][0])
            retour.update(id="TEST_RENVOI", type_relation="renvoie_a", origine_id="TEST_C_A", reference=brut["articles"][2]["reference"])
            brut["relations"].append(retour)
        else:
            brut["relations"][0].update(type_relation="rectifie", justification="AUTRE PREUVE NON OFFICIELLE")
            retour = copy.deepcopy(brut["relations"][0])
            retour.update(id="TEST_AUTRE_RENVOI", type_relation="renvoie_a", origine_id="TEST_C_A", reference=brut["articles"][2]["reference"])
            brut["relations"].append(retour)
    rapport = comparer_lots_code(*lots_code(tmp_path, changer))
    assert rapport["relations"]["retires"] == ["TEST_RENVOI"]
    assert rapport["relations"]["ajoutes"] == ["TEST_AUTRE_RENVOI"]
    assert set(rapport["relations"]["modifies"][0]["changements"]) == {"type_relation", "justification"}
    assert rapport["details_ajouts_retraits"]["relations"]["ajoutes"][0]["reference"]["source_id"] == "TEST_C"


def test_documents_ajoutes_retires_et_metadonnees_modifiees(tmp_path):
    def changer(nom, brut, meta, entree):
        if nom == "apres":
            meta["documents"][0]["document"]["titre"] = "AUTRE TITRE NON OFFICIEL"
            meta["documents"][2]["document"]["id"] = "TEST_C_NOUVEAU"
            brut["articles"][2]["reference"]["source_id"] = "TEST_C_NOUVEAU"
    rapport = comparer_lots_code(*lots_code(tmp_path, changer))
    assert rapport["documents"]["ajoutes"] == ["TEST_C_NOUVEAU"]
    assert rapport["documents"]["retires"] == ["TEST_C"]
    assert rapport["documents"]["modifies"][0]["changements"]["titre"]["apres"] == "AUTRE TITRE NON OFFICIEL"


def test_coherence_ne_prouve_pas_authenticite_et_version_ambigue(tmp_path):
    def changer(nom, brut, meta, entree):
        if nom == "apres":
            doc = meta["documents"][0]
            pdf = entree / doc["fichier_recu"]
            pdf.write_bytes(pdf.read_bytes() + b"AUTRE CONTENU NON OFFICIEL")
            doc["document"]["sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    a, b = lots_code(tmp_path, changer)
    assert charger_lot_code(a)[1]["integrite_locale"] == charger_lot_code(b)[1]["integrite_locale"]
    rapport = comparer_lots_code(a, b)
    assert rapport["versions_documentaires_ambigues"] == ["TEST_O"]
    assert rapport["articles"]["modifies"] == []
    assert rapport["transcription_verification"] == "non_verifiee"
    assert any("WORM" in message for message in rapport["avertissements"])


def test_archive_sans_articles_acceptable_sans_restitution_a_date(tmp_path):
    def changer(nom, brut, meta, entree):
        brut.update(articles=[], relations=[])
    a, b = lots_code(tmp_path, changer)
    assert charger_lot_code(a)[1]["articles_declares"] == 0
    assert comparer_lots_code(a, b)["restitution_juridique_a_date"] is False


@pytest.mark.parametrize("fichier", ["transcription_recue.json", "metadata_original.json", "lot_code.json", "rapport.json", "document_0001.pdf"])
def test_alteration_empreinte_refus_sans_resultat_partiel(tmp_path, fichier):
    a, b = lots_code(tmp_path)
    cible = b / fichier
    cible.write_bytes(cible.read_bytes() + b" ")
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError, match="Empreinte Code différente"):
        comparer_lots_code(a, b)
    assert snapshot(tmp_path) == avant


def test_lot_rehashe_non_reproductible(tmp_path):
    a, b = lots_code(tmp_path)
    remplacer_json(b, "lot_code.json", lambda brut: brut["articles"][0].update(texte_integral="ALTERATION NON PRESENTE DANS LA TRANSCRIPTION"))
    with pytest.raises(ValueError, match="non reproductible"):
        comparer_lots_code(a, b)


@pytest.mark.parametrize("champ,valeur", [("documents_recus", True), ("articles_declares", 3.0), ("publication_active", 0),
                                         ("ecrit", 1), ("articles_par_nature", {"originale": True, "modificative": 1, "consolidee_provisoire": 1}), ("archives", []), ("transcription_verification", "verifiee"), ("inconnu", True)])
def test_rapport_rehashe_types_et_champs_incoherents(tmp_path, champ, valeur):
    a, b = lots_code(tmp_path)
    remplacer_json(b, "rapport.json", lambda brut: brut.update({champ: valeur}))
    with pytest.raises(ValueError, match="Rapport Code incohérent"):
        comparer_lots_code(a, b)


@pytest.mark.parametrize("champ,valeur", [("publication_active", True), ("publication_active", 0), ("statut", "actif"),
                                         ("validation_juridique", "validee"), ("type_lot", "tarif"),
                                         ("date_importation", None), ("date_importation", "2026-11-06T12:00:00"),
                                         ("transcription_nom_recu", ""), ("champ_inconnu", False)])
def test_manifest_refuse_et_types_stricts(tmp_path, champ, valeur):
    a, b = lots_code(tmp_path)
    path = b / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest[champ] = valeur
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        comparer_lots_code(a, b)


@pytest.mark.parametrize("defaut", ["manifest_absent", "pdf_absent", "extra", "repertoire", "symlink_lot", "symlink_manifest", "symlink_pdf", "traversal", "indice", "hash_invalide", "trop_fichiers"])
def test_archives_manquantes_ou_non_sures(tmp_path, defaut):
    a, b = lots_code(tmp_path)
    if defaut == "manifest_absent":
        (b / "manifest.json").unlink()
    elif defaut == "pdf_absent":
        (b / "document_0001.pdf").unlink()
    elif defaut == "extra":
        (b / "inattendu").write_text("NON OFFICIEL")
    elif defaut == "repertoire":
        (b / "document_0001.pdf").unlink()
        (b / "document_0001.pdf").mkdir()
    elif defaut == "symlink_lot":
        lien = tmp_path / "lien_lot"
        lien.symlink_to(b, target_is_directory=True)
        b = lien
    elif defaut in {"symlink_manifest", "symlink_pdf"}:
        nom = "manifest.json" if defaut == "symlink_manifest" else "document_0001.pdf"
        (b / nom).unlink()
        (b / nom).symlink_to(a / nom)
    elif defaut == "trop_fichiers":
        for i in range(70):
            (b / f"inattendu_{i}").write_text("")
    else:
        path = b / "manifest.json"
        manifest = json.loads(path.read_text())
        if defaut == "traversal":
            manifest["fichiers_sha256"]["../exterieur"] = "a" * 64
        elif defaut == "indice":
            manifest["fichiers_sha256"]["document_0000.pdf"] = manifest["fichiers_sha256"].pop("document_0001.pdf")
        else:
            manifest["fichiers_sha256"]["document_0001.pdf"] = "x" * 64
        path.write_text(json.dumps(manifest))
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError):
        comparer_lots_code(a, b)
    assert snapshot(tmp_path) == avant


def test_correspondances_manifest_et_noms_recus_verifies(tmp_path):
    a, b = lots_code(tmp_path)
    path = b / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["documents"][0]["nom_recu"] = "FAUX_NOM.pdf"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Correspondances"):
        comparer_lots_code(a, b)


def test_metadonnees_rehashees_ne_changent_pas_le_lot_silencieusement(tmp_path):
    a, b = lots_code(tmp_path)
    remplacer_json(b, "metadata_original.json", lambda brut: brut["documents"][0]["document"].update(version_source="TEST_AUTRE_VERSION"))
    with pytest.raises(ValueError, match="non reproductible"):
        comparer_lots_code(a, b)


def test_pas_de_resolution_fichier_recu_hors_archive(tmp_path):
    a, b = lots_code(tmp_path)
    remplacer_json(b, "metadata_original.json", lambda brut: brut["documents"][0].update(fichier_recu="../exterieur.pdf"))
    with pytest.raises(ValueError, match="Nom local simple"):
        comparer_lots_code(a, b)
    assert not (tmp_path / "exterieur.pdf").exists()


def test_nombre_archives_et_metadonnees_doivent_correspondre(tmp_path):
    a, b = lots_code(tmp_path)
    # Retirer un PDF du manifeste et du dossier ne doit pas rendre le lot complet.
    path = b / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["fichiers_sha256"].pop("document_0003.pdf")
    path.write_text(json.dumps(manifest))
    (b / "document_0003.pdf").unlink()
    with pytest.raises(ValueError, match="Document archivé absent"):
        comparer_lots_code(a, b)


def test_borne_taille_globale_archive(tmp_path, monkeypatch):
    from unocr.customs_reference import legal_comparison
    a, b = lots_code(tmp_path)
    monkeypatch.setattr(legal_comparison, "MAX_ARCHIVE", 1)
    with pytest.raises(ValueError, match="volumineuse"):
        comparer_lots_code(a, b)


@pytest.mark.parametrize("fichier", ["lot_code.json", "metadata_original.json", "transcription_recue.json", "rapport.json", "manifest.json"])
def test_json_duplique_refuse_meme_rehashe(tmp_path, fichier):
    a, b = lots_code(tmp_path)
    (b / fichier).write_text('{"articles": [], "articles": [], "relations": []}')
    if fichier != "manifest.json":
        rehasher(b, fichier)
    with pytest.raises(ValueError, match="dupliquée"):
        comparer_lots_code(a, b)


def test_lot_tarifaire_refuse_par_lecteur_code(tmp_path):
    source, metadata = fichiers(tmp_path)
    sortie = tmp_path / "tarif"
    preparer_tarif(source, metadata, sortie)
    with pytest.raises(ValueError, match="Manifeste Code"):
        charger_lot_code(sortie)


def test_cli_check_diff_et_refus_sans_ecriture(tmp_path, capsys):
    a, b = lots_code(tmp_path)
    avant = snapshot(tmp_path)
    assert main(["customs-code-check", str(a)]) == 0
    assert json.loads(capsys.readouterr().out)["integrite_locale"] == "coherente_au_rejeu"
    assert main(["customs-code-diff", str(a), str(b)]) == 0
    assert json.loads(capsys.readouterr().out)["lecture_seule"] is True
    assert main(["customs-code-diff", str(a), str(tmp_path / "absent")]) == 2
    refuse = json.loads(capsys.readouterr().out)
    assert refuse["statut"] == "refuse" and "articles" not in refuse
    assert main(["customs-code-check", str(tmp_path / "absent")]) == 2
    assert json.loads(capsys.readouterr().out)["publication_active"] is False
    assert snapshot(tmp_path) == avant


def test_cli_processus_independant_ne_cree_pas_de_stores(tmp_path):
    a, b = lots_code(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
           "PYTHONDONTWRITEBYTECODE": "1", "UNOCR_DATA_DIR": str(tmp_path / "stores_absents"),
           "UNOCR_LOG_DIR": str(tmp_path / "logs_absents")}
    avant = snapshot(tmp_path)
    for args, code in ((["customs-code-check", str(a)], 0), (["customs-code-diff", str(a), str(b)], 0),
                       (["customs-code-check", str(tmp_path / "absent")], 2)):
        resultat = subprocess.run([sys.executable, "-m", "unocr.cli", *args], env=env, cwd=tmp_path,
                                  capture_output=True, text=True, timeout=30)
        assert resultat.returncode == code, resultat.stderr
        assert json.loads(resultat.stdout)["publication_active"] is False
        assert snapshot(tmp_path) == avant


def test_archive_documentaire_supplementaire_non_ignoree(tmp_path):
    a, b = lots_code(tmp_path)
    remplacer_json(b, "metadata_original.json", lambda brut: brut["documents"].pop())
    remplacer_json(b, "transcription_recue.json", lambda brut: brut.update(articles=brut["articles"][:2]))
    with pytest.raises(ValueError, match="Archives documentaires et métadonnées incohérentes"):
        comparer_lots_code(a, b)


@pytest.mark.parametrize("nombre", [1, 64])
def test_bornes_admises_du_nombre_de_documents(tmp_path, nombre):
    def changer(nom, brut, meta, entree):
        modele = copy.deepcopy(meta["documents"][0])
        contenu = (entree / modele["fichier_recu"]).read_bytes()
        meta["documents"] = []
        for i in range(nombre):
            doc = copy.deepcopy(modele)
            doc["document"]["id"] = f"TEST_DOC_{i}"
            doc["fichier_recu"] = f"FIXTURE_NON_OFFICIELLE_{i}.pdf"
            (entree / doc["fichier_recu"]).write_bytes(contenu)
            meta["documents"].append(doc)
        brut.update(articles=[], relations=[])
    a, b = lots_code(tmp_path, changer)
    assert charger_lot_code(a)[1]["documents_recus"] == nombre
    assert comparer_lots_code(a, b)["documents"]["modifies"] == []
