# Rapport lot 58 — pistes documentaires partielles explicites

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

Ajout Python/CLI `customs-tariff-candidates`, distinct de la recherche AND conservée.
Admission d'une ligne sur au moins une paire critère-terme littérale FR/AR, tri
public par critères complets puis paires retrouvées puis code10. Provenance,
positions, extraits, termes non retrouvés et pagination sont exposés. Pas score de
confiance, IA, attribut certifié, RGI ou classement validé. Aucun fallback implicite.

[Contrat et limites](PISTES_TARIFAIRES.md), [recette détaillée](RECETTE_LOT58.json).

## Qualification locale

- **36 nouveaux tests réussis**, paramètres invalides avant I/O, AND inchangé,
  admission partielle, FR/AR et spans originaux, priorités/égalités stables,
  déduplication/paires non indépendantes, source réordonnée, pagination, préfixe,
  extraits plafonnés à 16, exclusion des mesures et refus des archives altérées.
- Lanceur ciblé : **2 079 réussis, 65 fichiers, 0 ignoré, 1 avertissement,
  52,78 s**. Ruff code 0 et **186 scénarios JSDOM** existants réussis.
- Les quatre ponts UI/API existants rejouent encore leurs **70 exports** (58
  simples dont 14 PDF, 12 paires) et vérifient 4 copies PDF Code. Cela qualifie la
  non-régression des parcours existants, **pas une UI ou un export de pistes**.
- Nouvelle suite complète exécutée : **3 111 réussis, 18 échecs, 11 ignorés,
  1 avertissement, 214,61 s**, soit 3 140 tests. **Suite non verte, code 1**.
  Les 18 identifiants d'échec sont identiques au lot 56, vérification JUnit.
  Aucun échec OCR masqué, ignoré ou déclaré résolu ; Tesseract/Indra toujours absents.
- **27/27 empreintes conformes à la recette 56 après la complète**, sans restauration.
  Aucun fichier de fixture suivi modifié. Journaux historiques hors commit.
  Artefacts bruts locaux : `/home/user/recettes-unocr/lot58`.

## CI distante

Code du lot 58 au commit **`3de68f4a`**, vérifié à distance : run
**[42390539305](https://github.com/boa-crypto/ocr-universal/actions/runs/42390539305)**
terminé **success**, job **1 min 15 s**, installation stricte, recette ciblée et
upload des artefacts réussis. Vérification `gh run watch --exit-status` code 0 puis
`gh run view`. Runner Ubuntu 24.04, Node 24, Python 3.11. Les métriques détaillées
ci-dessus sont celles de la recette locale ; pas de relecture locale du JUnit
hébergé sur le stockage externe GitHub revendiquée. Ce succès ciblé ne rend pas
la suite complète ci-dessus verte.

Aucun nouvel endpoint, écran, autorisation, export, cache, intégration au pipeline
marchandises/facturation ou publication active. La phase IA/recherche métier reste
partielle : pistes littérales seulement. **0 nouvel original officiel acquis,
0 article/code national officiellement validé, 0 publication active.**
