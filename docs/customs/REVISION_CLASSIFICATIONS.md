# Révision de contenu avant sauvegarde des classifications — lot 80

7 novembre 2026. Périmètre : les deux routes de classification de jobs
`POST /api/jobs/{job_id}/classify` et `PATCH /api/jobs/{job_id}/classification`.

## Problème et contrat

Le contrôle `manual` du lot 79 précédait le calcul et la sauvegarde. Une
correction manuelle pouvait être enregistrée pendant ce calcul, puis écrasée
par le résultat automatique issu de l'ancienne lecture. Une modification de
champ pouvait également être perdue par ce remplacement du résultat entier.

`JobStore.load_result_revision` lit le JSON et calcule le SHA-256 des **mêmes
octets**. Les routes conservent cette révision pendant le calcul. À la sauvegarde,
`replace_result_revision` compare la révision courante sous un verrou réentrant
partagé par tous les stores de résultats du processus et n'écrit qu'en cas
d'égalité. `save_result` participe au même verrou, pour que comparaison et
écriture soient indivisibles vis-à-vis de ces sauvegardes dans ce processus.

Résultat modifié ou supprimé entre lecture et comparaison : **409**, sans
remplacement ni audit de classification réussie, avec invitation à relire.
Pas relecture/réessai automatique qui appliquerait la décision à un autre état.
Une révision manquante ne permet pas de recréer un résultat supprimé.
Les contrôles de rôle, visibilité, existence et décision manuelle restent en amont.

## Portée exacte

- Révision des octets, pas version monotone, signature ou authenticité : une
  simple reformatisation provoque aussi un conflit. Un retour A→B→A aux mêmes
  octets n'est pas distingué d'un état resté A (limite ABA).
- Protection du **commit de ces deux classifications**, pas de toute édition.
  D'autres routes/écrivains qui sauvegardent un résultat lu avant une modification
  peuvent encore écraser celle-ci après ce commit. Leur `save_result` est sérialisé,
  mais leur propre lecture/modification n'est pas devenue conditionnelle.
- Verrou Python commun au processus, pas verrou multiprocessus, réseau ou
  filesystem ; écritures directes et autres serveurs exclus de la garantie.
- Calcul du classifieur hors verrou ; seules comparaison/lecture courante et
  sauvegardes participent au verrou global des résultats. Pas qualification
  de charge ; JSON lu intégralement, sans nouvelle limite de taille.
- Audit legacy best-effort après commit, pas transaction audit/résultat,
  crash/exactly-once, journal WORM ou historique complet. JSON courant malformé
  ou erreur d'I/O peuvent encore faire échouer la requête, sans réparation.

## Recette

21 nouveaux cas : deux lectures/remplacements par store courant ou neuf,
quatre conflits (classification, champ, format, suppression), absence de résultat,
course entre deux stores sur la même révision avec un seul gagnant, quatre
changements injectés pendant les calculs API, un vrai entrelacement de requêtes
HTTP automatique/manuelle synchronisé par événements et huit gardes avant accès
aux nouvelles primitives de révision.

Stores/audits réels temporaires ; barrières/événements sans temporisation de
hasard. L'automatique suspendu laisse la requête manuelle réussir, puis reçoit
409 ; seule la décision manuelle reste et seul son succès est journalisé.
Les calculs de conflit sont synthétiques ou interceptés pour imposer l'entrelacement,
pas mesure de précision métier ou OCR fournisseur.

Contre-épreuve : corps exacts des deux anciens handlers réinjectés en mémoire,
**nouveau store conservé** pour isoler leur absence d'usage de la révision.
Pas rejeu complet de l'ancien stockage. Checkout et aperçu non remplacés.
Résultats mesurés dans [le rapport](RAPPORT_LOT80.md), [recette](RECETTE_LOT80.json).

Les limites des lots 77–79 (déclarations d'acteur, score manuel, historique,
exports en cache) restent applicables. L'aperçu backend76 est maintenu pour
préserver les traitements ; le code 77–80 poussé/testé n'y est pas chargé avant
redémarrage maîtrisé. Pas activation automatique du RBAC ni validation juridique.
