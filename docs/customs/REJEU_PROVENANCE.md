# Rejeu de provenance, historique et navigation — lot 52

Extension de la [matrice typée du lot 51](REJEU_EXPORTS_TYPES.md), dans le même
contrôleur `verifier_rejeu_export` / `customs-review-export-replay`. Même archive
et identité fournies explicitement, même type non deviné, aucune nouvelle API/UI.

## Routes supplémentaires

Sous `/api/v1/customs-review/lots/ID/` :

| Route | Type(s) | Paramètres admis |
|---|---|---|
| `check` | code, tarif, mesures | Aucun |
| `coverage` | code, tarif, mesures | Aucun |
| `sources` | code, tarif, mesures | `q`, `source_id`, `nature_document`, `limit`, `offset` |
| `history` | code | `article` requis, `limit`, `offset`, `relations_limit`, `relations_offset` |
| `article-relations` | code | `article_id` requis, `direction`, `relation_type`, `limit`, `offset` |
| `article-diff` | code | `avant_id` et `apres_id` requis, `field`, `limit`, `offset_avant`, `offset_apres` |
| `code-tree` | code | `source_id`, `path`, `limit`, `offset` |
| `tree` | tarif | `level`, `parent`, `limit`, `offset` |

Alias traduits vers les arguments des mêmes services que l'API ; défauts et bornes
conservés. `nature_document` reste Code uniquement, refusé par le service pour un
autre type avant lecture. Les deux paginations de l'historique restent distinctes.
Les deux offsets de l'écart d'articles gardent leur borne Unicode 67 108 864,
différente de l'offset de résultats 1 000 000. IDs, sens/types de relations, niveaux
et parents restent des sélections exactes, jamais des paramètres de consolidation.

L'écart `article-diff` ici compare deux versions **du même lot**. La route
multi-archives `/api/v1/customs-review/article-diff` reste refusée. Aucun dossier
secondaire, `after_lot`, ID de registre ou URL du rapport ne choisit une archive.

## Sémantique strictement documentaire

- `check` rejoue les lecteurs et contrôles de l'archive fournie, y compris les
  fichiers reçus du lot ; ne certifie pas l'origine des documents ni leur fidélité.
- `coverage` restitue les compteurs du lot, pas un dénominateur officiel ou un
  pourcentage de complétude réglementaire.
- `sources` compare les métadonnées, références et compteurs reçus, pas l'existence
  d'un original sur le site déclaré. Aucune URL n'est suivie.
- `history` garde les dates/sources/versionnements déclarés et les deux pages,
  pas une succession juridiquement vérifiée ou une restitution du droit à date.
- `article-relations` conserve sens, type, justification et provenance déclarés,
  pas des liens prouvés ou une transitivité juridique.
- `article-diff` conserve fragments, offsets et constats littéraux sans qualifier
  les changements comme modifications, abrogations ou consolidations juridiques.
- Arbres : chemins hiérarchiques reçus uniquement, sans reconstruire un parent
  par similarité ou préfixe. `path` du Code est un **JSON hiérarchique**, jamais
  un chemin filesystem ; clés/niveaux/ordre/source contrôlés par le service.

Comparaison du rapport entier : champs, listes, types JSON, provenance, compteurs,
contexte, filtres et drapeaux de non-validation. Une différence n'est pas retirée
pour obtenir une égalité. Les marqueurs d'authenticité/registre/audit restent false.

## Limites conservées

Neuf paramètres au plus, pas paramètres inconnus/dupliqués après décodage, ni
encodages invalides ; pagination décimale ASCII stricte. Paramètres/route/type
incompatibles refusés, pas essai automatique d'un autre lecteur. Export limité à
10 Mio et requête relative à 16 384 caractères selon contrat existant : ces plafonds
peuvent exclure des rapports ou chemins très volumineux, sans troncature silencieuse.

Pas rejeu des extractions/rapprochements PDF, copies binaires ou comparaisons
multi-archives. Leur simple contrôle structurel ne devient pas un rejeu. Le
contrôle d'archive peut lire/hacher les PDF d'un lot Code, sans lancer pour autant
une extraction PDFium/ocr de leurs pages.

Pas signature, WORM, transaction filesystem, identité humaine, validité juridique
ou protection contre modification concurrente après lecture. Même mémoire/rejeu
complet et limites de charge que les services d'origine. Aucun corpus publié,
calcul fiscal, classement IA, acquisition réseau ou changement du cache v69.
