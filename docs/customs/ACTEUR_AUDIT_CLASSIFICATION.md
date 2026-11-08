# Acteur du nouvel audit de classification manuelle — lot 87

Complète le lot86 : `corrected_by` était déjà résolu côté serveur et persisté,
mais le résumé `document_classified` ne portait pas cette attribution.

## Changement ciblé

Après succès du compare-and-replace, le PATCH de classification transmet son
acteur déjà résolu à `consigne_classification(..., manuel=True, acteur=acteur)`.
L'événement conserve ses champs précédents et ajoute **`acteur`**, égal au
`corrected_by` de la décision sauvegardée par cette requête. Nom du compte RBAC,
`environnement` pour jeton global avec RBAC actif, `anonyme` sans RBAC.
Les déclarations corps/en-têtes/query ne remplacent pas ce principal.

Le helper accepte un argument optionnel **keyword-only** `acteur`. Si absent ou
None, aucun champ acteur n'est ajouté : les appels existants, notamment la route
automatique, conservent la forme précédente de l'événement. Le helper ne déduit
jamais l'identité du `corrected_by` du résultat, qui peut être déclaratif dans
un appel Python extérieur. Un acteur explicitement donné à ce helper reste une
déclaration de son appelant ; l'authentification est celle de la frontière HTTP,
pas une propriété du helper de journalisation.

Refus d'accès, catégorie invalide, job absent et conflit ne créent pas de succès.
Une vérification au moment précis de l'appel audit relit le résultat via un
nouveau store et contrôle catégorie/acteur déjà persistés. Pas transaction
atomique audit/résultat : voir limites ci-dessous.

## Recette

34 nouveaux cas : 12 comptes/catégories, trois tentatives corps/header/query,
deux modes sans RBAC, une séquence a/b/a, quatre refus d'accès, trois catégories
invalides, un conflit, un job absent, quatre contrats helper sans acteur,
un helper avec acteur explicite, une route automatique sans nouveau champ,
un contrôle audit après persistance. Requêtes HTTP et stores/jobs/audits réels
temporaires ; contenu exact des clés et concordance résultat/événement, pas
jeton/usurpation dans les succès testés. Pas OCR fournisseur ou navigateur réel.

Contre-épreuve : ancien handler **et ancien helper** réinjectés ensemble en
mémoire, signatures/defaults cohérents ; sources/aperçu non remplacés. Inclut
le refus historique du nouveau mot-clé du helper : échec attendu de son contrat,
pas ancien helper branché au nouveau handler par erreur.
[Rapport](RAPPORT_LOT87.md), [recette](RECETTE_LOT87.json).

## Limites

Nom de principal, pas identité civile/ID immuable/signature. Registre modifiable,
jetons partageables, fallback anonyme. L'audit demeure best-effort postcommit :
une panne peut séparer résultat et journal, sans transaction ou garantie WORM.
Le résultat peut changer de nouveau après ce commit ; l'événement décrit cette
opération, pas forcément l'état courant à toute lecture ultérieure.

Pas réécriture ou attribution rétroactive des anciens événements. Pas identité
inférée pour l'automatique ou les appels Python sans acteur explicite. Le GET
conserve la concordance cinq champs du lot78 pour son timestamp, sans comparer
l'acteur ni prouver une identité de révision. Aucune garantie globale de
non-répudiation ou de redaction des motifs/valeurs sensibles.

Pas changement de score manuel1, catégorie, profil suggéré, droits, exports en
cache, autres opérations dossiers à acteur client, révision processus/ABA.
Aperçu backend76 maintenu : code77–87 poussé/testé mais non chargé avant
redémarrage maîtrisé pour préserver les traitements. RBAC non activé
implicitement ; mission réglementaire toujours partielle.
