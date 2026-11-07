# API de revue administrative — lots 6 à 15

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

**Sauvegarde (lot 7) :** le dossier `customs-quarantine` est désormais couvert
avec option **CLI explicite**, destination dédiée et refus de fusion en reprise.
Les routes HTTP legacy ne peuvent pas activer cette inclusion. Voir le
[guide de sauvegarde/reprise](SAUVEGARDE_QUARANTAINE.md). La qualification reste
technique, pas une validation réglementaire des fichiers.

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
| `/api/v1/customs-review/lots/{lot_id}/history?article=NUMERO` | Historique documentaire du numéro exact et relations déclarées, pour un lot Code seulement |
| `/api/v1/customs-review/lots/{lot_id}/tariff/{code10}` | Fiche du code exact, parents et mesures déclarés du lot tarifaire |
| `/api/v1/customs-review/lots/{lot_id}/coverage` | Diagnostic descriptif du lot reçu, sans score de complétude réglementaire |
| `/api/v1/customs-review/lots/{lot_id}/tree` | Enfants tarifaires directs d’un parent exact, sans reconstruction normative |
| `/api/v1/customs-review/lots/{lot_id}/article?article_id=ID` | Lecture fragmentée d’une transcription de version exacte, sans choix d’applicabilité |
| `/api/v1/customs-review/diff?avant=ID&apres=ID` | Contrôle et comparaison de deux lots de même type |

Recherche : `q` (256 caractères maximum), `limit` (1–100), `offset` (0–1000000).
Pour le Code seulement : `article`, `source` (256 caractères maximum) et `nature`
(`originale`, `modificative`, `consolidee_provisoire`). Au moins une requête ou un
filtre Code explicite. [Sémantique, limites et champs recherchés](RECHERCHE_LOCALE.md).
[Historique (lot 9)](HISTORIQUE_DOCUMENTAIRE.md) : article exact requis ; versions
et relations paginées indépendamment, sans choix de droit applicable.
[Fiche tarifaire (lot 10)](FICHE_TARIFAIRE.md) : code exact dix chiffres ASCII ;
mesures paginées séparées des taux inconnus de ligne. Une ligne absente est
annoncée explicitement avec statut 200, sans conclure à une absence nationale.
[Couverture (lot 11)](COUVERTURE_DOCUMENTAIRE.md) : compteurs du seul lot reçu,
champs non renseignés et limites ; aucun dénominateur national ou seuil de publication.
[Navigation (lot 12)](NAVIGATION_TARIFAIRE.md) : `level`, parent exact, `limit` et
`offset` ; sections → chapitres → positions → SH6 → codes10 déclarés.
[Lecture d’article (lot 13)](LECTURE_ARTICLE.md) : ID exact, champ textuel explicite,
plage de 1–16000 points de code ; aucune substitution de langue ou version applicable.
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
503 pour registre absent/invalide ou audit obligatoire indisponible. Les contrôles du middleware peuvent précéder
ces statuts. Les routes n’exposent ni PDF brut ni fichier de configuration.

Aucun endpoint POST/PUT/PATCH/DELETE de revue. Pas de route `validate`, d’import
HTTP, d’inscription de lot, de publication ou de calcul. Les API publiques
`customs-code/articles`, `tariff/codes` et la classification restent distinctes,
non livrées comme référentiel officiel par cette étape. Le [lot 8](INTERFACE_REVUE.md)
ajoute une interface dans la coque UniOCR, sans UI séparée ni droits supplémentaires.

## Audit et limites

Les événements `revue_douaniere` et `revue_douaniere_acces_refuse` réutilisent
l’audit JSONL existant : acteur, opération, IDs de lots et statut. Ils n’enregistrent
ni jeton, ni requête de recherche, ni texte d’article. Depuis le [lot 15](AUDIT_REVUE.md), les succès de ce routeur exigent un append
et une synchronisation locale réussis avant remise de la réponse ; sinon 503 sans
résultat. Les événements de succès incluent les manifestes épinglés. Les refus et
le middleware restent best-effort ; aucun WORM ou accusé de livraison garanti.
Les journaux HTTP du serveur/proxy peuvent contenir les paramètres de l’URL :
leur configuration et leur rétention doivent être adaptées au déploiement.

Les lectures relancent les contrôles complets ; pas de cache ni de benchmark sur
un corpus national réel. Les plafonds des lecteurs et de la recherche s’appliquent.
Cette API ne remplace ni le workflow humain habilité et tracé, ni la gouvernance
des versions, ni la revue réglementaire qui devront précéder toute publication.


## Pages PDF reçues (lot 21)

`GET /api/v1/customs-review/lots/{lot_id}/pdf?document_id=ID&page=1&limit=4000&offset=0`
Code seulement ; texte natif en fragment, aucun binaire ou chemin client. Succès
soumis aux mêmes épingles et audit obligatoire, opération `lecture_pdf`.
[Contrat, refus et limites](LECTURE_PDF.md). Pas d’OCR ou validation juridique.

### Comparaison littérale de versions (lot 25)

`GET /lots/{lot_id}/article-diff?avant_id=…&apres_id=…&field=texte_integral&limit=4000&offset_avant=0&offset_apres=0`
compare deux IDs exacts d’un même lot Code, sans succession juridique déduite.
Même autorisation/épingle/audit/no-store ; tarif et paramètres invalides 422.
Voir [COMPARAISON_ARTICLES.md](COMPARAISON_ARTICLES.md) pour le contrat des blocs,
les absences, la pagination indépendante et les limites.

