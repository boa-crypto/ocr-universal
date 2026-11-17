# Classification manuelle persistée — lot 77

7 novembre 2026. Périmètre : `PATCH /api/jobs/{job_id}/classification`.

## Défaut et correction

La route construisait une décision manuelle, la renvoyait et la journalisait,
mais ne modifiait pas `result.json`. Le GET privilégie pourtant la classification
du résultat : une ancienne catégorie pouvait rester affichée avec une indication
manuelle issue du seul journal.

La route exige explicitement le rôle opérateur puis la visibilité du job,
vérifie son existence (404) et la disponibilité de son résultat (409). Après
validation de la catégorie, elle remplace seulement l'objet `classification`
du résultat et appelle `save_result` **avant** l'audit de succès et la réponse.
Une lecture par un store neuf et le GET retrouvent donc la décision manuelle.
Catégorie invalide : 422 sans écriture ou audit de classification réussie.

Les pages, champs et autres données du résultat ne sont pas réécrits
sémantiquement. Les preuves automatiques de l'ancienne catégorie ne sont pas
attribuées à la nouvelle : la décision manuelle garde les listes de preuves et
alternatives vides produites par le service existant. L'ancien objet de
classification est remplacé, **pas archivé intégralement par ce correctif**.

## Contrats inchangés et limites

- La catégorie doit appartenir au classifieur configuré ; pas nomenclature
  douanière officielle ou modification automatique du profil d'extraction.
- `corrected_by` reste issu du `user` déclaratif du corps, ou `utilisateur` :
  **pas identité authentifiée**. Le lot 75 ne concernait que les routes OCR
  de dossiers, pas cette route de classification de jobs.
- Le score manuel historique 1,0 et `needs_review=False` restent inchangés ;
  ce n'est pas une probabilité moteur calibrée ni une validation juridique.
- Jobs partagés/non classés, administrateur/jeton global et mode sans RBAC
  conservent leurs politiques. Pas activation automatique de protection.
- Audit legacy best-effort, pas transaction audit/résultat, verrou de concurrence,
  garantie crash/exactly-once ou journal WORM/signé. Une exception de sauvegarde
  se propage sans succès ; l'injection testée échoue avant écriture.
- Pas refonte de la route automatique `/classify`, du repli GET sur les anciens
  journaux, d'un historique complet de décisions ou des exports déjà mis en cache.
  Pas migration des anciennes corrections seulement journalisées.

## Recette

31 nouveaux cas : 18 créations/remplacements de décision manuelle (3 catégories,
3 politiques de visibilité, présence/absence d'ancienne classification),
2 accès privilégiés, 4 refus avant lecture/écriture, 3 catégories invalides,
job absent, résultat absent, sauvegarde échouée et décisions successives.
Stores/jobs et audits temporaires réels ; relecture par `JobStore` neuf,
validation `DocumentResult`, GET et absence de modifications hors classification.
Pas moteur OCR ou fournisseur réel exécuté par ces tests.

Contre-épreuve : corps exact de l'ancien handler réinjecté en mémoire, sans
remplacer le checkout ni l'aperçu, mêmes 31 cas. Résultats mesurés dans
[le rapport](RAPPORT_LOT77.md), [recette structurée](RECETTE_LOT77.json).

L'aperçu existant est maintenu avec le backend du lot 76, sans redémarrage imposé
pour ne pas interrompre les traitements. Le code 77 poussé et testé ne sera
chargé dans ce processus qu'après un prochain redémarrage maîtrisé.
