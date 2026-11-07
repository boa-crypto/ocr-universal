# Rapport lot 60 — interface des pistes et nouvelle recette complète

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

Action explicite de pistes partielles dans la revue existante : résumé de rang,
critères/paires retrouvés, termes non retrouvés, extraits FR/AR, fiche exacte par
clic, pagination conservant les paramètres du rapport et export relu/audité.
Pas de basculement automatique depuis la recherche stricte ni classement retenu.

[Interface et protections](INTERFACE_PISTES_TARIFAIRES.md),
[recette machine](RECETTE_LOT60.json).

## Qualification exécutée

- **212 scénarios JSDOM réussis, dont 26 nouveaux** : action distincte, paramètres,
  rendu textuel hostile/Unicode, compteurs/rangs, pagination, fiche, vide/hors page,
  refus des types/paramètres, changements lot/compte, réponse tardive, audit/droits,
  cohérence des rapports et export bloqué sur 503.
- Sélection Python : **2 124 réussis, 66 fichiers, 0 ignoré, 1 avertissement,
  51,79 s**. Les quatre ponts existants sont enrichis sans nouveau cas Python
  artificiellement compté ; Ruff, syntaxe JS et diff-check réussis.
- **74 exports UI/API contrôlés et rejoués identiquement** : 62 simples dont 14
  PDF sur opt-in et 12 paires. Parmi eux, **4 nouveaux exports de pistes**, un par
  parcours fiscal CSV/XLSX/XLS/PDF ; le lot tarifaire recherché reste la fixture
  JSON commune, pas une qualification de quatre nouveaux lecteurs de tarif.
  4 copies PDF Code vérifiées. Les cinq rapports API seuls du lot 59 restent une
  qualification séparée, pas cinq nouveaux parcours navigateur.
- Nouvelle suite complète : **3 156 réussis, 18 échecs, 11 ignorés,
  1 avertissement, 220,78 s**, soit **3 185 tests**, code **1**. **Suite non verte**.
  Les 18 identifiants d'échec sont identiques au lot 58 (JUnit comparés).
  Tesseract/Indra toujours absents ; aucun échec masqué ou déclaré résolu.
- **27/27 empreintes conformes à la référence 56 après la complète**, sans
  restauration ; fixtures suivies inchangées, journaux historiques hors commit.
  Artefacts bruts conservés dans `/home/user/recettes-unocr/lot60`.

## CI et aperçu

Code **`49e36b49`** : run
**[42391862178](https://github.com/boa-crypto/ocr-universal/actions/runs/42391862178)**
terminé **success**, installations/recette/upload réussis, état et révision
confirmés par API. Ubuntu 24.04 / Node 24 / Python 3.11. Les métriques détaillées
ci-dessus sont locales, pas extraites d'un JUnit distant téléchargé. La réussite
ciblée ne rend pas la CI OCR complète verte.

Coquille **SW v70** ; aperçu relancé sur 0.0.0.0:8000 pour charger aussi l'API récente.
Smoke HTTP local avec Host e2b : `/`, module, SW et OpenAPI **200** ; route pistes
présente dans OpenAPI, accès anonyme **403**. Ce n'est pas un test navigateur distant.

**Mission partielle : 0 nouvel original officiel acquis, 0 article/code national
officiellement validé, 0 publication active.** Pas IA, RGI, décision humaine,
pertinence juridique, source authentifiée ou calcul fiscal applicable attestés.
