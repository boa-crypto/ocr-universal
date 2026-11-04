"""Tests de sauvegarde / restauration (lot P0).

Ce que ces tests verrouillent : le magasin est la seule trace des documents
traités et des corrections humaines. Une sauvegarde qu'on ne peut pas
vérifier, ou une restauration qui écrase sans prévenir, détruit ce travail.
"""
import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient  # noqa: E402

from unocr.api import app  # noqa: E402
from unocr.backup import (  # noqa: E402
    MANIFESTE,
    BackupError,
    ResultatSauvegarde,
    creer_sauvegarde,
    lister_sauvegardes,
    purger_sauvegardes,
    restaurer_sauvegarde,
    verifier_sauvegarde,
)


@pytest.fixture()
def client(tmp_cfg):
    return TestClient(app)


@pytest.fixture()
def magasin_peuple(tmp_cfg):
    """Un magasin minimal mais réel : un job, un dossier, une entrée d'audit."""
    jobs = tmp_cfg.data_dir / "jobs" / "job_test0001"
    (jobs / "originaux").mkdir(parents=True, exist_ok=True)
    (jobs / "resultat.json").write_text(json.dumps(
        {"id": "job_test0001", "fields": {"invoice_number": {
            "raw_value": "INV-1", "value_origin": "raw", "status": "detected"}}}),
        encoding="utf-8")
    dossiers = tmp_cfg.data_dir / "dossiers"
    dossiers.mkdir(parents=True, exist_ok=True)
    (dossiers / "dos_test.json").write_text(json.dumps(
        {"id": "dos_test", "label": "dossier de test",
         "arbitrages": {"poids_divergent": {"status": "accepte",
                                            "acteur": "amina"}}}),
        encoding="utf-8")
    tmp_cfg.log_dir.mkdir(parents=True, exist_ok=True)
    (tmp_cfg.log_dir / "audit.log").write_text(
        json.dumps({"event": "sauvegarde_creee", "job_id": "job_test0001"}) + "\n",
        encoding="utf-8")
    return tmp_cfg


# ───────────────────────────── création ─────────────────────────────

def test_sauvegarde_contient_le_magasin(magasin_peuple):
    res = creer_sauvegarde(magasin_peuple)
    assert isinstance(res, ResultatSauvegarde)
    assert res.chemin.is_file()
    assert res.fichiers >= 3
    assert res.taille > 0
    with zipfile.ZipFile(res.chemin) as zf:
        noms = zf.namelist()
    assert MANIFESTE in noms
    assert any("job_test0001" in n for n in noms)
    # le journal est archivé sous son propre préfixe : il ne vit pas dans
    # le magasin, et l'oublier perdrait l'historique des transmissions
    assert any(n.startswith("logs/") and n.endswith("audit.log") for n in noms)


def test_sauvegarde_est_verifiable(magasin_peuple):
    res = creer_sauvegarde(magasin_peuple)
    etat = verifier_sauvegarde(res.chemin)
    assert etat["valide"] is True
    assert etat["fichiers"] >= 3
    assert etat["manquants"] == []


def test_sauvegarde_corrompue_est_refusee(magasin_peuple, tmp_path):
    """Une archive altérée doit être refusée, pas « restaurée » à l'aveugle."""
    res = creer_sauvegarde(magasin_peuple)
    cible = tmp_path / "falsifiee.zip"
    with zipfile.ZipFile(res.chemin) as zf:
        donnees = {n: zf.read(n) for n in zf.namelist()}
    # on réécrit un fichier avec un contenu différent de son empreinte
    cle = next(n for n in donnees if "resultat.json" in n)
    donnees[cle] = b'{"id": "trafique"}'
    with zipfile.ZipFile(cible, "w") as zf:
        for n, contenu in donnees.items():
            zf.writestr(n, contenu)
    with pytest.raises(BackupError) as exc:
        verifier_sauvegarde(cible)
    assert "altéré" in str(exc.value)


def test_sauvegarde_sans_manifeste_est_refusee(tmp_path):
    archive = tmp_path / "sans_manifeste.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("jobs/x.json", "{}")
    with pytest.raises(BackupError):
        verifier_sauvegarde(archive)


def test_sauvegardes_ne_s_ecrasent_pas(magasin_peuple):
    """Deux sauvegardes dans la même minute portent des noms distincts."""
    premiere = creer_sauvegarde(magasin_peuple)
    time.sleep(1.1)
    seconde = creer_sauvegarde(magasin_peuple)
    assert premiere.chemin != seconde.chemin
    assert premiere.chemin.is_file() and seconde.chemin.is_file()


# ───────────────────────────── restauration ─────────────────────────────

def test_restauration_refuse_un_magasin_non_vide(magasin_peuple):
    """Restaurer par-dessus ferait perdre les documents plus récents."""
    res = creer_sauvegarde(magasin_peuple)
    with pytest.raises(BackupError) as exc:
        restaurer_sauvegarde(magasin_peuple, res.chemin)
    assert "force" in str(exc.value)


