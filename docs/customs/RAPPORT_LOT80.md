# Rapport du lot 80 — contrôle de révision des classifications

7 novembre 2026. **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Protection livrée

Les classifications automatique et manuelle lisent désormais le JSON et la
révision SHA-256 des mêmes octets. Avant écriture, la révision est comparée sous
un verrou réentrant partagé par les stores de résultats du processus ; les
`save_result` participent à ce verrou. Si le résultat a changé ou disparu,
**409 sans écrasement ni audit de classification réussie**, sans retry implicite.
Le calcul reste hors verrou ; gardes de rôle/périmètre et refus du manuel conservés.
[Contrat et portée exacte](REVISION_CLASSIFICATIONS.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Révision/classification/valeurs/annulation/attribution/cloisonnement/RBAC | 485 réussis, 1 avertissement | 10,02 s |
| Anciens handlers, mêmes 21 nouveaux cas | **5 échecs attendus**, 16 réussis | 3,25 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 58,54 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **3 881 réussis, 2 échecs, 1 ignoré**, 2 avertissement(s) | 366,84 s |

21 nouveaux cas : snapshot/remplacement, conflits de classification/champ/format/
suppression, résultat absent, deux stores concurrents (un seul gagnant), quatre
changements injectés pendant les calculs API, deux requêtes HTTP réellement
entrelacées par événements et huit gardes avant accès aux révisions.

Dans l'entrelacement HTTP, l'automatique est suspendu, le manuel réussit, puis
l'automatique reçoit 409 : décision manuelle conservée et un seul audit de succès.
Pas sommeil de hasard. Stores/jobs/audits réels temporaires ; calculs de conflit
synthétiques/interceptés, pas précision métier, OCR fournisseur ou charge.

Témoin : corps exacts des deux anciens handlers, seulement réinjectés en mémoire
sans décorateurs dans un autre processus ; **nouveau store conservé** pour isoler
l'absence d'usage de la révision. Pas rejeu complet de l'ancien stockage, checkout
et aperçu non remplacés. Les cinq cas d'écriture concurrente échouent avec les
anciens handlers ; seize autres contrôles passent. Code de sortie 1 attendu.

JUnit complet : 3884 cas, 366.754 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot 79 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Révision et CI

Code `ea1db514f71f9cfb62a02d4d316ee6fc21e95396`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42417828157)
sur cette révision : 466 révision/classification/valeurs/annulation/attribution/
cloisonnement/RBAC, 243 qualité/Baidu, 24 ingestion/PDF, 10 UI et documentaire.
Sélections se recouvrant, pas effectifs additionnés. Pas suite OCR complète en CI
ni JUnit distant téléchargé. Ruff global et `git diff --check` réussis.
[Recette structurée](RECETTE_LOT80.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot80/`, `revision.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, source ancienne et témoin.

## Limites et fonctionnement

**Protection du commit des deux classifications dans le processus**, pas
transaction globale : autres écrivains non conditionnels peuvent encore sauver
un état périmé après ce commit. Pas verrou multiprocessus/réseau ou protection
contre écritures directes ; pas monotonicité (limite ABA) ou signature. Un simple
reformatage change la révision. JSON lu intégralement, verrou global des résultats,
charge non qualifiée. Audit legacy best-effort après sauvegarde : pas transaction,
crash/exactly-once, WORM ou historique complet. JSON courant malformé/I/O non réparés.
Limites métier des lots 77–79 conservées (acteur, score manuel, exports en cache).

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires conservés hors commit sans nouvelle attribution de
leurs modifications aux présents tests.

**Aperçu backend76 maintenu** sans redémarrage pour préserver les traitements :
code77–80 poussé/testé, pas chargé dans ce processus avant redémarrage maîtrisé.
RBAC toujours non configuré dans cet aperçu historique ouvert ; aucun compte,
jeton ou protection créé automatiquement. **0 nouvel original officiel,
0 article/code officiellement validé, aucune publication active.**
Mission réglementaire non déclarée achevée.
