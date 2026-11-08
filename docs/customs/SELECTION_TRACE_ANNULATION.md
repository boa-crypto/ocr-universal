# Trace exploitable pour annulation de champ — lot 82

Mesures du `2026-11-08` (horloge environnement). Périmètre : `_derniere_correction`, utilisée par l'annulation
`POST /api/jobs/{job_id}/fields/{name}/undo`.

## Défaut et décision

La recherche prenait une ligne contenant `field_validated` pour une correction
sans vérifier le nom exact d'événement. Une mention dans un autre événement
pouvait servir de trace ; certaines valeurs JSON non objets provoquaient une
exception. Une trace incomplète ou une opération de statut seul pouvait aussi
être utilisée pour effacer une valeur humaine et annoncer un état restauré.

Après le préfiltre littéral existant, seules les entrées JSON objets avec
`event == field_validated`, le bon `job_id` et le bon `field` sont candidates.
Les JSON cassés/non objets et autres événements/cibles sont ignorés.

La **dernière candidate exacte** doit contenir les trois clés `ancienne_valeur`,
`ancienne_origine`, `ancien_statut`, et au moins `confirmed` ou `corrected`
non `None`. Une chaîne vide reste une intervention de valeur, comme au lot 76.
Si la candidate est incomplète ou sans opération de valeur, retour `None` :
la route renvoie **409**, sans mutation ni audit d'annulation réussie. Elle ne
remonte pas silencieusement à une correction plus ancienne.

**Changement métier explicite :** une modification de statut seul après une
correction de valeur bloque l'annulation par ce chemin. Ce lot n'implémente ni
annulation de statut, ni choix d'un ancien événement. Les anciennes traces
insuffisantes ne sont pas complétées par des valeurs inventées.

## Recette

17 nouveaux cas sur stores/jobs/audits temporaires réels : six bruits JSON ou
non-événements, deux mauvaises cibles, JSON cassé, trois clés antérieures
manquantes, deux traces sans valeur, deux vraies saisies vides et une véritable
requête de statut seul après correction. Vérification de la sélection, du
retour 409 sans modification/annulation réussie, ou de la restauration simple
attendue pour les cas autorisés.

Contre-épreuve : corps exact de l'ancien helper réinjecté en mémoire, mêmes
17 cas, checkout et aperçu non remplacés. Résultats dans
[le rapport](RAPPORT_LOT82.md), [recette structurée](RECETTE_LOT82.json).

## Limites

Présence de clés et intervention de valeur déclarée, **pas validation complète
des types, authenticité ou correspondance avec une révision précise du champ**.
Pas restauration fidèle de tous les emplacements manuels antérieurs ou pile
multi-niveau. Les dernières traces restent des déclarations legacy non signées,
non WORM ; elles ne sont ni réparées ni migrées. Le seul journal n'est pas couvert
par la révision de résultat du lot 81. Lecture entière non bornée/streamée,
préfiltre littéral conservé, pas import universel de tous les encodages JSON.

Gardes de rôle/périmètre et contrôle de révision du lot 81 conservés. Acteurs,
statuts acceptés, valeurs journalisées, exports en cache et qualité non refondus.
Aperçu backend76 maintenu pour préserver les traitements ; code77–82 poussé/testé,
non chargé avant redémarrage maîtrisé. RBAC non activé automatiquement ; mission
réglementaire toujours partielle.
