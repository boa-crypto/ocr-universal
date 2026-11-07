# Lanceur commun local / CI — lot 57

## Exécution locale

Installer les dépendances **sans fallback silencieux**, puis lancer :

```sh
python -m pip install -e ".[dev]"
npm ci
python scripts/customs_review_recipe.py --artifacts /chemin/hors-du-depot/recettes
```

Avec l'environnement local déjà installé, employer `.venv/bin/python`. Le dossier
parent des artefacts doit être hors du checkout (par exemple
`/home/user/recettes-unocr`). Chaque invocation crée un sous-dossier `recette-*`
neuf : `ruff.log`, `pytest.log`, `pytest.xml`, `interface.log`, `recette.json`.
Ne pas lancer la commande manuelle de régénération des fixtures suivies.

Le script utilise son propre interpréteur Python, sans shell. Il retrouve la
racine depuis son fichier, sélectionne tous les `tests/test_customs*.py` et les
dix supports explicitement listés dans `SUPPORT`. Toute absence d'un support ou
de tests douaniers refuse la sélection ; un nouveau test douanier est inclus
sans recopier une liste dans le workflow. Le script est lui-même linté.

Les trois étapes sont exécutées même si une précédente échoue, avec leurs codes
réels consignés séparément. Un succès UI ne peut pas effacer un échec Python ou
Ruff. Une commande indisponible est marquée 127. Les erreurs d'installation, elles,
restent hors du lanceur : la CI les traite comme des erreurs d'étape.

Le bilan exige également un JUnit lisible/non vide, sans échec, erreur ou test
ignoré. Ce choix strict est propre à **cette sélection**, qui inclut quatre ponts
UI/API nécessitant Node et jsdom. Il ne modifie pas les skips de la suite complète.
Aucun nombre de tests ou résultat métier attendu n'est codé en dur dans le lanceur.

Codes du lanceur : **0** sélection réussie, **1** étape ou JUnit non satisfaisant,
**2** configuration/destination incompatible. Les codes d'étape figurent dans le
JSON. Un arrêt externe ou une interruption peut laisser des artefacts partiels,
pas un bilan de succès. Les données/logs/profils utilisateur du processus de tests
sont dirigés vers un répertoire temporaire distinct, nettoyé en sortie normale.
Cela ne constitue pas un sandbox OS ni une garantie de l'absence de toute écriture.

## GitHub Actions

`.github/workflows/customs-review.yml` utilise Python 3.11, Node 20, installation
Python stricte et `npm ci`, permissions `contents:read`, limite de 15 minutes et
upload des journaux/JUnit/bilan même si le lanceur échoue. Il se déclenche sur PR,
déclenchement manuel, et push main/master/branche Arena actuelle.

Le workflow CI général existant n'est ni remplacé, ni rendu facultatif. Son test
OCR complet ne devient pas vert parce que ce job ciblé réussit. Le nouveau job
n'installe ou ne certifie pas Tesseract/Indra, ne valide pas les benchmarks, Docker,
les navigateurs réels ou la réglementation.

**Validation locale effectuée ; exécution distante non attestée au lot 57.**
Après le premier push, `gh run list` ne retourne aucun run de cette branche. La
lecture des permissions Actions renvoie HTTP 403 « Resource not accessible by
integration ». Cause de l'absence de run indéterminée ; aucune permission du dépôt
n'a été modifiée et aucune réussite Actions n'est revendiquée.
