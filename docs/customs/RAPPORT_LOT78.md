# Rapport du lot 78 — cohérence de lecture classification/journal

7 novembre 2026. **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction livrée

Le GET ne réécrit plus l'indicateur `manual` stocké à partir d'une autre décision
journalisée. La classification stockée reste la référence, avec libellé, preuves,
alternatives et autres champs inchangés. Le journal ne peut fournir `ts` que si
les cinq champs catégorie/confiance/version/besoin de revue/manual concordent.
Une trace récente conflictuelle ne conduit pas à reprendre une ancienne date
correspondante.

Seuls les objets JSON avec `event=document_classified` exact et `job_id`
correspondant sont retenus, après le préfiltre littéral préexistant. Mentions
dans d'autres événements, valeurs JSON non objets et JSON cassé ne deviennent
pas des classifications. Le repli historique sans décision stockée reste
possible. [Contrat précis](LECTURE_CLASSIFICATION_ET_AUDIT.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Lecture/classification/valeurs/annulation/attribution/cloisonnement/RBAC | 435 réussis, 1 avertissement | 9,38 s |
| Ancien GET, mêmes 22 nouveaux cas | **12 échecs attendus**, 10 réussis | 7,99 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 62,38 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **3 831 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 371,5 s |

22 nouveaux cas sur stores/jobs/audits temporaires réels : divergences sur les
cinq champs, événements concordants ou conflictuels, bruit JSON/non-événements,
autre job, absence de trace, repli legacy et refus avant lecture du résultat.
Pas moteur OCR, fournisseur réel, navigateur ou test de charge.

Contre-épreuve : corps exact de l'ancien GET sans décorateur, réinjecté seulement
en mémoire dans un processus distinct. Checkout et aperçu non remplacés.
Douze échecs attendus sur divergences, requalification/timestamp et bruit ;
dix autres contrôles restent corrects. Code de sortie 1 attendu.

JUnit complet : 3834 cas, 371.41 s ; compteurs
cohérents, pas preuve d'authenticité. Échecs et ignoré identiques au lot 77 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal local.

## Code, CI et preuves

Code `2c1db264376964caddda8f498c47052bfd6fd2ee`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42416162318)
sur cette révision : 416 lecture/classification/valeurs/annulation/attribution/
cloisonnement/RBAC, 243 qualité/Baidu, 24 ingestion/PDF, 10 UI et documentaire.
Sélections se recouvrant, pas effectifs additionnés. Pas suite OCR complète en CI
ou JUnit distant téléchargé. Ruff global et `git diff --check` réussis.

Artefacts hors Git : `/home/user/recettes-unocr/lot78/`, `lecture.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, ancienne source et
plugin témoin. [Recette structurée](RECETTE_LOT78.json).

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires conservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

**Aperçu maintenu backend 76**, sans redémarrage imposé pour préserver les
traitements : code 77/78 poussé et testé, non chargé dans ce processus avant
redémarrage maîtrisé. `data/rbac.json` absent, rôles et cloisonnement inactifs
dans cet aperçu historique ouvert ; aucun compte/jeton/RBAC créé implicitement.

Égalité déclarative sur cinq champs, **pas identité de révision, hash de contenu,
signature ou vérification des preuves**. Deux décisions distinctes identiques
sur ces champs restent indistinguables. Pas validation stricte des types/ts du
journal, lecture bornée/streamée, archivage complet ou migration des anciennes
contradictions. Préfiltre littéral conservé, pas import JSON universel. Résultat
malformé non globalement réparé. Audit legacy best-effort, pas transaction,
concurrence ou WORM. `corrected_by` déclaratif, score manuel et autres politiques
inchangés, pas preuve de présence humaine. **0 nouvel original officiel,
0 article/code officiellement validé, aucune publication active.**
Mission réglementaire non déclarée achevée.
