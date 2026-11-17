# Recette sans réécriture des documents suivis — lot 56

## Défaut constaté

`fixtures_dir` appelait le générateur dans `tests/fixtures` à chaque session.
Les parcours facture/BL/colisage réécrivaient aussi leurs PDF au même endroit.
ReportLab et DOCX produisent des octets variables entre générations : la suite
complète laissait huit fichiers binaires modifiés, nécessitant une restauration
explicite après vérification qu'ils étaient propres avant l'exécution.

## Correction

- `make_all(destination)` et `make_capture_images(destination)` acceptent une
  destination explicite, propagée à tous les fichiers et à `ground_truth.json`.
- La fixture pytest de session crée son corpus avec `tmp_path_factory.mktemp`,
  sans modifier les constantes de module ni l'environnement global.
- `creer_fixtures(destination)` génère les trois PDF métier dans le `tmp_path` de
  chaque test concerné (formulaire, recherche, corrections, bout en bout/reprise).
- Les deux tests Pipeline du formulaire concernés utilisent aussi `tmp_cfg`.
- Les appels manuels sans destination restent compatibles :
  `python tests/make_fixtures.py` continue de régénérer le dossier historique,
  **volontairement**. Cette commande n'est pas l'entrée utilisée par pytest.

Les documents passent toujours par les mêmes générateurs et le pipeline réel ;
aucun résultat OCR simulé, aucun saut/xfail ajouté, aucune assertion existante
supprimée. Les tests qui lisent explicitement des fichiers statiques de
`tests/fixtures` peuvent continuer à le faire : cette correction concerne les
**écritures des générateurs**, pas l'interdiction de lire le corpus suivi.

## Exécution reproductible

Depuis la racine, utiliser les dépendances de développement déjà installées :

```sh
iso=$(mktemp -d /tmp/unocr-recette-XXXXXX)
UNOCR_DATA_DIR="$iso/data" UNOCR_LOG_DIR="$iso/logs" \
  .venv/bin/python -m pytest tests/ -q --junitxml="$iso/resultats.xml"
```

Le code de sortie reste **1** dans l'environnement actuel, avec les 18 échecs OCR.
Ne pas masquer ce code pour annoncer une suite verte. Les répertoires temporaires
pytest et les fichiers JUnit sont des artefacts d'exécution, pas des données à
committer. Ne pas choisir un `--basetemp` situé dans un dossier utilisateur ou dans
le corpus suivi. Pytest gère la rétention/nettoyage de ses propres répertoires.

## Contrôle exécuté

Avant la suite complète : SHA256 des **25 fichiers suivis de `tests/fixtures`** et
de `data/reglementation/base.json` et `data/referentiels.json`. Après exécution :
**27/27 identiques**, aucune restauration et aucun changement Git des fixtures.
Les empreintes sont conservées dans [RECETTE_LOT56.json](RECETTE_LOT56.json).
Cette mesure ne prouve pas l'absence de toute écriture transitoire ou de tout effet
hors de ces chemins ; ce n'est ni un moniteur système ni un sandbox de tests.

Neuf nouveaux cas vérifient génération hors corpus, textes PDF/DOCX réellement lus,
indépendance de deux destinations, photos, parcours et compatibilité du défaut
manuel substitué vers un dossier temporaire, refus de destination invalide sans
repli. Pas de prétention de PDF/DOCX déterministes octet par octet entre générations.

Aucun changement de code de production, API, permissions, publication, interface,
cache ou mécanisme de rejeu. Aucun moteur absent installé ou annoncé disponible.
