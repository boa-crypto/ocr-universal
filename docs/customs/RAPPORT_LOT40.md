# Rapport lot 40 — XLSX textuel de mesures autonomes

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit et livré

Audit du lecteur XLSX borné déjà utilisé pour les nomenclatures et des préparateurs
JSON/CSV autonomes. Réutilisation, sans nouveau magasin ni moteur de calcul :

- XLSX avec feuille, en-tête et mapping déclarés ; cellules mappées textuelles,
  jamais codes/taux numériques convertis, dates Excel ou formules évaluées.
- Références aux lignes réelles, colonnes et feuilles non importées signalées ;
  gardes ZIP/XML et bornes existantes réutilisées, 100 000 mesures maximum.
- Source/sidecar exacts, archive SHA/rejeu, une seule source cohérente avec son
  format ; schémas et CLI étendus, options étrangères au format refusées.
- Revue/recherche/consultation séparée tarif-mesures et sauvegarde/reprise existantes
  vérifiées avec XLSX ; compatibilité des sorties JSON/CSV historiques conservée.

[Contrat et limites](MESURES_AUTONOMES_XLSX.md), [tableau des restes](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 587 tests Python réussis**, sélection étendue **48 fichiers**, **31,93 s** ;
  **1 avertissement** préexistant Starlette/httpx. Pas la suite OCR entière.
- **46 nouveaux cas Python** : plan sans écriture, octets source/sidecar,
  précision/zéro/null/FR/AR, références, cellules numériques et formatées, dates,
  formules y compris colonne non importée, en-têtes/mapping/feuilles invalides,
  dimensions trompeuses, DTD/macros, six bornes lecteur, vide, CLI, altération,
  deux sources, API et consultation sans rattachement, sauvegarde/reprise.
- Empreintes figées du préparateur 39 (`2ef18216`) : lot et rapport CSV identiques.
  Tests d'empreintes historiques JSON 38 conservés et réussis également.
- **138 scénarios JSDOM réussis** (inchangés). Pont interface/HTTP/API réelle
  exécuté **deux fois**, avec mesures CSV puis XLSX NON OFFICIELLES : recherche
  FR/AR, sources, couverture, consultation séparée, format et ligne de référence
  contrôlés ; **16 exports JSON + 1 copie PDF Code par parcours**, soit
  **32 exports JSON vérifiés hors ligne et 2 copies PDF** au total. Pas une recette
  Chrome/Firefox, visuelle/accessibilité ou nationale.
- Ruff, syntaxe des trois JS et `git diff --check` : succès.
- Empreintes historiques inchangées : base
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ; référentiels
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Mission globale et limites

**0 nouvel original officiel acquis, 0 article/code10 officiel validé,
0 publication active.** Aucun fichier fiscal national réel qualifié. Acquisition,
PDF fiscal autonome, rapprochement juridique, contrôle humain, droit à date,
recherche métier/IA, publication et recette nationale restent ouverts.
Ni code syntaxique ni SHA/rejeu ne prouvent authenticité ou applicabilité.
Pas de calcul réel, mémoire constante, antivirus universel, WORM ou transaction
multi-dossiers. Feuille et préambule non importés ne sont pas validés métier.

## Aperçu et conservation

Backend de l'aperçu redémarré sur `0.0.0.0:8000`, interface/cache v63 inchangés.
Racine/module/service worker accessibles avec Host distant, consultation anonyme
refusée 403. Empreintes historiques revérifiées ; aucun lot réel inscrit, réécrit
ou fusionné. Journaux existants préservés hors commit.
