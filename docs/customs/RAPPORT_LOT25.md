# Rapport lot 25 — comparaison littérale de versions d’article

Date : 6 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Livré

- Service central de comparaison de deux IDs exacts du même lot Code, sans
  appariement ni chronologie juridique inférée.
- Préfixe/suffixe communs stricts et blocs centraux indépendamment paginés,
  Unicode Python sans normalisation ; absence de champ explicitement indisponible.
- Métadonnées, sources et relations directes déclarées conservées, sans prétendre
  établir une relation juridique ou rapprocher les transcriptions du PDF.
- CLI `customs-code-article-diff` ; route protégée `/lots/{lot_id}/article-diff`.
- Formulaire intégré à la revue, décalages et suites par côté ; tarif désactivé.
- Export partiel existant et contrôle de son enveloppe étendus à cette route ;
  service worker `v51-diff-articles`.

Guide : [COMPARAISON_ARTICLES.md](COMPARAISON_ARTICLES.md).

## Qualification exécutée

- **1 117 tests Python réussis**, sélection étendue de 33 fichiers isolée dans
  des répertoires de données/journaux temporaires ; 1 avertissement de dépréciation
  Starlette/httpx préexistant. Durée : 21,78 s. Ce n’est pas toute la suite OCR.
- **56 scénarios JSDOM réussis**, dont 4 nouveaux : paramètres/Unicode/suite
  indépendante, champ absent, IDs requis/tarif, panne d’audit.
- **25 nouveaux cas Python** : égalité/insertion/suppression, préfixe/suffixe,
  accents combinés/arabe/emoji/CRLF, pagination indépendante/hors fin,
  paramètres avant lecture, absence sans repli, CLI sans écriture, droits/API,
  audit épinglé/503 sans résultat, export structurel.
- Pont interface → HTTP → API réelle : comparaison des versions de fixture,
  provenance conservée, export relu puis analysé hors ligne ; trois exports
  partiels contrôlés (PDF, comparaison d’article, tarif). Fixtures NON OFFICIELLES
  temporaires uniquement, aucun lot utilisateur créé ni donnée nationale inventée.
- Ruff, syntaxe des trois fichiers JavaScript et `git diff --check` réussis.
- Empreintes historiques inchangées :
  - base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  - référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et mission restante

Pas de diff minimal/mot à mot, de traduction, de concordance avec le PDF,
comparaison inter-lots, consolidation juridique, droit applicable à date ou
validation humaine signée. Les décalages ne sont pas des positions UTF-16/graphèmes.
La pagination ne garantit pas une consommation mémoire constante. JSDOM n’est pas
une recette visuelle Chrome/Firefox ou une qualification de charge nationale.

**0 nouvel original officiel acquis ; 0 article/code national officiel validé ;
0 publication active.** Complétude réglementaire non établie. StarterPack,
originaux/modifications exhaustifs, tarif national courant et fiscalité sourcée
restent à acquérir et valider. Aucun référentiel non vérifié n’est autorisé pour
un calcul douanier réel. Journaux locaux conservés hors commit.

Aperçu backend redémarré sur `0.0.0.0:8000`. Contrôle avec hôte de
prévisualisation distant : coque, module et service worker v51 HTTP 200 ;
comparaison anonyme HTTP 403, sans résultat exposé.
