# Export JSON groupé indépendant du fichier horodaté — lot 91

Route : `GET /api/batches/export/json?ids=...`.

## Changement ciblé

La route écrivait un fichier dont le répertoire dépendait des IDs et le nom
de la seconde courante, puis le rouvrait via `FileResponse`. Deux requêtes du
même lot dans la même seconde pouvaient remplacer le contenu servi à la première.

Après les lectures et contrôles existants, la branche JSON prépare maintenant
une **réponse en mémoire** avant l'audit. Pas accès au répertoire d'export, pas
création/réouverture de fichier JSON. Anciens fichiers laissés inchangés.

Contrat HTTP explicite : **`application/json`** au lieu d'octet-stream,
**nom fixe `lot.json`** au lieu du nom horodaté, `Cache-Control: no-store`,
sans ETag/Last-Modified de fichier. JSON compact ; tableau des résultats bruts
conservé, sans introduction de `DocumentResult` ou suppression de clés inconnues.
La sérialisation standard de `JSONResponse` n'est pas une validation métier.

Ordre, doublons, retrait des espaces/tokens vides, maximum200 entrées conservés.
Les doublons comptent dans cette limite et dans l'audit. Contrôle par job avant
sa lecture ; une entrée ultérieure interdite/absente/indisponible empêche toute
réponse groupée et tout audit de succès, mais les entrées autorisées précédentes
peuvent déjà avoir été lues. Pas garantie de garde globale avant toutes lectures.
Audit `batch_exported`, format et nombre de documents, conservé après préparation ;
pas nouvel acteur attribué ni preuve de livraison.

**Séquence de snapshots par document, pas snapshot atomique du lot.** Un test
modifie deux documents après lecture du premier : le tableau contient alors
la première version du premier et la nouvelle version du second, explicitement
accepté comme limite plutôt que masqué par le terme snapshot.

## Recette

26 nouveaux cas : quatre ordres/doublons, un nettoyage de tokens, des fichiers
anciens intacts, une primitive chemin piégée, des en-têtes conditionnels,
quatre changements entre téléchargements, trois refus d'accès, un job absent,
un résultat absent, quatre listes invalides/trop longues, une limite200 répétée,
un résultat brut non normalisé, un TXT fichier, une séquence de lectures
non atomiques, un entrelacement HTTP de deux lots et d'un PATCH.

Entrelacement : horodatage de nom fixé pour reproduire deux générations dans
la même seconde ; premier lot suspendu à l'audit, PATCH, second lot terminé,
puis premier libéré. Assertion des corps avant en-têtes : ancien handler sert
la nouvelle valeur au premier ; nouveau code conserve deux réponses indépendantes.
Stores/jobs/audits temporaires réels, véritables requêtes TestClient/barrières
maîtrisées, pas navigateur, fournisseur OCR ou mesure de charge.

Contre-épreuve : seul ancien handler réinjecté en mémoire, fixtures/autres
handlers conservés, checkout/aperçu non remplacés. Échec de contenu de la course
vérifié dans le JUnit, pas seulement nouveau nom/media/no-store.
[Rapport](RAPPORT_LOT91.md), [recette](RECETTE_LOT91.json).

## Limites

JSON groupé seulement : TXT/CSV/XLSX/archives groupés conservent leurs chemins
et risques partagés ; formats complets/sélectionnés non JSON inchangés. JSON
unitaire/sélectionné relèvent des lots89/90. Pas purge/réparation des anciens
fichiers ni autres consommateurs. no-store ne purge pas les caches clients,
proxies ou offline déjà présents.

Pas transaction de lecture multi-documents, dernier état garanti en fin transfert,
révision globale ou signature. Résultats bruts : pas validation universelle de
leur structure/qualité/fiscalité. Sérialisation JSON standard plus stricte pour
les nombres non finis que l'ancien json.dumps permissif ; pas nouvelle gestion
neutre de toutes les erreurs. Modèle/tableau/réponse en mémoire, limite200 n'est
pas une borne d'octets/CPU/mémoire ; pas streaming ou qualification de charge.

Pas redaction des résultats complets, changement de droits ou acteur authentifié
de l'audit. Révision processus/ABA et autres écrivains inchangés. Aperçu backend76
maintenu : code77–91 poussé/testé mais non chargé avant redémarrage maîtrisé
pour préserver les traitements. RBAC non activé implicitement ; mission
réglementaire toujours partielle.
