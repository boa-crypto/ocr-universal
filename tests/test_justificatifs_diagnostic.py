"""Diagnostic sans réparation : ni les anomalies ni les états ambigus ne sont purgés."""
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from unocr.business_store import BusinessStore
from unocr.cli import main
from unocr.justificatifs_diagnostic import diagnostiquer_pieces
from unocr.models import Frais, Justificatif


def preparer(racine):
    relatif = "justificatifs/" + "a" * 32 + ".bin"
    fichier = racine / relatif
    fichier.parent.mkdir()
    fichier.write_bytes(b"abc")
    frais = BusinessStore(racine / "metier.sqlite3", "frais", Frais)
    frais["frais_test"] = Frais(id="frais_test", justificatifs=["just_test"])
    pieces = BusinessStore(racine / "metier.sqlite3", "justificatif", Justificatif)
    pieces["just_test"] = Justificatif(id="just_test", frais_id="frais_test", chemin_fichier=relatif,
                                    taille_octets=3, hash_sha256=hashlib.sha256(b"abc").hexdigest())
    return frais, pieces, fichier


def categories(rapport):
    return {a["categorie"] for a in rapport["anomalies"]}


def empreintes(racine):
    return {str(p.relative_to(racine)): (p.stat().st_mtime_ns, p.read_bytes())
            for p in racine.rglob("*") if p.is_file() and not p.is_symlink()}


def test_sain_sans_mutation(tmp_path):
    preparer(tmp_path)
    avant = empreintes(tmp_path)
    rapport = diagnostiquer_pieces(tmp_path)
    assert rapport["etat"] == "conforme" and rapport["pieces_referencees"] == 1
    assert rapport["lecture_seule"] is True
    assert empreintes(tmp_path) == avant


def test_vide_ne_cree_pas_base(tmp_path, monkeypatch):
    assert diagnostiquer_pieces(tmp_path)["etat"] == "conforme"
    assert list(tmp_path.iterdir()) == []
    (tmp_path / "justificatifs").mkdir()
    (tmp_path / "justificatifs" / ("b" * 32 + ".bin")).write_bytes(b"ancienne piece")
    rapport = diagnostiquer_pieces(tmp_path)
    assert "blob_non_classe" in categories(rapport)
    assert "blob_sans_reference" not in categories(rapport)
    absent = tmp_path / "absent"
    assert diagnostiquer_pieces(absent)["etat"] == "indisponible"
    assert not absent.exists()
    monkeypatch.setenv("UNOCR_DATA_DIR", str(absent))
    assert main(["pieces-check", "--json"]) == 2
    assert not absent.exists()
    def inaccessible(self):
        raise PermissionError("accès refusé")
    with monkeypatch.context() as contexte:
        contexte.setattr(Path, "is_dir", inaccessible)
        assert diagnostiquer_pieces(tmp_path)["etat"] == "indisponible"


@pytest.mark.parametrize("modification,categorie", [
    (None, "fichier_absent"), (b"abcdef", "taille_incoherente"),
    (b"xyz", "empreinte_incoherente"),
])
def test_fichier_invalide_signale_non_repare(tmp_path, modification, categorie):
    _, _, fichier = preparer(tmp_path)
    if modification is None:
        fichier.unlink()
    else:
        fichier.write_bytes(modification)
    avant = empreintes(tmp_path)
    assert categorie in categories(diagnostiquer_pieces(tmp_path))
    assert empreintes(tmp_path) == avant


def test_residus_et_quarantaine_referencee(tmp_path):
    _, _, fichier = preparer(tmp_path)
    quarantaine = fichier.with_name("." + fichier.name + ".deleted.tmp")
    fichier.rename(quarantaine)
    (fichier.parent / ("b" * 32 + ".bin")).write_bytes(b"orphelin")
    (fichier.parent / "tmp_ecriture.tmp").write_bytes(b"incomplet")
    avant = empreintes(tmp_path)
    rapport = diagnostiquer_pieces(tmp_path)
    assert categories(rapport) >= {"fichier_absent", "quarantaine", "blob_sans_reference", "temporaire"}
    assert any(a["categorie"] == "quarantaine" and "just_test" in a["detail"] for a in rapport["anomalies"])
    assert empreintes(tmp_path) == avant


