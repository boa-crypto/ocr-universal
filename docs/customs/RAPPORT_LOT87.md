# Rapport du lot 87 — acteur du nouvel audit de classification manuelle

Mesures datées `2026-11-08` par l'horloge de l'environnement
(JUnit). **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction et contrat explicite

Le PATCH de classification transmet désormais au journal l'acteur serveur déjà
utilisé pour le `corrected_by` persisté au lot86. Après succès du compare-and-
replace, `document_classified` conserve son résumé et ajoute **`acteur`**.
Compte RBAC, `environnement` avec jeton global/RBAC, `anonyme` sans RBAC ;
corps/en-têtes/query déclaratifs non attributifs.

Argument helper optionnel **keyword-only** ; absent/None conserve l'événement
sans nouveau champ, notamment pour l'automatique HTTP. Pas identité inférée du
`corrected_by` d'un résultat fourni en Python ; acteur explicite du helper reste
une déclaration de l'appelant. La garantie serveur concerne la frontière HTTP.
Pas migration rétroactive. [Contrat](ACTEUR_AUDIT_CLASSIFICATION.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| Audit/attribution/démo/action/statuts/annulation/champs/révision/classification/cloisonnement/RBAC | 755 réussis, 1 avertissement | 24,3 s |
| Ancien handler et helper, mêmes 34 nouveaux cas | **20 échecs attendus**, 14 réussis | 5,73 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 58,64 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **4 143 réussis, 2 échecs, 1 ignoré**, 2 avertissement(s) | 373,36 s |

34 nouveaux cas : 12 comptes/catégories, trois déclarations corps/header/query,
deux modes sans RBAC, une séquence a/b/a, quatre refus, trois catégories
invalides, un conflit, un job absent, quatre contrats helper sans acteur,
un acteur helper explicite, un automatique HTTP inchangé et un contrôle de
persistance **au moment précis de l'appel audit** via nouveau store.
Requêtes HTTP et stores/jobs/audits temporaires réels ; clés exactes et
concordance acteur/résultat, pas marqueurs jeton/usurpation dans les succès
testés. Pas OCR fournisseur, navigateur réel ou précision métier.

Témoin : ancien handler **et ancien helper**, signatures/defaults cohérents,
réinjectés ensemble en mémoire. Checkout et aperçu non remplacés. Vingt échecs
attendus : 18 attributions manuelles, le contrôle au point d'audit et le nouveau
contrat mot-clé du helper (ancien helper ne le supporte pas). Quatorze contrôles
sans acteur/gardes passent ; code de sortie1 attendu. Pas helper ancien branché
au nouveau handler par erreur et pas preuve d'identité réelle.

JUnit complet : 4146 cas, 373.279 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot86 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `d896802a28b93e88d077e30e5fe9954d619820ff`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42461512710)
sur cette révision : 736 audit/attribution/démo/action/statuts/annulation/champs/
révision/classification/valeurs/cloisonnement/RBAC, 243 qualité/Baidu,
24 ingestion/PDF, 10 UI et documentaire. Sélections se recouvrant, pas effectifs
additionnés. Pas suite OCR complète en CI ou JUnit distant téléchargé.
Ruff global et `git diff --check` réussis. [Recette](RECETTE_LOT87.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot87/`, `attribution.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, anciennes sources et témoin.

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

Principal résolu, **pas identité civile, ID immuable ou signature** ; registre
modifiable, jetons partageables, fallback anonyme. Audit postcommit best-effort,
pas transaction globale ou WORM. Le résultat peut changer après le commit :
l'événement décrit l'opération, pas forcément l'état courant à toute lecture.
Historique et automatique sans acteur non attribués rétroactivement. GET et
concordance cinq champs pour timestamp inchangés, sans comparaison acteur ni
identité de révision. Pas redaction universelle ou non-répudiation.
Autres opérations dossiers à acteur client, score manuel1, profil suggéré,
révision processus/ABA, exports en cache et qualité non refondus.

**Aperçu backend76 maintenu** pour préserver les traitements : code77–87 poussé/
testé, non chargé avant redémarrage maîtrisé. RBAC absent de l'aperçu historique
ouvert, aucun compte/jeton/protection créé implicitement. **0 nouvel original
officiel, 0 article/code officiellement validé, aucune publication active.**
Mission réglementaire non déclarée achevée.
