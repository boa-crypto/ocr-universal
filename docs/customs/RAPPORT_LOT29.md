# Rapport lot 29 — inspection des relations d’une version exacte d’article

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit préalable et livré

Inspection du modèle RelationJuridique, de ses règles d’intégrité, de l’historique
par numéro, des lecteurs d’article/PDF, des gardes/audits et des exports de revue.
Réutilisation du même lot et modèle central, sans nouveau magasin actif.

- Service `consulter_relations_article` : un seul saut incident à une version exacte,
  filtres sens/type, ordre déterministe, pagination et compteurs avant/après filtres.
- Justification/référence intégrales, métadonnées de l’autre version et sources
  de preuve de la page ; pas de texte intégral ajouté aux métadonnées voisines.
- CLI `customs-code-article-relations`, route protégée `/lots/{lot_id}/article-relations`,
  mêmes autorisation/épingle/rejeu/audit obligatoire/no-store.
- Interface intégrée : formulaire, raccourci depuis la lecture d’article, suites,
  ouverture d’autres versions et de leur PDF de preuve explicitement en page 1.
  Aucun localisateur libre interprété comme page ; actions obsolètes inertes.
- Export partiel relu et contrôle d’enveloppe étendus à la route ; service worker
  `v55-article-relations`. Aucun changement de schéma métier ou de lot existant.

[Guide](RELATIONS_ARTICLE.md) et [tableau lots/restes](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 232 tests Python réussis**, sélection étendue de 37 fichiers isolée avant
  import API, 1 avertissement préexistant Starlette/httpx. Durée : 23,60 s.
  Pas l’ensemble de la suite OCR ni une recette nationale.
- **36 nouveaux cas Python** : version exacte malgré numéro partagé, non-transitivité,
  renvois réciproques, cinq types déclarés non validés et synchronisation du filtre
  avec le contrat métier, sens/type combinés, compteurs, sources de page,
  pagination/hors fin, absence d’ID ou absence de lien, paramètres avant lecture,
  CLI, droits/tarif, audit/épingle/503, export et corpus inchangé.
- **81 scénarios JSDOM réussis**, dont 6 nouveaux : filtres/justification sans HTML,
  lecture de preuve page 1, lecture de l’autre version/dédoublonnage, suite conservant
  filtres, incohérences sans actions, ID/tarif/actions anciennes, raccourci depuis
  article et panne d’audit.
- Pont interface → HTTP → API réelle : inspection du lien entrant modificatif de
  fixture, autre version et preuve non rapprochée conservées ; septième export relu
  et contrôlé hors ligne ; lecture de la page 1 du PDF source de la preuve.
- Ruff, syntaxe des trois fichiers JavaScript et `git diff --check` réussis.
- Empreintes historiques inchangées :
  - base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  - référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

Fixtures NON OFFICIELLES temporaires uniquement ; aucune relation nationale
inventée ni donnée/compte utilisateur créé pour la recette.

## Limites et mission restante

Relations déclarées non validées, pas graphe juridique exhaustif ou transitif,
rapprochement automatique de justification/PDF, liens inter-lots ou articles↔tarif,
validation humaine signée, consolidation ou droit applicable à date. Pagination ≠
RAM constante ; JSDOM ≠ recette visuelle/accessibilité complète ou charge nationale.

**0 nouvel original officiel acquis ; 0 article/code national officiel validé ;
0 publication active. Complétude réglementaire non établie.** Corpus officiel,
StarterPack, tarif/fiscalité sourcés, relations transversales prouvées, validation et
intégration métier complète restent à réaliser. Calculs non sourcés toujours bloqués.
Journaux locaux conservés hors commit.

Aperçu backend redémarré sur `0.0.0.0:8000` : coque/module/service worker v55
HTTP 200 avec hôte distant de prévisualisation ; inspection anonyme HTTP 403
sans résultat exposé. Empreintes historiques inchangées après redémarrage.
