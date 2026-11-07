# Valeurs vides de champs : `None` n'est pas `""` — lot 76

7 novembre 2026. Périmètre : modèle `FieldValue.value`, état antérieur de champ
consigné par l'API, valeur après correction relue dans le journal et condition
d'entrée de l'annulation d'un champ de job.

## Défaut et contrat

Les chaînes de `or` prenaient une saisie humaine vide pour une absence et
réactivaient une valeur corrigée, normalisée ou OCR moins prioritaire.
L'annulation refusait aussi une confirmation/correction vide comme s'il n'y
avait eu aucune intervention humaine.

La priorité reste **confirmée > corrigée > normalisée > brute**, mais le premier
emplacement **non `None`** gagne, y compris une chaîne vide. `"0"`, français et
arabe ne sont pas réinterprétés. Si tous les emplacements sont absents/`None`,
la valeur est `None`. L'état consigné et la sélection de `valeur_apres` suivent
la même distinction. La garde d'annulation vérifie désormais les deux emplacements
humains avec `is None`, pas leur vérité booléenne.

Les tests d'aller-retour ont aussi découvert que l'API émettait déjà le statut
`corrected`, absent de l'énumération `FieldStatus`. Il est ajouté sans modifier
les autres statuts : une correction API peut ainsi être relue comme `FieldValue`
et exportée par la voie JSON existante sans erreur de validation du modèle.
Les deux paramétrisations qualité existantes couvrant tous les statuts s'étendent
automatiquement à ce statut. Ce n'est ni un changement de seuil, ni une garantie
de recalcul qualité après édition.

## Recette et contre-épreuves

106 nouveaux cas :
- 81 combinaisons de quatre emplacements parmi `None`, `""` et `"0"` ;
- 8 sélections non vides français/arabe ;
- 8 cycles simples correction/confirmation → annulation, valeur vide ou zéro,
  avec ou sans normalisation de base ;
- 4 traces d'une valeur manuelle antérieure vide et 3 priorités de trace récente ;
- 2 exports JSON réels après correction, relus avec statut et valeur corrects.

Deux cas existants supplémentaires sont collectés par la paramétrisation de
qualité sur l'énumération étendue. Tests de routes sur jobs/stores/audits
synthétiques temporaires, pas fournisseur OCR ni données officielles.

Deux témoins en processus séparés, corps exacts antérieurs réinjectés seulement
en mémoire : (1) sélection de valeur + trois fonctions API ; (2) annulation
ancienne seule, pour ne pas masquer son défaut par la sélection déjà erronée.
L'énumération étendue reste active dans les témoins : ils isolent la gestion du
vide, pas un rejeu complet de l'ancien schéma. Checkout et aperçu non remplacés.
Résultats dans [le rapport](RAPPORT_LOT76.md), [recette](RECETTE_LOT76.json).

## Limites explicites

Le cycle testé revient à un champ de base sans valeur manuelle préalable.
**Pas refonte du multi-niveau d'annulation**, reconstruction exacte des quatre
emplacements d'un état manuel antérieur, filtrage des événements de statut seul,
concurrence ou transaction audit/résultat. Une ancienne trace ayant déjà perdu
un vide ne peut pas être réparée implicitement. Pas migration des journaux.

Les consommateurs utilisant `FieldValue.value` bénéficient de sa nouvelle
sémantique ; pas audit exhaustif des replis booléens ailleurs, notamment dans
l'interface JavaScript, ni recette navigateur de saisie vide. Le type de valeur
reste chaîne facultative ; aucun support général de nombres/booléens arbitraires
n'est ajouté. Acteur client des corrections de jobs, audit legacy best-effort,
statut global et validation réglementaire ne sont pas refondus. Les gardes de
rôle/périmètre du lot 72 et politiques partagées/non classées restent inchangées.
Le mode sans RBAC configuré demeure historique ouvert.
