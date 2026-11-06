# API de revue administrative — lot 6

2026-11-06. **Lecture seule de lots en quarantaine ; ni validation ni publication.**

## Frontière d’accès

L’API est incluse dans l’application FastAPI UniOCR existante, sous
`/api/v1/customs-review`. Elle réutilise le middleware d’authentification et le
journal d’audit existants, puis ajoute des exigences **plus strictes** que les
routes legacy :

1. RBAC actif et compte identifié par son jeton personnel ;
2. rôle `administrateur` explicitement présent ;
3. compte non issu du passe-partout d’environnement ;
4. nom exact du compte inscrit dans `reviseurs` du registre de revue serveur.

Le mode ouvert historique ne donne aucun accès. `UNIOCR_TOKEN` seul n’est pas
une habilitation de revue ; les en-têtes client de rôle/nom ne sont pas utilisés.
Une habilitation de revue permet **seulement de lire**, pas de valider un texte.
L’identité reste celle d’un compte local à jeton porteur : ce n’est pas une
signature juridique, une preuve de présence humaine ou un SSO.

La sécurité de l’administration RBAC existante et du système de fichiers reste
un préalable de déploiement. La liste locale de réviseurs ajoute une barrière à
l’attribution d’un simple rôle, mais ne protège pas d’un administrateur capable
de réécrire le registre, de compromettre les comptes autorisés ou de modifier
le programme. Aucun durcissement global des routes legacy n’est prétendu ici.

## Configuration hors HTTP

Aucun compte, registre ou lot n’est créé automatiquement. Le registre est lu à
chaque opération depuis :

`<data_dir effectif>/customs-quarantine/registre.json`

Le répertoire de données effectif respecte `UNOCR_DATA_DIR`/la configuration
existante. Seul un opérateur du serveur prépare les lots et cette configuration.
Les droits du système de fichiers doivent en réserver l’écriture à l’administration.
Schéma : [RegistreRevue](schemas/RegistreRevue.schema.json).

Objet de configuration :

- `schema_version` : `"1"` ;
- `reviseurs` : 0 à 64 noms exacts de comptes RBAC existants (non vides, 128
  caractères maximum, sans doublon). Une liste vide n’autorise personne ;
- `lots` : 0 à 64 entrées, chacune avec :
  - `id` : identifiant HTTP ;
  - `type_lot` : `tarif` ou `code` ;
  - `dossier` : nom d’un sous-dossier direct de `customs-quarantine` ;
  - `manifest_sha256` : SHA256 exact du manifeste du lot, 64 hexadécimaux minuscules.

IDs et dossiers : 1 à 64 caractères ASCII, premier caractère alphanumérique,
puis lettres/chiffres/tiret/underscore. Pas de chemins, points, lecteur Windows,
traversée, dossier répété ou ID répété. Registre limité à 1 Mio ; clés JSON
dupliquées et champs inconnus refusés. Les symlinks directs du registre/de son
répertoire et ceux des lots sont refusés par les lecteurs.

**Sauvegarde :** le dossier `customs-quarantine` ne figure pas actuellement dans
les répertoires inclus par `backup.py`. Prévoir une copie protégée indépendante
du registre et des lots ; l’intégration sauvegarde/reprise de ce nouveau dossier
reste à qualifier avant un déploiement documentaire réel. Les tests de reprise
RBAC ne constituent pas une preuve de sauvegarde de ces lots.

Les lots préparés doivent être copiés avec **tous** leurs fichiers, sans modifier
leurs originaux. Calculer l’empreinte attendue sur le manifeste réellement revu,
par exemple avec `sha256sum /chemin/lot/manifest.json`. Une modification ultérieure
du manifeste entraîne un refus tant que le registre serveur n’a pas été mis à
jour explicitement après revue. Ne jamais recopier une empreinte proposée par
un appelant HTTP comme preuve d’authenticité.

L’empreinte est contrôlée avant le traitement **et** comparée à celle effectivement
utilisée par le lecteur/rejeu. Cette épingle ancre un instantané local ; elle ne
certifie pas l’origine officielle, la correspondance transcription/PDF, un
horodatage ou une immutabilité WORM. Pas de garantie contre un écrivain hostile
ayant les mêmes droits système ; ce n’est pas un verrouillage transactionnel du corpus.

## Routes GET

| Route | Fonction |
|---|---|
| `/api/v1/customs-review/lots` | Liste des IDs/types/empreintes attendues autorisés dans le registre ; pas de validation des contenus par cette liste |
| `/api/v1/customs-review/lots/{lot_id}/check` | Contrôle/rejeu complet du lot épinglé |
| `/api/v1/customs-review/lots/{lot_id}/search` | Recherche du lot 5 dans le lot épinglé |
| `/api/v1/customs-review/diff?avant=ID&apres=ID` | Contrôle et comparaison de deux lots de même type |

Recherche : `q` (256 caractères maximum), `limit` (1–100), `offset` (0–1000000).
Pour le Code seulement : `article`, `source` (256 caractères maximum) et `nature`
(`originale`, `modificative`, `consolidee_provisoire`). Au moins une requête ou un
filtre Code explicite. [Sémantique, limites et champs recherchés](RECHERCHE_LOCALE.md).
Aucun paramètre ne permet de choisir un chemin local ou une URL source.

Les réponses métier réussies sont en JSON, `Cache-Control: no-store`, avec
`lecture_seule=true`, `publication_active=false`, `validation_juridique=non_validee`,
`perimetre=revue_administrative_quarantaine` et le champ `resultat` du service partagé.
Les textes et références déclarés restent tels que reçus. Les erreurs de revue
sont génériques : pas de chemin serveur ni contenu de validation interne renvoyé.
La liste des lots indique explicitement que leur intégrité n’a pas été contrôlée
par la simple consultation du registre.

Statuts : 401 pour jeton inconnu/absent quand le middleware RBAC le demande ;
403 pour absence d’habilitation nominative ; 404 pour ID non inscrit ; 409 pour
lot incohérent ou empreinte différente ; 422 pour paramètres/types incompatibles ;
503 pour registre absent/invalide. Les contrôles du middleware peuvent précéder
ces statuts. Les routes n’exposent ni PDF brut ni fichier de configuration.

Aucun endpoint POST/PUT/PATCH/DELETE de revue. Pas de route `validate`, d’import
HTTP, d’inscription de lot, de publication ou de calcul. Les API publiques
`customs-code/articles`, `tariff/codes` et la classification restent distinctes,
non livrées comme référentiel officiel par cette étape. Aucune UI séparée ajoutée.

## Audit et limites

Les événements `revue_douaniere` et `revue_douaniere_acces_refuse` réutilisent
l’audit JSONL existant : acteur, opération, IDs de lots et statut. Ils n’enregistrent
ni jeton, ni requête de recherche, ni texte d’article. Ce journal reste **best-effort**,
non WORM ; un échec d’audit n’est pas une validation juridique implicite.
Les journaux HTTP du serveur/proxy peuvent contenir les paramètres de l’URL :
leur configuration et leur rétention doivent être adaptées au déploiement.

Les lectures relancent les contrôles complets ; pas de cache ni de benchmark sur
un corpus national réel. Les plafonds des lecteurs et de la recherche s’appliquent.
Cette API ne remplace ni le workflow humain habilité et tracé, ni la gouvernance
des versions, ni la revue réglementaire qui devront précéder toute publication.
