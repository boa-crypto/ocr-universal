#!/usr/bin/env python3
"""Recette documentaire ciblée, distincte de la suite complète et du droit validé."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = (
    "test_fixture_isolation.py", "test_backup.py", "test_corrections_routes.py",
    "test_referentiels.py", "test_referentiels_base.py", "test_rbac.py",
    "test_rbac_ecritures.py", "test_rbac_reprise.py", "test_ui_premium.py",
    "test_web_architecture_refactored.py",
)


def selectionner(racine):
    customs = sorted((racine / "tests").glob("test_customs*.py"))
    support = [racine / "tests" / nom for nom in SUPPORT]
    if not customs or any(not p.is_file() for p in support):
        raise ValueError("Sélection documentaire absente ou incomplète")
    return [p.relative_to(racine).as_posix() for p in sorted(set(customs + support))]


def executer(nom, commande, destination, environnement):
    """Pas de shell ; code réel conservé, diagnostics dans un fichier dédié."""
    journal = destination / (nom + ".log")
    print(f"Recette ciblée : {nom}", flush=True)
    with journal.open("w", encoding="utf-8") as sortie:
        try:
            resultat = subprocess.run(commande, cwd=ROOT, env=environnement,
                                      stdout=sortie, stderr=subprocess.STDOUT, check=False)
            code = resultat.returncode
        except OSError:
            sortie.write("Commande indisponible ou impossible à démarrer.\n")
            code = 127
    print(f"{nom} : code {code}, journal {journal}", flush=True)
    return {"nom": nom, "commande": commande, "code_sortie": code, "journal": journal.name}


def bilan_junit(fichier):
    try:
        racine = ET.parse(fichier).getroot()
        suites = [racine] if racine.tag == "testsuite" else list(racine.iter("testsuite"))
        if not suites or any(list(s.iter("testsuite"))[1:] for s in suites):
            raise ValueError("Suites imbriquées non prises en charge")
        comptes = {cle: sum(int(s.attrib[cle]) for s in suites)
                   for cle in ("tests", "failures", "errors", "skipped")}
        valide = comptes["tests"] > 0 and all(v >= 0 for v in comptes.values())
        valide = valide and all(comptes[c] == 0 for c in ("failures", "errors", "skipped"))
        return {"lisible": True, "selection_sans_echec_ni_ignore": valide, **comptes}
    except (OSError, ET.ParseError, KeyError, ValueError):
        return {"lisible": False, "selection_sans_echec_ni_ignore": False}


def recette(destination):
    selection = selectionner(ROOT)
    # Chaque invocation produit un sous-dossier neuf, même si deux appels ciblent
    # le même parent. Un ancien JUnit ne doit pas passer pour le résultat courant.
    destination.mkdir(parents=True, exist_ok=True)
    dossier = Path(tempfile.mkdtemp(prefix="recette-", dir=destination))
    with tempfile.TemporaryDirectory(prefix="unocr-documentaire-") as temporaire:
        environnement = os.environ.copy()
        for variable, nom in (("UNOCR_DATA_DIR", "data"), ("UNOCR_LOG_DIR", "logs"),
                              ("UNOCR_USER_PROFILES_DIR", "user_profiles")):
            environnement[variable] = str(Path(temporaire) / nom)
        commandes = (
            ("ruff", [sys.executable, "-m", "ruff", "check", "src", "tests", "scripts/customs_review_recipe.py"]),
            ("pytest", [sys.executable, "-m", "pytest", *selection, "-q",
                        "--junitxml=" + str(dossier / "pytest.xml")]),
            ("interface", ["npm.cmd" if os.name == "nt" else "npm", "run", "ui:customs-review"]),
        )
        # Les diagnostics UI sont exécutés même si pytest ou Ruff échouent, mais
        # leur succès ne peut jamais effacer l'échec d'une autre étape.
        etapes = [executer(nom, commande, dossier, environnement) for nom, commande in commandes]
    junit = bilan_junit(dossier / "pytest.xml")
    code = int(any(etape["code_sortie"] != 0 for etape in etapes) or not junit["selection_sans_echec_ni_ignore"])
    rapport = {
        "type_rapport": "recette_documentaire_ciblee_non_validation_reglementaire",
        "suite_complete_executee": False, "validation_juridique": "non_validee",
        "publication_active": False, "mission_globale": "partielle",
        "tests_selectionnes": selection, "etapes": etapes, "junit": junit, "code_sortie": code,
        "statut": "selection_reussie" if code == 0 else "selection_en_echec",
        "limites": ["Pas une exécution de la suite OCR complète.",
                    "Tests sur fixtures NON OFFICIELLES, pas homologation ou validation juridique.",
                    "JSDOM et ponts HTTP/API, pas recette de navigateurs réels ni charge nationale."],
    }
    (dossier / "recette.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Rapport ciblé : {dossier / 'recette.json'}", flush=True)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True,
                        help="dossier parent des résultats, hors des données et sources du projet")
    args = parser.parse_args(argv)
    destination = args.artifacts.expanduser().absolute()
    # Évite de produire des artefacts dans le checkout ou une de ses données.
    if destination.resolve().is_relative_to(ROOT.resolve()):
        parser.error("Les artefacts doivent être hors du dépôt")
    try:
        return recette(destination)
    except (OSError, ValueError):
        print("Recette impossible : destination ou sélection incompatible.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
