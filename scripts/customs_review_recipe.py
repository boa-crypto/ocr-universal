#!/usr/bin/env python3
"""Recette documentaire ciblée, distincte de la suite complète et du droit validé."""
import argparse
import json
import os
import re
import stat
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


MAX_JUNIT = 32 * 1024 * 1024
COMPTEURS_JUNIT = ("tests", "failures", "errors", "skipped")


def _entier_junit(valeur):
    if not isinstance(valeur,str) or re.fullmatch(r"[0-9]{1,9}",valeur) is None:
        raise ValueError("Compteur décimal ASCII requis")
    return int(valeur)


def _racine_junit(fichier):
    if fichier.is_symlink():
        raise ValueError("Lien symbolique refusé")
    flags = os.O_RDONLY | getattr(os,"O_NOFOLLOW",0) | getattr(os,"O_NONBLOCK",0)
    with os.fdopen(os.open(fichier,flags),"rb") as entree:
        infos = os.fstat(entree.fileno())
        if not stat.S_ISREG(infos.st_mode) or infos.st_size > MAX_JUNIT:
            raise ValueError("JUnit non régulier ou trop volumineux")
        contenu = entree.read(MAX_JUNIT+1)
    contenu.decode("utf-8")
    if not contenu or len(contenu)>MAX_JUNIT or b"\x00" in contenu or b"<!DOCTYPE" in contenu or b"<!ENTITY" in contenu:
        raise ValueError("JUnit vide, trop volumineux ou DTD interdit")
    # Contrôle de profondeur pendant l'analyse, avant de construire une arborescence
    # arbitrairement profonde. Pas validation XSD ni bac à sable OS.
    analyseur = ET.XMLPullParser(events=("start","end"))
    racine, profondeur = None,0
    for debut in range(0,len(contenu),4096):
        analyseur.feed(contenu[debut:debut+4096])
        for evenement,element in analyseur.read_events():
            if evenement == "start":
                profondeur += 1
                if profondeur > 16:
                    raise ValueError("JUnit trop profond")
                if racine is None:
                    racine = element
            else:
                profondeur -= 1
    analyseur.close()
    return racine


def _metadata_junit(element):
    if element.tag == "properties":
        if any(p.tag != "property" or len(p) for p in element):
            raise ValueError("Propriétés JUnit incompatibles")
    elif len(element):
        raise ValueError("Contenu imbriqué incompatible")


def bilan_junit(fichier):
    try:
        racine = _racine_junit(fichier)
        if racine.tag not in {"testsuite","testsuites"}:
            raise ValueError("Racine JUnit incompatible")
        suites = [racine] if racine.tag == "testsuite" else list(racine)
        if not suites or any(s.tag != "testsuite" for s in suites) or list(racine.iter("testsuite")) != suites:
            raise ValueError("Suites absentes, imbriquées ou masquées")
        comptes = dict.fromkeys(COMPTEURS_JUNIT,0)
        for suite in suites:
            declares = {c:_entier_junit(suite.attrib[c]) for c in COMPTEURS_JUNIT}
            mesures = dict.fromkeys(COMPTEURS_JUNIT,0)
            if any(e.tag not in {"testcase","properties","system-out","system-err"} for e in suite):
                raise ValueError("Enfant de suite incompatible")
            for element in suite:
                if element.tag != "testcase":
                    _metadata_junit(element)
            cas = list(suite.findall("testcase"))
            if list(suite.iter("testcase")) != cas:
                raise ValueError("Cas imbriqués ou masqués")
            mesures["tests"] = len(cas)
            for cas_test in cas:
                if any(e.tag not in {"failure","error","skipped","properties","system-out","system-err"} for e in cas_test):
                    raise ValueError("Statut de cas incompatible")
                for element in cas_test:
                    _metadata_junit(element)
                statuts = [e.tag for e in cas_test if e.tag in {"failure","error","skipped"}]
                if len(statuts)>1:
                    raise ValueError("Statuts de cas contradictoires")
                if statuts:
                    mesures[{"failure":"failures","error":"errors","skipped":"skipped"}[statuts[0]]] += 1
            if declares != mesures:
                raise ValueError("Compteurs de suite différents des cas réels")
            for cle in comptes:
                comptes[cle] += mesures[cle]
        if racine.tag == "testsuites" and any(_entier_junit(racine.attrib[c]) != comptes[c] for c in COMPTEURS_JUNIT if c in racine.attrib):
            raise ValueError("Compteurs globaux différents des suites")
        valide = comptes["tests"]>0 and all(comptes[c]==0 for c in ("failures","errors","skipped"))
        return {"lisible":True,"compteurs_coherents_avec_cas":True,
                "selection_sans_echec_ni_ignore":valide,**comptes}
    except (OSError, ET.ParseError, KeyError, ValueError):
        return {"lisible":False,"compteurs_coherents_avec_cas":False,"selection_sans_echec_ni_ignore":False}


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
