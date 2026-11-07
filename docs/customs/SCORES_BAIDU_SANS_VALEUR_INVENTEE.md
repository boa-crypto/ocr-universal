# Lot 66 — confiance Baidu absente ou invalide

7 novembre 2026. Contrat de conversion de réponse testé hors réseau, pas mesure
de précision OCR ni validation juridique des mots reconnus.

## Correction

L'adaptateur attribuait **0,95 à chaque mot**, même sans score du fournisseur.
Cette constante pouvait faire préférer Baidu à un autre moteur et éviter le
signalement de faible confiance. Elle est supprimée pour Baidu uniquement.
Les conventions du natif PDF et des autres moteurs ne sont pas modifiées ici.

Pour chaque élément de `words_result` :

| Réponse | Valeur numérique conservée | Provenance |
|---|---:|---|
| `probability.average`, nombre JSON fini entre 0 et 1 inclus | valeur déclarée, sans promotion ni normalisation | `reported` |
| champ `probability` absent | 0, repli conservateur | `missing` |
| objet/average absent ou invalide, booléen, chaîne, hors bornes, NaN/Inf | 0, repli conservateur | `invalid` |

Aucune coercition de chaîne (`"0.99"` n'est pas un score numérique), booléen,
écrêtage vers 1 ou remplacement par 0,95. Un véritable score numérique 0 ou 1
est conservé ; un score explicitement déclaré 0,95 peut donc toujours exister.
La moyenne est calculée sur **tous** les éléments retournés, y compris les zéros
conservateurs et déclarés. Une réponse vide donne une moyenne 0.

Le texte reste accessible quand seul le score manque ; cela ne devient pas une
reconnaissance certifiée. Les erreurs de transport/structure continuent à suivre
le contrat privé du lot 65, sans résultat partiel ni erreur distante réémise.

## Provenance locale de conversion

`EngineOutput.raw["confidence"]` contient uniquement :

```json
{
  "policy": "provider_average_else_zero",
  "calibrated": false,
  "reported": 0,
  "missing": 1,
  "invalid": 0
}
```

Compteurs par éléments de réponse, sans texte distant, clé ou jeton. Il s'agit de
mots/blocs tels que l'adaptateur les représente déjà : pas garantie de découpage
linguistique en mots indépendants. Le module ne réclame pas un nouveau paramètre
à l'API et ne change pas d'endpoint ; si le fournisseur n'envoie aucun score,
tous restent au repli conservateur.

**Limite du modèle existant :** la confiance d'un `Word` est numérique, pas
optionnelle. Le zéro de repli ne prouve pas une probabilité réelle nulle. Les
compteurs ci-dessus distinguent absent/invalide/déclaré dans l'`EngineOutput`,
mais son `raw` n'est **pas persisté** par le pipeline actuel. Les mots, runs et
rapports qualité persistés conservent le zéro ; ils ne distinguent donc pas un
score déclaré nul d'un score absent. Pas nouvelle UI de provenance ni évolution
globale de schéma prétendue par cette correction.

Le rapport qualité existant signale les pages sous son seuil. Un test de passage
par le pipeline vérifie qu'un mot Baidu sans score reste à zéro dans les mots,
le run et la qualité, et que sa page figure dans la liste à revoir. Cela n'est
pas une garantie d'approbation/refus administratif : la revue humaine reste une
opération distincte. Le consensus n'est pas recalibré ; les scores déclarés de
moteurs différents ne deviennent pas automatiquement comparables.

## Vérifications

**30 nouveaux cas** : cinq scores valides, 19 formes invalides, score absent,
moyenne mixte, sortie vide, comparaison avec un moteur noté, qualité et pipeline.
Le fournisseur et ses réponses sont des doubles explicitement synthétiques,
pas une reconnaissance distante réelle. Une contre-épreuve charge l'adaptateur
exact du lot 65 dans un processus séparé : **30/30 cas échouent**, code 1 attendu,
sans remplacement des fichiers sources du checkout.

```sh
.venv/bin/python -m pytest tests/test_baidu_confidence.py \
  tests/test_baidu_transport.py tests/test_baidu_ocr.py -q
```

La sélection contient 90 tests, dont les 60 existants de transport/enregistrement.
Elle est également exécutée en CI. Aucun appel réel Baidu ni usage de clés réelles.

## Limites maintenues

Un score fournisseur déclaré n'est **pas une probabilité calibrée**, une garantie
de justesse ou une validation humaine. Ce lot ne qualifie pas la présence réelle
ou la sémantique statistique du champ chez le fournisseur : l'acceptation de cette
forme ne prouve pas qu'il la renverra pour un compte donné. Pas nouveau score
appris ni évaluation terrain/FR-AR. La géométrie approximative préexistante en
absence de `location` reste inchangée et n'est pas qualifiée comme localisation
réelle. L'endpoint, les limites du transport et l'exposition résiduelle des
paramètres OAuth en query restent ceux du lot 65. Indra reste absent.
Aucun corpus officiel acquis, article/code validé ou publication activée.
