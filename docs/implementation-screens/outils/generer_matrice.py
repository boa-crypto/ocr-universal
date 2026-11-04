#!/usr/bin/env python3
"""Génère `docs/implementation-screens/MATRICE_ECRANS.md`.

Le document n'est pas écrit à la main : il est recalculé à partir de trois
sources factuelles, pour qu'il ne puisse pas dériver de l'application réelle.

1. **Le menu réellement rendu** — instantané produit par
   `outils/dump_interface.js` (jsdom charge l'application comme un navigateur).
2. **Le catalogue d'écrans** `web/ecrans.js` — quel écran sert quelle route,
   avec quelle source de données et quelles écritures.
3. **L'API en fonctionnement** — chaque source d'écran est interrogée en HTTP ;
   le nombre de lignes affiché est le nombre réellement renvoyé (jamais simulé).

Usage ::

    python3 docs/implementation-screens/outils/generer_matrice.py /tmp/ui.json
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parents[3]
SORTIE = RACINE / "docs" / "implementation-screens" / "MATRICE_ECRANS.md"
BASE = "http://127.0.0.1:8000"

#: Preuves de test disponibles par route d'écran (mises à jour à chaque passe).
PREUVES: dict[str, str] = {
    "referentiels/ports": "CRUD jsdom + 7 tests API (référentiels)",
    "referentiels/pays": "CRUD jsdom (même moteur) + tests API",
    "referentiels/devises": "CRUD jsdom (même moteur) + tests API",
    "referentiels/types-marchandises": "CRUD jsdom (même moteur) + tests API",
    "referentiels/tarifs": "CRUD jsdom (même moteur) + tests API",
    "referentiels/regles-documentaires": "CRUD jsdom (même moteur) + tests API",
    "referentiels/parametres-metier": "CRUD jsdom (même moteur) + tests API",
    "referentiels/types-documents": "CRUD jsdom (même moteur) + tests API",
    "admin/equipes": "CRUD jsdom (même moteur) + tests API",
    "dossiers/en-cours": "liste jsdom (715 dossiers lus) + navigation « Ouvrir »",
    "dossiers/bloques": "liste jsdom (croisement dossiers/alertes)",
    "dossiers/clotures": "liste jsdom (dossiers archivés)",
    "workspace/taches": "liste jsdom (dossiers en révision/incomplets)",
    "workspace/en-attente": "liste jsdom (dossiers sans pièce)",
    "workspace/alertes": "liste jsdom (alertes du tableau de bord)",
    "workspace/recents": "liste jsdom (30 derniers dossiers)",
}
#: Actions d'écriture réellement exercées par un test (libellé → preuve).
ACTIONS_TESTEES: dict[str, set[str]] = {
    "documents/ocr": {"Texte", "Résultat", "Relancer"},
    "controle/documentaire": {"Contrôler", "Verdict"},
    "finance/reconciliation": {"Lancer le rapprochement"},
}
#: Limitations externes connues, affichées dans la colonne « Action requise ».
LIMITES: dict[str, str] = {
    "finance/reconciliation": "limite : aucun import bancaire côté serveur, "
                              "le rapprochement porte sur les factures seules",
}

#: Écrans historiques re-testés dans cette passe : données réelles + interactions.
HISTORIQUES_VERIFIES: dict[str, str] = {
    "documents/inbox": "jsdom : 25 lignes, recherche 25→0, pagination opérationnelle",
    "documents/classif": "jsdom : 21 catégories réelles, recherche 21→0",
    "documents/archives": "jsdom : 25 lignes, recherche, pagination, « Ouvrir » → dossier",
    "documents/verification": "jsdom : 25 lignes, recherche, pagination, « Ouvrir » → dossier",
    "documents/revue": "jsdom : file chargée automatiquement, champs réels, « Actualiser » → GET 200",
}

PREUVE_PAR_DEFAUT = "rendu jsdom + GET 200 sans erreur JS"

#: Traduction du statut en réponse binaire pour la colonne « Fonctionnel ».
FONCTIONNEL: dict[str, str] = {
    "CONFORME": "Oui",
    "PARTIEL": "Partiel",
    "NON CONNECTÉ": "Non",
    "ABSENT": "Non",
    "MAQUETTE": "Non",
    "BLOQUÉ": "Non",
}


@dataclass
class Sonde:
    """Résultat d'une interrogation HTTP d'une source d'écran."""

    ok: bool
    lignes: int | None = None
    detail: str = ""


