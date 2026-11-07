# Rapport lot 52 — rejeu des provenances, historiques et relations déclarés

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

## Livraison

Extension du rejeu local typé à huit familles de routes : contrôle d'archive,
couverture, sources, historique d'article, relations déclarées, écart littéral
de versions du même lot, navigation Code et tarif. Même CLI/service et règles
strictes ; pas de type ou chemin local déduit du rapport.

Deux paginations d'historique et deux offsets Unicode d'écart d'article conservés.
Rapport entier comparé, y compris provenance, fragments, filtres, compteurs et
non-validation. Aucune chronologie déclarée promue en droit à date, relation
validée, source authentifiée ou classement IA.

[Contrat, matrice complémentaire et limites](REJEU_PROVENANCE.md).

## Qualification exécutée

- **1 924 tests Python sélectionnés réussis**, **59 fichiers**, **44,62 s**,
  1 avertissement Starlette/httpx préexistant ; Ruff et diff-check réussis.
- **36 nouveaux cas Python** : 19 lectures API réelles selon les trois types avec
  comparaison et altération détectée, matrice/types/routes/paramètres incompatibles,
  doublons/encodages, IDs requis et faux chemin filesystem dans la navigation Code.
  Archives inchangées pendant les contrôles.
- Le cas de refus `history` de la recette 51 a été remplacé par une autre route
  hors périmètre (`fiscal-pdf`) : historique désormais explicitement pris en charge
  et testé avec ses deux paginations, pas suppression d'une exigence d'intégrité.
- **186 scénarios JSDOM existants réussis**, aucun nouveau scénario UI attribué.
  Quatre parcours UI → HTTP → API réelle NON OFFICIELS : **70 exports JSON vérifiés
  structurellement, 44 rejeux typés identiques** (11 par format, incluant les
  critères antérieurs), **4 copies PDF Code**. Pas de navigateurs réels qualifiés.
- Données historiques inchangées, SHA base :
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

Journaux préexistants conservés hors commit ; interface, aperçu et cache v69
inchangés. Aucun endpoint de lecture de chemins locaux ajouté.

## État global

Dernière suite complète : **lot 50**, **2 885 réussis, 18 échecs OCR, 11 ignorés,
2 avertissements, 208,03 s** ; **non relancée intégralement au lot 52**. Les échecs
Tesseract/Indra ne sont ni masqués ni annoncés résolus.

**0 nouvel original officiel acquis, 0 article/code national officiellement validé,
0 publication active.** Mission partielle ; reproductibilité locale n'est pas
origine officielle, signature, registre, décision humaine ou validation juridique.
