# Rapport lot 27 — rapprochement littéral article / PDF source

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit préalable et livraison

Inspection des lecteurs d’article/PDF, du worker, des contrôles de lots, de la revue
et des exports existants avant implémentation. Réutilisation de ces services :
pas de second extracteur ou d’interface autonome.

- Service central `rapprocher_fragment_article_pdf` : recherche stricte d’un
  fragment de transcription dans une page physique choisie explicitement.
- Source imposée par la référence de l’article, première occurrence et positions
  Unicode Python ; recherche sur la page entière bornée, pas seulement son aperçu.
- Cas absents/vides/blancs sans extraction et page sans texte natif distingués ;
  aucune égalité vide positive ou substitution de langue.
- Extraction PDF mutualisée avec le lecteur existant : un seul rejeu, SHA revérifié
  avant worker ; limites PDF et protections existantes conservées.
- CLI `customs-code-article-pdf-match`, route de revue `/lots/{lot_id}/article-pdf-match`,
  mêmes droits/épingle/audit obligatoire/no-store.
- Formulaire intégré, reprise du fragment suivant, ouverture de la page rapprochée,
  export partiel relu et contrôle hors ligne ; service worker `v53-article-pdf-match`.

Contrat et interprétation : [RAPPROCHEMENT_ARTICLE_PDF.md](RAPPROCHEMENT_ARTICLE_PDF.md).
Tableau actualisé des lots et restes : [TABLEAU_LOTS.md](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 177 tests Python réussis**, sélection étendue de 35 fichiers isolée avant
  import API ; 1 avertissement préexistant Starlette/httpx, durée 23,90 s.
  Il ne s’agit pas de l’ensemble de la suite OCR.
- **30 nouveaux cas Python** : présence/absence/page blanche, cas sans extraction,
  Unicode strict/pagination, recherche après le 16 000e caractère, première
  occurrence, un seul rejeu, PDF altéré après rejeu, page absente, CLI, droits,
  audit/épingle/503, export et absence de mutation du corpus.
- **68 scénarios JSDOM réussis**, dont 6 nouveaux : paramètres/source imposée,
  ouverture de page, suite Unicode, indisponibilité/rendu sans HTML, invalides/tarif,
  ancienne action inerte, panne d’audit.
- Pont interface → HTTP → API réelle : rapprochement positif d’un fragment de
  fixture sur la page 2 de sa source imposée, maintien du statut non vérifié,
  lecture de la page rapprochée ; cinquième export relu et contrôlé hors ligne.
- Recette initiale du pont : un échec de sélecteur de limite absent. Attributs
  stables de limite/décalage ajoutés au formulaire et fragment de fixture choisi
  explicitement ; parcours corrigé puis recette étendue réussie.
- Ruff, syntaxe des trois fichiers JavaScript et `git diff --check` réussis.
- Empreintes historiques inchangées :
  - base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  - référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

Tests sur fixtures NON OFFICIELLES temporaires uniquement. Cas Unicode et texte
natif très long également testés par réponse worker contrôlée, sans prétendre
qualifier leur rendu réel dans un PDF officiel. Aucun compte/lot national créé.

## Limites et mission restante

Présence ≠ fidélité complète, emplacement juridique ou authenticité. Absence ≠
erreur de transcription. Pas d’OCR, alignement visuel/flou, contrôle multi-pages,
attestation humaine, consolidation ou validation juridique. Les textes conservent
leur statut non vérifié. Bornes de fragments ≠ RAM globale constante ; worker ≠
sandbox OS ; JSDOM ≠ recette visuelle/accessibilité complète ou charge nationale.

**0 nouvel original officiel acquis ; 0 article/code national officiel validé ;
0 publication active. Complétude réglementaire non établie.** Corpus officiel,
StarterPack, tarif national, fiscalité sourcée, validation/publication et intégration
métier complète restent à réaliser. Les calculs non sourcés restent bloqués.
Journaux locaux conservés hors commit.

Aperçu backend redémarré sur `0.0.0.0:8000` : coque/module/service worker v53
HTTP 200 avec hôte distant de prévisualisation ; rapprochement anonyme HTTP 403
sans résultat exposé. Empreintes historiques inchangées après redémarrage.