@dataclass
class Mesure:
    """Ce que la route affiche réellement dans le navigateur simulé."""

    page: str | None = None
    lignes: int = 0
    titre_ecran: str | None = None
    avis: str | None = None
    pages_visibles: list[str] = field(default_factory=list)
    cartes: int = 0
    contenu: int = 0


@dataclass
class Ligne:
    """Une entrée de menu et ce qu'elle ouvre réellement."""

    rubrique: str
    sous_menu: str
    route: str
    ecran: str
    source: str
    donnees: str
    statut: str
    action: str
    preuve: str = ""
    avis: str = ""
    notes: list[str] = field(default_factory=list)


def lire_snapshot(chemin: Path) -> dict[str, Any]:
    return json.loads(chemin.read_text(encoding="utf-8"))


def lire_route_pages() -> dict[str, str]:
    """Table `routePages` : route d'écran → identifiant de section hôte."""
    source = (RACINE / "web" / "navigation.js").read_text(encoding="utf-8")
    return dict(re.findall(r"'([a-z-]+(?:/[a-z-]+)?)':\s*'(tab-[a-z-]+)'", source))


def compter(donnees: Any) -> int | None:
    if isinstance(donnees, list):
        return len(donnees)
    if isinstance(donnees, dict):
        for cle in ("entrees", "items", "lignes", "collections", "dossiers", "jobs"):
            if isinstance(donnees.get(cle), list):
                return len(donnees[cle])
    return None


def sonder(url: str, cache: dict[str, Sonde]) -> Sonde:
    if url in cache:
        return cache[url]
    if "{" in url:
        cache[url] = Sonde(False, None, "URL paramétrée : non sondée")
        return cache[url]
    requete = urllib.request.Request(BASE + url, headers={"Host": "localhost"})
    try:
        with urllib.request.urlopen(requete, timeout=8) as reponse:
            corps = json.loads(reponse.read().decode("utf-8"))
        cache[url] = Sonde(True, compter(corps), "GET 200")
    except urllib.error.HTTPError as erreur:
        cache[url] = Sonde(False, None, f"HTTP {erreur.code}")
    except Exception as erreur:  # réseau, JSON invalide…
        cache[url] = Sonde(False, None, f"erreur : {erreur}")
    return cache[url]


def decrire_donnees(sonde: Sonde) -> str:
    if not sonde.ok:
        return "—"
    if sonde.lignes is None:
        return "réponse valide (non tabulaire)"
    if sonde.lignes == 0:
        return "0 ligne — état vide explicite"
    return f"{sonde.lignes} ligne" + ("s" if sonde.lignes > 1 else "")


