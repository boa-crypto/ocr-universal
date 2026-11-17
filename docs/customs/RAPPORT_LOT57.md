# Rapport lot 57 — recette documentaire automatisable et bilan non ambigu

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

Ajout de `scripts/customs_review_recipe.py` et du workflow dédié
`customs-review.yml`. Même sélection/exécution en local et CI ; rapports distincts
pour Ruff, pytest, JSDOM et JUnit. Aucun échec effacé par l'étape suivante ; pas
succès annoncé à partir d'un JUnit absent, malformé, vide ou avec tests ignorés.

[Utilisation et limites](LANCEUR_RECETTE_CIBLEE.md),
[résultats persistants](RECETTE_LOT57.json).

## Qualification exécutée

- **18 nouveaux tests du lanceur réussis** : sélection stable, supports manquants,
  agrégation des codes, isolation, commande absente, invocations distinctes,
  destination invalide et refus de bilan JUnit insuffisant. Les simulations de
  processus servent à tester l'orchestrateur, pas à simuler des résultats OCR.
- Exécution **réelle** du lanceur : **2 043 réussis, 0 échec, 0 ignoré**, **64
  fichiers**, **48,51 s**, 1 avertissement Starlette/httpx préexistant.
- **186 scénarios UI JSDOM** réussis ; quatre ponts UI/HTTP/API et leurs 70 exports
  rejoués avec références attendues restent dans la sélection (58 simples dont
  14 PDF sur opt-in, 12 paires), ainsi que les 4 copies PDF Code.
- Ruff code 0, pytest code 0, interface code 0 ; JUnit valide et bilan global ciblé
  code 0. **27/27 empreintes de la recette 56 inchangées après le lanceur**.
  Diff-check réussi. Journaux historiques préservés hors commit.
- Copie brute des artefacts locaux conservée hors Git dans
  `/home/user/recettes-unocr/lot57` : JUnit, trois journaux, bilan du lanceur.
  Leurs chemins d'exécution d'origine peuvent mentionner `/tmp`.

## CI distante ciblée : réussite observée

Lanceur/test au commit `505481a8`. Le run initial a réussi après un délai
d'apparition ; ses annotations de dépréciation Node 20 ont été traitées. Workflow
final au commit **`f4eb0b79`** : **Ubuntu 24.04, Node 24**, actions publiées à runtime
Node 24 vérifiées (checkout v7.0.1, setup-python/node v7.1.0, upload-artifact v7.0.2).

Run final **[42370535241](https://github.com/boa-crypto/ocr-universal/actions/runs/42370535241)** :
**success**, job de **1 min 9 s**, installation stricte, recette et upload des
artefacts réussis ; `gh run watch --exit-status` code 0, état confirmé par API.
Pas annotation Node 20 sur ce run final. Les chiffres détaillés ci-dessus sont
mesurés localement, pas annoncés comme extraits du JUnit distant.

Le 403 initial concernait la lecture des permissions administratives Actions,
pas un refus d'exécuter le workflow. Aucune permission du dépôt modifiée. La
redirection de téléchargement des artefacts du premier run est bloquée par le
réseau du sandbox ; aucune relecture locale de ces artefacts distants revendiquée.
La copie locale du statut final est conservée avec les artefacts locaux.

**Suite complète non relancée pour le lot 57.** Dernière complète exécutée : lot 56,
**3 057 réussis, 18 échecs, 11 ignorés, 211,56 s**. Les 18 échecs OCR restent ouverts.
Le nouvel indicateur ciblé ne prétend pas rendre l'ensemble de la CI vert.

Aucun changement du moteur OCR, de la logique documentaire de production, des
API, permissions utilisateur, publication, interface ou cache v69.
**Mission réglementaire partielle : 0 nouvel original officiel acquis,
0 article/code national officiellement validé, 0 publication active.**
