# Rapport lot 28 — comparaison littérale d’articles entre lots Code

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit préalable et livré

Inspection du moteur de comparaison intra-lot, des contrôles/audits multi-lots
existants, du registre, de l’export à provenance simple/double et des gardes UI.
Réutilisation du moteur central, sans deuxième extracteur ou magasin actif.

- Comparaison de deux IDs exacts dans deux lots Code explicitement choisis.
- Métadonnées et sources séparées même si les IDs se répètent ; aucune relation
  locale transposée ni identité juridique déduite. Double provenance de manifestes.
- CLI existante étendue par `--after-lot` ; route protégée `/article-diff`.
  Comparaison intra-lot et son contrat de réponse conservés.
- Interface : sélection des deux lots, suites indépendantes, ouverture de chaque
  version dans son propre lot. Changement du lot après invalide aussi les anciennes
  actions et réponses tardives.
- Export partiel relu, whitelist/schéma et contrôle hors ligne étendus à la route
  à provenance double. Service worker `v54-article-diff-lots`.

[Guide](COMPARAISON_ARTICLES_INTER_LOTS.md) et [tableau lots/restes](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 196 tests Python réussis**, sélection étendue de 36 fichiers isolée avant
  import ; 1 avertissement préexistant Starlette/httpx. Durée : 23,04 s.
  Ce n’est pas toute la suite OCR ni une recette nationale.
- **19 nouveaux cas Python** : mêmes IDs/sources locales séparées, égalité,
  insertion/suppression, arabe/emoji/accents sans normalisation, pagination,
  absences sans repli, non-transposition de relations, paramètres avant lecture,
  CLI, droits/tarif, deux épingles, empreinte du résultat après, audit/503 et
  export double refusant une provenance ambiguë ; corpus inchangé.
- **75 scénarios JSDOM réussis**, dont 7 nouveaux : deux lots/IDs encodés,
  suite Unicode indépendante, tarif/paire incohérente, ancienne action et réponse
  tardive après changement du lot après, panne d’audit et lecture du bon côté.
- Pont interface → HTTP → API réelle : deux lots aux mêmes IDs/textes mais aux
  PDF/manifeste distincts, comparaison littérale et provenance séparée, ouverture
  de la version après dans son propre lot. Sixième export relu/contrôlé hors ligne.
  L’ancienne archive de fixture est conservée et inscrite sous un autre ID ;
  aucune archive écrasée, aucun corpus national ou compte utilisateur créé.
- Ruff, syntaxe des trois fichiers JavaScript et `git diff --check` réussis.
- Empreintes historiques inchangées :
  - base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  - référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

Fixtures NON OFFICIELLES temporaires uniquement. Les cas métier ne prouvent aucune
succession juridique ni fidélité des transcriptions à des sources officielles.

## Limites et mission restante

Le bloc central n’est pas un diff minimal ; ni traduction ni consolidation.
Deux archives peuvent être chargées en mémoire ; pagination ≠ RAM constante,
contrôle d’épingle ≠ transaction multi-dossiers/WORM/authenticité. JSDOM ≠ recette
visuelle/accessibilité complète en navigateur ou qualification de charge nationale.

**0 nouvel original officiel acquis ; 0 article/code national officiel validé ;
0 publication active. Complétude réglementaire non établie.** Collecte officielle,
StarterPack, tarif national/fiscalité, validation humaine, droit à date et intégration
métier complète restent à réaliser. Journaux locaux conservés hors commit.

Aperçu backend redémarré sur `0.0.0.0:8000` : coque/module/service worker v54
HTTP 200 avec hôte distant de prévisualisation ; nouvelle comparaison anonyme
HTTP 403 sans résultat. Empreintes historiques inchangées après redémarrage.
