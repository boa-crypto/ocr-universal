"""Recherche dans des fixtures NON OFFICIELLES uniquement, sans classement IA."""
import copy
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_customs_legal import fichiers_code
from tests.test_customs_reference import fichiers, snapshot
from unocr.cli import main
from unocr.customs_reference.importer import preparer_tarif
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.search import rechercher_code, rechercher_tarif


def lot_tarif(tmp_path):
    source, metadata = fichiers(tmp_path)
    base = json.loads(source.read_text())[0]
    lignes = []
    for i, fr, ar in ((0, "Équipement mécanique NON OFFICIEL", "مُعَـدَّات اختبار غير رسمية"),
                      (1, "Autre désignation NON OFFICIELLE", None),
                      (2, "Équipement de contrôle NON OFFICIEL", None),
                      (3, "Pompe technique NON OFFICIELLE", None),
                      (4, None, "مضخة تجريبية غير رسمية")):
        ligne = copy.deepcopy(base)
        ligne.update(id=f"TEST_{i}", code_tarifaire_10="010100000" + str(i),
                     designation_officielle_fr=fr, designation_officielle_ar=ar)
        lignes.append(ligne)
    source.write_text(json.dumps(lignes, ensure_ascii=False))
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    meta["lot"]["mesures"] = [{"id": "TEST_M_EXCLUE", "type_mesure": "restriction", "description": "TERME_MESURE_EXCLU",
                               "code_tarifaire_10": "0101000000", "reference": base["reference"]}]
    metadata.write_text(json.dumps(meta))
    sortie = tmp_path / "tarif"
    preparer_tarif(source, metadata, sortie)
    return sortie


