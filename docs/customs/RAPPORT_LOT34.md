# Rapport lot 34 — inventaire consultable des sources déclarées

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit et livré

Inspection du tableau de mission, de SourceDocument/DocumentJuridique, des liens
locaux des lots, de la couverture, de la recherche, des lectures PDF et des
routes/export/UI de revue. Aucun nouveau corpus ou magasin de production créé.

- Service `inventorier_sources` : type explicite, filtres exacts ID/nature,
  recherche de métadonnées FR/AR, pagination déterministe, références complètes.
- Compteurs de rattachements reçus, distinction source sans article/document vide,
  autres IDs de même empreinte dans le lot sans inférence d'identité juridique.
- CLI `customs-sources`, API protégée `/lots/{lot_id}/sources`, audit obligatoire.
- Formulaire intégré, suite indépendante, hiérarchie par source et lecture du
  PDF local page 1 sur Code seulement, gardes d'obsolescence existantes réutilisées.
- Export relu/audité, whitelist/schéma/vérificateur hors ligne ; cache v60-source-catalog.

[Guide et limites](INVENTAIRE_SOURCES.md), [tableau des lots/restes](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 373 tests Python réussis**, sélection étendue de **42 fichiers**, **26,01 s**,
  **1 avertissement** préexistant Starlette/httpx. Pas la suite OCR entière.
- **35 nouveaux cas Python** : FR/AR, métadonnées/filtres exacts, pagination, types,
  compteurs dont historique répété, empreintes identiques/IDs distincts, documents
  sans articles, tarif sans nature inventée, paramètres avant lecture, CLI/API,
  droits/audit/503/export et empreintes avant traitement/résultat recontrôlées.
- **114 scénarios JSDOM réussis**, dont **8 nouveaux** : paramètres encodés, suite,
  hiérarchie/PDF par source, tarif sans filtre Code, incohérences, ancien bouton, 503.
- Pont interface/API réelle sur fixtures NON OFFICIELLES : **12 exports** relus et
  vérifiés hors ligne. Inventaire, navigation par source puis PDF local compris.
- Ruff, syntaxe des trois JS et `git diff --check` : succès.
- Empreintes historiques inchangées :
  - base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  - référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et état global

**0 nouvel original officiel acquis, 0 article/code10 officiel validé,
0 publication active.** StarterPack, corpus national et import fiscal autonome
restent absents. Inventaire de déclarations, pas authentification des sources,
dépouillement exhaustif des modifications, dédoublonnage juridique ou droit à date.
Aucune validation humaine ou fonction de calcul réel activée. Pas de benchmark
national, mémoire constante ou recette visuelle/accessibilité navigateur réel.

## Aperçu et conservation

Aperçu redémarré sur `0.0.0.0:8000` ; smoke avec Host distant de prévisualisation :
racine/module/service worker 200, cache v60, route sources anonyme 403. Empreintes
historiques revérifiées après démarrage. Journaux existants préservés hors commit.