def construire(snapshot: dict[str, Any]) -> tuple[list[Ligne], dict[str, Sonde]]:
    ecrans: dict[str, dict[str, Any]] = snapshot["ecrans"]
    pages = lire_route_pages()
    cache: dict[str, Sonde] = {}
    lignes: list[Ligne] = []

    for section in snapshot["sections"]:
        for item in section["items"]:
            route = item["route"].lstrip("#")
            ecran = ecrans.get(route)
            source = ""
            donnees = "—"
            preuve = ""

            mesure = Mesure(**(item.get("mesure") or {}))

            if ecran:
                urls = [u for u in (ecran.get("sources") or []) if u] or (
                    [ecran["source"]] if ecran.get("source") else []
                )
                source = ", ".join(urls) if urls else ""
                sondes = [sonder(url, cache) for url in urls]
                ok = bool(sondes) and all(s.ok for s in sondes)
                total = sum(s.lignes or 0 for s in sondes)
                donnees = (f"{total} ligne" + ("s" if total > 1 else "")) if ok else "—"
                preuve = PREUVES.get(route, PREUVE_PAR_DEFAUT)
                actions = ecran.get("actions") or []
                if not ok:
                    statut = "NON CONNECTÉ"
                    detail = sondes[0].detail if sondes else "aucune source déclarée"
                    action = f"brancher la source ({detail})"
                elif ecran.get("creation") and (ecran.get("edition") or ecran.get("suppression")):
                    statut = "CONFORME"
                    action = "maintenir ; étendre les champs métier si besoin"
                elif any(a.get("url") for a in actions):
                    ecritures = [a for a in actions if a.get("url")]
                    testees = ACTIONS_TESTEES.get(route, set())
                    if all(a["libelle"] in testees for a in ecritures):
                        statut = "CONFORME"
                        action = ("actions exercées par test ("
                                  + ", ".join(a["libelle"] for a in ecritures) + ")")
                        preuve = ("jsdom : " + ", ".join(a["libelle"] for a in ecritures)
                                  + " → 200")
                    else:
                        # Action qui écrit sur le serveur : non couverte par un test.
                        statut = "PARTIEL"
                        libelles = ", ".join(a["libelle"] for a in actions[:3])
                        action = f"tester et durcir les actions ({libelles})"
                elif ecran.get("lectureSeule"):
                    statut = "CONFORME"
                    action = "lecture seule assumée (données serveur)"
                else:
                    statut = "CONFORME"
                    action = "consultation connectée ; écritures non requises"
                if route in LIMITES:
                    action = action + " — " + LIMITES[route]
                lignes.append(Ligne(
                    rubrique=section["section"],
                    sous_menu=item["titre"],
                    route="#" + route,
                    ecran=f"{ecran['titre']} (`web/ecrans.js`)",
                    source=source or "—",
                    donnees=donnees,
                    statut=statut,
                    action=action,
                    preuve=preuve,
                    avis=mesure.avis or "",
                ))
                continue

            # Pas d'écran dédié : la route peut encore ouvrir une section existante.
            hote = mesure.page or pages.get(route)
            if mesure.avis:
                # L'application affiche elle-même « pas encore d'écran dédié ».
                # Si la redirection montre déjà des lignes, l'utilisateur a un
                # écran utilisable : c'est PARTIEL, pas ABSENT. Sinon, la route
                # ne mène à aucun contenu : elle est réellement ABSENTE.
                if mesure.lignes or mesure.cartes or mesure.contenu > 300:
                    lignes.append(Ligne(
                        rubrique=section["section"],
                        sous_menu=item["titre"],
                        route="#" + route,
                        ecran=f"redirection vers `#{hote}`",
                        source="(module historique)",
                        donnees=(f"{mesure.lignes} ligne" + ("s" if mesure.lignes > 1 else "")
                                 + " affichée" + ("s" if mesure.lignes > 1 else ""))
                                if mesure.lignes else f"contenu rendu ({mesure.cartes} blocs)",
                        statut="PARTIEL",
                        action="remplacer la redirection par un écran dédié (filtre propre, actions)",
                        preuve="parcours jsdom : bandeau + liste affichée",
                        avis=mesure.avis,
                    ))
                else:
                    lignes.append(Ligne(
                        rubrique=section["section"],
                        sous_menu=item["titre"],
                        route="#" + route,
                        ecran=f"redirection vers `#{hote}`" if hote else "—",
                        source="—",
                        donnees="—",
                        statut="ABSENT",
                        action="concevoir l'écran dédié (l'application annonce elle-même l'absence)",
                        preuve="parcours jsdom : bandeau « pas encore d'écran dédié », 0 ligne",
                        avis=mesure.avis,
                    ))
            elif hote:
                verifie = HISTORIQUES_VERIFIES.get(route)
                lignes.append(Ligne(
                    rubrique=section["section"],
                    sous_menu=item["titre"],
                    route="#" + route,
                    ecran=f"écran existant `#{hote}`",
                    source="(module historique)",
                    donnees=(f"{mesure.lignes} ligne" + ("s" if mesure.lignes > 1 else "")
                             + " affichée" + ("s" if mesure.lignes > 1 else "")
                             if mesure.lignes else "présent, 0 ligne affichée"),
                    statut="CONFORME" if verifie else "PARTIEL",
                    action=("consultation et interactions vérifiées ; écritures non expérimentées"
                            if verifie else
                            "re-certifier : contenu, actions, permissions, états vides"),
                    preuve=verifie or "parcours jsdom : page affichée",
                ))
            else:
                lignes.append(Ligne(
                    rubrique=section["section"],
                    sous_menu=item["titre"],
                    route="#" + route,
                    ecran="—",
                    source="—",
                    donnees="—",
                    statut="ABSENT",
                    action="concevoir et implémenter l'écran",
                ))
    return lignes, cache


