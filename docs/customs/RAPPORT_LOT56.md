# Rapport lot 56 — isolation des générations de fixtures

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

Les générations de documents déclenchées par pytest se font désormais dans ses
répertoires temporaires. Plus de restauration manuelle des huit PDF/DOCX suivis
après la recette exécutée. Les fichiers restent réellement générés puis traités.
La génération manuelle sans destination reste compatible et explicitement distincte.

[Détails et commande](RECETTE_ISOLEE.md), [résultats machine](RECETTE_LOT56.json).

## Qualification exécutée

- Ciblage isolation + formulaire/corrections/recherche/parcours/reprise : **57
  réussis, 1 avertissement, 15,06 s**, dont **9 nouveaux cas d'isolation**.
- Sélection habituelle étendue à ces nouveaux cas : **2 025 réussis, 63 fichiers,
  1 avertissement, 48,19 s**.
- **186 scénarios JSDOM** existants réussis ; les quatre ponts UI/HTTP/API ont encore
  contrôlé et rejoué **70 exports** avec références attendues (58 simples dont 14
  PDF, 12 paires) et contrôlé 4 copies PDF Code. Pas de nouvelle fonctionnalité UI.
- Nouvelle suite complète : **3 057 réussis, 18 échecs, 11 ignorés, 1 avertissement,
  211,56 s**, soit **3 086 tests**. **Suite non verte** ; liste des 18 échecs
  identique au lot 55, comparaison JUnit. Tesseract/Indra toujours absents ; aucun
  échec caché, réétiqueté ou déclaré résolu.
- **27/27 SHA256 identiques avant/après la suite complète**, sans `git restore` :
  25 fixtures suivies et les deux JSON historiques. Ruff et diff-check réussis.
  Les journaux historiques ne sont ni restaurés ni ajoutés au commit.

Aucun changement de code de production. Pas test navigateur réel, sandbox,
absence garantie de toute écriture transitoire, déterminisme binaire de PDF/DOCX,
ni recette de charge nationale revendiqués. Recettes 45/50/55 conservées.

**Mission réglementaire toujours partielle : 0 nouvel original officiel acquis,
0 article/code national officiellement validé, 0 publication active.** Cette
correction qualifie l'outillage de recette, pas les références juridiques/fiscales.
