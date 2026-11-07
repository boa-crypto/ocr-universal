# Rapport lot 50 — rejeu local des exports et nouvelle recette complète

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

## Livraison

- Service `verifier_rejeu_criteres`, commande `customs-review-export-replay` :
  comparaison d'un export multicritère à une archive et une identité explicites.
- Lecture sécurisée mutualisée avec le contrôleur de structure existant, contrat
  et schéma inchangés ; requêtes ambiguës/dupliquées/inconnues refusées.
- Comparaison de tout le résultat : types JSON, listes, filtres, preuves Unicode,
  diagnostic et provenance. Ordre des clés sans effet ; contenu modifié détecté.
- Codes CLI 0 identique / 1 différent / 2 refus. Constat sans recopier le rapport,
  sans validation d'authenticité, signature, registre, audit serveur ou humain.
- Aucun nouveau endpoint de chemins locaux, écriture ou fonctionnalité UI prétendue.

[Contrat et limites](REJEU_EXPORT_CRITERES.md).

## Qualification sélectionnée

**1 853 tests Python réussis**, sélection étendue **57 fichiers**, **44,81 s**,
1 avertissement Starlette/httpx préexistant ; Ruff et diff-check réussis.

**33 nouveaux cas Python** : FR/AR, modes/pagination/préfixes et zéro résultat,
modifications de compteurs/positions/drapeaux/champs, distinction false/0 et
int/float, ordre des listes/objets, date client non rejouée, route et identité
explicites, requêtes ambiguës/encodages/paramètres refusés avant archive, archive
incohérente ou différente, fichier trop grand/FIFO/symlink/doublons et codes CLI.
Archives inchangées pendant le contrôle ; aucun texte de différence exposé.

**186 scénarios JSDOM existants réussis** ; pas nouveau scénario UI attribué au
lot 50. Quatre parcours UI → HTTP → API réelle NON OFFICIELS : **70 exports JSON
contrôlés structurellement, 4 exports de critères rejoués identiquement**, 4 copies
PDF Code. Pas de navigateurs réels ou de recette nationale qualifiés.

## Nouvelle suite complète exécutée après le lot 49

**2 885 réussis, 18 échoués, 11 ignorés, 2 avertissements, 208,03 s**, soit
2 914 tests. **Suite globale non verte.** Les identifiants des 18 échecs sont
identiques à ceux du lot 45, comparaison effectuée sur les résultats JUnit.
Binaire Tesseract et module Indra OCR toujours absents ; aucune simulation,
attente affaiblie ou test d'échec masqué. Pas preuve qu'un provisionnement suffirait
à faire passer tous ces tests. Détail : [RECETTE_LOT50.json](RECETTE_LOT50.json).

Avertissements observés : Starlette/httpx, puis Pydantic sur l'alias
`liquidation_update` sans effet dans un test de concurrence liquidation. Le rapport
antérieur du lot 45 est conservé comme historique, pas réécrit comme recette 50.

Huit fixtures binaires régénérées par la suite complète ont été explicitement
restaurées (elles étaient propres avant la recette) ; journaux historiques
préservés hors commit. SHA inchangés :

- base `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## État global

**0 nouvel original officiel acquis, 0 article/code national officiellement validé,
0 publication active.** Le rejeu local n'est pas une validation réglementaire ni
un classement IA ; les chantiers du bilan restent ouverts. Mission partielle.
L'interface n'a pas changé : cache v69 et aperçu existant conservés ; aucune
nouvelle fonction UI inventée pour ce contrôle local CLI.
