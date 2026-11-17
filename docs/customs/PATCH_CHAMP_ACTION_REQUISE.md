# Une action de champ est requise pour un PATCH — lot 84

Périmètre : `PATCH /api/jobs/{job_id}/fields/{name}`. Complète les lots 82/83.

## Défaut et changement explicite

Un corps vide, uniquement déclaratif (`user`/`reason`) ou dont les trois champs
d'action étaient `null` produisait un audit `field_validated` sans action sur
une valeur ou un statut. Cette dernière trace pouvait ensuite bloquer
l'annulation légitime avec la politique fail-closed du lot 82.

Après les gardes de rôle et de visibilité, la route exige au moins une valeur
non `None` parmi `confirmed_value`, `corrected_value` et `status`. Sinon :
**422 `aucune modification de champ fournie`**, avant lecture ou écriture de
révision du résultat, sans audit de validation réussie.

Il s'agit d'**action fournie**, pas d'une différence calculée dans le fichier :
- valeur humaine `""` ou `"0"` : action explicite, acceptée ;
- statut reconnu seul, même identique à l'existant : action explicite, acceptée ;
- reconfirmation explicite de la même valeur : acceptée et tracée ;
- absence/null de statut avec valeur explicite : comportements précédents conservés ;
- absence/null de statut sans valeur ni autre statut explicite : désormais refusée.

Deux cas du test introduit au lot 83, qui attendaient le succès d'un corps
sans action (statut absent/null), sont mis à jour pour ce **nouveau contrat**.
Les documents historiques 83 décrivent l'état livré alors, pas la règle 84.
Les métadonnées seules ne deviennent pas une fonction de commentaire/revue.

## Recette

28 nouveaux cas : sept corps sans action refusés avant accès révision, six chaînes
correction → requête sans action refusée → annulation réussie, quatre valeurs
vides/zéro, six statuts seuls, quatre refus d'autorisation avant nouvelle garde,
une double reconfirmation explicite. Stores/jobs/audits réels temporaires,
empreintes et journal identiques pour les refus de l'opérateur testé.

Contre-épreuve : corps exact de l'ancien PATCH réinjecté uniquement en mémoire,
mêmes 28 nouveaux cas, schéma et fixtures conservés ; checkout/aperçu non remplacés.
Résultats dans [rapport](RAPPORT_LOT84.md), [recette](RECETTE_LOT84.json).

## Limites

Pas détection de toute opération sémantiquement identique ou idempotence de
confirmation ; confirmations répétées peuvent ajouter plusieurs audits.
Pas commentaire autonome, validation de transitions, identité authentifiée ou
refonte de l'undo. Le statut seul reste une action et bloque toujours l'undo
de valeur selon le lot 82. `null` ne devient pas une commande d'effacement.

La garde d'action précède la recherche du résultat/champ : sans action, 422
peut donc précéder les erreurs de disponibilité/absence, mais après les gardes
d'accès. La validation Pydantic d'un corps mal formé garde son ordre propre.
Les audits de sécurité du middleware peuvent exister sur refus ; pas promesse
de journal global inchangé pour tous les jetons. Limites de révision processus,
ABA, audit best-effort, anciennes traces/no-op déjà présentes, exports en cache
et qualité inchangées. Pas migration ou réparation rétroactive.

Aperçu backend76 maintenu pour préserver les traitements ; code77–84 poussé/testé,
non chargé avant redémarrage maîtrisé. Pas activation automatique du RBAC ;
mission réglementaire toujours partielle.
