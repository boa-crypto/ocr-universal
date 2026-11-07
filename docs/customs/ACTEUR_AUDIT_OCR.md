# Acteur des audits de validation et correction OCR — lot 75

7 novembre 2026. Périmètre : uniquement les deux routes OCR de dossiers
`POST …/{extraction_id}/valider` et `POST …/{extraction_id}/corriger`.

## Défaut corrigé

Ces routes transmettaient toujours la chaîne `utilisateur` au service, même
lorsque le middleware avait résolu un opérateur nommé. Le journal ne permettait
pas d'attribuer ces opérations au principal de la requête.

La garde commune renvoie maintenant l'utilisateur autorisé, **après** contrôle du
rôle et du périmètre. Les deux routes transmettent son `nom` au service et à ses
événements existants `ocr_extraction_validee` / `ocr_champ_corrige`, sous la clé
historique `user`. Pas nouveau champ de réponse, stockage d'identité dans
l'extraction ou élargissement d'autorisation.

## Sens exact du nom journalisé

| Configuration | Nom utilisé | Portée de l'attribution |
|---|---|---|
| RBAC actif, jeton enregistré | `nom` du principal résolu | Registre local + possession du jeton porteur ; pas identité civile |
| RBAC actif, jeton global | `environnement` | Passe-partout partagé préexistant ; pas attribution individuelle |
| RBAC inactif, sans jeton | `local` | Poste ouvert, pas utilisateur authentifié |
| RBAC inactif, jeton global exigé | `local` | Accès par secret partagé, middleware sans utilisateur RBAC individuel |

Corps, paramètres et en-têtes déclarant `user`, `acteur`, `utilisateur`, `X-User`
ou `X-Actor` ne deviennent pas des sources d'identité. Ces entrées sont ignorées
par ces routes, pas nouvellement rejetées. Le correctif n'est pas présenté comme
la fermeture d'une ancienne injection d'acteur : auparavant, l'acteur était
simplement générique.

Les gardes de rôle/périmètre/appartenance du lot 73 et le refus de champ absent
du lot 74 restent en place. Refus 401/403/404 : pas événement de validation ou
correction réussie, pas modification des JSON contrôlés. Les gardes existantes
conservent leurs journaux de refus ; pas nouveau journal dédié ici.

## Vérification et limites

33 nouveaux cas sur stores réels temporaires : huit succès opérateurs/admin/jeton
global, six tentatives de remplacement de nom côté client, quatre cas sans RBAC,
dix refus d'autorisation, un champ absent, deux extractions absentes et deux
séquences de changement d'acteur a→b→a. Vérification du journal, des mutations
attendues et des empreintes JSON sur refus ; absence de jeton et valeurs OCR ou
corrigées dans les événements de succès contrôlés. Pas test de concurrence.

Contre-épreuve : corps exacts des deux anciens handlers réinjectés en mémoire,
sans remplacer le checkout ou l'aperçu ; mêmes 33 cas. Résultats mesurés dans
[le rapport](RAPPORT_LOT75.md), [recette structurée](RECETTE_LOT75.json).

Le nom seul n'ajoute ni identifiant immuable ni mode d'authentification au journal ;
collisions et renommages sont possibles. Les jetons sont partageables, et les
appels directs au service acceptent toujours un argument `user`. Les autres
routes, notamment les corrections de jobs, ne sont pas refondues. Les événements
historiques `utilisateur` ne sont pas réattribués. Audit legacy best-effort et
configuration du service inchangés : pas transaction, signature, WORM, annuaire,
preuve de présence humaine ou validation réglementaire. Le mode ouvert reste
ouvert ; aucun compte, secret ou RBAC n'est créé automatiquement.
