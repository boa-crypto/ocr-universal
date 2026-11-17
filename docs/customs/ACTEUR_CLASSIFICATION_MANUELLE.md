# Attribution serveur de la classification manuelle — lot 86

Route : `PATCH /api/jobs/{job_id}/classification`.

## Changement et portée

Le `corrected_by` de la classification persistée était alimenté par `user`
client. La route fournit maintenant `_acteur(request)` à `classification_manuelle` :
nom du principal RBAC, `environnement` avec jeton global et RBAC actif,
**`anonyme` sans RBAC**, y compris avec jeton partagé historique.

`user` reste accepté dans le corps pour compatibilité, sans effet attributif.
Les déclarations `acteur`/`corrected_by`, en-têtes `X-User`/`X-Actor` et query
ne remplacent pas le principal serveur. Réponse, résultat relu via nouveau
`JobStore`, modèle `DocumentResult`, GET et nouvel export JSON conservent la
même attribution. Persistance conditionnelle avant audit/réponse inchangée.
Un conflit ne publie ni nouvelle classification ni audit de succès.

Le journal `document_classified` reste le résumé existant **sans acteur ajouté**.
Ne pas déduire une attribution serveur de cet ancien événement ou de sa seule
concordance avec le GET. Le helper Python `classification_manuelle` reste une
fonction métier recevant un utilisateur : son paramètre n'est pas, à lui seul,
une identité authentifiée. Seule la frontière HTTP ciblée résout le principal.

Le test de persistance du lot77 (18 cas paramétrés concernés) attend désormais
le principal `a`, plus `DECLARED77` transmis par le client. L'assertion conserve
sa précision ; pas suppression de la vérification d'attribution. Les documents
historiques77 décrivent l'état livré alors, remplacé ici pour ce point.

## Recette

40 nouveaux cas : 12 comptes/catégories (deux opérateurs, admin, environnement),
neuf déclarations corps/header/query, six modes ouverts/jeton partagé,
une séquence a/b/a, trois exports JSON, quatre refus d'accès, trois catégories
invalides, un conflit et un job absent. Requêtes HTTP et stores/jobs/audits
réels temporaires ; relecture typée et nouveau store, résultat inchangé sur
refus, pas succès classif fantôme. Pas précision métier, OCR fournisseur ou
navigateur réel.

Contre-épreuve : ancien handler exact réinjecté uniquement en mémoire, décorateur
retiré, schéma/fixtures conservés. Checkout/aperçu non remplacés.
[Rapport](RAPPORT_LOT86.md), [recette](RECETTE_LOT86.json).

## Limites

Principal résolu, **pas identité civile, identifiant immuable ou signature**.
Registre modifiable, jetons partageables et fallback anonyme ne prouvent pas
une personne. Pas enrichissement de l'audit résumé ou migration de l'historique,
pas reconstruction d'anciennes classifications et pas invalidation des exports
préexistants en cache. Les exports testés sont générés après la classification.

Score manuel1, motifs, normalisation/validation de catégorie, modèle de profil
suggéré non appliqué, autorisations et politique de révision restent inchangés.
Pas transaction globale résultat/audit, WORM, garantie multiprocessus ou anti-ABA.
Autres opérations dossiers à acteur client non refondues. Pas activation RBAC.
Aperçu backend76 maintenu : code77–86 poussé/testé mais non chargé avant
redémarrage maîtrisé pour préserver les traitements. Mission réglementaire partielle.
