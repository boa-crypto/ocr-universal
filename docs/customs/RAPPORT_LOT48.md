# Rapport lot 48 — mots entiers normalisés et retrait des outils sur refus

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

## Livraison

- Mode optionnel `mots_entiers` pour les critères tarifaires ; le défaut
  `sous_chaine` est conservé. Évite notamment « acier » trouvé dans « glacier ».
- Service, CLI `--match-mode`, enum API et sélecteur d'interface intégrés ; mode
  restitué dans les filtres, réappliqué lors de la suite et conservé dans l'export.
- Localisation conforme au même mode : premier mot admissible, pas première
  sous-chaîne accidentelle. Normalisation FR/AR et projection Unicode originales
  conservées, sans morphologie, synonyme ou règle juridique.
- Correctif révélé par le sélecteur : trois groupes d'outils auparavant hors du
  conteneur d'effacement sont maintenant retirés aussi sur 401/403/503. Tests
  renforcés sans réduire les exigences d'accès ou masquer les refus.

[Contrat, exemples et limites](MODES_CORRESPONDANCE_TARIF.md).

## Qualification

- **1 806 tests Python réussis**, sélection étendue **55 fichiers**, 1 avertissement
  Starlette/httpx préexistant. Pas la suite OCR entière.
- **24 nouveaux cas Python** : frontières FR/AR et Unicode, faux positifs/pluriels,
  fraction NFKD, première occurrence entière après sous-chaîne, pas de regex fournie
  exécutée, modes invalides avant lecture, conjonction, préfixe seul, pagination,
  CLI, API, audit, export et archives inchangées.
- **178 scénarios JSDOM réussis**, **9 nouveaux** : défaut explicite, choix du mode,
  restauration lors d'une suite, ancien rapport, mode invalide/inconnu et retrait
  complet des fieldsets sur 401/403/503.
- Quatre parcours UI → HTTP → API réelle NON OFFICIELS, mots entiers puis
  pagination malgré modification du brouillon : **70 exports JSON vérifiés hors
  ligne et 4 copies PDF Code**. Pas parcours national ou navigateurs réels.
- Ruff, syntaxe des trois JS et diff-check : succès ; SHA historiques inchangés,
  base `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f`,
  référentiels `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

Aperçu redémarré, racine/module/SW v68 accessibles avec Host distant ; route
anonyme refusée 403. Journaux historiques préservés hors commit.

## État global

**0 nouvel original officiel acquis, 0 article/code national officiellement validé,
0 publication active.** Un mot entier normalisé n'atteste ni matière ni attribut
technique : aucun classement IA, taux ou droit à date ajouté. Mission partielle.
Dernière suite complète : **lot 45**, 2 773 réussites, 18 échecs OCR, 11 ignorés ;
non relancée intégralement ici. Aucun de ces échecs annoncé comme résolu.
