# Rapport du lot 81 — révision des corrections et annulations de champs

7 novembre 2026. **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Protection livrée

PATCH champ et POST undo utilisent le snapshot et le compare/remplacement du
lot 80. Résultat modifié depuis la lecture : **409 sans écrasement, audit de
succès ou retry implicite**. Ces commits périmés ne peuvent plus effacer une
classification ou une correction plus récente. Disparition constatée lors de
la comparaison également refusée. Gardes de rôle/périmètre en amont, effets
métier hors conflit conservés. [Contrat](REVISION_CORRECTIONS_CHAMPS.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Champs/révision/classification/valeurs/annulation/attribution/cloisonnement/RBAC | 505 réussis, 1 avertissement | 9,99 s |
| Anciens handlers, mêmes 20 nouveaux cas | **10 échecs attendus**, 10 réussis | 5,62 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 61,63 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **3 901 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 368,47 s |

20 nouveaux cas : huit changements injectés après lecture (classification, même
champ, autre champ, suppression), huit gardes avant révision, deux erreurs de
sauvegarde avant écriture et deux entrelacements HTTP synchronisés par événements.
Correction/annulation suspendue, seconde correction réussie, première refusée :
seconde valeur persistée et elle seule ajoute un succès. Stores/jobs/audits
réels temporaires ; pas sommeil de hasard, précision métier, OCR fournisseur ou
charge qualifiée. L'échec injecté n'est pas une preuve d'atomicité après crash.

Témoin : corps exacts des deux anciens handlers sans décorateurs réinjectés
seulement en mémoire dans un processus distinct ; store du lot 80 conservé.
Pas rejeu complet de l'ancien stockage, checkout/aperçu non remplacés. Les dix
cas d'écriture périmée échouent ; dix refus/échecs de sauvegarde restent corrects.
Code de sortie 1 attendu.

JUnit complet : 3904 cas, 368.38 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot 80 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `26be00470e0a2f3373cce9523e17eda220061159`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42418513586)
sur cette révision : 486 champs/révision/classification/valeurs/annulation/
attribution/cloisonnement/RBAC, 243 qualité/Baidu, 24 ingestion/PDF, 10 UI et
documentaire. Sélections se recouvrant, pas effectifs additionnés. Pas suite
OCR complète en CI ou JUnit distant téléchargé. Ruff global et `git diff --check`
réussis. [Recette structurée](RECETTE_LOT81.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot81/`, `champs.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, ancienne source et témoin.

## Limites et fonctionnement

Verrou processus des participants seulement, pas autres processus, écritures
directes ou suppressions non participantes. Un pipeline/écrivain non conditionnel
peut encore sauver un état périmé plus tard. SHA de contenu avec limite ABA,
pas version monotone ou signature. Reformatage conflictuel, JSON entier et charge
non qualifiés. Un changement du seul audit n'est pas révisionné. Pas refonte
multi-niveau de l'undo ou lecture du journal exhaustivement qualifiée. Acteurs,
statuts et valeurs journalisées historiques inchangés. Audit legacy best-effort,
pas transaction, WORM ou exactly-once. Exports en cache/qualité non recalculés.

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit, sans nouvelle attribution de
leurs modifications aux présents tests.

**Aperçu backend76 maintenu** sans redémarrage pour préserver les traitements :
code77–81 poussé/testé, non chargé dans ce processus avant redémarrage maîtrisé.
RBAC non configuré dans cet aperçu historique ouvert ; aucun compte, jeton ou
protection créé implicitement. **0 nouvel original officiel, 0 article/code
ofﬁciellement validé, aucune publication active.** Mission réglementaire partielle.
