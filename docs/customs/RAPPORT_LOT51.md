# Rapport lot 51 — rejeu typé Code, tarif et mesures

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

## Livraison

- Service générique `verifier_rejeu_export`, type obligatoire en Python ; CLI
  `--type-lot code|tarif|mesures`, défaut tarif historique conservé.
- Rejeu de recherche Code/tarif, lecture d'article, fiche code10, recherche de
  mesures natives/autonomes, plus critères du lot 50. Matrice fermée et filtres
  exacts ; type jamais deviné ni lecteur de repli essayé.
- Paramètres HTTP traduits comme dans l'API ; borne Unicode complète des articles,
  codes textuels, zéros résultats et objets absents conservés.
- Même comparaison complète et mêmes refus de sécurité ; fonction historique du
  lot 50 toujours limitée aux critères. Pas de nouvelle route HTTP/écriture/UI.

[Matrice des routes, limites et contrat](REJEU_EXPORTS_TYPES.md).

## Vérification exécutée

**1 888 tests Python sélectionnés réussis**, **58 fichiers**, **45,10 s**,
1 avertissement Starlette/httpx préexistant. **35 nouveaux cas** : douze lectures
réelles API selon les trois types, altération du contenu détectée, routes/types
incompatibles ou inconnus refusés, paramètres ambigus/encodages/pagination,
archive d'un mauvais type, ID article requis, CLI, compatibilité et grand offset
Unicode d'article. Archives inchangées lors des contrôles.

**186 scénarios JSDOM existants réussis**, aucun nouveau scénario UI attribué à
ce lot. Quatre parcours UI → HTTP → API réelle NON OFFICIELS : **70 exports JSON
contrôlés structurellement, 20 rejeux typés identiques** (cinq par format, incluant
les quatre critères du lot 50), **4 copies PDF Code**. Pas de navigateurs réels
ou de recette nationale qualifiés. Ruff et diff-check : succès.

Empreintes historiques inchangées :
- base `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.
Journaux préexistants conservés hors commit. Interface et cache v69 inchangés.

## État global

Dernière suite complète : **lot 50**, **2 885 réussites, 18 échecs OCR,
11 ignorés, 2 avertissements**, 208,03 s. **Non relancée intégralement au lot 51** ;
ne pas présenter la sélection ci-dessus comme recette globale verte. Tesseract
et module Indra restent absents ; aucun échec annoncé comme résolu.

**0 nouvel original officiel acquis, 0 article/code national officiellement validé,
0 publication active.** Reproductibilité locale ≠ origine officielle, registre,
audit, signature, décision humaine ou validité juridique. Mission partielle.
