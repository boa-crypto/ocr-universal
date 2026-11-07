# Deux fiches tarifaires documentaires séparées

Lot 31 — 7 novembre 2026. Lecture seule, pas rapprochement fiscal applicable.

## Périmètre

Un code exact à dix chiffres ASCII est recherché séparément dans deux lots
tarifaires explicitement choisis. Les deux lots doivent être déjà préparés et
contrôlables par le lecteur existant. Chaque fiche conserve sa source, sa ligne,
ses parents déclarés, ses périodes et ses mesures. Aucun contenu n’est fusionné.

Les deux publications peuvent différer par source/date/périmètre. « Avant/après »
est seulement l’ordre demandé, pas une chronologie ni le choix du droit applicable.
Les IDs de source/mesure restent locaux à leur lot : aucune identité ou succession
n’est déduite de leur égalité. Le même lot peut être choisi deux fois explicitement.

Cette lecture réutilise les fiches existantes, pas un nouveau modèle de fiscalité.
**Elle ne permet pas d’importer un fichier fiscal autonome** dépourvu du contrat
TariffBatch ni de rattacher automatiquement une fiscalité externe à une nomenclature.
Ce chantier et sa validation juridique restent à réaliser. Le diff global des lots
existants reste distinct de cette consultation ciblée d’un seul code.

## CLI

```sh
unocr customs-tariff-compare LOT_AVANT LOT_APRES --code CODE10_EXACT \
  --before-limit 20 --before-offset 0 --after-limit 20 --after-offset 0
```

Deux paginations indépendantes de mesures. Limites entières 1–100 ; décalages
entiers 0–1 000 000 ; code chaîne de dix chiffres ASCII, sans conversion, zfill,
troncature ou espaces supprimés. Tous les paramètres, y compris ceux du côté après,
sont vérifiés avant le premier chargement. Les deux lots sont ensuite rejoués.

## API

```text
GET /api/v1/customs-review/tariff-compare
    ?avant=ID_LOT_AVANT&apres=ID_LOT_APRES&code10=CODE10_EXACT
    &before_limit=20&before_offset=0&after_limit=20&after_offset=0
```

Aucun chemin fourni par HTTP. Les deux lots doivent être inscrits, de type tarif,
et leurs manifestes épinglés avant traitement et comparés aux empreintes restituées.
Mêmes autorisation nominative, habilitation, audit obligatoire et `no-store`.
Paramètres/types invalides : 422 ; lot inconnu : 404 ; incohérence/empreinte : 409 ;
audit indisponible : 503 sans résultat. CLI hors contrat d’audit HTTP.

Les URLs peuvent figurer dans les journaux HTTP d’infrastructure. Le succès d’audit
métier contient les IDs et empreintes des lots, pas le code consulté ou les mesures.

## Rapport

`type_rapport=juxtaposition_documentaire_fiches_tarifaires`, `lots_exacts`,
`archives.avant/apres` (pas d’archive simple). Les blocs `avant` et `apres` conservent
indépendamment :

- `ligne_trouvee`, `ligne_declaree`, `hierarchie_declaree`, `source_declaree` ;
- `total_mesures_declarees`, `limite_mesures`, `decalage_mesures`,
  `decalage_mesures_suivant` et `mesures_declarees`.

Les dates sont celles déclarées dans chaque lot, pas des dates validées par la
comparaison. Les chaînes de taux Decimal sont conservées exactement, sans flottants,
arrondi ou taux combiné. `null` et zéro déclaré restent distincts. Aucun taux n’est
recopié dans la ligne tarifaire ou dans l’autre fiche. Toutes les catégories de
mesures reçues sont conservées : droits, TVA, autres taxes, restrictions,
autorisations et régimes, sans rapprocher leurs identités entre lots.

Un code peut être absent d’un seul côté ou des deux. Absence dans un lot ≠ création,
suppression nationale ou interdiction. Code présent sans mesure ≠ exonération.
Hors fin : page vide ; fin signalée par `decalage_mesures_suivant=null`.
Compteurs par lot seulement, pas un dénominateur ou pourcentage national.

Marqueurs : `mesures_fusionnees=false`, `identites_mesures_rapprochees=false`,
`fiscalite_applicable_etablie=false`, `classement_douanier_valide=false`,
`utilisable_pour_calcul_douanier=false`, publication inactive et validation juridique
non réalisée. Les sources restent non vérifiées.

## Interface et export

Dans la revue existante, choisir les deux lots en haut, saisir le code dans la
fiche tarifaire, puis « Consulter les deux fiches tarifaires séparées ». Pagination
avant = formulaire de fiche ; pagination après = nouveau formulaire dédié. Le
rapport affiche deux blocs JSON séparés, pas un tableau de taux applicable.

Les suites de mesures conservent la paire, le code et l’autre pagination. Les
boutons « Fiche avant/apres du lot… » ouvrent la fiche exacte dans son propre lot.
Changement du lot après, compte, lot principal ou résultat invalide les actions
anciennes selon les gardes existantes. Type Code et codes non ASCII refusés.

L’export partiel relit la route sous droits/audit courants. Whitelist, schéma et
contrôle hors ligne étendus à la nouvelle route, avec provenance double obligatoire ;
une provenance simple/ambiguë est refusée. Toujours structurel/déclaratif, pas
preuve d’authenticité. Anciens contrôleurs stricts susceptibles de refuser l’ajout
à l’enveloppe version 1. Ni export de corpus complet ni publication active.

## Limites

Deux lots chargés/rejoués en mémoire ; pagination ≠ RAM constante ou transaction
multi-dossiers. Intégrité locale ≠ authenticité éditeur/WORM. Pas de rapprochement
sémantique des mesures, calcul de différences de taux, sélection à date, fusion
nomenclature/fiscalité, attestation humaine, classification ou calcul de droits.
Le tarif national et les sources fiscales officielles restent à acquérir et valider.
