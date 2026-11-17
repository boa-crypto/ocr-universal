# Rapport du lot 73 — cloisonnement des routes OCR de dossiers

7 novembre 2026. **Livraison technique ; mission douanière toujours partielle,
non recevable pour production fiscale.**

## Changements livrés

Les sept routes OCR de dossiers contrôlent le rôle et la visibilité du dossier
avant le service d'intégration. Lecture, mise à jour, validation et correction
vérifient l'appartenance de l'extraction. Une extraction étrangère ne peut plus
être validée/corrigée sous un dossier visible : 403, sans mutation ni valeur renvoyée.
Les dossiers invisibles sont refusés avant chargement du singleton.

À la création, cohérence corps/chemin, contrôle du job source, stores de l'API
corrects et résultat déjà autorisé transmis au service. Le service ne relit pas
ce résultat dans une autre configuration. Deux factories de date OCR invalides
sont corrigées pour permettre la construction réelle des modèles.
Les anciens appels internes restent compatibles.

[Contrat et limites détaillés](CLOISONNEMENT_OCR_DOSSIERS.md).

## Recette mesurée

| Sélection | Résultat | Durée console |
|---|---|---:|
| Cloisonnement/rôles, dont 59 nouveaux cas | 179 réussis, 1 avertissement | 4,42 s |
| Contre-épreuve : six anciens handlers | **10 échecs attendus**, 35 réussis, 14 désélectionnés | 7,15 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 60,68 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Suite complète locale | **3 599 réussis, 2 échecs, 1 ignoré**, 1 avertissement | 357,52 s |

JUnit complet : 3602 cas, 357.426 s ; compteurs
cohérents avec les cas. La cohérence du rapport ne prouve pas son authenticité.
Les échecs demeurent exactement ceux du lot 72 :
`tests.test_indra_ocr::test_indra_engine_availability` et
`tests.test_ocr::test_selection_prefers_native_when_present`.
Ignoré : `tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
pas une suite complète verte.

La contre-épreuve charge les corps exacts des six anciens handlers sans leurs
décorateurs, uniquement en mémoire dans le processus de test. Checkout et aperçu
non remplacés ; audits du témoin dirigés vers les stores temporaires. Les dix
échecs sont les six accès à dossier caché et quatre validations/corrections
hors association. La création ancienne utilisait un store incompatible : elle
est **exclue du témoin**, ainsi que factories et argument interne nouveaux.
Leurs tests positifs supplémentaires passent dans le nouveau chemin ; cette
contre-épreuve ne mesure pas une exploitation ancienne de la création.

## CI et révisions

Code : `e34e3df47a415b44584aa2e8d2275817e60725e0`, puis test de mode ouvert
`2999aaf50d8ce0a0c48c38d697ecb834175568cc`. [GitHub Actions ciblé réussi](https://github.com/boa-crypto/ocr-universal/actions/runs/42411082360)
sur cette dernière révision : 179 cloisonnement/RBAC, 241 qualité/Baidu,
24 ingestion/PDF, 10 UI et documentaire. Les sélections se recouvrent ; ne pas
additionner leurs effectifs. Pas de suite OCR complète en CI ni téléchargement
du JUnit distant.

Ruff global et `git diff --check` réussis. Artefacts locaux :
`/home/user/recettes-unocr/lot73/` : `cloisonnement.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json` et témoin.
[Recette structurée](RECETTE_LOT73.json).

## Intégrité et fonctionnement conservé

**26/27 empreintes historiques conformes**, même écart depuis le lot 64 :
`data/referentiels.json`, attendu
`b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observé `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, quatre dossiers suivis
modifiés, journaux et fichiers exploratoires non suivis conservés hors commit.

Aperçu redémarré avec le backend 73 sur le port 8000. `data/rbac.json` absent :
**rôles et cloisonnement inactifs dans cet aperçu historique ouvert**. La
livraison ne crée ni comptes, ni jetons, ni configuration de protection implicite.
Les tests de protection utilisent une configuration temporaire explicite.

Pas audit exhaustif, transaction ni garantie de concurrence. Politique des jobs
partagés/non classés et administrateur/jeton global inchangée. Les refus par gardes
existantes restent audités ; pas nouvelle trace dédiée au refus d'appartenance.
Le `user` historique de correction/validation n'est pas une preuve d'identité.
Pas refonte du recalcul qualité après édition. Les opérations de création testées
convertissent des résultats synthétiques persistés, sans OCR fournisseur réel.
**0 nouvel original officiel, 0 article/code officiellement validé, aucune
publication active**. La mission réglementaire n'est pas déclarée terminée.
