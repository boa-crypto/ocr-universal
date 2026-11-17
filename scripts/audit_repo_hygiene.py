#!/usr/bin/env python3
"""Inventaire d'hygiène Git : secrets, artefacts et données locales.

L'outil ne supprime rien et n'affiche jamais le contenu d'un secret. Il sert
à rendre visible la dette de dépôt (environnements virtuels, caches, journaux,
clés) et à bloquer en CI la réintroduction d'un secret suivi par Git.

Usage :
    python scripts/audit_repo_hygiene.py
    python scripts/audit_repo_hygiene.py --strict-secrets
    python scripts/audit_repo_hygiene.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

VENDOR_PREFIXES = (".venv-agency/", "tmp_packages/", "node_modules/")
SECRET_PATH_PREFIXES = ("data/keys/", ".agentic-qe/witness-keys/")
SECRET_SUFFIXES = (".pem", ".key", ".p8", ".p12", ".pfx")
PRIVATE_KEY_RE = re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----")
ENV_RE = re.compile(r"(^|/)\.env(?:\.[^/]+)?$")
ENV_EXAMPLE_SUFFIXES = (".example", ".sample", ".dist", ".template")

ARTIFACT_PREFIXES = (
    ".venv-agency/", "tmp_packages/", ".agentic-qe/", "logs/",
    "node_modules/", ".pytest_cache/", ".ruff_cache/", ".mypy_cache/",
)
ARTIFACT_SUFFIXES = (".pyc", ".pyo", ".egg-info/", ".log")
ROOT_SCRATCH = {
    "verify_both.py", "verify_fix.py", "verify_import.py", "verify_result.txt",
    "write_import.py", "test_i18n_check.py",
}


def _est_vendor(path: str) -> bool:
    return path.startswith(VENDOR_PREFIXES)


def _est_secret_path(path: str) -> bool:
    if path.startswith(SECRET_PATH_PREFIXES):
        return True
    nom = path.rsplit("/", 1)[-1]
    if ENV_RE.search(path) and not nom.endswith(ENV_EXAMPLE_SUFFIXES):
        return True
    return False


def _contient_cle_privee(chemin: Path) -> bool:
    try:
        if chemin.stat().st_size > 1024 * 1024:
            return False
        return bool(PRIVATE_KEY_RE.search(chemin.read_bytes()))
    except OSError:
        return False


def detecter_secrets(root: Path, paths: list[str]) -> list[str]:
    secrets = []
    for path in paths:
        if _est_secret_path(path):
            secrets.append(path)
            continue
        if _est_vendor(path):
            continue
        if path.endswith(SECRET_SUFFIXES) and _contient_cle_privee(root / path):
            secrets.append(path)
    return sorted(secrets)


def _est_artefact(path: str) -> bool:
    if path.startswith(ARTIFACT_PREFIXES):
        return True
    if path.endswith(ARTIFACT_SUFFIXES):
        return True
    if "__pycache__/" in path or ".egg-info/" in path:
        return True
    if path in ROOT_SCRATCH or path == ".claude/settings.local.json":
        return True
    return False


def inventorier(root: Path, paths: list[str]) -> dict:
    secrets = detecter_secrets(root, paths)
    artefacts = [p for p in paths if _est_artefact(p)]
    donnees = [p for p in paths if p.startswith("data/") and p not in secrets]

    def taille(liste: list[str]) -> int:
        total = 0
        for p in liste:
            try:
                total += (root / p).stat().st_size
            except OSError:
                pass
        return total

    prefixes = Counter()
    for p in artefacts:
        if p.startswith(".venv-agency/"):
            prefixes[".venv-agency/"] += 1
        elif p.startswith("tmp_packages/"):
            prefixes["tmp_packages/"] += 1
        elif p.startswith(".agentic-qe/"):
            prefixes[".agentic-qe/"] += 1
        elif p.startswith("data/"):
            prefixes["data/"] += 1
        elif p.startswith("logs/"):
            prefixes["logs/"] += 1
        elif ".egg-info/" in p:
            prefixes["*.egg-info/"] += 1
        elif "__pycache__/" in p or p.endswith((".pyc", ".pyo")):
            prefixes["__pycache__/"] += 1
        else:
            prefixes["racine/outillage"] += 1

    return {
        "fichiers_suivis": len(paths),
        "secrets": {"nombre": len(secrets), "chemins": secrets},
        "artefacts": {
            "nombre": len(artefacts),
            "octets": taille(artefacts),
            "par_prefixe": dict(sorted(prefixes.items())),
        },
        "donnees_locales": {"nombre": len(donnees), "octets": taille(donnees)},
    }


def _chemins_suivis(root: Path) -> list[str]:
    sortie = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    return [p for p in sortie.decode("utf-8", errors="surrogateescape").split("\0") if p]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", help="sortie JSON machine")
    parser.add_argument("--strict-secrets", action="store_true",
                        help="échoue si un secret est suivi par Git")
    parser.add_argument("--strict", action="store_true",
                        help="échoue aussi sur les artefacts suivis")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    rapport = inventorier(root, _chemins_suivis(root))

    if args.json:
        print(json.dumps(rapport, ensure_ascii=False, indent=2))
    else:
        print(f"Fichiers suivis : {rapport['fichiers_suivis']}")
        print(f"Secrets suivis : {rapport['secrets']['nombre']}")
        for chemin in rapport["secrets"]["chemins"]:
            print(f"  SECRET {chemin}")
        print(f"Artefacts suivis : {rapport['artefacts']['nombre']} "
              f"({rapport['artefacts']['octets']} octets)")
        for prefixe, nombre in rapport["artefacts"]["par_prefixe"].items():
            print(f"  {prefixe}: {nombre}")
        print(f"Données locales data/ : {rapport['donnees_locales']['nombre']} "
              f"({rapport['donnees_locales']['octets']} octets) — inventaire, pas purge")

    if args.strict_secrets and rapport["secrets"]["nombre"]:
        return 1
    if args.strict and (rapport["secrets"]["nombre"] or rapport["artefacts"]["nombre"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
