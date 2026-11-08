# Acteur serveur des corrections et annulations de champs — lot 85

Routes : `PATCH /api/jobs/{job_id}/fields/{name}` et
`POST /api/jobs/{job_id}/fields/{name}/undo`.

## Attribution

Les événements `field_validated` et `field_correction_annulee` emploient désormais
`_acteur(request)`, helper existant de l'API, au lieu de `user` fourni dans le corps.
L'acteur est le nom du principal résolu par le middleware : compte nominatif RBAC
ou `environnement` pour le jeton global quand le RBAC est actif. Sans RBAC,
le helper renvoie **`anonyme`**, y compris avec le jeton partagé historique.
Ce nom diffère du libellé `local` employé par les routes OCR du lot75 : aucune
harmonisation globale des helpers n'est revendiquée.

Le paramètre `user` reste accepté pour compatibilité, mais n'attribue plus ces
deux événements. `X-User`, `X-Actor` et les paramètres de requête déclaratifs ne
le remplacent pas. `reason`/`motif` restent déclaratifs et conservés, comme les
valeurs avant/après. L'acteur est résolu après réussite du compare-and-replace ;
les refus rôle/périmètre, champ absent, absence d'action et conflit ne produisent
pas d'événement de validation/annulation réussie.

Deux tests historiques sont explicitement actualisés : annulation attendant
`marie` déclaré et démonstration attendant `amina`, tous deux en mode ouvert.
Audit `anonyme`, motif et valeurs conservés ; vérification ajoutée de l'acteur
de correction dans le test d'annulation. Le fichier de démonstration (huit cas)
est ajouté à la sélection CI. Une première complète à trois échecs a révélé le
second contrat historique ; elle est conservée dans `complete-initial/`. La
suite complète est réexécutée après ajustement, pas déclarée verte par omission.

## Recette

65 nouveaux cas : 16 combinaisons des quatre actions confirmation/correction/
statut/undo et comptes opérateurs/admin/environnement ; 12 tentatives déclaratives
corps/en-têtes/query ; huit cas ouverts/jeton partagé sans RBAC ; quatre séquences
a/b/a ; 16 refus d'accès ; quatre champs absents ; quatre conflits de révision ;
une demande sans action. Requêtes HTTP avec stores/jobs/audits temporaires réels,
valeurs métier et réponses conservées, empreintes inchangées sur refus,
absence de faux succès et de marqueurs de jeton/usurpation dans les événements
de succès testés. Pas test de fournisseur OCR ou navigateur réel.

Contre-épreuve : anciens corps des deux handlers réinjectés uniquement en mémoire,
schéma/fixtures identiques, aucun remplacement du checkout ou de l'aperçu.
[Rapport](RAPPORT_LOT85.md), [recette](RECETTE_LOT85.json).

## Limites

Nom de principal résolu, **pas identité civile, identifiant immuable, signature
ou preuve non-répudiable**. Registre modifiable, jetons partageables et fallback
anonyme ne permettent pas une attribution individuelle certaine. Anciens
événements non réécrits, autres routes à acteur déclaratif non refondues,
notamment classification manuelle et opérations dossiers.

Pas redaction universelle : motifs/valeurs restent journalisés selon le contrat
existant et peuvent contenir des données sensibles. Pas transaction globale
résultat/audit, authentification renforcée, RBAC obligatoire ou journal WORM.
Limites de révision processus/ABA, annulation, exports en cache et qualité
inchangées. Pas modification de statut, priorité des valeurs ou droits d'accès.

Aperçu backend76 maintenu pour préserver les traitements ; code77–85 poussé/testé,
non chargé avant redémarrage maîtrisé. RBAC non activé automatiquement ;
mission réglementaire toujours partielle.
