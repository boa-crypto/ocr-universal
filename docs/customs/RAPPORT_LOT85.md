# Rapport du lot 85 — acteur serveur des corrections et annulations

Mesures datées `2026-11-08` par l'horloge de l'environnement
(JUnit). **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction et contrat explicite

L'acteur des événements `field_validated` et `field_correction_annulee` ne provient
plus du `user` déclaré dans le corps : les deux handlers utilisent désormais
`_acteur(request)`, helper existant de l'API. Compte RBAC résolu, `environnement`
pour jeton global avec RBAC actif, **`anonyme` sans RBAC**, même avec jeton partagé.
Ce fallback n'est pas le libellé `local` des routes OCR ; pas harmonisation globale.

`user` reste accepté, non attributif. En-têtes/query déclaratifs ne remplacent
pas le principal. Motifs et valeurs conservés, droits et règles métier inchangés.
Attribution après réussite du compare-and-replace ; refus/conflits ne fabriquent
pas d'événement de succès. Deux tests historiques attendant `marie`/`amina` clients en mode ouvert sont
actualisés vers `anonyme`, motifs et valeurs conservés ; l'acteur de correction
est aussi vérifié dans l'annulation. Les huit cas de démonstration sont ajoutés
à la sélection CI. Une première complète révélait trois échecs : ce second
contrat historique et les deux Indra. Journal/XML préservés dans
`complete-initial/` (4 068 réussis, 3 échecs, 1 ignoré, 369,88 s) ; complète
entière réexécutée après ajustement, pas échec supprimé du bilan. [Contrat](ACTEUR_CORRECTIONS_CHAMPS.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Attribution/action/statuts/annulation/champs/révision/classification/cloisonnement/RBAC | 681 réussis, 1 avertissement | 19,57 s |
| Anciens handlers, mêmes 65 nouveaux cas | **40 échecs attendus**, 25 réussis | 4,61 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 57,83 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **4 069 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 365,34 s |

65 nouveaux cas : 16 comptes/actions, 12 déclarations corps/en-têtes/query,
huit modes sans RBAC, quatre séquences a/b/a, 16 refus, quatre champs absents,
quatre conflits et une demande sans action. Requêtes HTTP, stores/jobs/audits
temporaires réels ; valeurs/réponses conservées, empreintes inchangées sur refus.
Événements de succès testés sans marqueurs de jeton ou d'usurpation. Pas OCR
fournisseur, navigateur réel ou mesure de précision métier.

Témoin : corps exacts des PATCH/undo du lot84, sans décorateurs, réinjectés en
mémoire dans un processus distinct ; mêmes schéma/fixtures. Checkout et aperçu
non remplacés. Quarante cas d'attribution échouent, 25 gardes restent correctes ;
code de sortie1 attendu. Ce n'est pas une preuve d'identité réelle.

JUnit complet : 4072 cas, 365.225 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot84 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `7e6e0bdb89cc41d893ea00a071e26850d98d3e2d`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42460288284)
sur cette révision : 662 attribution/action/statuts/annulation/champs/révision/
classification/valeurs/cloisonnement/RBAC, 243 qualité/Baidu, 24 ingestion/PDF,
10 UI et documentaire. Sélections se recouvrant, pas effectifs additionnés.
Pas suite OCR complète en CI ou JUnit distant téléchargé. Ruff global et
`git diff --check` réussis. [Recette structurée](RECETTE_LOT85.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot85/`, `attribution.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `complete-initial/`, `github-run.json`, `empreintes.json`, ancienne API et témoin.

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

**Nom de principal, pas identité civile, identifiant immuable, signature ou
non-répudiation**. Registre modifiable, jetons partageables, fallback anonyme.
Événements historiques non réécrits et autres routes à acteur client non
refondues (classification manuelle, dossiers notamment). Motifs/valeurs peuvent
toujours contenir des données sensibles ; pas redaction universelle. Pas
transaction globale résultat/audit ou journal WORM. Révision processus/ABA,
limites d'annulation, exports en cache et qualité inchangés.

**Aperçu backend76 maintenu** pour préserver les traitements : code77–85 poussé/
testé, non chargé avant redémarrage maîtrisé. RBAC absent de l'aperçu historique
ouvert, aucun compte/jeton/protection créé implicitement. **0 nouvel original
officiel, 0 article/code officiellement validé, aucune publication active.**
Mission réglementaire non déclarée achevée.
