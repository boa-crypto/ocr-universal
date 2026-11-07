# Rapport lot 54 — rejeu des comparaisons à deux archives

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

## Livraison

- Nouveau service `verifier_rejeu_paire`, commande
  `customs-review-export-replay-pair`, deux dossiers/IDs/types explicitement ordonnés.
- Quatre routes : diff Code/tarif, écart d'articles inter-lots, juxtaposition de
  fiches tarifaires, consultation tarif/mesures autonomes. Types/rôles/IDs stricts,
  aucune archive choisie depuis l'export ou devinée sur disque.
- Comparaison complète mutualisée avec le rejeu simple, manifestes ordonnés et
  champs de provenance distincts pour une paire. Contenu altéré ou dossiers
  inversés détectés ; refus en cas d'archive incohérente, pas de succès partiel.
- Pas nouvelle API/UI, extraction PDF, validation humaine, consolidation, fusion
  fiscale ou droit à date. Cache v69 inchangé.

[Contrat, matrice et limites](REJEU_DEUX_ARCHIVES.md).

## Qualification exécutée

- **1 989 tests Python sélectionnés réussis**, **61 fichiers**, **46,56 s**,
  1 avertissement Starlette/httpx préexistant ; Ruff et diff-check réussis.
- **31 nouveaux cas Python** : neuf comparaisons API réelles selon les rôles/types,
  pagination indépendante et grand offset, même archive explicitement répétée,
  champs modifiés, IDs/types/rôles/paramètres incompatibles, dossier inversé,
  archive altérée, absence d'objets/code, refus et codes CLI 0/1/2.
- **186 scénarios JSDOM existants réussis**, aucun nouveau scénario UI attribué.
  Quatre parcours UI → HTTP → API réelle NON OFFICIELS : **70 exports JSON contrôlés
  structurellement et 70 rejoués identiquement** : **58 à une archive dont 14 PDF**
  sur opt-in local, **12 à deux archives** (trois par parcours), **4 copies PDF Code**.
  Pas de réponse métier/rejeu simulée ni de navigateurs réels prétendus qualifiés.
- Les 70 exports couvrent **ces fixtures et ces parcours**, pas tout fichier,
  requête, cas métier national ou version logicielle future. Aucun « 100 % » de
  conformité, d'authenticité ou de complétude réglementaire n'en est déduit.
- SHA historiques inchangés : base
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  référentiels `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

Archives inchangées pendant les contrôles ; journaux préexistants conservés hors
commit. Aucun nouvel original acquis ou lot de production créé.

## État global

Dernière suite complète : **lot 50**, **2 885 réussites, 18 échecs OCR, 11 ignorés,
2 avertissements, 208,03 s** ; **non relancée intégralement au lot 54**. Tesseract
et Indra restent absents ; aucun de ces échecs annoncé résolu.

**0 article/code national officiellement validé, 0 publication active.** Mission
partielle ; rejeu technique ≠ authenticité, signature, registre, preuve juridique,
décision habilitée ou calcul fiscal validé. Les chantiers du bilan restent ouverts.
