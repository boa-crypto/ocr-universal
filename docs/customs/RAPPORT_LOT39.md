# Rapport lot 39 — préparation CSV de mesures autonomes

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Livré après audit

Extension de l'import autonome JSON 36 et de sa revue/consultation 37–38 :

- CSV UTF-8/BOM à mapping explicite et délimiteur déclaré ; cellules textuelles,
  codes sans conversion et taux précis/zéro/null distincts, FR/AR et multilignes.
- Références locales à la fin physique de chaque enregistrement ; colonnes non
  importées signalées ; fichiers incohérents refusés avant création du dossier.
- Archive originale CSV + sidecar exacts, manifeste/SHA/rejeu strict, une seule
  source cohérente avec son format ; sorties JSON historiques inchangées.
- CLI existante étendue, schéma de configuration dédié et schémas source actualisés.
  Revue/recherche et consultation tarif/mesures existantes sans fusion réutilisées.
- Sauvegarde/reprise opaque existante vérifiée avec une archive CSV et son mapping.

[Contrat et limites](MESURES_AUTONOMES_CSV.md), [tableau des restes](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 540 tests Python réussis**, sélection étendue **47 fichiers**, **28,07 s** ;
  **1 avertissement** préexistant Starlette/httpx. Pas la suite OCR entière.
- **42 nouveaux cas Python** : BOM/dialectes, FR/AR/multiligne, codes et précision,
  vide/null/zéro, mapping absent/invalide/partagé, en-têtes, largeur, syntaxe et
  encodage invalides, doublons, CLI/schéma, archives altérées ou deux sources,
  rejeu et sauvegarde/reprise, API et consultation sans fiche tarif fabriquée.
- Compatibilité JSON : empreintes du lot normalisé et du rapport produites par le
  code précédent `b4142425`, identiques après extension sur la même fixture.
- **138 scénarios JSDOM réussis** (inchangés). Pont UI/HTTP/API réelle désormais
  alimenté par une **archive CSV NON OFFICIELLE** pour les mesures autonomes :
  format CSV et repérage physique vérifiés, recherche FR/AR, sources, couverture,
  consultation séparée, **16 exports JSON** relus/vérifiés hors ligne et
  **1 copie PDF Code**. Pas une recette Chrome/Firefox, visuelle ou nationale.
- Ruff, syntaxe JS et `git diff --check` vérifiés.
- Empreintes historiques inchangées : base
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ; référentiels
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Mission globale et limites

**0 nouvel original officiel acquis, 0 article/code10 officiel validé,
0 publication active.** Import technique CSV disponible mais aucun fichier fiscal
national officiel qualifié. XLSX/PDF autonomes, acquisition, rapprochement juridique,
contrôle humain, droit à date, IA métier, publication et recette nationale restent
ouverts. Ni code syntaxique ni SHA/rejeu ne prouvent authenticité ou applicabilité.
Pas de calcul réel, mémoire constante, WORM ou transaction multi-dossiers.

## Aperçu et conservation

Backend de l'aperçu redémarré sur `0.0.0.0:8000`, interface/cache v63 inchangés.
Racine/module/service worker accessibles avec Host distant, consultation anonyme
refusée 403. Empreintes historiques revérifiées ; aucun lot réel inscrit, réécrit
ou fusionné. Journaux existants préservés hors commit.
