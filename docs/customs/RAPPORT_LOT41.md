# Rapport lot 41 — mesures autonomes XLS OLE/BIFF8 textuel

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit et livré

Audit du lecteur XLS binaire restreint déjà utilisé pour les nomenclatures, du
préparateur autonome et de l'adaptateur XLSX 40. Extension sans nouveau magasin :

- Format autonome XLS OLE/BIFF8 à feuille/en-tête/mapping explicites, lecteur
  existant et gardes binaires réutilisés, références aux lignes réelles.
- Cellules textuelles ou vides, y compris colonnes non mappées ; nombres, styles
  de codes à zéros initiaux, dates Excel, booléens et formules non convertis.
- Contrôle binaire global, notamment formule sur une autre feuille refusée ;
  sous-ensemble strict, pas prise en charge de tous les fichiers XLS.
- Source/sidecar exacts, SHA/rejeu et source unique cohérente, schémas/CLI étendus.
  Archives JSON/CSV/XLSX historiques préservées ; pas activation ou fusion fiscale.
- Recherche/revue/consultation et sauvegarde/reprise existantes vérifiées en XLS.

[Contrat et limites](MESURES_AUTONOMES_XLS.md), [tableau des restes](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 637 tests Python réussis**, sélection étendue **49 fichiers**, **35,40 s** ;
  **1 avertissement** préexistant Starlette/httpx. Pas la suite OCR entière.
- **49 nouveaux cas Python** : plan sans écriture, précision/zéro/null/FR/AR,
  octets et références, types Excel/formules/autre feuille/colonnes non importées,
  mapping/en-têtes/feuille invalides, fusions, cinq bornes lecteur, faux XLS/OLE
  tronqué, vide, CLI, archives altérées ou deux sources, garde de format interne,
  API/consultation sans rattachement, sauvegarde/reprise et compatibilité XLSX 40.
- Empreintes obtenues avec préparateur et adaptateur du commit **e66148c2** :
  lot et rapport XLSX identiques sur une fixture dont seules les dates ZIP et
  propriétés temporelles ont été neutralisées pour le test. Aucun original réel
  modifié. Tests d'empreintes JSON 38 et CSV 39 également conservés et réussis.
- **138 scénarios JSDOM réussis** (inchangés). Pont interface/HTTP/API réelle
  désormais exécuté **trois fois**, avec mesures CSV, XLSX et XLS NON OFFICIELLES.
  Format, référence, recherche FR/AR, sources, couverture et consultation séparée
  contrôlés : **16 exports JSON + 1 copie PDF Code par parcours**, soit
  **48 exports JSON vérifiés hors ligne et 3 copies PDF** au total.
  Pas une recette Chrome/Firefox, visuelle/accessibilité ou nationale.
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
Pas de calcul réel, mémoire constante, innocuité universelle, WORM ou transaction
multi-dossiers. Les restrictions XLS restent plus fortes que celles de XLSX.

## Aperçu et conservation

Backend de l'aperçu redémarré sur `0.0.0.0:8000`, interface/cache v63 inchangés.
Racine/module/service worker accessibles avec Host distant, consultation anonyme
refusée 403. Empreintes historiques revérifiées ; aucun lot réel inscrit, réécrit
ou fusionné. Journaux existants préservés hors commit.