def lot_code(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    brut = json.loads(transcription.read_text())
    brut["articles"][0].update(texte_integral="ÉQUIPEMENT À CONTRÔLER — FIXTURE NON OFFICIELLE",
                               texte_francais="  Équipement à contrôler\nNON OFFICIEL  ",
                               texte_arabe="مُعَـدَّات اختبار غير رسمية", intitule="Contrôle documentaire NON OFFICIEL",
                               notes_explicatives_non_officielles=["TERME_NOTE_EXCLUE"], statut_juridique_declare="abroge")
    brut["articles"][1]["texte_integral"] = "DISPOSITION MODIFICATIVE NON OFFICIELLE"
    brut["articles"][2]["texte_integral"] = "COMPILATION PROVISOIRE NON OFFICIELLE"
    transcription.write_text(json.dumps(brut, ensure_ascii=False))
    sortie = tmp_path / "code"
    preparer_code(transcription, metadata, sortie)
    return sortie


def test_tarif_fr_accents_casse_sous_chaines_et_preuves(tmp_path):
    lot = lot_tarif(tmp_path)
    avant = snapshot(tmp_path)
    rapport = rechercher_tarif(lot, "EQUIPEMENT mecani")
    assert rapport["total_correspondances"] == 1
    ligne = rapport["resultats"][0]["ligne"]
    assert ligne["designation_officielle_fr"] == "Équipement mécanique NON OFFICIEL"
    assert ligne["code_tarifaire_10"] == "0101000000"
    assert rapport["resultats"][0]["champs_correspondants"]["mecani"] == ["designation_officielle_fr"]
    assert rapport["classement_douanier_valide"] is False
    assert rapport["publication_active"] is False
    assert rapport["completude_reglementaire"] == "non_etablie"
    assert rapport["source_declaree"]["verification"] == "non_verifiee"
    assert rapport["archive"]["manifest_sha256"]
    assert snapshot(tmp_path) == avant


def test_arabe_diacritiques_tatweel_et_multilingue_sans_recriture(tmp_path):
    lot = lot_tarif(tmp_path)
    rapport = rechercher_tarif(lot, "معدات MECANIQUE")
    assert rapport["total_correspondances"] == 1
    assert rapport["resultats"][0]["ligne"]["designation_officielle_ar"] == "مُعَـدَّات اختبار غير رسمية"
    assert rapport["resultats"][0]["champs_correspondants"]["معدات"] == ["designation_officielle_ar"]
    assert rechercher_tarif(lot, "مضخة")["resultats"][0]["ligne"]["designation_officielle_fr"] is None


@pytest.mark.parametrize("requete,total", [("0", 5), ("01", 5), ("0101", 5), ("010100", 5), ("01010000", 5),
                                          ("0101000000", 1), ("101", 0)])
def test_prefixes_codes_ascii_sans_zfill(tmp_path, requete, total):
    rapport = rechercher_tarif(lot_tarif(tmp_path), requete)
    assert rapport["mode"] == "prefixe_code_ascii"
    assert rapport["total_correspondances"] == total
    assert all(len(r["ligne"]["code_tarifaire_10"]) == 10 for r in rapport["resultats"])


@pytest.mark.parametrize("requete", ["０１０１００", "٠١٠١٠٠", "01010000000"])
def test_codes_numeriques_non_ascii_ou_trop_longs_refuses(tmp_path, requete):
    with pytest.raises(ValueError, match="ASCII"):
        rechercher_tarif(lot_tarif(tmp_path), requete)


def test_pagination_totaux_et_tri_deterministe(tmp_path):
    lot = lot_tarif(tmp_path)
    premier = rechercher_tarif(lot, "010100", limite=2)
    second = rechercher_tarif(lot, "010100", limite=2, decalage=2)
    dernier = rechercher_tarif(lot, "010100", limite=2, decalage=4)
    assert premier["total_correspondances"] == second["total_correspondances"] == dernier["total_correspondances"] == 5
    assert [r["ligne"]["code_tarifaire_10"] for r in premier["resultats"]] == ["0101000000", "0101000001"]
    assert premier["decalage_suivant"] == 2
    assert second["decalage_suivant"] == 4
    assert dernier["decalage_suivant"] is None
    assert rechercher_tarif(lot, "010100", decalage=100)["resultats"] == []


def test_pas_de_synonymes_taux_ou_parent_inventes(tmp_path):
    lot = lot_tarif(tmp_path)
    assert rechercher_tarif(lot, "TERME_MESURE_EXCLU")["resultats"] == []
    assert rechercher_tarif(lot, "machine")["resultats"] == []
    assert rechercher_tarif(lot, "Équipement absent")["resultats"] == []
    assert rechercher_tarif(lot, "Équipement ÉQUIPEMENT")["termes_normalises"] == ["equipement"]


def test_code_fr_ar_titre_non_normalises_et_filtres(tmp_path):
    lot = lot_code(tmp_path)
    avant = snapshot(tmp_path)
    rapport = rechercher_code(lot, "EQUIPEMENT معدات")
    assert rapport["total_correspondances"] == 1
    article = rapport["resultats"][0]
    assert article["id"] == "TEST_O_A"
    assert article["statut_juridique_declare"] == "abroge"
    assert article["apercus"]["texte_francais"]["texte"] == "  Équipement à contrôler\nNON OFFICIEL  "
    assert article["apercus"]["texte_arabe"]["texte"] == "مُعَـدَّات اختبار غير رسمية"
    assert article["reference"]["source_id"] == "TEST_O"
    assert article["validation_juridique"] == "non_validee"
    assert rapport["restitution_juridique_a_date"] is False
    assert rapport["transcription_verification"] == "non_verifiee"
    assert rechercher_code(lot, "CONTROLE")["total_correspondances"] == 1
    assert rechercher_code(lot, "TERME_NOTE_EXCLUE")["total_correspondances"] == 0
    assert snapshot(tmp_path) == avant


def test_numero_exact_sans_fusion_des_versions_ou_choix_applicable(tmp_path):
    lot = lot_code(tmp_path)
    rapport = rechercher_code(lot, numero_article="5 bis", limite=1)
    assert rapport["total_correspondances"] == 2
    assert rapport["decalage_suivant"] == 1
    assert rapport["resultats"][0]["nature_version"] == "consolidee_provisoire"
    autre = rechercher_code(lot, numero_article="5 bis", decalage=1)
    assert autre["resultats"][0]["nature_version"] == "originale"
    assert rechercher_code(lot, numero_article="5 BIS")["total_correspondances"] == 0
    assert rechercher_code(lot, numero_article="5")["total_correspondances"] == 0
    assert rechercher_code(lot, numero_article="7")["resultats"][0]["id"] == "TEST_M_A"
    assert rechercher_code(lot, source_id="TEST_M")["total_correspondances"] == 1
    assert rechercher_code(lot, nature="originale", source_id="TEST_M")["total_correspondances"] == 0
    assert rechercher_code(lot, nature="modificative")["resultats"][0]["numero_article"] == "7"


def test_apercu_borne_initial_non_centre_et_champs_correspondants(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    brut = json.loads(transcription.read_text())
    texte = "DEBUT NON OFFICIEL " + "x" * 600 + " MOT_RECHERCHE_FIN"
    brut["articles"][0]["texte_integral"] = texte
    transcription.write_text(json.dumps(brut))
    lot = tmp_path / "code"
    preparer_code(transcription, metadata, lot)
    rapport = rechercher_code(lot, "RECHERCHE FIN")
    assert rapport["total_correspondances"] == 1
    apercu = rapport["resultats"][0]["apercus"]["texte_integral"]
    assert apercu["texte"] == texte[:512] and apercu["tronque"] is True
    assert rapport["resultats"][0]["champs_correspondants"]["recherche"] == ["texte_integral"]


@pytest.mark.parametrize("fonction", [rechercher_code, rechercher_tarif])
@pytest.mark.parametrize("parametres", [{"limite": 0}, {"limite": 101}, {"limite": True}, {"limite": 1.0},
                                       {"decalage": -1}, {"decalage": 1_000_001}, {"decalage": False},
                                       {"requete": ""}, {"requete": "!!!"}, {"requete": "a" * 257},
                                       {"requete": "a\x00b"}, {"requete": 123}, {"requete": " ".join("t" + str(i) for i in range(17))}])
def test_parametres_invalides_avant_lecture(tmp_path, fonction, parametres):
    arguments = {"requete": "TEST", **parametres}
    with pytest.raises(ValueError):
        fonction(tmp_path / "lot_absent", **arguments)


@pytest.mark.parametrize("parametres", [{"numero_article": 5}, {"numero_article": " "}, {"source_id": True},
                                       {"source_id": ""}, {"nature": "validee"}, {"nature": []}])
def test_filtres_invalides(tmp_path, parametres):
    with pytest.raises(ValueError):
        rechercher_code(tmp_path / "absent", **parametres)


@pytest.mark.parametrize("type_lot", ["code", "tarif"])
def test_corruption_meme_hors_premiere_page_refusee(tmp_path, type_lot):
    lot = lot_code(tmp_path) if type_lot == "code" else lot_tarif(tmp_path)
    nom = "lot_code.json" if type_lot == "code" else "lot.json"
    path = lot / nom
    path.write_bytes(path.read_bytes() + b" ")
    avant = snapshot(tmp_path)
    fonction = rechercher_code if type_lot == "code" else rechercher_tarif
    with pytest.raises(ValueError, match="Empreinte"):
        fonction(lot, "NON OFFICIEL", limite=1)
    assert snapshot(tmp_path) == avant


def test_types_de_lots_non_interchangeables(tmp_path):
    dcode, dtarif = tmp_path / "recu_code", tmp_path / "recu_tarif"
    dcode.mkdir()
    dtarif.mkdir()
    code, tarif = lot_code(dcode), lot_tarif(dtarif)
    with pytest.raises(ValueError):
        rechercher_code(tarif, "NON OFFICIEL")
    with pytest.raises(ValueError):
        rechercher_tarif(code, "NON OFFICIEL")


def test_zero_resultat_ne_prouve_pas_absence_de_regle(tmp_path):
    rapport = rechercher_code(lot_code(tmp_path), "INEXISTANT")
    assert rapport["resultats"] == [] and rapport["decalage_suivant"] is None
    assert rapport["completude_reglementaire"] == "non_etablie"
    assert any("pas absence de droit" in message for message in rapport["avertissements"])


def test_cli_recherche_et_refus_sans_ecriture(tmp_path, capsys):
    dcode, dtarif = tmp_path / "recu_code", tmp_path / "recu_tarif"
    dcode.mkdir()
    dtarif.mkdir()
    code, tarif = lot_code(dcode), lot_tarif(dtarif)
    avant = snapshot(tmp_path)
    assert main(["customs-tariff-search", str(tarif), "--query", "010100", "--limit", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["total_correspondances"] == 5
    assert main(["customs-code-search", str(code), "--article", "5 bis", "--nature", "originale"]) == 0
    assert json.loads(capsys.readouterr().out)["total_correspondances"] == 1
    assert main(["customs-code-search", str(code), "--query", "معدات"]) == 0
    assert json.loads(capsys.readouterr().out)["resultats"][0]["id"] == "TEST_O_A"
    assert main(["customs-tariff-search", str(tarif), "--query", "010100", "--limit", "-1"]) == 2
    assert json.loads(capsys.readouterr().out)["statut"] == "refuse"
    assert main(["customs-code-search", str(code)]) == 2
    assert json.loads(capsys.readouterr().out)["statut"] == "refuse"
    assert snapshot(tmp_path) == avant


def test_cli_processus_independant_sans_stores(tmp_path):
    dcode, dtarif = tmp_path / "recu_code", tmp_path / "recu_tarif"
    dcode.mkdir()
    dtarif.mkdir()
    code, tarif = lot_code(dcode), lot_tarif(dtarif)
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
           "PYTHONDONTWRITEBYTECODE": "1", "UNOCR_DATA_DIR": str(tmp_path / "stores_absents"),
           "UNOCR_LOG_DIR": str(tmp_path / "logs_absents")}
    avant = snapshot(tmp_path)
    for arguments, compteur in ((["customs-code-search", str(code), "--article", "5 bis"], 2),
                                 (["customs-tariff-search", str(tarif), "--query", "معدات"], 1)):
        resultat = subprocess.run([sys.executable, "-m", "unocr.cli", *arguments], env=env, cwd=tmp_path,
                                  capture_output=True, text=True, timeout=30)
        assert resultat.returncode == 0, resultat.stderr
        assert json.loads(resultat.stdout)["total_correspondances"] == compteur
        assert snapshot(tmp_path) == avant


def test_recherche_dans_archive_xlsx_et_perimetre_feuille(tmp_path):
    from tests.test_customs_xlsx import xlsx_fichiers
    source, metadata = xlsx_fichiers(tmp_path)
    lot = tmp_path / "tarif_xlsx"
    preparer_tarif(source, metadata, lot)
    rapport = rechercher_tarif(lot, "010100")
    assert rapport["total_correspondances"] == 1
    assert rapport["source_declaree"]["format"] == "xlsx"
    assert rapport["perimetre_lecture"]["feuilles_non_importees"] == ["Notes"]
    assert rapport["resultats"][0]["ligne"]["reference"]["localisateur"].startswith("XLSX,")


def test_recherche_dans_archive_csv_utf8(tmp_path):
    source, metadata = fichiers(tmp_path)
    ligne = json.loads(source.read_text())[0]
    ligne["designation_officielle_fr"] = "Café NON OFFICIEL"
    champs = ["code_tarifaire_10", "code_sh_6", "chapitre", "position", "sous_position", "section_id", "designation_officielle_fr"]
    csv_source = tmp_path / "fixture_NON_OFFICIELLE.csv"
    with csv_source.open("w", encoding="utf-8", newline="") as fichier:
        writer = csv.DictWriter(fichier, fieldnames=champs, delimiter=";")
        writer.writeheader()
        writer.writerow({champ: ligne[champ] for champ in champs})
    meta = json.loads(metadata.read_text())
    meta["lot"]["source"].update(format="csv", sha256=hashlib.sha256(csv_source.read_bytes()).hexdigest())
    meta["colonnes"] = {champ: champ for champ in champs}
    metadata.write_text(json.dumps(meta))
    lot = tmp_path / "tarif_csv"
    preparer_tarif(csv_source, metadata, lot)
    rapport = rechercher_tarif(lot, "CAFE")
    assert rapport["total_correspondances"] == 1
    assert rapport["resultats"][0]["ligne"]["designation_officielle_fr"] == "Café NON OFFICIEL"
    assert rapport["resultats"][0]["ligne"]["reference"]["localisateur"].startswith("CSV,")


def test_bornes_admises_pagination_et_deduplication_termes(tmp_path):
    rapport = rechercher_tarif(lot_tarif(tmp_path), "equipement EQUIPEMENT", limite=100, decalage=1_000_000)
    assert rapport["termes_normalises"] == ["equipement"]
    assert rapport["total_correspondances"] == 2
    assert rapport["resultats"] == [] and rapport["decalage_suivant"] is None


def test_ligatures_francaises_sans_changer_le_texte_recu(tmp_path):
    transcription, metadata = fichiers_code(tmp_path)
    brut = json.loads(transcription.read_text())
    brut["articles"][0]["texte_integral"] = "ŒUVRE — CŒUR — ÆTHER — FIXTURE NON OFFICIELLE"
    transcription.write_text(json.dumps(brut, ensure_ascii=False))
    lot = tmp_path / "code"
    preparer_code(transcription, metadata, lot)
    rapport = rechercher_code(lot, "oeuvre coeur aether")
    assert rapport["total_correspondances"] == 1
    assert rapport["resultats"][0]["apercus"]["texte_integral"]["texte"].startswith("ŒUVRE — CŒUR — ÆTHER")
