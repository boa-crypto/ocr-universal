# Rapport lot 46 — recherche tarifaire multicritère explicite

7 novembre 2026. Branche `arena/2cd4c91a-ocr-universal`.

## Livré après audit

Audit du moteur littéral FR/AR, de ses preuves de correspondance, des gardes de
revue et des exports. Ajout sans attribut produit ou raisonnement juridique inventés :

- Cinq critères nommés (désignation, matière, fonction, usage, caractéristiques),
  conjonction sur une même ligne, préfixe ASCII facultatif et pagination séparée.
- Preuves par critère/terme et libellé FR/AR ; libellés et codes originaux conservés.
- Service `rechercher_tarif_criteres`, CLI `customs-tariff-criteria`, API dédiée
  `/lots/{id}/tariff-criteria`, opération `recherche_tarif_criteres` tarif uniquement.
- Interface intégrée, suite restituant les filtres exacts, ouverture de fiche et
  export à provenance simple ; schéma/contrôleur hors ligne et cache v66 actualisés.

[Contrat et limites](RECHERCHE_TARIF_CRITERES.md), [tableau global](TABLEAU_LOTS.md).

## Qualification exécutée

- **1 769 tests Python réussis**, sélection étendue **53 fichiers**, **42,34 s**,
  **1 avertissement** Starlette/httpx préexistant. Pas la suite OCR entière.
- **28 nouveaux cas Python** : critères FR/AR et preuves distinctes, AND d'une même
  ligne, pas de synonymes/traduction/matière inventée ou mesure fiscale recherchée,
  préfixes/pagination, paramètres avant lecture, CLI, types/droits, audit 503,
  épingle du résultat et export contrôlé, archives inchangées.
- **158 scénarios JSDOM réussis**, dont **6 nouveaux** : paramètres, fiche,
  restitution des critères lors d'une suite, vide/préfixe non ASCII refusés,
  ancienne suite inerte après changement de lot et audit 503.
- Quatre parcours UI/HTTP/API réelle NON OFFICIELS : **70 exports JSON vérifiés
  hors ligne** (17 pour CSV/XLSX/XLS, 19 pour PDF transcrit), **4 copies PDF Code**.
  Nouvelle recherche puis pagination réelles avec preuve par critère, export des
  filtres exacts et état non certifié vérifiés.
- Ruff, syntaxe des trois JS et diff-check : succès. SHA historiques inchangés :
  base `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  référentiels `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et état global

Critères = étiquettes explicites de requête, pas attributs techniques certifiés.
Pas d'IA, score, RGI, notes/exclusions, rapprochement fiscal, taux ou droit à date
ajoutés. **0 original officiel acquis, 0 article/code officiellement validé,
0 publication active.** Mission globale partielle.

Dernière suite complète : celle du **lot 45**, 2 773 réussites, 18 échecs OCR,
11 ignorés. **Non relancée intégralement pour ce lot** ; ne pas présenter ces
chiffres comme une nouvelle recette complète verte. OCR Tesseract/Indra non
provisionné ; les chantiers du bilan de réception restent ouverts.

Aperçu redémarré sur `0.0.0.0:8000`, racine/module/SW v66 accessibles avec Host
distant, route anonyme refusée 403. Données et journaux historiques conservés,
aucun lot réel inscrit ou réécrit. Pas recette nationale ou navigateurs réels.
