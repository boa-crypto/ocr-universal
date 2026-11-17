# Rapport du lot 88 — concordance acteur de l'horodatage de classification

Mesures datées `2026-11-08` par l'horloge de l'environnement
(JUnit). **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction et contrat explicite

Le GET garde le résultat comme référence. Pour ajouter `ts` depuis la dernière
trace attribuée, les cinq champs de décision doivent toujours concorder et,
désormais, **manual doit être exactement True dans trace/résultat et l'acteur
une chaîne non blanche égale au `corrected_by` stocké**. Null/vide/inexploitable
n'est pas une absence de clé. Pas normalisation silencieuse ou remontée à une
ancienne trace en cas de divergence.

Legacy **sans clé acteur** : même politique cinq champs, sans identité inventée.
Fallback sans décision : cinq champs conservés, pas acteur inféré donc pas
horodatage d'une trace attribuée. Timestamp déjà stocké non purgé/réparé : la
règle empêche un ajout/écrasement depuis une trace incompatible. Les nouvelles
chaînes PATCH87 → GET conservent leur timestamp. [Contrat](HORODATAGE_ACTEUR_CLASSIFICATION.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Horodatage/audit/attribution/action/statuts/annulation/révision/classification/cloisonnement/RBAC | 790 réussis, 1 avertissement | 23,54 s |
| Ancien GET, mêmes 35 nouveaux cas | **22 échecs attendus**, 13 réussis | 4,64 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 57,29 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **4 178 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 365,19 s |

35 nouveaux cas : 11 acteurs invalides/divergents, trois noms concordants FR/AR,
trois legacy sans acteur, une dernière trace conflictuelle, quatre manual autres
que booléen True, trois fallbacks sans décision, deux acteurs stockés absents/
null, trois gardes avant journal, quatre PATCH/GET réels et un `ts` déjà stocké.
Stores/jobs/audits réels temporaires ; traces négatives synthétiques explicites,
empreintes de résultat inchangées sur GET. Pas OCR fournisseur, navigateur réel
ou mesure de précision métier.

Témoin : seul GET précédent réinjecté en mémoire, mêmes fixtures/autres handlers.
Checkout et aperçu non remplacés. Vingt-deux échecs attendus, treize contrôles
positifs/legacy/gardes passent ; code de sortie1 attendu. Pas authenticité
attestée des données du journal.

JUnit complet : 4181 cas, 365.081 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot87 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `644f5bffaffb36e26a4c3a1edb783fb1383e2df8`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42462187363)
sur cette révision : 771 horodatage/audit/attribution/démo/action/statuts/
annulation/champs/révision/classification/valeurs/cloisonnement/RBAC,
243 qualité/Baidu, 24 ingestion/PDF, 10 UI et documentaire. Sélections se
recouvrant, pas effectifs additionnés. Pas suite OCR complète en CI ou JUnit
distant téléchargé. Ruff global et `git diff --check` réussis.
[Recette](RECETTE_LOT88.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot88/`, `horodatage.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, ancienne API et témoin.

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

**Concordance déclarative, pas signature, authenticité ou identité de révision**.
Même acteur et cinq champs peuvent désigner plusieurs opérations ; pas comparaison
complète de toutes les preuves/libellés. Pas validation universelle des types/ts,
purge du ts stocké ou migration legacy. Sans acteur, compatibilité moins stricte.
La nouvelle règle vise les traces attribuées manuelles ; l'automatique87 n'ajoute
pas d'acteur. Lecture entière/préfiltre du journal non bornés et lecture sans
transaction globale inchangés. Audit postcommit, révision processus/ABA, droits,
exports en cache et qualité non refondus.

**Aperçu backend76 maintenu** pour préserver les traitements : code77–88 poussé/
testé, non chargé avant redémarrage maîtrisé. RBAC absent de l'aperçu historique
ouvert, aucun compte/jeton/protection créé implicitement. **0 nouvel original
officiel, 0 article/code officiellement validé, aucune publication active.**
Mission réglementaire non déclarée achevée.
