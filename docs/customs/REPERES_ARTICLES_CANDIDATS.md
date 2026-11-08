# Repères d'articles candidats et lecture contextualisée

## Fonction documentaire

Les pages natives déjà indexées peuvent être parcourues par **repères typographiques
candidats**, puis ouvertes directement au décalage correspondant. Il ne s'agit
ni de créer des `ArticleVersion`, ni de valider la portée d'une disposition.

Le détecteur recherche en début de ligne des formes françaises telles que
`Article 1er`, `Art 4bis`, `Art. 137`, `Art 340 quater`, suivies d'un séparateur.
Casse de détection ignorée ; numéro et en-tête restitués **littéralement**, sans
normalisation. Espaces internes bornés. Les renvois dans la prose ne sont pas
recherchés ; des en-têtes cassés, cités, multicolonnes ou arabes peuvent manquer.
Aucune exhaustivité d'articles n'est garantie.

Une loi modificative peut citer/réécrire des dispositions avec leurs propres
repères. Une occurrence n'est donc pas nécessairement un article autonome de
cette loi. Deux textes ayant le même numéro ne sont ni fusionnés ni reliés
juridiquement par le logiciel. Aucun statut d'abrogation ou date d'effet déduit.

## Observation sur les deux PDF reçus

Sur l'index épinglé des 221 pages : **591 occurrences candidates**, réparties en
**140 pour la copie 17-04** et **451 pour la compilation affichant Juin 2017**.
Ce ne sont pas des nombres d'articles juridiquement qualifiés ou uniques.

Le filtre littéral `137` conduit notamment à :

- copie 17-04 : page physique 35 ;
- compilation du Code : page physique 89.

Ces deux occurrences ne sont pas réputées être le même article. La recette
vérifie seulement que les en-têtes sont retrouvés dans la copie de leur page,
avec les mêmes empreintes et positions Unicode.

## API

### Repères

`GET /api/v1/customs-review/lots/{lot_id}/pdf-article-markers`

Filtres facultatifs : `document_id` exact, `numero` littéral exact (32 caractères).
`limit` 1–100, `offset` 0–1000000. Ordre documentaire, page puis position. Chaque
résultat contient identifiant du repère, document/SHA PDF, page physique,
SHA du texte, en-tête, numéro, bornes Unicode et contexte borné.

`reperes_detectes_automatiquement=true`, mais
`articles_localises_automatiquement=false` et
`statut=repere_candidat_non_valide`. Les numéros `4bis` et `4 bis`, par exemple,
ne sont pas assimilés par le filtre exact.

### Page indexée

`GET /api/v1/customs-review/lots/{lot_id}/pdf-index-page`

`document_id` obligatoire ; `page` 1–10000 ; `limit` 1–16000 (4000 par défaut) ;
`offset` 0–67108864, en points de code Unicode Python. Retour : fragment de la
copie indexée, pagination textuelle, nombre de pages, empreintes du PDF/texte,
index et manifeste, version de l'extracteur. Pas nouvelle extraction PDFium
susceptible d'avoir changé après une mise à jour du moteur.

Document/page absents 404 ; paramètres invalides 422 ; index absent/non épinglé/
incohérent 409. Même autorisation nominative, allowlist, archive intégralement
revalidée, audit obligatoire et réponses no-store que la recherche 98. Pas de
construction d'index ou écriture juridique durant ces GET.

## Interface

La zone de recherche permet de choisir texte ou repères candidats. En mode
repères, numéro vide = tous les repères ; sinon égalité littérale. Les résultats
proposent **Lire la page** : pour un repère, le fragment commence au plus 200 points
Unicode avant son en-tête, afin de ne pas ouvrir systématiquement le début d'une
longue page. Le texte est affiché sans interprétation HTML, avec son origine.

La lecture refuse un changement d'empreinte de texte, PDF, index ou manifeste
par rapport au résultat sélectionné. La pagination refuse également un index
changé et demande de recommencer la recherche. Changements de lot, requête,
mode, route ou compte invalident les réponses tardives ; 401/403 effacent la vue.
Les fonctions restent entièrement en lecture seule pour les documents métier.

## Limites et exploitation

Les défauts du texte natif et de l'ordre des colonnes sont conservés. Le PDF
présentant le JO n'est pas authentifié par cette détection ; la compilation ne
devient pas l'original 1979. Pas OCR, traduction, consolidation, article validé,
règle fiscale ou jugement juridique. Les bornes, index épinglé et limites de
sécurité de 98 restent applicables.

Les PDF/index existants ne sont pas modifiés. Les repères sont calculés à la
lecture et ne changent pas le registre ou ses habilitations. L'API du serveur
partagé n'a pas été redémarrée : l'interface 99 nécessite un backend actualisé et
un compte habilité, non une ouverture automatique des droits.
