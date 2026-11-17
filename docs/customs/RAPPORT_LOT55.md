# Rapport lot 55 — références d'empreintes et recette complète actualisée

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

Ajout de références SHA256 facultatives aux rejeux simples et aux paires : export
brut et manifeste(s) explicitement fournis par l'opérateur. Préconditions validées
avant analyse JSON ou avant service/worker, puis manifestes du résultat revérifiés.
Un échec donne refus/code 2. Pas référence attendue choisie dans le rapport lui-même,
ni authenticité déduite de la seule égalité des empreintes.

[Options, ordre des contrôles et limites](EMPREINTES_ATTENDUES_REJEU.md).

## Qualification exécutée

- **2 016 tests Python sélectionnés réussis**, **62 fichiers**, **47,05 s**,
  1 avertissement Starlette/httpx préexistant ; Ruff et diff-check réussis.
- **27 nouveaux cas Python** : références absentes/partielles/complètes, formats
  invalides avant fichier, enveloppe modifiée qui échoue à l'empreinte, refus avant
  parseur ou lecteur PDF, manifeste restitué différent, symlinks, trois épingles
  ordonnées pour une paire et options CLI simples/paires.
- **186 scénarios JSDOM existants réussis**, pas nouveau scénario UI attribué.
  Quatre parcours UI/HTTP/API NON OFFICIELS : **70 exports structurellement contrôlés
  et rejoués identiquement avec références attendues**, 58 simples dont 14 PDF sur
  opt-in et 12 paires, 4 copies PDF Code. Références du test calculées sur ses
  fixtures : cela qualifie les contrôles, pas une source officielle authentifiée.

## Nouvelle suite complète

**3 048 réussis, 18 échecs, 11 ignorés, 1 avertissement, 206,23 s**, soit 3 077 tests.
**Suite non verte.** Les 18 identifiants d'échec sont identiques au lot 50, comparaison
JUnit effectuée. Tesseract et Indra toujours absents ; aucun échec masqué ou déclaré
résolu, aucune preuve qu'un provisionnement seul suffirait à tout rendre vert.
Détail persistant : [RECETTE_LOT55.json](RECETTE_LOT55.json). Recettes 45 et 50
conservées comme historiques, pas réécrites.

Huit fixtures binaires régénérées ont été explicitement restaurées (propres avant
recette) ; journaux historiques préservés hors commit. SHA inchangés :
- base `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

**0 nouvel original officiel acquis, 0 article/code national officiellement validé,
0 publication active.** Mission partielle : pas signature, authenticité officielle,
registre, décision humaine, IA de classement ou fiscalité applicable attestés.
Interface, aperçu et cache v69 inchangés ; aucune nouvelle fonction UI revendiquée.
