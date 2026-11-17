"""Reçus transactionnels : lecture sans création ni mutation du magasin."""
import json
import sqlite3

import pytest

from unocr.business_store import BusinessStore
from unocr.cli import main
from unocr.pieces_receipts import COLLECTION, RecuSuppressionPiece, consulter_suppression


def instantane(racine):
    return {str(p.relative_to(racine)): (p.stat().st_mtime_ns, p.read_bytes())
            for p in racine.rglob("*") if p.is_file() and not p.is_symlink()}


def creer_recu(racine):
    recu = RecuSuppressionPiece(id="just_test", frais_id="frais_test", hash_sha256="a" * 64, taille_octets=6)
    BusinessStore(racine / "metier.sqlite3", COLLECTION, RecuSuppressionPiece)[recu.id] = recu
    return recu


@pytest.mark.parametrize("repertoire_absent", [True, False])
def test_magasin_absent_sans_creation(tmp_path, repertoire_absent):
    racine = tmp_path / "absent" if repertoire_absent else tmp_path
    avant = instantane(tmp_path)
    assert consulter_suppression(racine, "just_test")["etat"] == "indisponible"
    assert instantane(tmp_path) == avant
    assert racine.exists() != repertoire_absent


@pytest.mark.parametrize("mode", ["corrompue", "wal", "symlink"])
def test_base_refusee_sans_effet(tmp_path, mode):
    base = tmp_path / "metier.sqlite3"
    if mode == "corrompue":
        base.write_bytes(b"pas SQLite")
    elif mode == "wal":
        with sqlite3.connect(base) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE exemple (id TEXT)")
        db.close()
    else:
        (tmp_path / "ailleurs").write_bytes(b"secret")
        base.symlink_to(tmp_path / "ailleurs")
    avant = instantane(tmp_path)
    assert consulter_suppression(tmp_path, "just_test")["etat"] == "indisponible"
    assert instantane(tmp_path) == avant
    if mode == "symlink":
        assert base.is_symlink()


@pytest.mark.parametrize("defaut", ["json", "id", "date"])
def test_recu_invalide_pas_de_fausse_absence(tmp_path, defaut):
    recu = creer_recu(tmp_path).model_dump(mode="json")
    if defaut == "id":
        recu["id"] = "autre"
    elif defaut == "date":
        recu["date_utc"] = "2026-11-04T12:00:00"  # date sans fuseau refusée
    with sqlite3.connect(tmp_path / "metier.sqlite3") as db:
        db.execute("UPDATE objects SET payload=? WHERE collection=?", ("{" if defaut == "json" else json.dumps(recu), COLLECTION))
    avant = instantane(tmp_path)
    assert consulter_suppression(tmp_path, "just_test")["etat"] == "indisponible"
    assert instantane(tmp_path) == avant


def test_consultation_et_cli_lecture_seule(tmp_path, capsys):
    recu = creer_recu(tmp_path)
    avant = instantane(tmp_path)
    rep = consulter_suppression(tmp_path, "just_test")
    assert rep["etat"] == "trouve" and rep["lecture_seule"] is True
    assert rep["recu"] == recu.model_dump(mode="json")
    args = ["pieces-receipt", "just_test", "--data-dir", str(tmp_path)]
    assert main(args + ["--json"]) == 0
    assert json.loads(capsys.readouterr().out) == rep
    assert main(args) == 0
    assert "trouve" in capsys.readouterr().out
    args[1] = "absent"
    assert main(args + ["--json"]) == 0
    assert json.loads(capsys.readouterr().out)["etat"] == "absent"
    assert instantane(tmp_path) == avant


def test_identifiant_sql_parametre_et_cli_indisponible(tmp_path, capsys):
    creer_recu(tmp_path)
    avant = instantane(tmp_path)
    assert consulter_suppression(tmp_path, "' OR 1=1 --")["etat"] == "absent"
    assert instantane(tmp_path) == avant
    assert main(["pieces-receipt", "just_test", "--data-dir", str(tmp_path / "absent"), "--json"]) == 2
    assert json.loads(capsys.readouterr().out)["etat"] == "indisponible"
    assert not (tmp_path / "absent").exists()
