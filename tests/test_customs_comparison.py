"""Comparaison de fixtures NON OFFICIELLES, pas d'abrogation légale déduite."""
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_customs_reference import fichiers, snapshot
from tests.test_customs_xlsx import xlsx_fichiers
from unocr.cli import main
from unocr.customs_reference.comparison import charger_lot, comparer_lots
from unocr.customs_reference.importer import preparer_tarif


def lots(tmp_path, modifier=None):
    sorties = []
    for nom in ("avant", "apres"):
        recu = tmp_path / ("recu_" + nom)
        recu.mkdir()
        source, metadata = fichiers(recu)
        meta = json.loads(metadata.read_text())
        lignes = json.loads(source.read_text())
        meta["lot"]["source"]["version_source"] = "TEST_" + nom
        if modifier:
            modifier(nom, meta, lignes)
        source.write_text(json.dumps(lignes))
        meta["lot"]["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        metadata.write_text(json.dumps(meta))
        sortie = tmp_path / ("lot_" + nom)
        preparer_tarif(source, metadata, sortie)
        sorties.append(sortie)
    return sorties


def rehasher(lot, fichier):
    manifeste = json.loads((lot / "manifest.json").read_text())
    manifeste["fichiers_sha256"][fichier] = hashlib.sha256((lot / fichier).read_bytes()).hexdigest()
    (lot / "manifest.json").write_text(json.dumps(manifeste))


def test_identiques_pas_de_faux_changement_et_lecture_seule(tmp_path):
    a, b = lots(tmp_path)
    avant = snapshot(tmp_path)
    rapport = comparer_lots(a, b)
    assert rapport["lignes"] == {"ajoutes": [], "retires": [], "modifies": []}
    assert rapport["mesures_modifiees"] == []
    assert rapport["lecture_seule"] is True and rapport["publication_active"] is False
    assert rapport["validation_humaine_requise"] is True
    assert rapport["archives"]["avant"]["source_nom_recu"] == "fixture_NON_OFFICIELLE.json"
    assert rapport["archives"]["avant"]["date_importation"].endswith("+00:00")
    assert rapport["completude_reglementaire"] == "non_etablie"
    assert rapport["sources"]["avant"]["version_source"] != rapport["sources"]["apres"]["version_source"]
    assert snapshot(tmp_path) == avant


def test_ajouts_retraits_modifications_sans_abrogation_deduite(tmp_path):
    def modifier(nom, meta, lignes):
        base = copy.deepcopy(lignes[0])
        lignes.clear()
        for suffixe in ([0, 1] if nom == "avant" else [1, 2]):
            ligne = copy.deepcopy(base)
            ligne["id"] += str(suffixe)
            ligne["code_tarifaire_10"] = "010100000" + str(suffixe)
            if suffixe == 1 and nom == "apres":
                ligne.update(designation_officielle_fr="AUTRE FIXTURE NON OFFICIELLE", unite_statistique="kg", date_entree_vigueur="2026-01-01")
            lignes.append(ligne)
    rapport = comparer_lots(*lots(tmp_path, modifier))
    assert rapport["lignes"]["ajoutes"] == ["0101000002"]
    assert rapport["lignes"]["retires"] == ["0101000000"]
    modification = rapport["lignes"]["modifies"][0]
    assert modification["identifiant"] == "0101000001"
    assert set(modification["changements"]) == {"designation_officielle_fr", "unite_statistique", "date_entree_vigueur"}
    assert any("ni abrogations" in message for message in rapport["avertissements"])


def test_ids_et_localisateurs_techniques_separes(tmp_path):
    def modifier(nom, meta, lignes):
        if nom == "apres":
            lignes[0]["id"] = "AUTRE_ID_TECHNIQUE"
            lignes[0]["reference"]["localisateur"] = "autre localisation fixture"
    rapport = comparer_lots(*lots(tmp_path, modifier))
    assert rapport["lignes"]["modifies"] == []
    assert rapport["sources"]["avant"]["sha256"] != rapport["sources"]["apres"]["sha256"]
    assert rapport["provenances_modifiees"]["lignes"][0]["apres"]["id"] == "AUTRE_ID_TECHNIQUE"


def test_hierarchie_et_taux_separes_des_designations(tmp_path):
    def modifier(nom, meta, lignes):
        meta["lot"]["mesures"] = [{"id": "TEST_MESURE", "code_tarifaire_10": "0101000000", "type_mesure": "tva", "description": "FIXTURE NON OFFICIELLE", "taux": "9" if nom == "avant" else "19", "unite_taux": "pourcent", "reference": lignes[0]["reference"]}]
        if nom == "apres":
            meta["lot"]["chapitres"][0]["designation"] = "NOUVELLE FIXTURE"
    rapport = comparer_lots(*lots(tmp_path, modifier))
    assert rapport["lignes"]["modifies"] == []
    assert rapport["hierarchie"]["chapitres"]["modifies"][0]["identifiant"] == "01"
    assert rapport["mesures_modifiees"][0]["avant"][0]["taux"] == "9"
    assert rapport["mesures_modifiees"][0]["apres"][0]["taux"] == "19"


def test_decimaux_equivalents_pas_de_faux_changement(tmp_path):
    def modifier(nom, meta, lignes):
        meta["lot"]["mesures"] = [{"id": "TEST_" + nom, "code_tarifaire_10": "0101000000", "type_mesure": "tva", "description": "FIXTURE NON OFFICIELLE", "taux": "19.0" if nom == "avant" else "19.00", "unite_taux": "pourcent", "reference": lignes[0]["reference"]}]
    rapport = comparer_lots(*lots(tmp_path, modifier))
    assert rapport["mesures_modifiees"] == []
    assert rapport["provenances_modifiees"]["mesures"][0]["code_tarifaire_10"] == "0101000000"


@pytest.mark.parametrize("fichier", ["source_recue.json", "metadata_original.json", "lot.json", "rapport.json"])
def test_empreinte_alteree_refus_integral(tmp_path, fichier):
    a, b = lots(tmp_path)
    cible = b / fichier
    cible.write_bytes(cible.read_bytes() + b" ")
    avant = snapshot(tmp_path)
    with pytest.raises(ValueError, match="Empreinte différente"):
        comparer_lots(a, b)
    assert snapshot(tmp_path) == avant


def test_lot_rehashe_non_reproductible_refuse(tmp_path):
    a, b = lots(tmp_path)
    brut = json.loads((b / "lot.json").read_text())
    brut["lignes"][0]["designation_officielle_fr"] = "ALTERATION NON PRESENTE DANS LA SOURCE"
    (b / "lot.json").write_text(json.dumps(brut))
    rehasher(b, "lot.json")
    with pytest.raises(ValueError, match="non reproductible"):
        comparer_lots(a, b)


@pytest.mark.parametrize("valeur", [999, True])
def test_rapport_rehashe_incoherent_refuse(tmp_path, valeur):
    a, b = lots(tmp_path)
    rapport = json.loads((b / "rapport.json").read_text())
    rapport["codes_uniques"] = valeur
    (b / "rapport.json").write_text(json.dumps(rapport))
    rehasher(b, "rapport.json")
    with pytest.raises(ValueError, match="Rapport d'import incohérent"):
        comparer_lots(a, b)


@pytest.mark.parametrize("defaut", ["manifest_absent", "fichier_absent", "extra", "symlink", "traversal", "actif", "recu_symlink"])
def test_lot_incomplet_ou_non_sur_refuse(tmp_path, defaut):
    a, b = lots(tmp_path)
    if defaut == "manifest_absent":
        (b / "manifest.json").unlink()
    elif defaut == "fichier_absent":
        (b / "source_recue.json").unlink()
    elif defaut == "extra":
        (b / "inattendu.json").write_text("{}")
    elif defaut == "symlink":
        lien = tmp_path / "lien"
        lien.symlink_to(b, target_is_directory=True)
        b = lien
    elif defaut == "recu_symlink":
        cible = b / "source_recue.json"
        cible.unlink()
        cible.symlink_to(a / "source_recue.json")
    else:
        manifeste = json.loads((b / "manifest.json").read_text())
        if defaut == "traversal":
            manifeste["fichiers_sha256"]["../hors-lot"] = "a" * 64
        else:
            manifeste["publication_active"] = True
        (b / "manifest.json").write_text(json.dumps(manifeste))
    with pytest.raises(ValueError):
        comparer_lots(a, b)


def test_meme_version_contenu_different_avertissement(tmp_path):
    def modifier(nom, meta, lignes):
        meta["lot"]["source"]["version_source"] = "TEST_IDENTIQUE"
        if nom == "apres":
            lignes[0]["designation_officielle_ar"] = "نص اختباري غير رسمي"
    rapport = comparer_lots(*lots(tmp_path, modifier))
    assert any("Même version" in message for message in rapport["avertissements"])


def test_xlsx_et_perimetres_differents_signales(tmp_path):
    a, b = lots(tmp_path)
    recu = tmp_path / "recu_xlsx"
    recu.mkdir()
    source, metadata = xlsx_fichiers(recu)
    autre = tmp_path / "lot_xlsx"
    preparer_tarif(source, metadata, autre)
    assert charger_lot(autre)[0].source.format == "xlsx"
    rapport = comparer_lots(a, autre)
    assert any("Périmètres" in message for message in rapport["avertissements"])
    assert set(rapport["lignes"]["modifies"][0]["changements"]) == {"designation_officielle_fr"}


def test_compatibilite_rapport_lot1_sans_perimetre(tmp_path):
    a, b = lots(tmp_path)
    rapport = json.loads((a / "rapport.json").read_text())
    rapport.pop("perimetre_lecture")
    (a / "rapport.json").write_text(json.dumps(rapport))
    rehasher(a, "rapport.json")
    assert comparer_lots(a, b)["lignes"]["modifies"] == []


def test_cli_diff_lecture_seule_et_refus(tmp_path, capsys):
    a, b = lots(tmp_path)
    avant = snapshot(tmp_path)
    assert main(["customs-diff", str(a), str(b)]) == 0
    assert json.loads(capsys.readouterr().out)["lecture_seule"] is True
    assert snapshot(tmp_path) == avant
    assert main(["customs-diff", str(a), str(tmp_path / "absent")]) == 2
    assert json.loads(capsys.readouterr().out)["statut"] == "refuse"


def test_taux_compare_sans_arrondi_contextuel(tmp_path):
    def modifier(nom, meta, lignes):
        meta["lot"]["mesures"] = [{"id": "TEST_MESURE", "code_tarifaire_10": "0101000000", "type_mesure": "tva", "description": "FIXTURE NON OFFICIELLE", "taux": "19.00000000000000000000000000001" if nom == "avant" else "19.00000000000000000000000000002", "unite_taux": "pourcent", "reference": lignes[0]["reference"]}]
    rapport = comparer_lots(*lots(tmp_path, modifier))
    assert rapport["mesures_modifiees"][0]["avant"][0]["taux"] != rapport["mesures_modifiees"][0]["apres"][0]["taux"]


@pytest.mark.parametrize("champ,valeur", [("perimetre_lecture", {"format": "xlsx"}), ("colonnes_non_importees", ["COLONNE_CACHEE"]), ("ecrit", 1)])
def test_rapport_perimetre_et_types_verifies(tmp_path, champ, valeur):
    a, b = lots(tmp_path)
    rapport = json.loads((b / "rapport.json").read_text())
    rapport[champ] = valeur
    (b / "rapport.json").write_text(json.dumps(rapport))
    rehasher(b, "rapport.json")
    with pytest.raises(ValueError, match="Rapport d'import incohérent"):
        comparer_lots(a, b)


@pytest.mark.parametrize("champ,valeur", [("date_importation", None), ("date_importation", "2026-11-06T12:00:00"), ("source_nom_recu", "")])
def test_manifest_tracabilite_requise(tmp_path, champ, valeur):
    a, b = lots(tmp_path)
    manifeste = json.loads((b / "manifest.json").read_text())
    manifeste[champ] = valeur
    (b / "manifest.json").write_text(json.dumps(manifeste))
    with pytest.raises(ValueError):
        comparer_lots(a, b)


def test_cli_sous_processus_ne_cree_pas_de_stores(tmp_path):
    a, b = lots(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
           "PYTHONDONTWRITEBYTECODE": "1", "UNOCR_DATA_DIR": str(tmp_path / "stores_absents"),
           "UNOCR_LOG_DIR": str(tmp_path / "logs_absents")}
    avant = snapshot(tmp_path)
    for cible, code in ((b, 0), (tmp_path / "absent", 2)):
        resultat = subprocess.run([sys.executable, "-m", "unocr.cli", "customs-diff", str(a), str(cible)],
                                  cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
        assert resultat.returncode == code, resultat.stderr
        assert isinstance(json.loads(resultat.stdout), dict)
        assert snapshot(tmp_path) == avant


@pytest.mark.parametrize("taux_apres,change", [("10e999999", False), ("1e1000001", True)])
def test_exposant_extreme_sans_expansion(tmp_path, taux_apres, change):
    def modifier(nom, meta, lignes):
        meta["lot"]["mesures"] = [{"id": "TEST_MESURE", "code_tarifaire_10": "0101000000", "type_mesure": "tva", "description": "FIXTURE NON OFFICIELLE", "taux": "1e1000000" if nom == "avant" else taux_apres, "unite_taux": "pourcent", "reference": lignes[0]["reference"]}]
    rapport = comparer_lots(*lots(tmp_path, modifier))
    assert bool(rapport["mesures_modifiees"]) is change
    assert rapport["provenances_modifiees"]["mesures"] == []
