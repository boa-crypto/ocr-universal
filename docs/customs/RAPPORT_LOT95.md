# Rapport consolidé95 — interface, audit et sauvegarde des dossiers

**Bilan : fonctions techniques intégrées et testées ; mission douanière globale
partielle, non recevable pour production fiscale.** Ce rapport ne transforme ni
les fixtures ni les pistes documentaires en classement applicable.

## Réalisations opérationnelles sur environnement de test

- Interface de création, relecture/réconciliation et révision des dossiers dans
  l'administration existante : cinq caractéristiques déclarées, questions,
  comparaison littérale FR/AR avec références/extraits, choix explicite du
  candidat, motivation humaine, transitions et historique. Pas de choix automatique.
- Contrôle des versions côté serveur ; prévention des doubles requêtes UI,
  refus de rejouer après409/503/panne réseau ; invalidation des réponses tardives,
  purge après refus d'autorisation et au prochain appel après changement de compte.
- Outbox SQLite des événements de version, insérée avec état/historique dans une
  même transaction. Livraison et acquittement récupérables à la relecture
  autorisée ; reprise paresseuse des versions94 ; identifiant d'événement stable.
- Sauvegarde cohérente SQLite du dossier et de son outbox, y compris en WAL,
  sans rejouer les anciens sidecars ; vérification SQLite et reprise sur cible
  neuve testées. Les données réelles n'ont pas été sauvegardées/restaurées.
- Scripts intégrés dans le shell/service worker et tests intégrés à la CI.

Contrat détaillé : [interface et audit](INTERFACE_ET_AUDIT_DOSSIERS.md).
Plan global et dépendances : [achèvement métier](ACHEVEMENT_METIER.md).

## Fichiers principaux

- `web/customs-assessments.js`, `web/customs-review.js`, `web/index.html`, `web/sw.js` ;
- `src/unocr/customs_reference/assessment.py`, `src/unocr/routes/customs_review.py`, `src/unocr/backup.py` ;
- `tests/test_customs_assessment.py`, `tests/test_customs_backup.py`,
  `tests/test_customs_assessments_ui.py`, `tests/ui_customs_assessments*.js`,
  `tests/test_ui_engine_provenance.py` ;
- `package.json`, `.github/workflows/customs-review.yml`, contrats et reçus documentaires.

Code fonctionnel `dfdc8dff`, correction du contrat de cache `2f21fb99` sur la
branche de session. Aucun fichier de données/journal partagé inclus dans ces commits.

## Tests et corrections

| Vérification | Résultat |
|---|---|
| Métier + revue + sauvegarde | **114 réussis** |
| Nouveaux cas Python | **7**, plus **16 scénarios JSDOM métier** |
| Interface historique | **212 scénarios réussis**, toujours distincts des écritures métier |
| Nouveau composant sur HTTP/API réelle | Création POST, révision PATCH et relecture GET réussies sur fixtures isolées |
| Recette documentaire | **2196 réussis**, aucune erreur/ignoré ; comprend le pont HTTP métier |
| Première complète | 4350 réussis, **3 échecs**, 1 ignoré : deux Indra historiques et contrat de cache71 devenu obsolète |
| Complète après correction | **4351 réussis, 2 échecs historiques, 1 ignoré**, 379,58s |
| CI ciblée sur `2f21fb99` | [42469367668 : réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42469367668) |
| Ruff périmètre source/tests/recette | Réussi |
| Empreintes historiques | **26/27**, même écart partagé `data/referentiels.json` préexistant, non restauré |

Les deux échecs restants sont `tests/test_indra_ocr.py::test_indra_engine_availability`
et `tests/test_ocr.py::test_selection_prefers_native_when_present`. Le test de
reconnaissance Indra est ignoré. Pas de modèle Indra téléchargé depuis un hôte
non autorisé et pas de masquage des échecs.

La première complète a révélé un test épinglant encore le cache71. Le contrat
vérifie désormais le cache95, l'ordre de chargement et la présence du nouveau
module ; suite complète réexécutée. Les deux résultats restent conservés.
Une tentative Ruff à la racine a également rencontré les scripts exploratoires
et paquets tiers préexistants hors périmètre ; ils n'ont pas été modifiés pour
rendre cette commande verte. La recette de référence contrôle source/tests.

Les simulations couvrent notamment XSS textuel, conflits,503 après commit,
réseau interrompu, double clic, changement de lot/route/compte,403, réponse
incomplète et réouverture. Les tests backend vérifient sortie durable après503,
récupération sans nouvelle version, altération refusée, concurrence et doublon
identique après append suivi d'une panne. JSDOM n'est pas un navigateur réel.

Mesures détaillées et empreintes : [RECETTE_LOT95.json](RECETTE_LOT95.json).
Artefacts bruts hors dépôt : `/home/user/recettes-unocr/lot95/` ; sélection
114 cas : `/home/user/recettes-unocr/lot95-targeted.xml`.

## Limites et intervention humaine restante

**Ne pas annoncer “tout achevé”.** L'UI et la récupération d'audit sont livrées,
mais le rattachement de justificatifs techniques, l'ontologie/IA, le raisonnement
RGI automatisé, la consolidation du droit à date, les relations juridiquement
prouvées et l'intégration centrale ne sont pas livrés par cette campagne.
Du développement reste possible ; il n'est pas assimilé à une dépendance externe
pour dissimuler son absence.

La clôture globale exige en plus les originaux officiels exhaustifs FR/AR et
leurs versions, les mesures fiscales sourcées, les règles et cas de référence
qualifiés, des responsables habilités et une politique de publication. Les sites
officiels ne sont pas accessibles via les hôtes réseau autorisés ici. Aucun faux
corpus, synonymes normatifs ou taux applicable n'a été inventé pour contourner
cette limite. **0 nouvel original officiel, 0 article/code officiellement validé,
0 publication active.**

Les événements de version sont récupérables **au moins une fois**, pas exactly-once.
Un crash entre append et acquittement peut dupliquer une ligne ; le résumé HTTP
reste un événement distinct et503 après commit demeure possible. Ni SHA ni
outbox ne fournissent signature, WORM ou preuve indépendante contre le propriétaire
du disque. Les sauvegardes ne sont pas un instantané distribué lots/journal/base.

L'aperçu partagé reste **backend76**, sans redémarrage pendant ses traitements :
les évolutions95 ne sont pas déployées sur ce processus. Aucun changement de RBAC
réel, publication ou restauration n'a été exécuté. Habilitation effective,
séparation des responsabilités, sauvegarde/reprise d'exploitation, navigateurs,
charge et réception métier doivent précéder la mise en service.
