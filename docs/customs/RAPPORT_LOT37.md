# Rapport lot 37 — revue intégrée des mesures autonomes

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit et livré

Inspection du registre à deux types, des branches implicites tarif/Code des routes
et de l'interface, des recherches/inventaire/couverture et du contrat autonome 36.
Ajout sans UI isolée, nouveau magasin ou publication :

- Type `mesures` explicite au registre et schéma mis à jour, quatre consultations
  autorisées : contrôle, recherche de mesures, sources, couverture.
- Garde centrale fail-closed pour toutes les autres opérations, avant mauvais
  chargeur ; aucun fallback de mesures vers le Code ou le tarif.
- Lecteur autonome réutilisé, sources/périodes propres, taux exacts, ligne tarifaire
  null et existence nationale non vérifiée. Aucun rapprochement ou choix de taux.
- Outils existants adaptés aux trois types, suites/exports et protections obsolètes ;
  CLI fiscal-search, sources/coverage type mesures ; cache v62-autonomous-review.

[Contrats et limites](REVUE_MESURES_AUTONOMES.md), [tableau des restes](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 473 tests Python réussis**, sélection étendue de **45 fichiers**, **26,53 s**,
  **1 avertissement** préexistant Starlette/httpx ; pas la suite OCR entière.
- **30 nouveaux cas Python** : inscription/recherche/compteurs/CLI, taux exacts,
  corpus inchangé, **16 cas de refus d'opérations incompatibles**, droits/paramètres,
  audit obligatoire sur les quatre opérations, 503, épingle et résultat recontrôlé.
- **130 scénarios JSDOM réussis**, dont **8 nouveaux** : trois types, outils et
  filtres, recherche/suite sans fiche fabriquée, inventaire sans actions PDF/Code,
  restauration après navigation, ancien bouton inerte et panne audit.
- Pont UI/HTTP/API réelle : **15 exports JSON** relus/vérifiés hors ligne (3 nouveaux :
  recherche autonome, sources, couverture) ; **1 copie PDF Code** toujours vérifiée.
  Toutes les données utilisées sont des fixtures explicitement NON OFFICIELLES.
- Ruff, syntaxe des trois JS, `git diff --check` : succès.
- Empreintes historiques inchangées : base
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ; référentiels
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Mission globale et limites

**0 nouvel original officiel acquis, 0 article/code10 officiel validé,
0 publication active.** La préparation JSON autonome et sa revue existent maintenant,
mais aucun fichier fiscal officiel réel n'a été qualifié/importé. Pas de CSV/XLSX/PDF
fiscal autonome, rapprochement multi-source, droit à date, validation humaine ou
calcul réel. Pas d'import depuis l'administration ajouté. Tests techniques isolés,
pas recette nationale, visuelle/accessibilité Chrome/Firefox ou benchmark de charge.

## Aperçu et conservation

Aperçu redémarré sur `0.0.0.0:8000` ; smoke avec Host distant de prévisualisation :
racine/module/service worker 200, cache v62 ; consultation anonyme refusée 403.
Empreintes historiques revérifiées après démarrage ; aucun lot réel inscrit ou
réécrit. Journaux existants préservés hors commit.