def test_liens_incoherents(tmp_path):
    frais, pieces, _ = preparer(tmp_path)
    frais["frais_test"] = Frais(id="frais_test", justificatifs=["inconnue", "inconnue"])
    assert categories(diagnostiquer_pieces(tmp_path)) >= {"lien_absent", "lien_sans_metadonnee", "liens_dupliques"}
    del frais["frais_test"]
    assert "frais_absent" in categories(diagnostiquer_pieces(tmp_path))
    assert pieces["just_test"].frais_id == "frais_test"


def test_base_corrompue_pas_de_faux_orphelin(tmp_path):
    _, _, fichier = preparer(tmp_path)
    (tmp_path / "metier.sqlite3").write_bytes(b"corruption")
    rapport = diagnostiquer_pieces(tmp_path)
    assert rapport["etat"] == "indisponible"
    assert "blob_sans_reference" not in categories(rapport)
    assert "blob_non_classe" in categories(rapport)
    assert fichier.read_bytes() == b"abc"


def test_metadonnee_corrompue_classement_suspendu(tmp_path):
    preparer(tmp_path)
    with sqlite3.connect(tmp_path / "metier.sqlite3") as db:
        db.execute("UPDATE objects SET payload=? WHERE collection='justificatif'", ("{invalide",))
    rapport = diagnostiquer_pieces(tmp_path)
    assert "metadonnee_invalide" in categories(rapport)
    assert "blob_sans_reference" not in categories(rapport)
    assert rapport["references_completes"] is False


def test_symlink_non_suivi(tmp_path):
    _, _, fichier = preparer(tmp_path)
    secret = tmp_path / "secret"
    secret.write_bytes(b"abc")
    fichier.unlink()
    fichier.symlink_to(secret)
    assert "symlink_refuse" in categories(diagnostiquer_pieces(tmp_path))
    assert secret.read_bytes() == b"abc"


def test_chemin_hors_magasin_non_suivi(tmp_path):
    _, pieces, _ = preparer(tmp_path)
    piece = pieces["just_test"]
    piece.chemin_fichier = "../secret"
    pieces[piece.id] = piece
    rapport = diagnostiquer_pieces(tmp_path)
    assert "chemin_refuse" in categories(rapport)
    assert "blob_sans_reference" not in categories(rapport)


@pytest.mark.parametrize("etat,code", [("sain", 0), ("manquant", 1), ("corrompu", 2)])
def test_cli_codes_json_sans_mutation(tmp_path, capsys, etat, code):
    _, _, fichier = preparer(tmp_path)
    if etat == "manquant":
        fichier.unlink()
    elif etat == "corrompu":
        (tmp_path / "metier.sqlite3").write_bytes(b"corruption")
    avant = empreintes(tmp_path)
    assert main(["pieces-check", "--data-dir", str(tmp_path), "--json"]) == code
    rapport = json.loads(capsys.readouterr().out)
    assert rapport["lecture_seule"] is True
    assert empreintes(tmp_path) == avant


def test_wal_refuse_sans_creation_sidecar(tmp_path):
    preparer(tmp_path)
    with sqlite3.connect(tmp_path / "metier.sqlite3") as db:
        assert db.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    db.close()
    avant = empreintes(tmp_path)
    rapport = diagnostiquer_pieces(tmp_path)
    assert rapport["etat"] == "indisponible"
    assert "base_wal" in categories(rapport)
    assert "blob_sans_reference" not in categories(rapport)
    assert empreintes(tmp_path) == avant
