# Rapport du lot 82 — sélection de trace pour annulation

Mesures datées `2026-11-08` par l'horloge de l'environnement
(JUnit). **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction livrée

La recherche du journal d'annulation exige désormais un objet JSON, l'événement
exact `field_validated` et le bon job/champ. Mentions dans d'autres événements,
JSON non objets/cassés et autres cibles ne deviennent pas des corrections.
La dernière candidate exacte doit contenir les trois clés d'état antérieur
et une valeur `confirmed` ou `corrected` non None, chaîne vide comprise.

Trace dernière incomplète ou sans opération de valeur : **409 sans modification
ni audit d'annulation réussie**, pas repli silencieux vers une trace plus ancienne.
**Changement métier explicite : un statut seul après correction bloque ce chemin
d'annulation** ; pas annulation de statut ou choix historique ajoutés.
Gardes et contrôle de révision du lot 81 conservés.
[Contrat précis](SELECTION_TRACE_ANNULATION.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Annulation/champs/révision/classification/valeurs/attribution/cloisonnement/RBAC | 522 réussis, 1 avertissement | 18,8 s |
| Ancien helper, mêmes 17 nouveaux cas | **10 échecs attendus**, 7 réussis | 7,69 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 89,48 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **3 918 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 447,57 s |

17 nouveaux cas : six bruits/non-événements JSON, deux mauvaises cibles,
JSON cassé, trois clés manquantes, deux traces sans valeur, deux saisies vides
et une vraie requête de statut seul après correction. Stores/jobs/journaux
temporaires réels ; empreintes et absence d'annulation réussie sur refus.
Aucun OCR fournisseur, navigateur réel ou charge qualifiée.

Témoin : corps exact de l'ancien helper uniquement réinjecté en mémoire dans
un processus distinct, mêmes 17 cas, checkout et aperçu non remplacés.
Dix échecs attendus sur mauvaise sélection/erreurs JSON et refus manquants ;
sept autres cas passent. Code de sortie 1 attendu.

JUnit complet : 3921 cas, 447.48 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot 81 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `47677afeb8acef45c13fa4fb2e296a44b1f0db60`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42457705968)
sur cette révision : 503 annulation/champs/révision/classification/valeurs/
attribution/cloisonnement/RBAC, 243 qualité/Baidu, 24 ingestion/PDF, 10 UI et
documentaire. Sélections se recouvrant, pas effectifs additionnés. Pas suite
OCR complète en CI ou JUnit distant téléchargé. Ruff global et `git diff --check`
réussis. [Recette structurée](RECETTE_LOT82.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot82/`, `annulation.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, ancienne source et témoin.

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

Présence de clés et valeur déclarée, **pas validation complète des types,
authenticité ou correspondance à une révision du champ**. Pas restauration
exacte des quatre emplacements manuels ou pile multi-niveau. Traces legacy non
réparées/migrées ; journal seul non révisionné, lecture entière non bornée et
préfiltre littéral conservés. Audit best-effort, pas transaction, WORM ou signature.
Acteurs, statuts acceptés, valeurs journalisées, exports et qualité non refondus.

**Aperçu backend76 maintenu** pour préserver les traitements : code77–82 poussé/
testé, non chargé dans ce processus avant redémarrage maîtrisé. RBAC absent dans
l'aperçu historique ouvert, aucun compte/jeton/protection créé automatiquement.
**0 nouvel original officiel, 0 article/code officiellement validé, aucune
publication active.** Mission réglementaire non déclarée achevée.
