# Rejeu typé des lectures documentaires — lot 51

Extension du [contrôle local du lot 50](REJEU_EXPORT_CRITERES.md) ; mêmes règles de
lecture, de comparaison complète, de refus et de non-authentification. Aucun
endpoint lisant des chemins locaux ajouté ; aucune donnée métier publiée.

```sh
unocr customs-review-export-replay rapport.json --lot DOSSIER --lot-id ID --type-lot code
```

Service : `verifier_rejeu_export(chemin_export, repertoire, lot_id, type_lot)`.
Type fourni obligatoirement en Python : `code`, `tarif` ou `mesures`. CLI : défaut
**tarif** conservé pour compatibilité avec le lot 50 ; Code/mesures nécessitent
l'option appropriée. Aucun type déduit de l'export, du nom de dossier ou du disque.
La fonction historique `verifier_rejeu_criteres` reste limitée aux critères.

## Matrice fermée

Toutes les routes sont sous `/api/v1/customs-review/lots/ID/` avec ID exact fourni.

| Route | Type(s) | Paramètres HTTP acceptés |
|---|---|---|
| `tariff-criteria` | tarif | Cinq critères, `code_prefix`, `match_mode`, `limit`, `offset` |
| `search` | tarif | `q`, `limit`, `offset` |
| `search` | code | `q`, `article`, `source`, `nature`, `limit`, `offset` |
| `article` | code | `article_id` requis, `field`, `limit`, `offset` |
| `tariff/CODE10` | tarif | `measures_limit`, `measures_offset` |
| `measure-search` | tarif, mesures | `q`, `code10`, `measure_type`, `limit`, `offset` |

Les alias HTTP sont traduits vers les mêmes arguments de services que dans l'API,
avec leurs mêmes valeurs par défaut, types et bornes. Lecture article : jusqu'à
16 000 caractères, offset Unicode jusqu'à 67 108 864, sans diminuer la borne à
celle d'une pagination de résultats. Code10 reste textuel, dix chiffres ASCII.
Fiche inconnue, article absent, recherche/page vide sont des résultats rejouables,
pas une erreur ni une preuve d'inexistence nationale.

Filtres réservés au Code refusés sur le tarif ; recherche de mesures refusée sur
le Code. Autres routes (PDF, historique, arbres, comparaisons multi-archives, etc.)
**non prises en charge** : refus, sans prétendre avoir vérifié tout l'export.
Un type compatible avec la route mais incompatible avec l'archive échoue au
rejeu du lecteur approprié : aucun essai automatique d'un autre lecteur.

## Gardes conservés

Lecture régulière bornée à 10 Mio, symlink final/FIFO/doublons JSON refusés,
contrat de structure validé. Route/ID exacts, neuf paramètres au plus, pas doublons
après décodage, inconnus, encodages invalides ou pagination non décimale ASCII.
Paramètres et archive incompatibles refusés, contenu d'erreur neutralisé.
Aucun chemin, URL ou type extrait du rapport pour choisir un dossier local.

Résultat entier comparé sous forme JSON canonique : ordre des clés ignoré, ordre
des listes/types/champs conservé. Les drapeaux de non-validation, preuves Unicode,
mesures et taux déclarés ne sont pas ignorés pour produire une égalité. Une
modification ou une version logicielle différente peut produire un résultat
« différent » sans permettre d'en déduire une fraude.

Constat générique `rejeu_local_export_documentaire`, avec `type_lot_explicite`
(valeur effective de l'argument) ; autres champs conservés. Codes CLI inchangés :
0 identique, 1 différent, 2 refus. Ni requête ni texte du rapport recopiés.

Authenticité, identité du registre, audit serveur, signature et habilitation
humaine restent **non attestés**. Une copie cohérente peut satisfaire ce contrôle.
Aucune écriture, déduction fiscale, classification IA, droit à date, transaction
filesystem ou garantie contre modification concurrente après lecture.

Pas de modification de l'interface ni du cache v69. Les exports réellement
produits par quatre parcours UI/HTTP/API sont contrôlés hors ligne par ces mêmes
services, pas par une réponse de rejeu simulée dans le navigateur.

## Extension lot 52

[Provenance, historique et navigation](REJEU_PROVENANCE.md) : huit familles de
routes supplémentaires, dont l’écart de versions du même lot. La liste des routes
non prises en charge ci-dessus décrit le périmètre historique 51 ; voir la matrice
complémentaire 52 pour les nouvelles lectures. PDF et multi-archives restent exclus.
