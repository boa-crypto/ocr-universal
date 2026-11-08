# Rapport du lot 83 — statuts de PATCH alignés sur le résultat

Mesures datées `2026-11-08` par l'horloge de l'environnement
(JUnit). **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction livrée

`FieldPatch.status` utilise maintenant `Optional[FieldStatus]` plutôt qu'une
chaîne libre. Seuls les six statuts du modèle sont admis ; la valeur persistée
reste une chaîne. Statut inconnu : **422 avant accès au résultat**, sans mutation
ni audit de validation réussie. OpenAPI expose la même enum.

`detected`, `not_detected`, `ambiguous`, `invalid`, `validated`, `corrected`
restent acceptés ; variantes de casse/espaces et chaîne vide refusées, sans
normalisation silencieuse. Absence et null gardent leurs effets existants,
y compris statuts implicites de confirmation/correction et valeurs humaines
vides. [Contrat et portée](STATUTS_PATCH_CHAMPS.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Statuts/annulation/champs/révision/classification/valeurs/attribution/cloisonnement/RBAC | 580 réussis, 1 avertissement | 15,22 s |
| API antérieure, mêmes 58 nouveaux cas | **13 échecs attendus**, 45 réussis | 10,98 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 59,82 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **3 976 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 369,15 s |

58 nouveaux cas : 18 statuts reconnus avec trois corps, 27 entrées invalides,
six cas absent/null, six exports JSON réels relus comme `DocumentResult`, un
contrat OpenAPI. Stores/jobs/audits temporaires réels, empreintes/journaux
inchangés sur refus et primitives de révision piégées. Pas OCR fournisseur,
navigateur ou mesure de précision métier.

Témoin : **API exacte du lot 82 chargée en mémoire avant compilation des schémas
FastAPI/Pydantic**, nom de module et chemin de ressources conservés. Ancien
schéma et handler cohérents, pas remplacement de fonction laissant le nouveau
validateur actif. Checkout/aperçu non remplacés. Douze chaînes invalides ne sont
pas refusées avant le stockage piégé et le contrat OpenAPI échoue ; 45 autres
cas passent. Pas 13 corruptions de fichiers fabriquées : le piège arrête les
lectures des cas invalides. Code de sortie 1 attendu.

JUnit complet : 3979 cas, 369.066 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot 82 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `115f53f843d8b619355e2cc94c1cd8b87f3d59a9`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42458450997)
sur cette révision : 561 statuts/annulation/champs/révision/classification/valeurs/
attribution/cloisonnement/RBAC, 243 qualité/Baidu, 24 ingestion/PDF, 10 UI et
documentaire. Sélections se recouvrant, pas effectifs additionnés. Pas suite
OCR complète en CI ou JUnit distant téléchargé. Ruff global et `git diff --check`
réussis. [Recette structurée](RECETTE_LOT83.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot83/`, `statuts.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, ancienne API et témoin.

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

Vocabulaire validé, **pas transitions métier ou cohérence statut/valeur**.
Statuts invalides déjà stockés non migrés ; autres écrivains non globalement
validés. Le corps FastAPI peut être refusé 422 avant garde de périmètre, sans
lecture de document : pas garantie403 pour toute requête mal formée. Gardes
existantes, révision processus/ABA et limites undo inchangées. Pas nouvelle
règle no-op, acteur authentifié, audit WORM, invalidation d'exports en cache ou
recalcul qualité global. Null/absence restent les comportements legacy.

**Aperçu backend76 maintenu** pour préserver les traitements : code77–83 poussé/
testé, non chargé avant redémarrage maîtrisé. RBAC non configuré dans l'aperçu
historique ouvert, aucun compte/jeton/protection créé automatiquement.
**0 nouvel original officiel, 0 article/code officiellement validé, aucune
publication active.** Mission réglementaire non déclarée achevée.
