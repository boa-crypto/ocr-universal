# Rapport lot 44 — constat littéral de description / page PDF

7 novembre 2026 — branche `arena/2cd4c91a-ocr-universal`.

Service `rapprocher_description_mesure_pdf`, CLI `customs-measure-pdf-match`, route
`/lots/{id}/measure-pdf-match`, opération d'audit dédiée et outil d'interface séparé.
Comparaison exacte d'un fragment d'une description dans une page physique choisie,
réutilisant le constat littéral et le worker existants. IDs locaux, provenance et
source séparés ; aucun taux/code/période ou rattachement juridiquement vérifié.

## Qualification

- **1 741 tests Python réussis**, sélection étendue **52 fichiers**, **43,01 s**,
  1 avertissement Starlette/httpx préexistant ; pas suite OCR entière.
- **22 nouveaux cas Python** : présence/absence, première occurrence, offsets,
  vide/blanc/mesure absente, paramètres avant lecture, source/page/format invalides,
  altération, CLI/API/types/autorisations, export simple et archives inchangées.
- **152 scénarios JSDOM**, dont **6 nouveaux** : paramètres/route, suite Unicode,
  texte hostile, paramètres invalides, ancien bouton inerte et audit 503.
- Quatre parcours UI/HTTP/API réels NON OFFICIELS : **66 exports JSON** contrôlés
  hors ligne (16 pour CSV/XLSX/XLS, 18 pour PDF transcrit), **4 copies PDF Code**.
  Le nouveau constat négatif sur la description est exporté sans taux attesté.
- Régression des lecteurs et constats PDF Code/autonomes, imports et empreintes
  historiques : succès. Ruff, syntaxe JS, diff-check et SHA données vérifiés.
- Base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

[Contrat](DESCRIPTION_MESURE_PDF.md), [tableau global](TABLEAU_LOTS.md).
**0 original officiel acquis, 0 code/article officiel validé, 0 publication active.**
Aucune fidélité intégrale ou validation humaine. Mission globale partielle ; les
chantiers métier restants ne sont pas transformés en lots terminés par ce constat.
Aperçu redémarré en v65, route anonyme refusée ; journaux hors commit.
