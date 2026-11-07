# Rapport du lot 74 — refus des corrections OCR sans champ

7 novembre 2026. **Livraison technique ; mission réglementaire toujours partielle,
non recevable pour production fiscale.**

## Correction livrée

Le service OCR retournait un succès, changeait la date et écrivait un audit de
correction même si aucun champ n'avait le nom demandé. Désormais, le champ
absent est refusé avant mutation, horodatage, écriture et audit de succès.
La route existante traduit `False` en **404**, `Document OCR ou champ introuvable`.
L'extraction absente garde son refus, et les gardes de rôle, dossier et
appartenance du lot 73 sont conservées.

La correction d'un champ existant reste réelle et persistée, y compris valeur
vide, chaîne `0`, français/arabe et sauts de ligne. Nom exact, première occurrence,
valeur OCR originale, confiance, anomalies, autres champs et statut global
conservés selon le comportement antérieur. [Contrat précis](CORRECTION_OCR_CHAMP_ABSENT.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Corrections/cloisonnement/rôles, dont 38 nouveaux cas | 217 réussis, 1 avertissement | 6,98 s |
| Contre-épreuve ancienne méthode, mêmes 38 nouveaux cas | **20 échecs attendus**, 18 réussis, 1 avertissement | 3,29 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 58,1 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **3 637 réussis, 2 échecs, 1 ignoré**, 1 avertissement | 361,72 s |

Les 38 nouveaux cas couvrent 14 recherches infructueuses avec écritures et audit
piégés, 2 extractions absentes, 12 corrections service, 6 refus API dans les états
extracted/validated/corrected et 4 corrections API. Cache froid/chaud, relecture
par un store neuf, empreintes JSON et audits temporaires vérifiés. Aucun moteur
OCR ni fournisseur réel appelé par ces nouveaux tests.

La contre-épreuve remplace seulement le corps exact de `correct_field` du lot 73
en mémoire, dans un autre processus de test, globals et fixtures réels conservés.
Checkout et aperçu non remplacés. Les 20 échecs sont les 14 refus service absents
et les 6 réponses API faussement réussies ; les 18 autres cas passent aussi avec
l'ancienne méthode. Pas témoin artificiellement cassé sur des opérations légitimes.

JUnit complet : 3640 cas, 361.633 s, compteurs
cohérents avec les cas ; cohérence n'est pas authenticité. Les deux échecs et
l'ignoré sont exactement ceux du lot 73 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. **Suite complète non verte**,
Indra indisponible, pas nouvelle installation simulée.

## Code, CI et preuves

Code `9b14509e6315eef649613d7d12991840fa243989`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42411808580)
sur cette révision : 217 corrections/cloisonnement/RBAC, 241 qualité/Baidu,
24 ingestion/PDF, 10 UI et documentaire. Sélections se recouvrant, pas de total
additionné ni de suite OCR complète en CI. Pas JUnit distant téléchargé.
Ruff global et `git diff --check` réussis.

Artefacts hors Git : `/home/user/recettes-unocr/lot74/`,
`corrections.{log,xml}`, `contre-epreuve.{log,xml,exit}`,
`complete/pytest.{log,xml}`, `ciblee/recette-*/`, `github-run.json`,
`empreintes.json`, source ancienne et plugin témoin.
[Recette structurée](RECETTE_LOT74.json).

## Intégrité, aperçu et limites

**26/27 empreintes historiques conformes**, même écart de référentiels que le lot 73 :
attendu `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observé `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Pas restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et fichiers exploratoires conservés hors commit, sans attribution nouvelle
de leurs modifications aux présents tests.

Aperçu redémarré avec le backend 74, port 8000. `data/rbac.json` absent :
**rôles et cloisonnement inactifs dans l'aperçu historique ouvert** ; les tests
utilisent un registre temporaire explicite. Aucun compte ou jeton créé implicitement.

Pas transaction ni garantie concurrence ; audit de succès legacy best-effort,
ni signé ni WORM, pas nouveau journal de refus dédié. Pas requalification des
anciens faux succès, historique/annulation, résolution des noms en doublon,
recalcul qualité ou invalidation du statut global de validation après correction.
Le `user` historique n'est pas une preuve d'identité authentifiée. Pas audit
exhaustif des autres routes ; politique partagée/non classée inchangée.
**0 nouvel original officiel, 0 article/code officiellement validé, aucune
publication active.** Ce lot ne clôture pas la mission réglementaire.
