# Rapport du lot 79 — reclassement automatique persistant et protégé

7 novembre 2026. **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction livrée

La route automatique renvoyait et journalisait une décision sans la sauvegarder.
Elle persiste maintenant l'objet `classification` dans le résultat avant audit
et réponse, après contrôle explicite du rôle opérateur, visibilité du job et
existence job/résultat (404). Les autres données du résultat sont conservées.

Avant appel au classifieur, refus 409 si une décision manuelle ou un marqueur
ambigu existe. Une classification absente/None ou objet dont `manual` est absent
ou vaut exactement False reste reclassable. True, null explicite dans `manual`,
chaînes, nombres (y compris 0), listes/objets et classification non objet sont
refusés. Pas paramètre force ou effacement automatique de décision humaine.
[Contrat précis](RECLASSEMENT_AUTOMATIQUE_PERSISTE.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Reclassement/lecture/classification/valeurs/annulation/attribution/cloisonnement/RBAC | 464 réussis, 1 avertissement | 9,77 s |
| Ancien handler, mêmes 29 nouveaux cas | **23 échecs attendus**, 6 réussis | 3,52 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 57,58 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **3 860 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 364,39 s |

29 nouveaux cas : neuf sauvegardes/relectures, sept marqueurs manuels/ambigus,
trois classifications non objets, quatre refus d'autorisation, deux accès
privilégiés, job/résultat absents, sauvegarde échouée avant écriture et décision
manuelle suivie d'un automatique refusé. Jobs/stores/audits temporaires réels.
**Classifieur substitué par une sortie synthétique contrôlée dans les nouveaux
tests** : mesure d'orchestration/persistance, pas précision métier ou OCR réel.
Les tests existants du classifieur sont inclus dans la sélection locale.

Témoin : corps exact de l'ancien handler, réinjecté seulement en mémoire sans
décorateur dans un autre processus, mêmes 29 cas. Checkout et aperçu non
remplacés. 23 échecs attendus de persistance/protection/sauvegarde, six contrôles
de refus restent corrects ; code de sortie 1 attendu.

JUnit complet : 3863 cas, 364.304 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot 78 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `0a633e98793a11f8eab51f9ccfba6a6f61a69371`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42416787172)
sur cette révision : 445 reclassement/lecture/classification/valeurs/annulation/
attribution/cloisonnement/RBAC, 243 qualité/Baidu, 24 ingestion/PDF, 10 UI et
documentaire. Sélections se recouvrant, pas addition des effectifs. Pas suite
OCR complète en CI ou JUnit distant téléchargé. Ruff global et `git diff --check`
réussis. [Recette structurée](RECETTE_LOT79.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot79/`, `automatique.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, ancienne source et témoin.

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires conservés hors commit sans nouvelle attribution de
leurs modifications aux présents tests.

**Aperçu backend76 maintenu**, sans redémarrage imposé pour préserver les
traitements : code77–79 poussé/testé, non chargé dans ce processus avant
redémarrage maîtrisé. `data/rbac.json` absent : rôles et cloisonnement inactifs
dans l'aperçu historique ouvert ; aucun compte/jeton/RBAC créé automatiquement.

Pas transaction/verrou : une décision concurrente reste un risque. Le `manual`
absent reste interprété historiquement automatique ; anciennes décisions
humaines seulement journalisées non reconstituées. Pas archivage intégral des
classifications remplacées, invalidation des exports en cache, recalcul qualité
global ou application de profil suggéré. Scores/règles du classifieur inchangés,
pas preuve de présence humaine ni validation juridique. Audit legacy best-effort,
pas signé/WORM ou exactly-once ; l'échec injecté ne qualifie pas les crashs.
**0 nouvel original officiel, 0 article/code officiellement validé, aucune
publication active.** Mission réglementaire non déclarée achevée.
