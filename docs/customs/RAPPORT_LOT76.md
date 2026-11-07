# Rapport du lot 76 — valeurs humaines vides de champs

7 novembre 2026. **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Changements livrés

`FieldValue.value` et l'état antérieur consigné par l'API choisissent le premier
emplacement non `None` : une confirmation/correction vide ne doit plus faire
réapparaître une valeur OCR ou normalisée moins prioritaire. Même distinction
pour la valeur après correction relue dans l'audit et pour la garde d'annulation.
Une saisie humaine vide peut être annulée lorsqu'une trace exploitable existe.
Priorité confirmée > corrigée > normalisée > brute, chaînes `0`, français/arabe
et autres comportements non vides conservés.

L'aller-retour modèle a révélé une incohérence supplémentaire : l'API écrivait
`status=corrected`, mais `FieldStatus` ne le reconnaissait pas. Cette valeur est
ajoutée ; correction et export JSON peuvent être relus avec le modèle réel,
sans contourner sa validation. Deux cas de qualité existants supplémentaires
sont collectés automatiquement par l'énumération étendue.
[Contrat détaillé](VALEURS_CHAMPS_VIDES.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Valeurs/annulation/attribution/cloisonnement/rôles + qualité zéro | 392 réussis, 1 avertissement | 7,5 s |
| Témoin anciens corps de sélection et API, mêmes 106 nouveaux cas | **43 échecs attendus**, 63 réussis | 6,14 s |
| Témoin ancienne annulation seule, mêmes 106 cas | **4 échecs attendus**, 102 réussis | 5,01 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 113,94 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **3 778 réussis, 2 échecs, 1 ignoré**, 2 avertissements | 472,85 s |

106 nouveaux cas dans le nouveau fichier : 81 combinaisons None/vide/zéro,
8 sélections FR/AR, 8 cycles simples de correction/annulation, 4 états manuels
antérieurs vides, 3 priorités d'audit et 2 exports JSON réels. Deux cas additionnels
dans les tests de qualité existants, soit +108 cas dans la suite complète.
Stores/jobs/audits temporaires réels ; aucun moteur OCR ou fournisseur réel
appelé par ces nouveaux tests.

Les témoins réinjectent les corps exacts antérieurs en mémoire dans deux
processus distincts. Le second isole l'annulation pour que son refus erroné
ne soit pas masqué par le défaut de sélection de valeur. L'énumération nouvelle
reste active dans les deux : **pas rejeu complet de l'ancien schéma**.
Checkout et aperçu non remplacés. Chaque témoin retourne 1 comme attendu.

JUnit complet : 3781 cas, 472.677 s ; compteurs
cohérents, pas preuve d'authenticité. Deux échecs et ignoré identiques au lot 75 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Deux avertissements observés : dépréciation
Starlette/httpx et `UnsupportedFieldAttributeWarning` sur l'alias `liquidation_id`
dans `test_creation_et_suppression_concurrentes_sans_orphelin` ; cause de ce
second avertissement non attribuée par ce lot.

## Code, CI et artefacts

Code `b13ebccc03c8d1b1419bf471b118ce8b206a7295`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42414044174)
sur cette révision : 363 valeurs/annulation/attribution/cloisonnement/RBAC,
243 qualité/Baidu, 24 ingestion/PDF, 10 UI et documentaire. Sélections se
recouvrant : ne pas additionner les effectifs. Pas suite OCR complète en CI
ou JUnit distant téléchargé. Ruff global et `git diff --check` réussis.

Artefacts hors Git : `/home/user/recettes-unocr/lot76/`, `valeurs.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `contre-epreuve-undo.{log,xml,exit}`,
`complete/pytest.{log,xml}`, `ciblee/recette-*/`, `github-run.json`,
`empreintes.json`, sources anciennes et plugin témoin.
[Recette structurée](RECETTE_LOT76.json).

## Intégrité, aperçu et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires conservés hors commit, sans nouvelle attribution de
leurs modifications aux présents tests.

Aperçu redémarré avec le backend 76, port 8000. `data/rbac.json` toujours absent :
**rôles et cloisonnement inactifs dans cet aperçu historique ouvert**. Aucune
création automatique de compte, jeton ou RBAC.

Le cycle testé revient à un champ de base sans valeur manuelle antérieure.
**Pas refonte multi-niveau de l'annulation**, restauration exacte des quatre
emplacements manuels, filtrage des événements de statut seul, concurrence ou
transaction audit/résultat. Anciennes traces déjà erronées non réparées.
Pas audit exhaustif des replis booléens d'autres consommateurs, notamment UI
JavaScript, ni recette navigateur. Acteur client des corrections de jobs et
audit legacy best-effort inchangés ; pas journal signé/WORM. Pas recalcul qualité
ou invalidation de validation globale ajoutés. Gardes et politiques de visibilité
existantes conservées. **0 nouvel original officiel, 0 article/code officiellement
validé, aucune publication active.** Mission réglementaire non déclarée achevée.
