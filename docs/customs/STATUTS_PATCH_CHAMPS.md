# Statuts des corrections de champs alignés sur le modèle — lot 83

Périmètre : schéma `FieldPatch.status` et affectation du statut dans
`PATCH /api/jobs/{job_id}/fields/{name}`.

## Défaut et changement

Le statut était une chaîne libre : une valeur inconnue pouvait être sauvegardée
puis rendre le résultat illisible par `DocumentResult` ou bloquer un export.
Le schéma utilise maintenant `Optional[FieldStatus]`, la même énumération que
le résultat. L'affectation enregistre explicitement la valeur chaîne de l'enum.

Valeurs reconnues : `detected`, `not_detected`, `ambiguous`, `invalid`,
`validated`, `corrected`. Les autres chaînes, y compris variantes de casse,
espaces ajoutés et chaîne vide, sont refusées avec **422** avant accès aux
primitives de révision du résultat. Les nombres, booléens, listes et objets
invalides restent refusés. OpenAPI expose la même énumération.

Statut absent ou `null` conserve le comportement existant : pas de statut explicite,
mais une confirmation/correction peut toujours produire son statut implicite.
La saisie de valeur vide reste autorisée. Aucun nettoyage implicite de casse ou
d'espaces n'est ajouté.

## Recette

58 nouveaux cas : 18 combinaisons des six statuts avec statut seul,
confirmation ou correction ; 27 entrées invalides avec ces trois types de corps ;
six cas absent/null, dont valeurs humaines vides ; six exports JSON réels avec
relecture typée ; un contrat OpenAPI. Stores/jobs/audits temporaires réels,
empreinte du résultat et journal inchangés sur refus, lectures/écritures révision
piégées pour les entrées invalides. Aucun OCR fournisseur ou navigateur réel.

Contre-épreuve : **API exacte du lot 82 chargée en mémoire avant construction
FastAPI/Pydantic**, pour tester ensemble l'ancien schéma chaîne et son handler.
Pas simple remplacement tardif de la fonction laissant le nouveau validateur
en place. Même nom de module et chemin de ressources, fixtures temporaires
conservées ; checkout et aperçu non remplacés. Résultats dans
[rapport](RAPPORT_LOT83.md), [recette](RECETTE_LOT83.json).

## Portée et limites

Validation de vocabulaire, **pas validation des transitions métier**, des couples
statut/valeur, présence humaine ou règles de qualité. Un statut connu peut rester
incohérent avec les valeurs : pas nouvelle machine à états. Pas nouvelle règle
sur les requêtes sans changement, `user`/motif déclaratifs ou audit legacy.

FastAPI valide le corps avant d'entrer dans le handler : un corps invalide peut
recevoir 422 avant la garde de périmètre, sans lecture de document ; pas promesse
de 403 pour toute requête mal formée. Middleware d'authentification et gardes
existantes conservés pour les opérations autorisées. Pas migration des statuts
inconnus déjà présents, validation générale de tous les écrivains ou refonte
undo/exports en cache. Contrôle de révision et ses limites processus/ABA inchangés.

Aperçu backend76 maintenu pour préserver les traitements ; code77–83 poussé/testé,
non chargé dans ce processus avant redémarrage maîtrisé. RBAC non activé
automatiquement ; mission réglementaire toujours partielle.