### Hiérarchie déclarée du Code (lot 26)

`GET /lots/{lot_id}/code-tree?source_id=…&path=…&limit=20&offset=0`.
Sans source et avec chemin `[]`, liste les documents. Avec source, parcourt les
couples `niveau`/`identifiant` transcrits, puis ouvre les versions exactes.
Même autorisation/épingle/audit/no-store ; tarif et sélecteurs invalides 422.
Contrat et limites : [NAVIGATION_CODE.md](NAVIGATION_CODE.md).

### Rapprochement littéral article / PDF (lot 27)

`GET /lots/{lot_id}/article-pdf-match?article_id=…&page=1&field=texte_integral&limit=4000&offset=0`.
Page obligatoire et source imposée par la référence de l’article ; recherche du
fragment dans le texte natif de cette page. Présence ≠ validation ; absence ≠ erreur.
Même autorisation/épingle/audit/no-store ; 422 paramètres/tarif, 409 PDF refusé,
503 audit indisponible. [Contrat et limites](RAPPROCHEMENT_ARTICLE_PDF.md).

### Articles entre deux lots Code (lot 28)

`GET /article-diff?avant=…&apres=…&avant_id=…&apres_id=…&field=texte_integral&limit=4000&offset_avant=0&offset_apres=0`.
Deux lots Code inscrits/épinglés, deux IDs locaux, provenance `archives.avant/apres`
(sans `archive` simple). Même autorisation/audit/no-store ; aucun appariement ou
relation juridique déduite. Route intra-lot conservée.
[Contrat et limites](COMPARAISON_ARTICLES_INTER_LOTS.md).

### Relations d’une version exacte (lot 29)

`GET /lots/{lot_id}/article-relations?article_id=…&direction=tous&relation_type=…&limit=20&offset=0`.
Un seul saut incident à l’ID exact, types/sens déclarés, sources de preuve de la page.
Type absent = tous ; même autorisation/épingle/audit/no-store. Tarif/paramètres
invalides 422 ; aucun lien juridique inféré. [Guide](RELATIONS_ARTICLE.md).

### Justification d’une relation / PDF (lot 30)

`GET /lots/{lot_id}/relation-pdf-match?relation_id=…&page=1&limit=4000&offset=0`.
Page obligatoire, fragment de justification et source imposée par la relation.
Constat littéral uniquement ; même autorisation/épingle/audit/no-store. Paramètres/
tarif 422 ; PDF refusé 409 ; audit indisponible 503.
[Guide](RAPPROCHEMENT_JUSTIFICATION_PDF.md).

### Deux fiches tarifaires séparées (lot 31)

`GET /tariff-compare?avant=…&apres=…&code10=…&before_limit=20&before_offset=0&after_limit=20&after_offset=0`.
Deux lots tarifaires inscrits/épinglés, code10 exact, mesures indépendamment paginées,
provenance double `archives.avant/apres`. Même autorisation/audit/no-store ; pas de
fusion fiscale. [Contrat et limites](FICHES_TARIFAIRES_SEPAREES.md).

### Recherche des descriptions de mesures (lot 32)

`GET /lots/{lot_id}/measure-search?q=…&code10=…&measure_type=restriction&limit=20&offset=0`.
Descriptions seulement, filtres exacts facultatifs (requête ou filtre requis).
Lot tarifaire uniquement ; mêmes droits/empreinte/rejeu/audit/no-store.
Pas de règle applicable ni calcul. [Contrat et limites](RECHERCHE_MESURES.md).

Lot 33 : la recherche Code conserve ses aperçus et ajoute des [extraits contextualisés](EXTRAITS_RECHERCHE_CODE.md) originaux avec positions Unicode, exportables et ouvrables par lecture exacte. Pas de fidélité PDF ou droit applicable déduits.

Lot 34 : [inventaire local des sources déclarées](INVENTAIRE_SOURCES.md) via `customs-sources` et `GET /lots/{lot_id}/sources`, filtres/recherche métadonnées et export partiel audité. Aucun corpus exhaustif ou document authentifié déduit.

Lot 35 : [téléchargement contrôlé du PDF archivé](COPIE_PDF_SOURCE.md) via `GET /lots/{lot_id}/pdf-source?document_id=…`, audit obligatoire et SHA navigateur, pièce jointe non validée (pas antivirus).

Lot 37 : [revue intégrée des mesures autonomes](REVUE_MESURES_AUTONOMES.md), type de registre `mesures`. Contrôle/recherche de mesures/sources/couverture et exports existants, autres opérations explicitement refusées ; aucun rapprochement fiscal.

Lot 38 : [consultation nomenclature et mesures autonomes](CONSULTATION_TARIF_MESURES.md), CLI `customs-tariff-measures`, API racine `/tariff-measures`. Paire tarif/mesures explicitement autorisée pour cette seule opération, sources/paginations séparées et export à double provenance. Aucun rattachement juridique établi.

## Complément lot 59 — pistes partielles

[GET tariff-candidates](API_PISTES_TARIFAIRES.md), distinct de la conjonction
`tariff-criteria` : pistes littérales partielles, audit obligatoire et provenance
épinglée, paramètres stricts ; pas classification, IA ou publication.
