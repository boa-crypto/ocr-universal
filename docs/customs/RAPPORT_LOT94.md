# Lot 94 — première tranche d'achèvement métier : dossiers de proposition tarifaire

**Nouvelle fonction métier livrée, pas achèvement global de la mission.**
Mesures JUnit `2026-11-08` selon l'horloge de l'environnement.
Code `f6d7db2e1f127780ef6c935ca10c3717773c8ee6`.

## Livré

Trois routes dans l'API de revue existante : création d'un dossier produit,
lecture avec historique, révision humaine avec contrôle de version. Produit
structuré, informations non renseignées/questions, pistes documentaires FR/AR,
abstention si aucune piste. États brouillon/revue/complétion/proposition humaine/
rejet/réouverture. Un code proposé exige caractéristiques complétées, candidat
du snapshot, justification, RGI/notes déclarés et référence candidate.
**Aucun statut de validation juridique ou publication accepté.**

Accès administrateur nominatif RBAC + allowlist de réviseurs, pas jeton global
ou mode ouvert ; lot tarifaire enregistré, manifeste épinglé et fichiers
revalidés. Acteur serveur, no-store, corps stricts sans user client. SQLite local
avec état/version/auteur/empreinte dans une transaction, refus409 des révisions
périmées. Concurrence testée entre deux instances **et deux processus**.
[Contrat/API](DOSSIERS_PROPOSITION_TARIFAIRE.md).

## Résultats vérifiés

| Recette | Résultat |
|---|---|
| Nouveaux scénarios métier | **29** |
| Métier + revue existante | **71 réussis** |
| Documentaire,67 fichiers | **2 189 réussis** |
| JSDOM historique | **212 scénarios réussis**, pas tests de la nouvelle UI |
| Complète locale | **4 344 réussis,2 échecs Indra,1 ignoré** |
| Ruff global / diff-check | Réussis |

[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42468040297) sur le code exact : 937 cas backend comprenant
le métier, plus sélections qualité/Baidu243, ingestion/PDF24, UI10 et documentaire.
Recouvrements, pas effectifs additionnés ; pas complète OCR en CI/JUnit distant.
Pas contre-épreuve d'ancien handler : fonctionnalité nouvelle. Scénarios couvrant
cycle complet, persistance, produit incomplet, abstention, motivation/références,
autorisations, modifications de source/base, révision périmée, audit indisponible,
concurrence. Fixtures NON OFFICIELLES ; vrais HTTP/SQLite, pas tests juridiques.

Complète JUnit 4347 cas, 368.766s ; mêmes échecs
qu'au93 : `tests.test_indra_ocr::test_indra_engine_availability` et
`tests.test_ocr::test_selection_prefers_native_when_present`, ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. **Complète non verte**.
[Recette structurée](RECETTE_LOT94.json), logs/XML dans `/home/user/recettes-unocr/lot94/`.

## Limites importantes, non masquées

- **Proposition humaine non applicable fiscalement** : RGI/notes sont déclarés,
  pas raisonnés automatiquement ou juridiquement prouvés. Pistes littérales,
  pas nouvelle IA, synonymes ou traduction. Autres références éventuelles
  déclarées, non vérifiées. Caractéristiques non certifiées.
- **Audit externe non atomique** : état et version SQLite atomiques ; journal
  de revue postcommit. Une panne donne503 après sauvegarde possible. Le client
  connaît dossier_id et doit relire après réparation, pas rejouer aveuglément.
  Ce cas est testé ; pas exactly-once ou livraison prouvée.
- Historique avec empreintes pas WORM/signature ; propriétaire du fichier peut
  réécrire. Pas séparation obligatoire de deux personnes. 100versions/512KiB par
  état, pas quota global ou charge qualifiée. UI métier non ajoutée, sauvegarde/
  chiffrement de la base non qualifiés.

**26/27 empreintes historiques conformes**, même référentiels partagé différent,
pas restauration pour forcer vert. Données/dossiers/journaux/exploratoires
préservés hors commit, sans attribution nouvelle de leurs changements aux tests.

## Reste pour achever les fonctions métier

[Plan d'achèvement](ACHEVEMENT_METIER.md) : UI de revue/saisie, ontologie et
recherche métier, raisonnement RGI sourcé, consolidation/droit à date, liens
juridiques prouvés, validation/publication/retrait contrôlés et intégration métier
sur référentiels validés. Il reste du développement et des qualifications,
pas seulement des documents externes. Cette livraison ne clôture pas ces points.

**Aperçu backend76 maintenu**, code77–94 poussé/testé non chargé pour préserver
les traitements ; RBAC absent/ouvert dans cet aperçu, nouvelle fonction non déployée.
**0 nouvel original officiel,0 article/code officiellement validé,0 publication
active. Mission globale partielle, non recevable pour production fiscale.**
