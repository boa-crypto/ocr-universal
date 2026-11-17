# Rapport lot 42 — PDF fiscal opaque et transcription JSON déclarée

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit et livré

Audit de l'archivage PDF opaque du Code et des préparations autonomes 36/39–41.
Extension explicite, sans OCR, nouveau magasin, import HTTP ou moteur fiscal :

- PDF original avec SHA/préfixe seulement, transcription JSON séparée requise par
  `--transcription`. Options tabulaires et transcription séparée hors PDF refusées.
- Références déclarées conservées sans localisation automatique ; taux textuels,
  codes exacts, null/zéro et périodes propres au contrat existant.
- Rapport distingue mesures transcrites et PDF non lu : compte source null,
  transcription non vérifiée, lecture/structure PDF false, SHA de transcription.
- Archive à six fichiers, octets originaux exacts, SHA et rejeu des deux entrées ;
  borne reçue totale 128 Mio et bornes communes. JSON/CSV/XLSX/XLS inchangés.
- Recherche/revue/consultation séparée et sauvegarde/reprise existantes vérifiées.
  Routes PDF Code toujours refusées sur ces lots, aucun téléchargement fiscal ajouté.

[Contrat et limites](MESURES_AUTONOMES_PDF.md), [tableau des restes](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 683 tests Python réussis**, sélection étendue **50 fichiers**, **38,82 s** ;
  **1 avertissement** préexistant Starlette/httpx. Pas la suite OCR entière.
- **45 nouveaux cas Python** : plan sans écriture, source/transcription/sidecar
  exacts, précision/zéro/null/FR/AR/dates, références propres, absence/localisation
  non vérifiée, options et JSON invalides, bornes, CLI, archives altérées ou deux
  sources, re-hachage y compris espaces sans effet sémantique, API, refus PDF Code,
  consultation sans rattachement et sauvegarde/reprise.
- Compatibilité : lot et rapport XLS identiques au préparateur/adaptateur du commit
  **7cf11a79** sur fixture NON OFFICIELLE. Tests d'empreintes JSON 38, CSV 39 et
  XLSX 40 également conservés et réussis.
- **138 scénarios JSDOM réussis** (inchangés). Pont interface/HTTP/API réelle
  exécuté **quatre fois** : mesures CSV, XLSX, XLS et PDF + transcription NON
  OFFICIELS. Recherche des descriptions FR/AR, sources, couverture, consultation,
  format et référence vérifiés ; cas PDF : absence d'extraction et statut non
  vérifié contrôlés. **16 exports JSON + 1 copie PDF Code par parcours**, soit
  **64 exports JSON vérifiés hors ligne et 4 copies PDF Code** au total.
  Aucune copie PDF fiscal servie, aucune recette Chrome/Firefox ou nationale.
- Ruff, syntaxe des trois JS et `git diff --check` : succès.
- Empreintes historiques inchangées : base
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ; référentiels
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Mission globale et limites

**0 nouvel original officiel acquis, 0 article/code10 officiel validé,
0 publication active.** Aucun fichier fiscal national réel qualifié. Signature
PDF seule ne prouve ni structure lisible ni innocuité. Référence fournie ne prouve
pas présence sur une page : même une page inexistante peut rester une déclaration
non vérifiée. Acquisition, lecture/rapprochement fiscal PDF, contrôle humain,
droit à date, recherche métier/IA, publication et recette nationale restent ouverts.
Pas d'OCR, extraction de taux, calcul réel, mémoire constante, WORM ou transaction
multi-dossiers. Les tests ne valident pas la fidélité des transcriptions.

## Aperçu et conservation

Backend de l'aperçu redémarré sur `0.0.0.0:8000`, interface/cache v63 inchangés.
Racine/module/service worker accessibles avec Host distant, consultation anonyme
refusée 403. Empreintes historiques revérifiées ; aucun lot réel inscrit, réécrit
ou fusionné. Journaux existants préservés hors commit.
