# Avancement — lot 5 : recherche documentaire locale français/arabe

**2026-11-06 — consultation de lots en quarantaine, pas de classement officiel.**

## Livré

- Service partagé `customs_reference.search`, réutilisant les lecteurs/rejeux
  tarifaires et Code déjà livrés. Pas de lecture de `CODES_SH_ALGERIE` ni du
  magasin legacy non vérifié, pas de nouvelle source de vérité active.
- `customs-tariff-search LOT --query TEXTE_OU_PREFIXE` : désignations FR/AR ou
  préfixe ASCII d’un code 10 déjà présent, notamment SH6 ; aucune complétion.
- `customs-code-search LOT` : textes/intitulés FR/AR et filtres cumulatifs exacts
  sur numéro d’article, source et nature ; versions distinctes, sans choix d’une
  version juridiquement applicable ni retrait automatique d’un texte déclaré abrogé.
- Normalisation uniquement pour comparaison : NFKD/casefold, marques combinantes,
  tatweel et ligatures françaises. Les textes reçus restent inchangés, avec arabe,
  accents, espaces et sauts de ligne. Champs correspondants et provenance restitués.
- Pagination bornée et déterministe ; aperçus initiaux des textes du Code limités
  à 512 caractères par champ, avec indication de troncature. Pas d’extrait centré
  faussement présenté comme la preuve du mot retrouvé.
- Contrôle complet du lot avant toute page ; refus intégral d’un lot incohérent.
  Aucun lot ni store n’est modifié. Pas d’index persistant, requête distante,
  dépendance supplémentaire ou nouvelle route HTTP.

[Commandes et contrat détaillé](RECHERCHE_LOCALE.md).
Les schémas et formats de préparation ne changent pas. La future API/admin
pourra réutiliser ces fonctions sous autorisation explicite ; aucun accès de
validation n’est ouvert via le RBAC historique permissif.

## Limites substantielles

Il s’agit de sous-chaînes littérales normalisées, tous les termes devant trouver
une correspondance dans la même ligne/version. Pas de synonymes documentés
acquis, traduction, lemmatisation, IA, recherche vectorielle, analyse de matière,
fonction/usage, raisonnement SH/notes/exclusions, score de confiance ou suggestion
de classification. Ces fonctionnalités restent à construire sur un corpus vérifié.

Les mesures fiscales et restrictions séparées ne sont pas recherchées ou utilisées
pour calculer des droits. Les notes explicitement non officielles ne sont pas
indexées comme du texte légal. Les aperçus ne remplacent pas les textes complets
ni les originaux archivés ; la correspondance transcription/PDF n’est pas validée.

Les compteurs indiquent uniquement les correspondances **dans le lot choisi**.
Zéro résultat ne démontre pas absence de droit. Un résultat n’atteste ni
l’existence d’une position nationale officielle, ni la validité d’un classement,
ni une date d’effet. Les flags de quarantaine/non-validation sont toujours présents.
Pas de qualification de performance ou de complétude sur un fichier national réel.

## Résultats techniques

**341 tests réussis, 1 avertissement Starlette/httpx**, avec data/logs isolés :
les 282 tests de la sélection lot 4 + **59 nouveaux cas** de recherche.
Sélection ciblée uniquement, pas la suite complète du dépôt.

```sh
python -m pytest tests/test_customs_search.py tests/test_customs_legal_comparison.py \
  tests/test_customs_legal.py tests/test_customs_reference.py \
  tests/test_customs_xlsx.py tests/test_customs_comparison.py \
  tests/test_corrections_routes.py tests/test_referentiels.py \
  tests/test_referentiels_base.py tests/test_customs_connector.py -q
```

Couverture nouvelle : accents/casse/ligatures, arabe diacrité/tatweel, champs FR/AR
combinés, lignes arabe seul, préfixes avec zéros conservés, refus des codes numériques
non ASCII/trop longs, pagination/totaux/tri, absence de synonymes inférés,
notes/mesures exclues, numéros exacts et versions non fusionnées, texte déclaré
abrogé toujours visible comme non validé, aperçus bornés non centrés, paramètres
et types ambigus refusés, corruption refusée même pour une page limitée,
interdiction de mélanger les types de lots, sources JSON/CSV UTF-8/XLSX avec
périmètre de feuille conservé, CLI en processus indépendant sans création de stores.

Fixtures exclusivement **NON OFFICIELLES**, temporaires ; aucun référentiel public
fictif livré. Ruff `src tests`, identité des schémas et `git diff --check` contrôlés.
Les deux données historiques gardent leurs SHA256 :

- `data/reglementation/base.json` :
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f`
- `data/referentiels.json` :
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`

## Complétude et prochaines dépendances

**0 nouveau document officiel acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, corpus original/modificatif exhaustif,
chronologie et export national courant avec sources fiscales toujours manquants.
Les deux calculs douaniers legacy non sourcés restent bloqués.

Restent notamment : acquisition/qualification sur les fichiers réels, validation
humaine habilitée, registre protégé et historique central, déduplication inter-lots,
liens Code/tarif documentés, reconstruction provisoire, restitution juridique à
une date, publication, recherche sur versions publiées, classification IA sourcée,
API v1 et administration réutilisant les composants existants. Aucun résultat de
cette recherche n’est branché sur un calcul douanier réel ou une décision métier.
