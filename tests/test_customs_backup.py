"""Reprise de fixtures NON OFFICIELLES, sans activation réglementaire."""
import hashlib
import json
import shutil
import stat
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from tests.test_customs_reference import snapshot
from tests.test_customs_search import lot_code, lot_tarif
from unocr import api, backup
from unocr.cli import main
from unocr.customs_reference.comparison import charger_lot
from unocr.customs_reference.legal_comparison import charger_lot_code
from unocr.customs_reference.review_registry import charger_registre
from unocr.rbac import RegistreRBAC


@pytest.fixture()
def corpus(tmp_cfg):
    racine = tmp_cfg.data_dir / "customs-quarantine"
    racine.mkdir()
    entrees = tmp_cfg.root / "entrees"
    entrees.mkdir()
    lots = []
    for nom, fonction, type_lot in (("tarif", lot_tarif, "tarif"), ("code", lot_code, "code")):
        dossier = entrees / nom
        dossier.mkdir()
        sortie = fonction(dossier)
        shutil.copytree(sortie, racine / nom)
        lots.append({"id": nom, "dossier": nom, "type_lot": type_lot,
                     "manifest_sha256": hashlib.sha256((sortie / "manifest.json").read_bytes()).hexdigest()})
    (racine / "registre.json").write_text(json.dumps({"lots": lots, "reviseurs": []}))
    return tmp_cfg, racine


def cible_neuve(tmp_path):
    return SimpleNamespace(data_dir=tmp_path / "reprise" / "data", log_dir=tmp_path / "reprise" / "logs")


def test_sauvegarde_reprise_exacte_registre_pdf_transcriptions_et_epingles(corpus, tmp_path):
    cfg, racine = corpus
    avant = snapshot(racine)
    resultat = backup.creer_sauvegarde(cfg, inclure_quarantaine=True)
    assert resultat.chemin.parent.name == "sauvegardes-quarantaine"
    assert stat.S_IMODE(resultat.chemin.stat().st_mode) & 0o077 == 0
    assert backup.verifier_sauvegarde(resultat.chemin)["quarantaine_presente"] is True
    cible = cible_neuve(tmp_path)
    backup.restaurer_sauvegarde(cible, resultat.chemin, inclure_quarantaine=True)
    restaure = cible.data_dir / "customs-quarantine"
    assert {nom: valeur[1] for nom, valeur in snapshot(restaure).items()} == {nom: valeur[1] for nom, valeur in avant.items()}
    assert snapshot(racine) == avant
    assert stat.S_IMODE(restaure.stat().st_mode) & 0o077 == 0
    registre = charger_registre(restaure / "registre.json")
    for entree in registre.lots:
        dossier = restaure / entree.dossier
        lot, rapport = (charger_lot(dossier) if entree.type_lot == "tarif" else charger_lot_code(dossier))
        assert rapport["archive"]["manifest_sha256"] == entree.manifest_sha256
    assert charger_lot_code(restaure / "code")[0].publication_active is False


def test_option_explicite_obligatoire_pas_d_omission_silencieuse(corpus):
    cfg, racine = corpus
    avant = snapshot(racine)
    with pytest.raises(backup.BackupError, match="CLI explicite"):
        backup.creer_sauvegarde(cfg)
    assert snapshot(racine) == avant
    assert not (cfg.data_dir.parent / "sauvegardes").exists()


@pytest.mark.parametrize("force", [False, True])
def test_reprise_quarantaine_option_obligatoire_avant_ecriture(corpus, tmp_path, force):
    cfg, racine = corpus
    resultat = backup.creer_sauvegarde(cfg, inclure_quarantaine=True)
    cible = cible_neuve(tmp_path)
    with pytest.raises(backup.BackupError, match="CLI explicite"):
        backup.restaurer_sauvegarde(cible, resultat.chemin, force=force)
    assert not cible.data_dir.exists()


@pytest.mark.parametrize("force", [False, True])
def test_aucune_fusion_ni_ecrasement_meme_avec_force(corpus, tmp_path, force):
    cfg, racine = corpus
    resultat = backup.creer_sauvegarde(cfg, inclure_quarantaine=True)
    cible = cible_neuve(tmp_path)
    destination = cible.data_dir / "customs-quarantine"
    destination.mkdir(parents=True)
    (destination / "a_conserver").write_text("TRACE LOCALE NON OFFICIELLE")
    avant = snapshot(cible.data_dir)
    with pytest.raises(backup.BackupError, match="magasin neuf"):
        backup.restaurer_sauvegarde(cible, resultat.chemin, force=force, inclure_quarantaine=True)
    assert snapshot(cible.data_dir) == avant


