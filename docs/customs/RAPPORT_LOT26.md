# Rapport lot 26 — navigation de la hiérarchie déclarée du Code

Date : 6 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Livré

- Service central `parcourir_code` : documents séparés, chemins déclarés exacts,
  enfants directs puis versions terminales, pagination et provenance conservée.
- Identité par source et chemin complet, sans fusion par numéro/intitulé.
  Intitulés divergents conservés ; aucun niveau manquant reconstitué.
- CLI `customs-code-tree` et API protégée `/lots/{lot_id}/code-tree`, même
  registre épinglé/rejeu/audit obligatoire/no-store que les autres lectures.
- Revue existante : formulaire, descente, remontée, pagination, lecture exacte
  d’article, désactivation tarif et actions anciennes inertes.
- Export partiel relu et contrôle d’enveloppe étendus ; service worker
  `v52-code-tree`. Aucun schéma métier d’article ou fichier de lot réécrit.

Guide détaillé : [NAVIGATION_CODE.md](NAVIGATION_CODE.md).

## Qualification exécutée

- **1 147 tests Python réussis** : sélection étendue de 34 fichiers, données et
  journaux isolés avant import ; 1 avertissement préexistant Starlette/httpx.
  Durée de la recette finale : 22,25 s. Pas l’ensemble de la suite OCR.
- **30 nouveaux cas Python** : absence de niveaux intermédiaires sans invention,
  variantes d’intitulés, séparation de sources même à chemin identique, dix niveaux
  déclarés, documents sans transcription, tri/pagination/hors fin, paramètres
  refusés avant lecture (dont JSON à clé dupliquée/substitut Unicode isolé), CLI,
  API/droits/tarif/audit/épingle/export et absence de mutation du corpus.
- **62 scénarios JSDOM réussis**, dont 6 nouveaux : descente et lecture exacte,
  pagination/remontée, chemins ou source incohérents sans action, JSON/source/tarif
  invalides sans requête, ancienne action inerte et panne d’audit.
- Pont interface → HTTP → API réelle : racine → document → texte → article →
  version exacte ; quatrième export partiel relu et contrôlé hors ligne.
  PDF, comparaison littérale et tarif continuent à être parcourus/exportés.
  Fixtures NON OFFICIELLES temporaires uniquement, aucun corpus utilisateur créé.
- Ruff, syntaxe des trois fichiers JavaScript et `git diff --check` réussis.
- Empreintes historiques inchangées :
  - base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  - référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

Première recette ciblée : 93 réussites / 4 échecs. La fixture initiale omettait
les niveaux texte/article obligatoires du modèle existant ; elle a été corrigée
sans assouplir le contrat. Les métadonnées de schéma export ont été restaurées.
Les recettes ciblées puis la sélection étendue finale passent.

## Limites et reste de la mission

Pas de hiérarchie officielle constituée, découpage automatique en alinéas, arbre
graphique dépliable, consolidation, chronologie juridique, version applicable ou
validation humaine signée. Les compteurs portent sur les seules transcriptions
reçues ; absence d’enfant ne prouve pas absence nationale. Pagination ≠ RAM
constante ; JSDOM ≠ recette visuelle Chrome/Firefox ou charge nationale.

**0 nouvel original officiel acquis ; 0 article/code national officiel validé ;
0 publication active. Complétude réglementaire non établie.** StarterPack,
originaux/modifications exhaustifs, tarif national courant et sources fiscales
restent à acquérir et valider humainement. Les calculs douaniers réels ne peuvent
pas exploiter ces références non vérifiées. Journaux locaux conservés hors commit.

Aperçu backend redémarré sur `0.0.0.0:8000` : coque, module et service worker
v52 HTTP 200 avec hôte distant de prévisualisation ; nouvelle navigation anonyme
HTTP 403 sans résultat. Empreintes historiques inchangées après redémarrage.
