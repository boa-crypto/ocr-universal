# Rapport lot 32 — recherche documentaire des mesures déclarées

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit et périmètre livré

Inspection de la recherche centrale FR/AR, des modèles de mesures, des fiches,
des routes autorisées, des exports, de l'interface et du tableau des restes.
La recherche existante ne cherchait pas dans les descriptions de mesures ; elle
reste inchangée. Réutilisation de sa normalisation/validation/présentation de
provenance, du rejeu central et des gardes d'interface existants.

- Nouveau service `rechercher_mesures_tarif`, descriptions normalisées et filtres
  code10/type exacts combinables, pagination stable code puis ID, sources/références.
- CLI `customs-tariff-measure-search`, API protégée `measure-search`, audit obligatoire.
- Formulaire intégré, page suivante et ouverture de fiche du code source ; export
  relu/audité et contrôle hors ligne compatible, service worker v58-measure-search.
- Taux Decimal exacts conservés, null/zéro distincts ; aucune règle applicable,
  classification de type, fusion fiscale, publication ou calcul déduit.

[Contrats et limites](RECHERCHE_MESURES.md), [tableau](TABLEAU_LOTS.md).

## Vérifications exécutées

- **1 318 tests Python réussis**, sélection étendue de **40 fichiers**, isolée avant
  imports API ; **1 avertissement** préexistant Starlette/httpx, **25,84 s**.
  Ce n'est pas la suite OCR entière ni une recette nationale.
- **34 nouveaux cas Python** : FR/AR, types, combinaison/pagination, champs exclus,
  taux précis/null/zéro, zéros initiaux, paramètres avant lecture, CLI, droits/API,
  audit obligatoire/panne 503, export hors ligne et corpus inchangé.
- **100 scénarios JSDOM réussis**, dont 6 nouveaux. Tests d'encodage/texte hostile,
  suite, fiche/dédoublonnage, code invalide, désactivation et actions obsolètes/503.
- Pont interface/API réelle sur fixtures NON OFFICIELLES : **10 exports** relus et
  vérifiés hors ligne ; nouvelle recherche et ouverture de fiche comprises.
- Ruff, syntaxe des trois JS et `git diff --check` : succès.
- Empreintes historiques inchangées :
  - base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  - référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## État global et limites

**0 nouvel original officiel, 0 nouveau code10/article officiel validé,
0 publication active.** StarterPack/export national et corpus consolidé non
acquis. Pas d'import fiscal autonome, moteur à date, synonymes métier ou IA.
Les périodes et types sont déclarés, non établis juridiquement. Les résultats
ne sont jamais utilisables pour un calcul douanier réel.

La pagination ne borne pas la mémoire du rejeu ou du tri ; aucun benchmark
national. JSDOM n'est pas une recette visuelle/accessibilité Chrome/Firefox.

## Aperçu et conservation

Aperçu redémarré sur `0.0.0.0:8000`. Smoke avec Host de prévisualisation distant :
page racine/module revue/service worker 200, cache v58 ; nouvelle route anonyme
403 (pas de données révélées). Empreintes historiques revérifiées après démarrage.
Journaux existants préservés et exclus du commit, pas de réécriture de lot existant.
