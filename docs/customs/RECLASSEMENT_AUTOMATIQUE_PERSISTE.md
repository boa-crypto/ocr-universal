# Reclassement automatique persistant, décision manuelle protégée — lot 79

7 novembre 2026. Périmètre : `POST /api/jobs/{job_id}/classify`.

## Défaut et changement

Comme l'ancienne route manuelle avant le lot 77, cette route renvoyait une
classification et la journalisait sans sauvegarder la décision dans le résultat.
La relecture pouvait donc conserver une autre catégorie. La route exige
maintenant explicitement le rôle opérateur puis la visibilité du job, vérifie
l'existence du job et du résultat (404), puis sauvegarde la nouvelle classification
avant audit de succès et réponse. Les autres données du résultat sont conservées.

Ce reclassement automatique ne doit pas annuler implicitement une décision
manuelle persistée. Avant appel au classifieur, la route refuse avec 409 si
la classification existante n'est ni absente/`None` ni un objet dont `manual`
est absent ou vaut exactement le booléen `False`. Une décision `manual=True`
est donc protégée ; marqueurs ambigus (`None`, chaînes, nombres, listes/objets)
et classifications non objets sont aussi refusés. `0` n'est pas assimilé à
`False` pour cette garde. Une classification historique sans clé `manual` reste
reclassable ; une ancienne intervention seulement journalisée n'est pas
reconstituée automatiquement.

## Comportements conservés

Le classifieur, son score heuristique, preuves, alternatives, motif et indicateur
de revue restent inchangés. La suggestion de profil reste une suggestion,
pas modification automatique du profil ou réextraction des champs. Jobs
partagés/non classés, administrateur/jeton global et mode sans RBAC conservent
leurs politiques ; aucune protection n'est activée implicitement.

Pas nouveau paramètre `force`, suppression de décision humaine, changement de
l'API de classification manuelle, ni migration d'historique. Une exception de
sauvegarde se propage sans succès ou audit de classification réussie ; l'échec
injecté dans le test survient avant écriture, pas preuve d'atomicité après crash.

## Recette

29 nouveaux cas sur jobs/stores/audits temporaires réels : neuf sauvegardes
avec visibilité partagée/non classée ou propre et état antérieur absent/ancien,
sept marqueurs manuels/ambigus refusés, trois classifications non objets,
quatre refus d'autorisation, deux accès privilégiés, job/résultat absent,
sauvegarde échouée et chaîne manuelle puis automatique refusée.

Le classifieur de ces nouveaux tests est **substitué par une sortie synthétique
contrôlée** pour vérifier orchestration, persistance et refus ; ce n'est pas une
mesure de précision du classifieur. Les tests existants du classifieur sont
également exécutés dans la sélection locale. Aucun OCR fournisseur réel,
navigateur ou corpus officiel ajouté.

Contre-épreuve : corps exact de l'ancien handler réinjecté en mémoire, mêmes
29 cas, sans remplacer checkout ou aperçu. Résultats mesurés dans
[le rapport](RAPPORT_LOT79.md), [recette](RECETTE_LOT79.json).

## Limites

Pas verrou/transaction entre lecture, garde, sauvegarde et audit : une décision
concurrente reste un risque. Pas historique complet des décisions remplacées,
archivage des anciennes preuves, invalidation des exports en cache, recalcul de
qualité globale, migration des interventions humaines seulement journalisées
ou contrôle d'identité civile. Le champ `manual` absent reste interprété selon
la politique historique automatique ; pas détection universelle d'interventions
humaines non marquées. Audit legacy best-effort, ni signé ni WORM.

Aperçu backend76 maintenu sans redémarrage pour préserver les traitements.
Le code 77–79 poussé/testé n'est pas chargé dans ce processus avant un
redémarrage maîtrisé. Mission réglementaire toujours partielle.
