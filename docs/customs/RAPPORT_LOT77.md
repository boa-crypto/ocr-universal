# Rapport du lot 77 — persistance de classification manuelle

7 novembre 2026. **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Défaut corrigé

La route de classification manuelle renvoyait et journalisait une catégorie,
mais ne l'enregistrait pas dans le résultat. Le GET privilégiait alors l'ancienne
classification stockée, susceptible d'être affichée avec l'indication manuelle
du seul journal. La décision est maintenant persistée dans `result.json` avant
l'audit de succès et la réponse.

Rôle opérateur explicite et visibilité avant lecture ; job absent 404, résultat
absent 409, catégorie invalide 422. Le résultat est conservé hors de l'objet
`classification`. Relecture par un store neuf, validation `DocumentResult`
et GET cohérents avec la décision renvoyée.
[Contrat et limites](CLASSIFICATION_MANUELLE_PERSISTEE.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Classification/valeurs/annulation/attribution/cloisonnement/RBAC | 413 réussis, 1 avertissement | 9,46 s |
| Contre-épreuve ancien handler, mêmes 31 nouveaux cas | **24 échecs attendus**, 7 réussis | 3,78 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 60,5 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **3 809 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 374,14 s |

31 nouveaux cas : 18 décisions sur trois catégories, trois politiques de
visibilité et ancienne classification présente/absente ; deux accès privilégiés,
quatre refus avant lecture/écriture, trois catégories invalides, job absent,
résultat absent, sauvegarde échouée avant écriture et décisions successives.
Stores, jobs et audits temporaires réels ; pas moteur OCR ou fournisseur exécuté.
L'injection d'échec de sauvegarde ne prouve pas une atomicité en cas de crash.

Témoin : corps exact de l'ancien handler réinjecté en mémoire sans décorateurs,
dans un processus distinct, checkout et aperçu non remplacés. Les 24 échecs
portent sur la persistance, les jobs/résultats absents et l'absence d'appel à
la sauvegarde ; sept refus restent corrects. Code de sortie 1 attendu.

JUnit complet : 3812 cas, 374.053 s ; compteurs
cohérents, pas preuve d'authenticité. Échecs et ignoré identiques au lot 76 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements de l'exécution conservés dans le journal.

## Code, CI et artefacts

Code `1608811c4a7863202f9e13a049eed36fbc7ec71a`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42415489351)
sur cette révision : 394 classification/valeurs/annulation/attribution/cloisonnement/RBAC,
243 qualité/Baidu, 24 ingestion/PDF, 10 UI et documentaire. Sélections se
recouvrant : ne pas additionner les effectifs. Pas suite OCR complète en CI
ou JUnit distant téléchargé. Ruff global et `git diff --check` réussis.

Artefacts hors Git : `/home/user/recettes-unocr/lot77/`,
`classification.{log,xml}`, `contre-epreuve.{log,xml,exit}`,
`complete/pytest.{log,xml}`, `ciblee/recette-*/`, `github-run.json`,
`empreintes.json`, ancienne source et plugin témoin.
[Recette structurée](RECETTE_LOT77.json).

## Intégrité et mise en service

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Pas restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

**Aperçu maintenu sur le backend 76**, sans redémarrage imposé pour ne pas
interrompre les traitements. Le code 77 est poussé et testé, mais pas chargé
dans ce processus : il le sera après un prochain redémarrage maîtrisé.
`data/rbac.json` toujours absent : rôles et cloisonnement inactifs dans cet
aperçu historique ouvert. Aucun compte, jeton ou RBAC créé automatiquement.

## Limites métier

L'objet courant de classification est remplacé, **pas intégralement archivé**.
Les preuves automatiques de l'ancienne catégorie ne sont pas attribuées à la
nouvelle décision : listes de preuves/alternatives manuelles vides conservées.
Pas historique complet, migration des anciennes décisions seulement journalisées,
refonte de `/classify`, du repli GET sur les journaux ou des exports déjà en cache.
`corrected_by` reste déclaratif, pas identité authentifiée ; score manuel 1,0
historique, pas confiance moteur calibrée ni preuve de présence humaine.
Audit legacy best-effort, pas transaction, concurrence, journal signé/WORM ou
validation juridique. Pas changement automatique de profil d'extraction.
**0 nouvel original officiel, 0 article/code officiellement validé, aucune
publication active.** Mission réglementaire non déclarée achevée.
