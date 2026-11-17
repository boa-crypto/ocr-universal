# Rapport lot 33 — extraits contextualisés de recherche Code

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit et livré

Audit de la recherche et des aperçus, du tableau des restes, de la lecture exacte
d'articles et des actions/export de la revue. Constat : les 512 caractères initiaux
pouvaient ne pas montrer la correspondance. Ajout sans nouvelle route/magasin :

- Extraits originaux contextualisés, un par champ correspondant, 384 points de
  code maximum, positions projetées depuis la normalisation FR/AR existante.
- Aperçus initiaux conservés ; stratégie explicite, aucune occurrence dénombrée.
- Affichage sûr et ouverture du fragment exact par ID/version/champ/décalage,
  sans URL externe ni interprétation HTML. Titre visible, pas de lecture invalide.
- Export existant relu/audité incluant ces fragments, cache v59-search-excerpts.

[Guide et limites](EXTRAITS_RECHERCHE_CODE.md), [tableau des lots](TABLEAU_LOTS.md).

## Qualification

- **1 338 tests Python réussis**, sélection étendue **41 fichiers**, **28,72 s**,
  1 avertissement préexistant Starlette/httpx. Pas la suite OCR complète.
- **20 nouveaux cas Python** : accents, arabe, ligatures, expansions, emoji,
  décompositions, projection sur Unicode divers, choix déterministe, span long,
  ancien aperçu conservé, lecture exacte, filtres/pagination, CLI/API/export/503.
- **106 scénarios JSDOM réussis**, dont 6 nouveaux : texte hostile, positions Unicode,
  titre, refus d'incohérences, dédoublonnage, actions anciennes et panne audit.
- Pont interface/API réelle : **11 exports** vérifiés hors ligne, dont recherche
  contextualisée puis relecture du même fragment. Fixtures NON OFFICIELLES isolées.
- Ruff, syntaxe des trois JS, `git diff --check` : succès.
- Empreintes historiques inchangées : base
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f`, référentiels
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et état global

**0 nouvel original officiel acquis, 0 article/code10 officiel validé, 0 publication
active.** Corpus national, StarterPack et import fiscal autonome restent absents.
Aucune preuve PDF, consolidation à date, IA, fiscalité applicable ou calcul ajoutés.
Les extraits ne couvrent pas toutes les occurrences. Pagination ≠ mémoire constante ;
pas de qualification nationale, visuelle ou accessibilité Chrome/Firefox.

## Aperçu et conservation

Aperçu redémarré sur `0.0.0.0:8000` : Host distant de prévisualisation accepté,
racine/module/service worker 200, cache v59 ; recherche anonyme 403. Empreintes
historiques revérifiées après démarrage. Journaux préservés hors commit.
