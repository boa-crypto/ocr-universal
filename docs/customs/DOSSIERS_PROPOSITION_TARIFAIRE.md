# Dossiers métier de proposition tarifaire — lot 94

## Fonction livrée

API de dossier persistant sur un lot tarifaire de quarantaine enregistré et
épinglé. Caractéristiques **déclarées** du produit, pistes littérales FR/AR,
questions sur les informations non renseignées, abstention documentaire,
revue humaine, proposition motivée, rejet et réouverture. Aucun code ou taux
applicable sélectionné automatiquement, aucune publication.

### API

Préfixe : `/api/v1/customs-review/lots/{lot_id}/assessments`.

- `POST` : créer avec `dossier_id` choisi par le client et `produit`.
- `GET /{dossier_id}` : état et historique résumé des versions.
- `PATCH /{dossier_id}` : transition avec `version_attendue`, `statut`,
  `justification`, et éventuellement `produit` complété.

Même authentification stricte que la revue : administrateur nominatif RBAC,
non environnement, puis nom dans l'allowlist de réviseurs. RBAC absent/ouvert
n'autorise pas ces routes. Aucun chemin ou acteur fourni par HTTP. Le corps
interdit les clés supplémentaires ; un `user` client n'est pas une identité.
Tous les accès vérifient lot autorisé, manifeste épinglé et intégrité du lot.
Le GET revalide également les fichiers reçus, pas seulement le manifeste.
Réponse no-store ; `lecture_seule=false` pour création/révision uniquement.

Exemple de création, avec des données de démonstration NON OFFICIELLES :

```json
{"dossier_id":"ESSAI94","produit":{"designation":"Équipement de démonstration"}}
```

États : `brouillon` → `en_revue`/`a_completer`/`rejetee` ;
`en_revue` → `en_revue`/`a_completer`/`proposition_humaine`/`rejetee` ;
`a_completer` → `a_completer`/`en_revue`/`rejetee` ;
`proposition_humaine` → `en_revue`/`rejetee` ; `rejetee` → `en_revue`.
Un produit proposé/rejeté doit d'abord être rouvert avant modification.

`proposition_humaine` exige tous les champs produit renseignés, un code parmi
les 20 pistes documentaires affichées, justification, raisonnement RGI déclaré,
notes/exclusions déclarées et référence exacte de la ligne candidate. Les
éventuelles autres références restent déclarées, non juridiquement vérifiées.
Ce statut **n'est pas une validation de classement douanier**. Les champs RGI/
notes sont un compte rendu humain, pas un moteur de règles ou une preuve de
leur applicabilité. Aucun statut `publiee`/`validee` n'est accepté.

Les pistes reprennent le moteur littéral existant en mots entiers normalisés,
pas synonymes, traduction ou IA. Matière/fonction/usage/caractéristiques sont
recherchés comme termes de libellés, pas déduits comme attributs certifiés.
Les informations manquantes sont celles non renseignées dans la fiche produit,
pas déduites de l'absence d'un mot dans le tarif. Zéro piste conduit à une
abstention documentaire, pas une conclusion d'absence de droit. Une pagination
limitée à20 est explicite ; aucune exhaustivité nationale n'est déduite.

## Persistance et concurrence

SQLite local `data/customs-quarantine/dossiers_metier.sqlite3`, non versionné.
État et version contenant acteur serveur, horodatage, produit, décision, résultat
et SHA-256 sont écrits dans une même transaction `BEGIN IMMEDIATE`. Révision
périmée/ID déjà utilisé : 409, sans version supplémentaire. Tests avec deux
instances et deux processus réels : une seule révision concurrente acceptée.
100 versions maximum, 512KiB par état ; ce n'est pas un quota total du stockage.
Historique résumé sans répéter les listes complètes de candidats à chaque version.
Vérification de concordance état/trace/empreinte, pas signature ou WORM ; un
propriétaire du fichier peut falsifier les deux. Aucun journal de production
ancien n'est migré. Pas nouvelle stratégie globale de sauvegarde du SQLite.

**Audit externe non atomique avec le commit SQLite.** Le journal de versions
interne est atomique ; le journal de revue existant est ensuite obligatoire pour
libérer la réponse. S'il échoue, HTTP503 peut survenir **après commit**. Le client
connaît son dossier_id : après rétablissement de l'audit, il doit faire GET pour
réconcilier, pas rejouer aveuglément POST/PATCH. Ce cas est testé. L'audit externe
seul n'est donc pas une preuve exhaustive des changements. Pas exactly-once ou
preuve de livraison réseau. Les diagnostics et données produit persistent dans
la base locale ; permissions/archivage/chiffrement restent à qualifier.

## Réception et portée

29 nouveaux scénarios : cycle complet persistant, questions/abstention,
complétion, entrées non autorisées, transitions et propositions incomplètes,
révision périmée, accès/allowlist/mode ouvert, séparation des lots, lot Code
refusé, altérations source/base, audit externe indisponible, concurrence de deux
instances et de deux processus. Fixtures NON OFFICIELLES, vrais HTTP/SQLite.
Pas nouvelle IA, validation juridique ou corpus réel. Interface graphique de
création/révision **non ajoutée** : intégration livrée par API de revue existante.

Aperçu maintenu sur backend76 : code77–94 poussé/testé, non chargé avant
redémarrage maîtrisé pour préserver les traitements. Aucun compte/lot officiel
ou publication créé automatiquement. [Rapport](RAPPORT_LOT94.md).