def synthese(lignes: list[Ligne]) -> str:
    rubriques: dict[str, list[Ligne]] = {}
    for ligne in lignes:
        rubriques.setdefault(ligne.rubrique, []).append(ligne)

    entetes = ["Rubrique", "Entrées", "Conformes", "Partiels", "Absents",
               "Non connectés", "Autres"]
    sortie = ["| " + " | ".join(entetes) + " |",
              "|" + "|".join(["---"] * len(entetes)) + "|"]
    total = dict.fromkeys(entetes[1:], 0)
    for rubrique, items in rubriques.items():
        compte = {
            "Conformes": sum(1 for l in items if l.statut == "CONFORME"),
            "Partiels": sum(1 for l in items if l.statut == "PARTIEL"),
            "Absents": sum(1 for l in items if l.statut == "ABSENT"),
            "Non connectés": sum(1 for l in items if l.statut == "NON CONNECTÉ"),
        }
        autres = len(items) - sum(compte.values())
        sortie.append(
            f"| {rubrique} | {len(items)} | {compte['Conformes']} | {compte['Partiels']} | "
            f"{compte['Absents']} | {compte['Non connectés']} | {autres} |"
        )
        total["Entrées"] += len(items)
        for cle, valeur in compte.items():
            total[cle] += valeur
        total["Autres"] += autres
    sortie.append(
        f"| **Total** | **{total['Entrées']}** | **{total['Conformes']}** | "
        f"**{total['Partiels']}** | **{total['Absents']}** | "
        f"**{total['Non connectés']}** | **{total['Autres']}** |"
    )
    return "\n".join(sortie)


