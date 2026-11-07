# Corrections et annulations : rôle et document visible — lot 72

7 novembre 2026. Alignement de deux routes existantes sur la garde documentaire
utilisée pour lire les résultats, sans nouvelle permission ni nouvelle API.

## Routes couvertes

- `PATCH /api/jobs/{job_id}/fields/{name}` : confirmation, correction ou statut ;
- `POST /api/jobs/{job_id}/fields/{name}/undo` : annulation.

Après le contrôle du rôle opérateur, `_exige_job(request, job_id)` est désormais
appelé **avant `store.load_result`**, la recherche du champ, l'audit d'une correction
réussie et toute sauvegarde. Avant ce lot, le rôle seul était vérifié ici : un
opérateur hors périmètre pouvait atteindre ces chemins alors que la lecture du
même résultat lui était refusée.

Avec RBAC actif, un document classé exclusivement dans des dossiers invisibles
renvoie **403 « document hors de votre périmètre »**, que le champ existe ou non.
Le résultat n'est ni chargé par ces handlers ni modifié, et aucun événement
`field_validated`/`field_correction_annulee` de succès n'est émis par le refus.
La garde préexistante trace `acces_refuse_document` avec acteur, route et
identifiants de job/dossiers, pas les valeurs du champ ou le corps de correction.
Le journal de refus lui-même n'est pas exempt de métadonnées sensibles.

## Politique conservée

La règle est **au moins un dossier visible**, pas « tous les dossiers visibles » :
un document partagé entre un dossier visible et un invisible reste accessible.
Un document non classé reste régi par le rôle seul. Les administrateurs et le
jeton d'environnement gardent leurs droits préexistants ; lecteurs et jetons
inconnus restent refusés par les contrôles centraux.

**Sans registre RBAC actif et sans jeton configuré, le comportement ouvert
historique est conservé.** Ce correctif n'active pas automatiquement le RBAC, ne
crée pas de propriétaire pour les documents non classés et ne réduit pas les
privilèges du jeton d'environnement. Ce sont des limites de la politique existante,
pas une isolation forte de tous les documents.

Les opérations autorisées gardent leur comportement : valeurs brutes/normalisées
préservées, confirmation/correction/statut appliqués, annulation et audit existants.
Pas changement des règles d'historique, des états de champ ou du calcul qualité.

## Vérifications

44 nouveaux cas sur stores et dossiers temporaires, pièces réellement rattachées,
registre RBAC synthétique et routes HTTP via TestClient : refus hors périmètre,
champ absent, garde avant chargement (lecture rendue interdite dans le harnais),
empreinte du `result.json` conservée, absence d'audit de succès et de valeurs dans
le refus ; accès visible/partagé/non classé, rôles, administrateur, jeton global et
mode sans RBAC. Une correction autorisée préalable crée le véritable événement
nécessaire pour tester l'annulation, pas un historique fictif ajouté en production.

Le témoin négatif réinjecte en mémoire les corps exacts des deux fonctions du lot
71 dans les mêmes callables de l'application de test, sans leurs décorateurs,
pour conserver les stores temporaires et éviter un double enregistrement de route.
Il ne remplace aucun fichier du checkout et ne modifie pas l'aperçu en cours.

## Non couvert

Pas audit exhaustif de toutes les routes ou de tous les moyens de rattacher un
job à un dossier, test de course rattachement/écriture, transaction globale,
politique de propriété, preuve d'identité du champ `user` fourni dans le corps,
journal signé/WORM ou garantie d'atomicité audit/sauvegarde. Les contenus et règles
préexistants des corrections/annulations ne sont pas refondus. Aucun nouveau
recalcul du rapport qualité après édition humaine.

Les identifiants figurent dans le journal de refus ; pas garantie générale contre
l'énumération par codes HTTP, les journaux tiers ou une configuration de rôles
excessivement large. Pas qualification de navigateur, charge ou production fiscale.
Voir [rapport et recette](RAPPORT_LOT72.md).