def test_sauvegarde_incomplete_conserve_fichiers_caches_et_tmp_sans_reparation(corpus, tmp_path):
    cfg, racine = corpus
    (racine / "code" / "manifest.json").unlink()
    (racine / "code" / ".trace").write_bytes(b"TRACE NON OFFICIELLE")
    (racine / "code" / "interruption.tmp").write_bytes(b"ECRITURE INTERROMPUE NON OFFICIELLE")
    avant = snapshot(racine)
    resultat = backup.creer_sauvegarde(cfg, inclure_quarantaine=True)
    cible = cible_neuve(tmp_path)
    backup.restaurer_sauvegarde(cible, resultat.chemin, inclure_quarantaine=True)
    assert {nom: valeur[1] for nom, valeur in snapshot(cible.data_dir / "customs-quarantine").items()} == {nom: valeur[1] for nom, valeur in avant.items()}
    with pytest.raises(ValueError):
        charger_lot_code(cible.data_dir / "customs-quarantine" / "code")


@pytest.mark.parametrize("niveau", ["racine", "fichier", "dossier"])
def test_symlinks_source_refuses(corpus, niveau):
    cfg, racine = corpus
    if niveau == "racine":
        autre = racine.with_name("autre")
        racine.rename(autre)
        racine.symlink_to(autre, target_is_directory=True)
    elif niveau == "dossier":
        autre = racine / "tarif_origine"
        (racine / "tarif").rename(autre)
        (racine / "tarif").symlink_to(autre, target_is_directory=True)
    else:
        cible = racine / "code" / "document_0001.pdf"
        cible.unlink()
        cible.symlink_to(racine / "code" / "document_0002.pdf")
    with pytest.raises(backup.BackupError, match="symbolique"):
        backup.creer_sauvegarde(cfg, inclure_quarantaine=True)


def test_collision_nom_sauvegarde_ne_perd_pas_la_precedente(corpus, monkeypatch):
    cfg, racine = corpus
    monkeypatch.setattr(backup.time, "strftime", lambda format: "DATE_TEST_FIXE")
    premiere = backup.creer_sauvegarde(cfg, inclure_quarantaine=True)
    octets = premiere.chemin.read_bytes()
    seconde = backup.creer_sauvegarde(cfg, inclure_quarantaine=True)
    assert premiere.chemin != seconde.chemin
    assert premiere.chemin.read_bytes() == octets
    assert backup.verifier_sauvegarde(seconde.chemin)["valide"] is True


def test_empreinte_copie_verifiee_avant_succes(corpus, monkeypatch):
    cfg, racine = corpus
    original = backup._empreinte
    cible = racine / "code" / "document_0001.pdf"
    def modification_concurrente(path):
        if path == cible:
            cible.write_bytes(cible.read_bytes() + b"MODIFICATION DE TEST")
        return original(path)
    monkeypatch.setattr(backup, "_empreinte", modification_concurrente)
    with pytest.raises(backup.BackupError, match="altéré"):
        backup.creer_sauvegarde(cfg, inclure_quarantaine=True)


def test_archive_corrompue_refusee_avant_reprise(corpus, tmp_path):
    cfg, racine = corpus
    resultat = backup.creer_sauvegarde(cfg, inclure_quarantaine=True)
    with zipfile.ZipFile(resultat.chemin) as archive:
        fichiers = {nom: archive.read(nom) for nom in archive.namelist()}
    fichiers["data/customs-quarantine/code/document_0001.pdf"] += b"ALTERATION"
    mauvais = tmp_path / "mauvais.zip"
    with zipfile.ZipFile(mauvais, "w") as archive:
        for nom, contenu in fichiers.items():
            archive.writestr(nom, contenu)
    cible = cible_neuve(tmp_path)
    with pytest.raises(backup.BackupError):
        backup.restaurer_sauvegarde(cible, mauvais, inclure_quarantaine=True)
    assert not cible.data_dir.exists()


def test_metadonnees_symlink_zip_refusees(corpus, tmp_path):
    cfg, racine = corpus
    resultat = backup.creer_sauvegarde(cfg, inclure_quarantaine=True)
    mauvais = tmp_path / "symlink.zip"
    with zipfile.ZipFile(resultat.chemin) as source, zipfile.ZipFile(mauvais, "w") as destination:
        for info in source.infolist():
            if info.filename.endswith("/document_0001.pdf"):
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
            destination.writestr(info, source.read(info))
    with pytest.raises(backup.BackupError, match="symbolique ZIP"):
        backup.verifier_sauvegarde(mauvais)


