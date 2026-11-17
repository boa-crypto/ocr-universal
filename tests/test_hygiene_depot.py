"""Garde-fous d'hygiène du dépôt : secrets et artefacts suivis par Git."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_repo_hygiene as hygiene  # noqa: E402


def test_secrets_detectes_par_chemin_et_contenu(tmp_path):
    (tmp_path / "data" / "keys").mkdir(parents=True)
    (tmp_path / "data" / "keys" / "master.key").write_bytes(b"cle-brute")
    (tmp_path / "certs").mkdir()
    (tmp_path / "certs" / "server.pem").write_text(
        "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n", encoding="utf-8")
    (tmp_path / "certs" / "public.pem").write_text(
        "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=local\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("TOKEN=\n", encoding="utf-8")

    paths = ["data/keys/master.key", "certs/server.pem", "certs/public.pem", ".env", ".env.example"]
    assert hygiene.detecter_secrets(tmp_path, paths) == [".env", "certs/server.pem", "data/keys/master.key"]


def test_les_cles_de_test_vendor_ne_sont_pas_des_secrets_projet(tmp_path):
    vendor = tmp_path / ".venv-agency" / "lib" / "tests"
    vendor.mkdir(parents=True)
    (vendor / "fixture.pem").write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n",
                                       encoding="utf-8")
    assert hygiene.detecter_secrets(tmp_path, [".venv-agency/lib/tests/fixture.pem"]) == []


def test_inventaire_separe_artefacts_et_donnees(tmp_path):
    paths = [
        ".venv-agency/bin/python", "tmp_packages/pkg/__init__.py", "logs/unocr.log",
        "src/unocr.egg-info/PKG-INFO", "tests/__pycache__/x.pyc", "data/dossiers/dos_a.json",
        "src/unocr/api.py",
    ]
    for p in paths:
        fichier = tmp_path / p
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text("x", encoding="utf-8")
    rapport = hygiene.inventorier(tmp_path, paths)
    assert rapport["fichiers_suivis"] == len(paths)
    assert rapport["artefacts"]["nombre"] == 5
    assert rapport["donnees_locales"]["nombre"] == 1
    assert rapport["secrets"]["nombre"] == 0


def test_depot_courant_ne_suit_plus_de_secret_detectable():
    paths = hygiene._chemins_suivis(ROOT)
    assert hygiene.detecter_secrets(ROOT, paths) == []


def test_gitignore_couvre_les_secret_et_artefacts_retires():
    texte = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for motif in ("/data/keys/", ".agentic-qe/", "tmp_packages/", "*.egg-info/", "*.log"):
        assert motif in texte


def test_ci_bloque_les_secrets_suivis():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "python scripts/audit_repo_hygiene.py --strict-secrets" in ci
