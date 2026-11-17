# Catalogue des pages indexées — 101

Le mode **Catalogue des pages physiques** permet de parcourir l'inventaire des
pages sans rechercher de texte ou d'en-tête d'article. Le filtre d'identifiant
exact du document reste facultatif. Un champ supplémentaire permet de demander
une page physique exacte. Sans document, cette page peut appartenir à plusieurs
PDF ; chaque résultat conserve son identifiant et son SHA PDF.

## Contrat API

`GET /api/v1/customs-review/lots/{lot_id}/pdf-index-catalog`

- `document_id` : filtre exact facultatif, 1–256 points de code, non blanc et
  sans caractères de contrôle ;
- `page` : page physique exacte facultative, 1–10000 ;
- `limit` :1–100, 20 par défaut ; `offset` : 0–1000000.

Le catalogue paginé suit l'ordre de l'index : document, puis page physique.
Chaque entrée contient `document_id`, `pdf_sha256`, `page_pdf`,
`nombre_pages_pdf`, `sha256_texte_utf8`, `total_caracteres` et
`texte_indexe_present`. Il ne contient pas le texte complet de la page.
`type_recherche=catalogue_pages_pdf`, requête vide, filtres exacts restitués,
SHA index/manifeste et statuts non validés explicites. Les pages sans texte
indexé sont incluses. Un filtre exact sans correspondance retourne 200 avec une
liste vide, sans supposer que ce document n'existe pas ailleurs.

Les mêmes contrôles que pour la lecture indexée s'appliquent : rôle nominatif,
réviseur inscrit, lot allowlisté de type Code, archive et index revalidés, audit
obligatoire, no-store. Authentification absente 401, rôle/réviseur refusé 403,
lot inconnu 404, index absent/incohérent 409, paramètres invalides ou autre type
de lot 422 ; audit indisponible 503 sans résultat. Aucun chemin interne n'est
fourni. Le catalogue n'indexe pas à la volée et ne modifie pas le registre.

## Interface et garanties

Le mode désactive le terme textuel, sans lancer de requête automatique. **Afficher
le catalogue** consulte au plus 20 pages à la fois. Le champ de page n'est actif
que dans ce mode. Chaque entrée propose **Lire la page**, y compris si le texte
indexé est vide. La lecture emploie les SHA du catalogue et contrôle aussi les
longueurs et nombres de pages annoncés. Les fragments 100 restent disponibles.

La pagination vérifie son curseur, le nombre attendu de résultats, les filtres,
les bornes et les empreintes ; un changement d'index impose une nouvelle
consultation. Modifier le champ de page invalide aussi les réponses tardives.
Les chaînes sont affichées comme texte, jamais comme HTML. Aucune persistance
de navigation, changement de droit, création d'article ou publication.

## Limites

Ce catalogue est celui d'un index natif épinglé, pas de l'ensemble des documents
juridiques existants. Une page sans texte indexé peut contenir du texte sous
forme d'image ou une extraction défaillante : elle n'est pas réputée vide.
Pas OCR, correction des colonnes, authentification, interprétation d'article
ou preuve d'absence de droit. Le numéro est physique, pas la pagination imprimée.

Index toujours borné à 1000 pages et 64 documents selon le contrat existant. Le
serveur partagé antérieur n'est pas redémarré par cette livraison ; l'utilisation
requiert le backend actualisé avec cette route et une identité déjà habilitée.
