# Rapport lot 30 — rapprochement littéral des justifications avec le PDF source

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit préalable et livré

Inspection des relations/preuves du lot 29, du rapprochement d’articles du lot 27,
du worker PDF, des gardes/audits et des exports avant implémentation. Mutualisation
du noyau de constat littéral ; aucun nouveau parseur ou magasin actif.

- Service `rapprocher_justification_pdf` : ID exact de relation, source de preuve
  imposée, page physique/fragment explicites, première occurrence et positions.
- Justification possiblement paraphrasée : présence/absence sans jugement sémantique
  ou validation du lien. Cas absents/vides/blancs sans extraction ; page sans texte
  natif indéterminée. Aucun statut documentaire ou juridique modifié.
- CLI `customs-code-relation-pdf-match`, route protégée `/lots/{lot_id}/relation-pdf-match`,
  mêmes droits/épingle/rejeu/audit obligatoire/no-store.
- Interface : préparation depuis une relation sans requête, choix de page, suite
  de justification et lecture de la page rapprochée ; tarif désactivé et actions
  obsolètes inertes. Export partiel relu et contrôlé hors ligne étendu.
- Service worker `v56-relation-pdf-match`. Contrat de rapprochement d’article
  conservé malgré la mutualisation, sans modification d’archive existante.

[Guide](RAPPROCHEMENT_JUSTIFICATION_PDF.md) et [tableau lots/restes](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 258 tests Python réussis**, sélection étendue de 38 fichiers isolée avant
  import API ; 1 avertissement préexistant Starlette/httpx, durée 25,10 s.
  Pas l’ensemble de la suite OCR ou une recette nationale.
- **26 nouveaux cas Python** : présence/absence/page blanche, source de preuve
  imposée plutôt que source de cible, inconnus/vides/blancs sans extraction,
  paramètres avant lecture, Unicode strict/pagination, occurrence après 16 000
  caractères, premier résultat, un seul rejeu, CLI/page absente, droits/tarif,
  audit/épingle/503/export et corpus inchangé.
- **87 scénarios JSDOM réussis**, dont 6 nouveaux : préparation sans extraction,
  paramètres/source/page, suite Unicode, rendu sûr/indisponibilité, invalides/tarif/
  anciennes actions, panne d’audit sans ancien résultat.
- Pont interface → HTTP → API réelle : relation → préparation → preuve PDF page 1
  → choix explicite page 2 et fragment → constat positif sans validation juridique
  → huitième export relu/contrôlé hors ligne → lecture de la page source rapprochée.
- Tests du lecteur PDF et du rapprochement d’article existants conservés après
  mutualisation ; Ruff/syntaxe des trois fichiers JavaScript/diff-check réussis.
  Un E702 de mise en forme du test initial a été corrigé avant recette finale.
- Empreintes historiques inchangées :
  - base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  - référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

Fixtures NON OFFICIELLES temporaires uniquement. Unicode et page très longue
également vérifiés par réponse worker contrôlée, sans prétendre qualifier leur
rendu dans des PDF officiels. Aucun compte/corpus national créé pour la recette.

## Limites et mission restante

Justification retrouvée ≠ portée juridique ou preuve authentifiée ; absence ≠
erreur. Pas d’OCR, alignement visuel/flou, contrôle multi-pages, attestation humaine,
consolidation ou droit à date. Worker borné ≠ sandbox OS ; pagination ≠ RAM globale
constante ; JSDOM ≠ recette visuelle/accessibilité complète ou charge nationale.

**0 nouvel original officiel acquis ; 0 article/code national officiel validé ;
0 publication active. Complétude réglementaire non établie.** Collecte officielle,
StarterPack, tarif/fiscalité, relations transversales prouvées, validation/publication
et intégration métier complète restent à réaliser. Journaux locaux hors commit.

Aperçu backend redémarré sur `0.0.0.0:8000` : coque/module/service worker v56
HTTP 200 avec hôte distant de prévisualisation ; nouveau rapprochement anonyme
HTTP 403 sans résultat. Empreintes historiques inchangées après redémarrage.
