# Révision avant correction/annulation de champ — lot 81

7 novembre 2026. Complète le [lot 80](REVISION_CLASSIFICATIONS.md).
Périmètre : `PATCH /api/jobs/{job_id}/fields/{name}` et
`POST /api/jobs/{job_id}/fields/{name}/undo`.

## Changement

Les deux routes lisent désormais résultat et révision des mêmes octets via
`load_result_revision`. Elles préparent la correction/annulation puis utilisent
`replace_result_revision` au lieu d'une sauvegarde inconditionnelle. Si le
résultat ne correspond plus à cette révision, **409**, sans remplacement,
audit de succès ou nouvelle tentative implicite.

Cela empêche ces deux commits périmés d'effacer une classification, une nouvelle
correction du même champ ou une modification d'un autre champ. Une disparition
constatée à la comparaison refuse aussi l'écriture. Les gardes de rôle/périmètre
précèdent les nouvelles primitives. Valeurs vides/zéro, statuts, acteurs
historiques et mécanisme d'annulation restent inchangés hors gestion du conflit.

## Recette

20 nouveaux cas sur stores/jobs et journaux temporaires réels :
- 8 modifications injectées après lecture (classification, même champ, autre
  champ, suppression), pour correction et annulation ;
- 8 refus rôle/périmètre/jeton avant lecture et comparaison de révision ;
- 2 erreurs de sauvegarde injectées avant écriture, sans audit de succès ;
- 2 entrelacements HTTP synchronisés par événements : correction ou annulation
  suspendue, deuxième correction réussie, première refusée 409. La deuxième
  valeur persiste et elle seule ajoute un succès au journal.

Pas sommeil de hasard ou fournisseur OCR ; mutations concurrentes de préparation
synthétiques, plus deux véritables requêtes HTTP entrelacées sur TestClient.
Contre-épreuve : corps exacts des deux anciens handlers réinjectés en mémoire,
store et révision du lot 80 conservés. Pas rejeu complet de l'ancien stockage,
checkout/aperçu non remplacés. Résultats dans [rapport](RAPPORT_LOT81.md) et
[recette](RECETTE_LOT81.json).

## Limites

Même verrou processus que le lot 80 : pas multiprocessus, écriture directe ou
suppression non participante couverte. Protection de ces commits, pas de tous
les écrivains : un pipeline/écrivain non conditionnel peut toujours sauvegarder
un état périmé plus tard. SHA de contenu avec limite ABA, pas version monotone,
signature ou preuve d'authenticité ; reformattage également conflictuel.

Pas refonte multi-niveau de l'annulation, restauration exacte de tous les
emplacements manuels antérieurs ou qualification exhaustive de la lecture du
journal. Un changement du seul audit sans changement du résultat n'est pas
capturé par cette révision. Audit legacy best-effort après sauvegarde, sans
transaction, WORM ou exactly-once ; acteurs déclaratifs et valeurs journalisées
inchangés. Pas invalidation d'exports en cache, recalcul qualité global, nouvelle
règle de statut ou migration de données.

Aperçu backend76 maintenu pour préserver les traitements ; code77–81 poussé et
testé, non chargé dans ce processus avant redémarrage maîtrisé. Pas activation
automatique du RBAC ; mission réglementaire toujours partielle.
