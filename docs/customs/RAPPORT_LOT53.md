# Rapport lot 53 — rejeu natif PDF sur opt-in local

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

## Livraison

- Cinq routes supplémentaires rejouables : lecture de page Code et fiscale,
  rapprochements littéraux d'article, justification de relation et description
  de mesure. Même archive/type/identité explicitement fournis.
- **Permission locale désactivée par défaut** : CLI `--allow-pdf`, Python
  `autoriser_pdf=True` booléen strict. Aucun export ne s'autorise lui-même.
- Réutilisation des services natifs PDFium et de leurs workers/validations/bornes,
  sans OCR, URL distante ou nouveau chemin choisi depuis le rapport.
- Résultat entier comparé, y compris fragments, positions, constats et provenance.
  Permission effective restituée, jamais confondue avec une extraction effectuée.
- Pas nouvelle API ou interface, pas copie de PDF brut ou rejeu multi-archives.

[Contrat d'autorisation et limites](REJEU_EXPORTS_PDF.md).

## Qualification exécutée

- **1 958 tests Python sélectionnés réussis**, **60 fichiers**, **46,32 s**,
  1 avertissement Starlette/httpx préexistant ; Ruff et diff-check réussis.
- **34 nouveaux cas Python** : onze sorties PDFium réelles rejouées, fragments et
  pages vides/objets absents, grand offset Unicode, contenu modifié détecté,
  cinq routes refusées sans permission avant lecteur/archive, types/IDs/pages/
  paramètres incompatibles, permission strictement booléenne, CLI et PDF altéré.
- Tests de refus des lots 51/52 conservés, avec message « non autorisé » désormais
  accepté sur leurs routes PDF : pas suppression d'un refus ou activation implicite.
- **186 scénarios JSDOM existants réussis**, aucun nouveau scénario UI attribué.
  Quatre parcours UI → HTTP → API réelle NON OFFICIELS : **70 exports JSON contrôlés
  structurellement, 58 rejeux typés identiques dont 14 PDF** (14/14/14/16 exports
  rejoués selon CSV/XLSX/XLS/PDF), **4 copies PDF Code**. Tous les rejeux PDF du pont
  demandent explicitement la permission locale ; pas réponse native simulée.
- SHA historiques inchangés : base
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  référentiels `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

Archives inchangées pendant les contrôles ; journaux préexistants conservés hors
commit. Interface, aperçu et cache v69 inchangés.

## État global

Dernière suite complète : **lot 50**, **2 885 réussis, 18 échecs OCR, 11 ignorés,
2 avertissements, 208,03 s** ; **non relancée intégralement au lot 53**. PDFium natif
réel ne remplace pas le provisionnement OCR Tesseract/Indra : aucun de ces échecs
annoncé résolu et aucune qualification juridique ou de navigateurs réels.

**0 nouvel original officiel acquis, 0 article/code national officiellement validé,
0 publication active.** Reproductibilité locale et présence littérale ne sont pas
origine officielle, preuve juridique, validation fiscale ou signature. Mission partielle.
