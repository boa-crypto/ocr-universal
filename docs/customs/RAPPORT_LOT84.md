# Rapport du lot 84 — action de champ requise au PATCH

Mesures datées `2026-11-08` par l'horloge de l'environnement
(JUnit). **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction et contrat explicite

Un corps vide, seulement `user`/`reason` ou trois actions null pouvait produire
un audit de validation et bloquer l'undo au lot 82. Après les gardes de rôle et
visibilité, le PATCH exige désormais une valeur non None parmi confirmation,
correction et statut. Sinon **422 avant lecture/écriture du résultat, sans
`field_validated`**. Une requête refusée ne remplace plus la trace légitime de
correction utilisée pour annuler.

Valeurs `""`/`"0"`, statuts seuls reconnus et reconfirmation explicite identique
restent acceptés. **Action fournie, pas différence sémantique calculée**.
Absence/null de statut avec valeur explicite reste accepté ; sans autre action,
désormais refusé. Deux cas de tests 83 actualisés pour ce nouveau contrat,
**pas maintien revendiqué de l'ancien succès sans action**.
[Contrat détaillé](PATCH_CHAMP_ACTION_REQUISE.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Action/statuts/annulation/champs/révision/classification/attribution/cloisonnement/RBAC | 608 réussis, 1 avertissement | 13,24 s |
| Ancien PATCH, mêmes 28 nouveaux cas | **13 échecs attendus**, 15 réussis | 9,43 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 58,95 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **4 004 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 372,43 s |

28 nouveaux cas : sept corps sans action, six chaînes correction/refus/undo,
quatre valeurs vides/zéro, six statuts seuls, quatre gardes d'accès et une double
reconfirmation identique. Stores/jobs/audits temporaires réels, empreintes et
journal de l'opérateur inchangés sur les refus testés. Pas OCR fournisseur,
navigateur réel ou mesure de précision métier.

Témoin : corps exact du PATCH précédent, sans décorateur, uniquement réinjecté
en mémoire dans un processus distinct ; schéma et fixtures conservés. Checkout
et aperçu non remplacés. Treize refus manquants échouent ; quinze cas valides
ou de droits restent corrects. Code de sortie 1 attendu.

JUnit complet : 4007 cas, 372.336 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot 83 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `ac7d44a2997773de5b4e755a8c50676b5efa1130`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42459208060)
sur cette révision : 589 action/statuts/annulation/champs/révision/classification/
valeurs/attribution/cloisonnement/RBAC, 243 qualité/Baidu, 24 ingestion/PDF,
10 UI et documentaire. Sélections se recouvrant, pas effectifs additionnés.
Pas suite OCR complète en CI ou JUnit distant téléchargé. Ruff global et
`git diff --check` réussis. [Recette structurée](RECETTE_LOT84.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot84/`, `sans-action.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, ancienne API et témoin.

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

Pas idempotence de confirmation, commentaire autonome, identité authentifiée,
transitions métier ou refonte d'undo. Le statut seul reste une action et bloque
l'undo de valeur selon le lot 82. Null ne devient pas effacement. Sans action,
422 précède recherche du résultat/champ mais suit les gardes d'accès ; validation
Pydantic garde son ordre propre. Audits de sécurité middleware possibles sur
refus, pas journal global universellement inchangé. Anciennes traces sans action
non réparées. Limites de révision processus/ABA, acteurs/audit legacy, exports en
cache et qualité inchangées.

**Aperçu backend76 maintenu** pour préserver les traitements : code77–84 poussé/
testé, non chargé avant redémarrage maîtrisé. RBAC absent de l'aperçu historique
ouvert, aucun compte/jeton/protection créé implicitement. **0 nouvel original
officiel, 0 article/code officiellement validé, aucune publication active.**
Mission réglementaire non déclarée achevée.
