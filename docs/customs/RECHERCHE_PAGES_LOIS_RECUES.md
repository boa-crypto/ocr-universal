# Recherche dans les pages natives des lois reçues

## Résultat sur les documents réels

Les deux copies du lot `lois_recues_1979_2017` sont indexées : **221 pages**, soit
35 pour la loi17-04 et186 pour la compilation du Code affichant Juin2017.
**486098 caractères** natifs conservés sans correction ni OCR. L'index est dérivé
des PDF archivés, relus page par page dans des processus bornés. Son SHA256 est
épinglé séparément au registre de revue et il référence le manifeste du lot.

Recherche vérifiée sur les fichiers réellement fournis :

| Termes | Pages correspondantes dans les deux copies |
|---|---:|
| `douanes` | 175 |
| `déclaration` | 87 |
| `abrogées` | 1 |

Ces nombres comptent des **pages**, pas des articles, occurrences ou règles en
vigueur. La requête utilise tous les termes normalisés, comme sous-chaînes sur
une même page ; aucune traduction, synonymie ou compréhension juridique.

## API et interface

`GET /api/v1/customs-review/lots/{lot_id}/pdf-search`

Paramètres : `q` obligatoire (256 caractères/16 termes maximum), `document_id`
exact facultatif, `limit`1–100 (20 par défaut), `offset`0–1000000. Pagination dans
l'ordre documentaire du lot puis par page physique croissante.

Les résultats contiennent document, page physique, SHA du PDF et du texte, extraits
de384 points Unicode maximum et positions dans le texte original de la page.
Un extrait est fourni pour le premier terme correspondant, pas pour toutes les
occurrences. `texte_integral` désigne le texte de la page, pas celui d'un article.

La nouvelle zone de la revue administrative est réservée aux lots `code`. Elle
lance exclusivement des GET explicites, affiche les extraits comme texte et
permet la pagination. Elle ignore les réponses tardives après changement de lot,
requête, route ou compte ;401/403 effacent le composant. Aucun index reconstruit
silencieusement sur panne ou lors d'une lecture.

Les mêmes contrôles nominatif/RBAC/allowlist, archive épinglée et audit obligatoire
s'appliquent. Index absent/non épinglé/incohérent409 ; paramètres invalides422.
Réponses no-store, pas de cache d'API dans le service worker. L'index ne confère
aucune habilitation et ne change pas les droits du registre local.

Le backend partagé ancien n'est pas redémarré. Les fichiers statiques ont évolué,
mais l'utilisation de cette API par l'interface exige un backend actualisé et un
compte habilité. Les lectures locales et la recette HTTP isolée ne constituent
pas un déploiement ni une ouverture des droits réels.

## Intégrité et bornes

- Nouveau champ facultatif `index_pdf_sha256` dans `LotRevue` ; les anciens lots
  sans ce champ restent lisibles, mais n'obtiennent pas de recherche native.
- Fichier local `data/customs-quarantine/index_pdf/{lot_id}.json`, hors du lot
  immuable. SHA exact exigé au registre ; aucune confiance dans un hash interne
  recalculé par un auteur de fichier modifié.
- Le lecteur contrôle à chaque recherche le lot entier, la liaison au manifeste,
  les documents/SHA, la continuité des pages et les SHA des textes.
- Construction explicite par `construire_index(lot, sortie)` du module
  `unocr.customs_reference.pdf_index`, sans écraser un fichier existant ni modifier
  le registre automatiquement. L'opérateur doit épingler le SHA après contrôle.
- Limites :1000 pages au total,4 millions de points Unicode,12Mio sérialisés,
  64 documents ;200000 caractères par page. Budget de construction vérifié entre
  pages :180s, plus au maximum l'appel de page courant (timeout15s).
- PDFium travaille dans un processus séparé avec limites lorsque disponibles ;
  ce n'est ni un antivirus ni un bac à sable OS complet.

Les SHA/épingles ne protègent pas contre un administrateur capable de modifier
le registre de confiance et les fichiers. La version de pypdfium2 est conservée.
L'index dérivé peut être reconstruit et son épingle doit alors être mise à jour
explicitement, sans changer les PDF sources. Pas de quota global de lots ou de
qualification charge/navigateurs réels introduit.

## Statut juridique

Textes natifs non vérifiés ; défauts d'encodage et ordre des colonnes conservés.
La compilation ne devient pas l'original1979. Pas de découpage automatique en
articles, qualification d'abrogations, consolidation à date, activation de règles
ou fiscalité applicable. Une absence de résultat n'est pas une absence de droit.

Le paquet transportable actualisé est conservé hors Git ; les sources restent
locales et privées. La sauvegarde de quarantaine avec option CLI explicite inclut
le registre, les PDF et l'index ; pas de restauration d'exploitation effectuée.

## Navigation complémentaire99

Les résultats disposent d’une lecture directe de la copie indexée. Le mode
[repères d’articles candidats](REPERES_ARTICLES_CANDIDATS.md) permet de filtrer
un numéro littéral et d’ouvrir son contexte, sans créer d’article qualifié.
La pagination refuse maintenant de poursuivre sur une nouvelle empreinte
d’index ou de manifeste : une recherche doit être relancée.