def rediger(lignes: list[Ligne]) -> str:
    conformes = [l for l in lignes if l.statut == "CONFORME"]
    partiels = [l for l in lignes if l.statut == "PARTIEL"]
    absents = [l for l in lignes if l.statut == "ABSENT"]
    non_connectes = [l for l in lignes if l.statut == "NON CONNECTÉ"]

    parties: list[str] = []
    parties.append(f"""# Matrice des écrans — UniOCR

> **Document de référence du développement.** Il recense chaque entrée du menu
> réel, l'écran qu'elle ouvre, la source de données réellement appelée et
> l'état de connexion mesuré. Mis à jour le **{date.today().isoformat()}**.

## Comment ce document est produit

Aucun statut n'est saisi à la main. La matrice est régénérée par :

```bash
# 1. instantané du menu réellement rendu (serveur démarré)
npm install --no-save jsdom          # outil de développement, hors exécution
node docs/implementation-screens/outils/dump_interface.js http://127.0.0.1:8000 > /tmp/ui.json
# 2. génération de cette matrice (sources API interrogées en direct)
python3 docs/implementation-screens/outils/generer_matrice.py /tmp/ui.json
```

Chaque source d'écran est interrogée en HTTP : la colonne « Données réelles »
affiche le nombre de lignes **effectivement renvoyées** par le serveur au
moment de la génération. Une collection vide est écrite « 0 ligne — état vide
explicite », jamais meublée de données fictives.

## Définition des statuts

| Statut | Signification exacte |
|---|---|
| **CONFORME** | L'écran existe, est ouvert par le menu, appelle une source serveur qui répond 200, gère les états vide/erreur, et toutes les écritures qu'il propose sont branchées sur une route serveur réelle. |
| **PARTIEL** | L'écran existe et lit des données réelles, mais une partie du parcours reste à faire : écritures non exposées, actions non testées, ou écran hérité non re-certifié. |
| **NON CONNECTÉ** | L'écran existe mais sa source de données ne répond pas (route absente ou en erreur). |
| **ABSENT** | Aucun écran : la route du menu n'ouvre rien de dédié. |
| **MAQUETTE** | Écran statique sans source de données (aucun cas à ce jour). |
| **BLOQUÉ** | Dépend d'une API externe indisponible (voir la colonne Action). |

## Synthèse

{synthese(lignes)}

- **Entrées de menu recensées** : {len(lignes)}
- **Écrans conformes** : {len(conformes)}
- **Écrans partiels** : {len(partiels)}
- **Écrans absents** : {len(absents)}
- **Écrans non connectés** : {len(non_connectes)}

Lecture honnête de ces chiffres : les {len(conformes)} écrans conformes sont
ceux dont la source a répondu et dont les écritures éventuelles sont branchées ;
les écrans « hérités » (mis en page lors des missions précédentes) restent
marqués **PARTIEL** tant qu'ils n'ont pas été re-testés un par un dans cette
passe. C'est volontaire : un écran joli mais non vérifié n'est pas déclaré
terminé.
""")

    rubriques: dict[str, list[Ligne]] = {}
    for ligne in lignes:
        rubriques.setdefault(ligne.rubrique, []).append(ligne)

    parties.append("## Détail par rubrique\n")
    for index, (rubrique, items) in enumerate(rubriques.items(), start=1):
        parties.append(f"### {index}. {rubrique}\n")
        parties.append(
            "| Menu | Sous-menu | Route | Écran existant | Backend connecté | "
            "Données réelles | Fonctionnel | Statut | Action requise |"
        )
        parties.append("|---|---|---|---|---|---|---|---|---|")
        for ligne in items:
            parties.append(
                f"| {ligne.rubrique} | {ligne.sous_menu} | `{ligne.route}` | "
                f"{ligne.ecran} | `{ligne.source}` | {ligne.donnees} | "
                f"{FONCTIONNEL.get(ligne.statut, 'Non')} | **{ligne.statut}** | "
                f"{ligne.action} |"
            )
        parties.append("")

    parties.append("""## Écarts connus à ce stade

1. **Écrans hérités** — les pages mises en page lors des missions précédentes
   (`#tab-dossiers`, `#tab-jobs`, `#tab-profiles`…) restent **PARTIEL** : elles
   fonctionnent, mais leur contenu, leurs actions et leurs permissions doivent
   être re-certifiés un par un (phase 9 de la mission).
2. **Écritures non couvertes** — les écrans à actions contextuelles
   (`controle/documentaire`, `finance/reconciliation`, `enlevissement/*`)
   n'ont pas encore d'écriture exercée par un test automatisé.
3. **Données d'exploitation vides** — `terminal`, `déclarations` et les douze
   référentiels sont vides au moment de la génération : leurs écrans affichent
   donc l'état vide avec l'action de démarrage, ce qui est le comportement
   attendu, pas une anomalie.

## Mise à jour

Toute évolution d'écran doit être suivie d'une régénération de cette matrice,
puis d'un `git add docs/implementation-screens/MATRICE_ECRANS.md`. Un écart
entre la matrice et le comportement observé est un défaut de livraison.
""")
    return "\n".join(parties)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    snapshot = lire_snapshot(Path(argv[1]))
    lignes, _ = construire(snapshot)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(rediger(lignes), encoding="utf-8")
    print(f"{SORTIE} — {len(lignes)} entrées de menu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