def test_api_legacy_ne_peut_pas_inclure_ou_restaurer_quarantaine(corpus, tmp_path, monkeypatch):
    cfg, racine = corpus
    monkeypatch.setattr(api, "_rbac", RegistreRBAC(actif=False))
    monkeypatch.setattr(api, "_AUTH_TOKEN", "")
    with TestClient(api.app) as client:
        avant = snapshot(racine)
        assert client.post("/api/backups", json={"include_customs_quarantine": True}).status_code == 409
        resultat = backup.creer_sauvegarde(cfg, inclure_quarantaine=True)
        # Le paramètre HTTP est ignoré : seule l'option du CLI est raccordée.
        assert client.post("/api/backups/restore", json={"chemin": str(resultat.chemin), "force": True,
                                                        "include_customs_quarantine": True}).status_code == 409
        assert snapshot(racine) == avant


def test_cli_option_sauvegarde_reprise_sur_destination_neuve(corpus, tmp_path, monkeypatch, capsys):
    cfg, racine = corpus
    destination = tmp_path / "copies"
    assert main(["backup", "--out", str(destination), "--keep", "0"]) == 2
    capsys.readouterr()
    assert main(["backup", "--out", str(destination), "--keep", "0", "--include-customs-quarantine"]) == 0
    capsys.readouterr()
    archive = next(destination.glob("*.zip"))
    monkeypatch.setenv("UNOCR_DATA_DIR", str(tmp_path / "nouveau_data"))
    monkeypatch.setenv("UNOCR_LOG_DIR", str(tmp_path / "nouveaux_logs"))
    assert main(["restore", str(archive), "--include-customs-quarantine"]) == 0
    capsys.readouterr()
    assert charger_lot_code(tmp_path / "nouveau_data" / "customs-quarantine" / "code")[0].publication_active is False


def test_quarantaine_non_repertoire_pas_omise(corpus):
    cfg, racine = corpus
    shutil.rmtree(racine)
    racine.write_text("TRACE NON OFFICIELLE, PAS UN DOSSIER")
    with pytest.raises(backup.BackupError, match="non répertoire"):
        backup.creer_sauvegarde(cfg, inclure_quarantaine=True)


def test_ancienne_archive_ne_peut_pas_recouvrir_un_magasin_avec_quarantaine(corpus, tmp_path):
    cfg, racine = corpus
    source = SimpleNamespace(data_dir=tmp_path / "ancien" / "data", log_dir=tmp_path / "ancien" / "logs")
    source.data_dir.mkdir(parents=True)
    archive = backup.creer_sauvegarde(source)
    avant = snapshot(cfg.data_dir)
    with pytest.raises(backup.BackupError, match="Quarantaine cible déjà présente"):
        backup.restaurer_sauvegarde(cfg, archive.chemin, force=True, inclure_quarantaine=True)
    assert snapshot(cfg.data_dir) == avant


def test_dossiers_metier_sqlite_wal_snapshot_et_reprise(corpus, tmp_path):
    import sqlite3
    cfg, racine = corpus
    db = racine / "dossiers_metier.sqlite3"
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE sorties_audit(id TEXT, livre INTEGER)")
        conn.execute("INSERT INTO sorties_audit VALUES ('NON-OFFICIEL',0)")
        conn.commit()
        assert Path(str(db)+"-wal").exists()
        result = backup.creer_sauvegarde(cfg, inclure_quarantaine=True)
        with zipfile.ZipFile(result.chemin) as archive:
            assert "data/customs-quarantine/dossiers_metier.sqlite3" in archive.namelist()
            assert not any(n.endswith((".sqlite3-wal", ".sqlite3-shm", ".sqlite3-journal")) for n in archive.namelist())
        cible = cible_neuve(tmp_path)
        backup.restaurer_sauvegarde(cible, result.chemin, inclure_quarantaine=True)
        copie = sqlite3.connect(cible.data_dir / "customs-quarantine/dossiers_metier.sqlite3")
        try:
            assert copie.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            assert copie.execute("SELECT * FROM sorties_audit").fetchall() == [("NON-OFFICIEL",0)]
        finally:
            copie.close()
    finally:
        conn.close()


def test_dossiers_metier_journal_orphelin_refuse(corpus):
    cfg, racine = corpus
    (racine / "dossiers_metier.sqlite3-wal").write_bytes(b"NON OFFICIEL")
    with pytest.raises(backup.BackupError, match="sans base principale"):
        backup.creer_sauvegarde(cfg, inclure_quarantaine=True)
