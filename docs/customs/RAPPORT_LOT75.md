# Rapport du lot 75 — acteur des validations et corrections OCR

7 novembre 2026. **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction livrée

Les routes OCR de validation et correction transmettaient toujours `utilisateur`
au service, même lorsqu'un principal était résolu. Elles transmettent maintenant
le nom renvoyé par la garde, après autorisation du rôle et du dossier. Le service
conserve ses événements existants et la clé `user` ; aucun nouvel acteur n'est
stocké dans l'extraction ni accepté depuis le client.

RBAC actif : nom du principal local ; jeton global : `environnement`.
Sans RBAC : `local`, avec ou sans secret partagé exigé. **Ce dernier nom ne
signifie pas personne authentifiée.** Corps, en-têtes et paramètres déclarant un
acteur ne modifient pas l'attribution ; leurs valeurs étaient déjà ignorées,
pas ancienne injection d'acteur prétendument fermée. Les contrôles des lots 73/74
et les effets métier sont conservés. [Contrat détaillé](ACTEUR_AUDIT_OCR.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Attribution/corrections/cloisonnement/rôles, dont 33 nouveaux cas | 250 réussis, 1 avertissement | 8,5 s |
| Contre-épreuve des deux anciens handlers, mêmes 33 cas | **20 échecs attendus**, 13 réussis, 1 avertissement | 2,15 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 60,25 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **3 670 réussis, 2 échecs, 1 ignoré**, 1 avertissement | 382,88 s |

33 nouveaux cas : huit succès nominatifs, six entrées client d'acteur ignorées,
quatre modes sans RBAC, dix refus d'autorisation, un champ absent, deux extractions
absentes et deux séquences a→b→a. Stores/cache/JSON et journaux temporaires réels,
empreintes sur refus, mutations autorisées vérifiées. Les événements de succès
contrôlés n'ajoutent ni jeton porteur ni valeur OCR/corrigée. Pas test de charge,
concurrence, navigateur réel ou fournisseur OCR.

Contre-épreuve : corps exacts des deux anciens handlers sans décorateurs,
réinjectés seulement en mémoire dans un processus de test. Checkout et aperçu
non remplacés. Les 20 cas d'attribution échouent avec l'ancien acteur générique ;
les 13 contrôles de refus passent. Pas mutation volontaire du checkout pour
fabriquer un résultat négatif.

JUnit complet : 3673 cas, 382.791 s ; compteurs
cohérents avec les cas, pas preuve d'authenticité. Échecs identiques au lot 74 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present`. Ignoré :
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**.

## Révision, CI et preuves

Code `65e08cf5f5bd8044f4d9c81cd004bf91d1e93632`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42412823043)
sur cette révision : 250 attribution/corrections/cloisonnement/RBAC,
241 qualité/Baidu, 24 ingestion/PDF, 10 UI et documentaire. Sélections se
recouvrant : ne pas additionner les effectifs. Pas suite OCR complète en CI
ni JUnit distant téléchargé. Ruff global et `git diff --check` réussis.

Artefacts locaux hors Git : `/home/user/recettes-unocr/lot75/`,
`attribution.{log,xml}`, `contre-epreuve.{log,xml,exit}`,
`complete/pytest.{log,xml}`, `ciblee/recette-*/`, `github-run.json`,
`empreintes.json`, source ancienne et plugin témoin.
[Recette structurée](RECETTE_LOT75.json).

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé de référentiels :
attendu `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observé `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Pas restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et fichiers exploratoires conservés hors commit sans attribution
nouvelle de leurs modifications aux présents tests.

Aperçu redémarré avec le backend 75, port 8000. `data/rbac.json` toujours absent :
**rôles et cloisonnement inactifs dans cet aperçu historique ouvert**. Aucun
compte, jeton ou RBAC créé automatiquement ; registre temporaire explicite en test.

Le nom seul n'ajoute pas d'identifiant immuable ni de mode d'authentification
au journal ; renommages et collisions possibles. Jetons partageables, pas
identité civile ou présence humaine prouvée. Audit legacy best-effort et
configuration de journal du service inchangés : pas transaction, signature ou
WORM. Pas réattribution des anciens événements `utilisateur`, refonte des autres
routes/corrections de jobs ou des arguments `user` des appels directs au service.
Pas recalcul qualité ou invalidation de validation globale par ce lot.
**0 nouvel original officiel, 0 article/code officiellement validé, aucune
publication active.** La mission réglementaire n'est pas déclarée achevée.