def test_restauration_avec_force_reecrit_le_magasin(magasin_peuple):
    res = creer_sauvegarde(magasin_peuple)
    # on simule une perte : le magasin est vidé, puis restauré
    for enfant in magasin_peuple.data_dir.iterdir():
        if enfant.is_dir():
            for f in enfant.rglob("*"):
                if f.is_file():
                    f.unlink()
    etat = restaurer_sauvegarde(magasin_peuple, res.chemin, force=True)
    assert etat["fichiers"] >= 3
    restaure = json.loads((magasin_peuple.data_dir / "jobs" / "job_test0001"
                           / "resultat.json").read_text(encoding="utf-8"))
    # le journal revient dans log_dir, pas dans data_dir
    assert (magasin_peuple.log_dir / "audit.log").is_file()
    assert restaure["fields"]["invoice_number"]["raw_value"] == "INV-1"
    # l'arbitrage humain survit à la restauration
    dos = json.loads((magasin_peuple.data_dir / "dossiers" / "dos_test.json")
                     .read_text(encoding="utf-8"))
    assert dos["arbitrages"]["poids_divergent"]["acteur"] == "amina"


def test_restauration_refuse_un_chemin_traversant(magasin_peuple, tmp_path):
    """Une archive hostile ne doit jamais écrire hors du magasin."""
    piege = tmp_path / "piege.zip"
    with zipfile.ZipFile(piege, "w") as zf:
        zf.writestr(MANIFESTE, json.dumps(
            {"version": 1, "fichiers": [{"nom": "../evasion.txt",
                                         "octets": 4,
                                         "empreinte": "0" * 64}]}))
        zf.writestr("../evasion.txt", "pirate")
    with pytest.raises(BackupError):
        restaurer_sauvegarde(magasin_peuple, piege, force=True)
    assert not (tmp_path / "evasion.txt").exists()


def test_verification_refuse_un_membre_absent_du_manifeste(tmp_path):
    archive = tmp_path / "membre-cache.zip"
    contenu = b'{"utilisateurs": []}'
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(MANIFESTE, json.dumps({"version": 1, "fichiers": []}))
        zf.writestr("data/rbac.json", contenu)
    with pytest.raises(BackupError):
        verifier_sauvegarde(archive)


def test_restauration_refuse_un_chemin_frere_au_prefixe_similaire(
        magasin_peuple, tmp_path):
    archive = tmp_path / "prefixe-frere.zip"
    membre = "data/../data-escape/owned.txt"
    contenu = b"hors du magasin"
    manifeste = {"version": 1, "fichiers": [{
        "nom": membre, "octets": len(contenu),
        "empreinte": hashlib.sha256(contenu).hexdigest()}]}
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(MANIFESTE, json.dumps(manifeste))
        zf.writestr(membre, contenu)
    with pytest.raises(BackupError):
        restaurer_sauvegarde(magasin_peuple, archive, force=True)
    assert not (magasin_peuple.data_dir.parent / "data-escape" / "owned.txt").exists()


def test_purge_conserve_les_plus_recentes(magasin_peuple):
    for _ in range(3):
        creer_sauvegarde(magasin_peuple)
        time.sleep(1.1)
    repertoire = magasin_peuple.data_dir.parent / "sauvegardes"
    avant = len(lister_sauvegardes(repertoire))
    assert avant == 3
    supprimees = purger_sauvegardes(repertoire, conserver=2)
    assert len(supprimees) == 1
    apres = lister_sauvegardes(repertoire)
    assert len(apres) == 2
    # la plus récente est toujours là, en tête
    assert apres[0]["nom"] > apres[1]["nom"]


def test_purge_refuse_zero(magasin_peuple):
    with pytest.raises(BackupError):
        purger_sauvegardes(magasin_peuple.data_dir.parent / "sauvegardes",
                           conserver=0)


# ───────────────────────────── routes API ─────────────────────────────

def test_api_backup_puis_liste(client, magasin_peuple):
    r = client.post("/api/backups", json={"keep": 0})
    assert r.status_code == 200, r.text
    corps = r.json()
    assert corps["fichiers"] >= 3
    assert corps["empreinte"]
    liste = client.get("/api/backups")
    assert liste.status_code == 200
    assert any(s["chemin"] == corps["chemin"]
               for s in liste.json()["sauvegardes"])


def test_api_verification(client, magasin_peuple):
    cree = client.post("/api/backups", json={"keep": 0}).json()
    r = client.post("/api/backups/verify", json={"chemin": cree["chemin"]})
    assert r.status_code == 200
    assert r.json()["valide"] is True


def test_api_verification_exige_un_chemin(client):
    r = client.post("/api/backups/verify", json={})
    assert r.status_code == 422


def test_api_restauration_refuse_sans_force(client, magasin_peuple):
    cree = client.post("/api/backups", json={"keep": 0}).json()
    r = client.post("/api/backups/restore", json={"chemin": cree["chemin"]})
    assert r.status_code == 409
    assert "force" in r.json()["detail"]


def test_api_restauration_avec_force(client, magasin_peuple):
    cree = client.post("/api/backups", json={"keep": 0}).json()
    r = client.post("/api/backups/restore",
                    json={"chemin": cree["chemin"], "force": True})
    assert r.status_code == 200, r.text
    assert r.json()["fichiers"] >= 3


def test_cli_backup_et_backups(magasin_peuple, capsys):
    from unocr.cli import cmd_backup, cmd_backups

    class Args:
        out = ""
        tag = "test"
        keep = 0

    assert cmd_backup(Args()) == 0
    sortie = capsys.readouterr().out
    assert "sauvegarde créée" in sortie
    assert "SHA-256" in sortie

    class ArgsListe:
        dir = ""

    assert cmd_backups(ArgsListe()) == 0
    assert "sauvegarde-" in capsys.readouterr().out
