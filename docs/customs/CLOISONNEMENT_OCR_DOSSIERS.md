# Routes OCR de dossiers : périmètre et appartenance — lot 73

7 novembre 2026. Complète le [cloisonnement des corrections de jobs](CLOISONNEMENT_CORRECTIONS_CHAMPS.md).

## Sept opérations sur dossiers

Création depuis un job, liste d'extractions, détail, mise à jour, validation,
correction et classification automatique : rôle lecteur/opérateur et visibilité
du dossier sont contrôlés avant accès au service d'intégration. Les droits du
middleware existant restent en place ; les gardes sont explicites dans les handlers.
La liste statique des types documentaires ne devient pas une ressource de dossier.

Pour détail, mise à jour, validation et correction, l'extraction doit appartenir
au `dossier_id` du chemin : 404 si absente, 403 si rattachée ailleurs. Validation
et correction ne peuvent plus accepter un identifiant d'extraction étrangère sous
un dossier visible. Les contrôles d'appartenance préexistants en lecture et mise
à jour sont regroupés sans en retirer la vérification.

Le contrôle d'un dossier invisible précède le chargement du service. Pour une
URL de dossier visible avec extraction étrangère, sa fiche est chargée pour
vérifier l'appartenance, mais pas renvoyée ou modifiée. Les tests vérifient
l'absence de valeur dans le refus et les empreintes des JSON temporaires.

## Création depuis un résultat contrôlé

- Identifiant dossier du corps égal au chemin, sinon 422.
- Dossier autorisé, job source visible selon `_exige_job` et enregistrement de
  job présent ; refus avant lecture de son résultat s'il est hors périmètre.
- Utilisation du store de dossiers de l'API, pas du `app.state.store` de jobs.
- Résultat lu dans le store de jobs contrôlé de l'API et transmis explicitement
  au service via le nouvel argument interne facultatif `result_json`.
- Ce chemin ne relit pas un résultat depuis une configuration globale différente.
  Les anciens appels internes à trois arguments conservent leur relecture legacy ;
  le cycle de configuration du singleton d'intégration n'est pas refondu.

Les dates par défaut de `ExtractionOCR` et `ChampExtrait` sont désormais des
fonctions appelables évaluées à la création, et non une chaîne passée comme
factory, qui empêchait la construction sans date explicite. Pas horodatage signé
ou source de temps de confiance.

## Politique et audit

Un job partagé avec au moins un dossier visible et un job non classé gardent la
politique existante. Administrateur, jeton global et mode sans RBAC/jeton restent
compatibles ; aucune protection n'est activée automatiquement sans configuration.
La cohérence corps/chemin et l'appartenance extraction/dossier restent requises
même sans RBAC.

Les refus de périmètre dossier/job utilisent les journaux des gardes existantes.
Le refus d'appartenance extraction/dossier reste un 403 sans nouvelle catégorie
d'audit dédiée. Les audits de modification des routes utilisent la configuration
de requête ; le service d'intégration conserve son mécanisme d'audit préexistant.
Les acteurs historiques de validation/correction ne deviennent pas une preuve
d'identité authentifiée par ce correctif.

## Mesure et limites

59 nouveaux cas sur TestClient, dossiers/jobs/extractions persistés dans des stores
temporaires, rôles synthétiques, empreintes JSON et opérations autorisées réelles.
Pas appel à un moteur OCR : la création convertit un résultat synthétique déclaré.
Les cas métier ne prouvent pas une validation humaine réelle ou réglementaire.

Contre-épreuve sur six anciens handlers, réinjectés en mémoire sans décorateurs.
La création, les factories et l'argument interne nouveaux sont exclus du témoin :
la création ancienne utilisait déjà un store incompatible. Les tests positifs du
nouveau chemin l'exercent sans prétendre que l'ancien fonctionnait.

Pas audit exhaustif de toutes les routes, rattachements, stores ou identifiants ;
pas transaction création/rattachement/audit, protection des courses entre gardes
et mutations, journal signé/WORM, isolation forte des documents non classés,
refonte de l'historique de correction ou recalcul qualité après édition.
Pas précision OCR, navigateur réel, charge ou production fiscale qualifiés.
Voir [rapport et recette](RAPPORT_LOT73.md).
