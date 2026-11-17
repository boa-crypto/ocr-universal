# Rapport lot 43 — lecture native du PDF fiscal archivé

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit et livré

Audit du worker PDF et du rejeu autonome 42 ; réutilisation sans moteur parallèle :

- Service `lire_page_pdf_mesures`, paramètres avant lecture, rejeu et relecture SHA
  du PDF puis worker commun borné. Rapport distinct, texte/page physique, jamais
  mesure extraite ou transcription comparée. Rapport d'import conservé inchangé.
- CLI `customs-fiscal-pdf-read`, route dédiée `/lots/{id}/fiscal-pdf`, opération
  `lecture_pdf_mesures`, types et source PDF exacts contrôlés. Anciennes routes
  Code et autres incompatibilités préservées, audit/épingles/no-store réutilisés.
- Interface avec lecteur fiscal séparé, accès depuis inventaire, fragments/pages
  suivants et texte littéral sûr ; cache v64-fiscal-pdf. Aucun PDF brut servi.
- Export partiel à provenance simple, whitelist et schéma hors ligne actualisés.

[Contrat et limites](LECTURE_PDF_MESURES.md), [tableau des restes](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 719 tests Python réussis**, sélection étendue **51 fichiers**, **40,49 s** ;
  **1 avertissement** préexistant Starlette/httpx. Pas la suite OCR entière.
- **36 nouveaux cas Python** : texte réel PDFium, fragments, pages, SHA PDF et
  transcription, archives/rapport d'import inchangés, paramètres avant lecture,
  types/source/page invalides, altération et relecture, worker timeout/crash/JSON/
  type/taille, PDF blanc/chiffré/faux, CLI, autorisations, audit obligatoire,
  provenance de résultat épinglée, refus mixtes et export hors ligne.
- **146 scénarios JSDOM réussis**, dont **8 nouveaux** : lecteur réservé aux
  mesures, route dédiée, texte hostile littéral, paramètres invalides, pagination
  Unicode/page, mauvaise empreinte, sans texte/OCR, anciens boutons et audit 503.
- Pont interface/HTTP/API réelle : quatre parcours CSV/XLSX/XLS/PDF transcrit NON
  OFFICIELS. **65 exports JSON vérifiés hors ligne** (16 par parcours, 17 pour PDF
  avec la lecture fiscale), **4 copies PDF Code** conservées. Le parcours PDF ouvre
  la source fiscale depuis l'inventaire, lit la page suivante, affiche son fragment
  et exporte la provenance ; aucune copie binaire fiscale ajoutée.
- Régression du lecteur Code, rapprochements PDF précédents, imports et empreintes
  historiques des lots JSON/CSV/XLSX/XLS : succès. Ruff, syntaxe des trois JS et
  `git diff --check` : succès. Pas recette Chrome/Firefox, visuelle ou nationale.
- Empreintes historiques inchangées : base
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ; référentiels
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Mission globale et limites

**0 nouvel original officiel acquis, 0 article/code10 officiel validé,
0 publication active.** Texte natif ≠ fidélité des mesures ou localisation de leurs
références. Aucun taux, période ou code rapproché avec le contenu du PDF. Acquisition,
rapprochement juridique, contrôle humain, droit à date, recherche métier/IA,
publication et recette nationale restent ouverts. Pas OCR, calcul réel, innocuité
universelle, quota global, mémoire constante, WORM ou transaction multi-dossiers.
L'épingle de la provenance retournée n'est pas une transaction filesystem.

## Aperçu et conservation

Aperçu redémarré sur `0.0.0.0:8000`, cache v64-fiscal-pdf. Racine/module/service
worker accessibles avec Host distant, route fiscale anonyme refusée 403.
Empreintes historiques revérifiées ; aucun lot réel inscrit ou réécrit.
Journaux existants préservés hors commit.
