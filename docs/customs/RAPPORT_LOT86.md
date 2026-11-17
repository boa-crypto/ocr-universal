# Rapport du lot 86 — attribution persistée de classification manuelle

Mesures datées `2026-11-08` par l'horloge de l'environnement
(JUnit). **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction et contrat explicite

La classification manuelle ne persiste plus un `corrected_by` issu du `user`
client : la route transmet `_acteur(request)` au helper métier. Principal RBAC,
`environnement` pour jeton global avec RBAC actif, **`anonyme` sans RBAC**, même
avec jeton partagé. `user` reste accepté, non attributif ; déclarations corps,
en-têtes et query ne remplacent pas ce principal.

Réponse, nouveau store, modèle typé, GET et trois exports JSON nouvellement
générés conservent cette attribution. Persistance conditionnelle avant
publication inchangée ; un conflit ne publie pas de nouveau succès. Dix-huit
cas paramétrés de persistance77 attendent maintenant `a`, plus `DECLARED77`
client, sans supprimer l'assertion. [Contrat](ACTEUR_CLASSIFICATION_MANUELLE.md).

**Le journal résumé `document_classified` reste inchangé, sans acteur ajouté.**
Le helper Python reste une fonction métier acceptant un nom, pas un mécanisme
d'authentification. Ne pas étendre la garantie HTTP à tous ses appelants.

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Attribution/démo/action/statuts/annulation/champs/révision/classification/cloisonnement/RBAC | 721 réussis, 1 avertissement | 19,62 s |
| Ancien handler, mêmes 40 nouveaux cas | **31 échecs attendus**, 9 réussis | 7,22 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 57,42 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **4 109 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 366,96 s |

40 nouveaux cas : 12 comptes/catégories, neuf déclarations corps/header/query,
six modes sans RBAC, une séquence a/b/a, trois exports JSON, quatre refus,
trois catégories invalides, un conflit et un job absent. Requêtes HTTP et
stores/jobs/audits temporaires réels ; relecture typée et nouveau store,
empreintes inchangées sur refus, pas classification fantôme. Pas OCR fournisseur,
navigateur réel ou mesure de précision métier.

Témoin : corps exact du PATCH classification85 réinjecté en mémoire, décorateur
retiré, mêmes schéma/fixtures. Checkout et aperçu non remplacés. Trente et un
cas d'attribution échouent, neuf gardes restent correctes ; code de sortie1
attendu. Pas preuve d'identité réelle.

JUnit complet : 4112 cas, 366.871 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot85 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `eb9983409f3c3b604829f2a098a6c26edf58f915`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42460922751)
sur cette révision : 702 attribution/démo/action/statuts/annulation/champs/
révision/classification/valeurs/cloisonnement/RBAC, 243 qualité/Baidu,
24 ingestion/PDF, 10 UI et documentaire. Sélections se recouvrant, pas effectifs
additionnés. Pas suite OCR complète en CI ou JUnit distant téléchargé.
Ruff global et `git diff --check` réussis. [Recette](RECETTE_LOT86.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot86/`, `attribution.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, ancienne API et témoin.

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

Principal résolu, **pas identité civile, ID immuable ou signature** ; registre
modifiable, jetons partageables, fallback anonyme. Pas enrichissement de l'audit
résumé, migration historique, reconstruction des anciennes classifications ou
invalidation des exports déjà en cache. Tests d'exports générés après décision.
Autres opérations dossiers à acteur client non refondues. Score manuel1,
validation/normalisation de catégorie, profil suggéré non appliqué et droits
inchangés. Révision processus/ABA, audit best-effort et qualité non refondus.

**Aperçu backend76 maintenu** pour préserver les traitements : code77–86 poussé/
testé, non chargé avant redémarrage maîtrisé. RBAC absent de l'aperçu historique
ouvert, aucun compte/jeton/protection créé implicitement. **0 nouvel original
officiel, 0 article/code officiellement validé, aucune publication active.**
Mission réglementaire non déclarée achevée.
