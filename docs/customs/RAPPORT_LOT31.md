# Rapport lot 31 — deux fiches tarifaires à sources et mesures séparées

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit préalable et livré

Inspection de TariffBatch/Mesure/Decimal, des fiches et du diff existants, du rejeu
et des contrôles/audits multi-lots, de la revue et des exports à double provenance.
Réutilisation du lecteur central de fiche ; aucun nouveau magasin fiscal actif.

- Service `juxtaposer_fiches_tarifaires` : même code10 exact, deux lots explicitement
  choisis, sources/parents/périodes/mesures conservés indépendamment.
- Validation des deux paginations avant toute lecture. Deux manifestes contrôlés,
  deux paginations indépendantes, taux exacts en chaînes sans fusion ou arrondi.
- CLI `customs-tariff-compare`, API protégée `/tariff-compare` et même autorisation/
  épingle/rejeu/audit obligatoire/no-store. Aucun taux applicable choisi/calculé.
- Interface intégrée : paire de lots et code, pagination après dédiée, suites par
  côté et ouverture de chaque fiche dans son propre lot ; gardes d’actions obsolètes.
- Export partiel relu, whitelist/schéma/contrôle hors ligne à provenance double ;
  service worker `v57-tariff-pair`. Contrat des fiches simples conservé.

[Guide](FICHES_TARIFAIRES_SEPAREES.md) et [tableau lots/restes](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 284 tests Python réussis**, sélection étendue de 39 fichiers isolée avant
  import API ; 1 avertissement préexistant Starlette/httpx, durée 25,82 s.
  Pas l’ensemble de la suite OCR ni une recette nationale.
- **26 nouveaux cas Python** : sources/dates/IDs locaux séparés, taux décimal
  précis/null/zéro distincts, périodes non triées en droit applicable, paginations
  indépendantes/hors fin, absence de code d’un côté/des deux, présence sans mesure,
  même lot explicitement sélectionné, paramètres avant les deux lectures, CLI,
  droits/types, deux épingles et empreinte du résultat après, audit/503, export
  double refusant une provenance ambiguë, corpus inchangé.
- **94 scénarios JSDOM réussis**, dont 7 nouveaux : paramètres/code chaîne,
  suite indépendante, ouverture côté après, code/type invalides, réponse incohérente
  ou numérique sans action, changement du lot après, panne d’audit.
- Pont interface → HTTP → API réelle : deux fiches du même code, chaîne de
  subdivisions déclarées présente avant mais absente après conservée sans
  propagation ; neuvième export relu/contrôlé hors ligne ; ouverture de la fiche
  après dans son propre lot. Aucun lot existant écrasé.
- Ruff, syntaxe des trois fichiers JavaScript et `git diff --check` réussis.
- Empreintes historiques inchangées :
  - base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  - référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

Fixtures NON OFFICIELLES temporaires uniquement ; les taux de test ne sont ni des
taux algériens établis ni des données de production. Aucun compte/corpus national créé.

## Limites et mission restante

Juxtaposition documentaire, pas fusion fiscale, diff sémantique de mesures,
chronologie juridique ou version applicable. Ne permet pas d’importer un fichier
fiscal autonome hors contrat TariffBatch : chantier multi-source fiscal encore à
réaliser/valider. Pagination ≠ RAM constante/transaction multi-dossiers ; JSDOM ≠
recette visuelle/accessibilité complète ou charge nationale.

**0 nouvel original officiel acquis ; 0 article/code national officiel validé ;
0 publication active. Complétude réglementaire non établie.** Corpus officiel,
StarterPack, tarif national/fiscalité, validation/publication et intégration métier
complète restent à réaliser. Calculs non sourcés toujours bloqués. Journaux hors commit.

Aperçu backend redémarré sur `0.0.0.0:8000` : coque/module/service worker v57
HTTP 200 avec hôte distant de prévisualisation ; lecture double anonyme HTTP 403
sans résultat. Empreintes historiques inchangées après redémarrage.
