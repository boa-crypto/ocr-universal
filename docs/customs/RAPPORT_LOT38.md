# Rapport lot 38 — consultation nomenclature / mesures autonomes

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit et livré

Audit des fiches à mesures natives, du contrat autonome 36, de sa recherche/revue
37, des gardes de types et de la double provenance/export existants. Ajout sans
nouveau magasin, fusion de données ou calcul :

- Service `juxtaposer_tarif_mesures`, même code exact, sources/dates/mesures séparées ;
  deux paginations validées avant lecture, fiche native et recherche autonome réutilisées.
- CLI `customs-tariff-measures`, API `/tariff-measures`, exception de paire de types
  limitée à cette opération et à l'ordre tarif/mesures ; autres refus conservés.
- Interface intégrée, sélecteur autonome dédié, suites indépendantes, lecture
  séparée de fiche/mesures ; absent de la nomenclature ≠ mesures masquées.
- Export relu/audité avec deux provenances, whitelist/schéma/contrôle hors ligne ;
  cache v63-tariff-measures. Aucun rapprochement fiscal juridiquement validé.

[Contrat et limites](CONSULTATION_TARIF_MESURES.md), [tableau des restes](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 498 tests Python réussis**, sélection étendue **46 fichiers**, **27,65 s**,
  **1 avertissement** préexistant Starlette/httpx. Pas la suite OCR entière.
- **25 nouveaux cas Python** : sources/IDs locaux/taux précis/null/zéro séparés,
  dates propres, paginations/absences, types invalides et paramètres avant lecture,
  CLI, droits/audit/503, export à double provenance et refus ambigu, deux épingles
  et empreinte de résultat du côté mesures recontrôlée, archives inchangées.
- **138 scénarios JSDOM réussis**, dont **8 nouveaux** : paramètres exacts, suites
  par côté, ouverture du lot autonome, codes/types invalides, sélection autonome
  modifiée, rôles de provenance incohérents, panne audit sans ancien résultat.
- Pont UI/HTTP/API réelle : **16 exports JSON** relus/vérifiés hors ligne, dont la
  nouvelle consultation à deux provenances, plus **1 copie PDF Code** inchangée.
  Cas réel de test : code absent du lot tarif mais trois mesures déclarées, puis
  ouverture du lot autonome exact. Fixtures NON OFFICIELLES seulement.
- Ruff, syntaxe des trois JS et `git diff --check` : succès.
- Empreintes historiques inchangées : base
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ; référentiels
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## État global

**0 nouvel original officiel acquis, 0 article/code10 officiel validé,
0 publication active.** Consultation de déclarations, pas rattachement ou règle
applicable. Aucun fichier fiscal officiel qualifié/importé. Acquisition, formats
fiscaux autonomes tabulaires/PDF, contrôle humain, rapprochement juridique des
sources, droit à date, publication et recette nationale restent ouverts.
Pas de calcul réel, mémoire constante ou transaction multi-dossiers.

## Aperçu et conservation

Aperçu redémarré sur `0.0.0.0:8000` ; Host distant de prévisualisation accepté :
racine/module/service worker 200, cache v63, nouvelle route anonyme 403.
Empreintes historiques revérifiées après démarrage ; aucun lot réel inscrit,
réécrit ou fusionné. Journaux existants préservés hors commit.
