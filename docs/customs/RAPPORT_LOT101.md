# Rapport 101 — Catalogue physique des pages indexées

## Résultat

La revue documentaire propose désormais **Catalogue des pages physiques**, sans
mot-clé ni numéro d'article. Il permet de parcourir toutes les pages de l'index,
ou de filtrer un document exact et/ou une page physique exacte, puis **Lire la
page**. Les pages sans texte indexé ne sont pas masquées.

La lecture et le parcours des fragments précédents restent disponibles, avec
les empreintes du résultat du catalogue. Le catalogue ne contient pas le texte
complet : il donne les identifiants, nombres de pages, longueurs et SHA utiles
pour la lecture contrôlée. Un même numéro physique peut apparaître dans deux
PDF ; ils ne sont pas confondus.

## Réalisation

- `src/unocr/customs_reference/pdf_markers.py` : `cataloguer_pages`, inventaire
  paginé incluant les pages sans texte, filtres exacts, provenance et statuts.
- `src/unocr/routes/customs_review.py` : GET protégé
  `/api/v1/customs-review/lots/{lot_id}/pdf-index-catalog` réutilisant le
  chargement validé, le contrôle nominatif, l'allowlist et l'audit obligatoire.
- `web/customs-legal-pages.js` : troisième mode, champ de page physique,
  validation du catalogue et ouverture via la lecture indexée existante.
- `web/sw.js` : cache `unocr-shell-v101-legal-catalog`.
- `tests/test_customs_pdf_catalog.py` : 18 nouveaux cas Python ; filtres,
  pagination, pages sans texte, refus des paramètres, sources modifiées,
  restrictions nominatives, no-store et audit indisponible.
- Tests JSDOM, pont HTTP, provenance de cache et workflow CI actualisés.

Contrat détaillé : [CATALOGUE_PAGES_INDEXEES.md](CATALOGUE_PAGES_INDEXEES.md).

## Vérification avec les fichiers reçus

Sur une API isolée avec copies des vraies sources et du registre, le catalogue
renvoie exactement les métadonnées des **221 pages** de l'index épinglé, sans
oubli ni doublon, en **12 requêtes paginées**. Les filtres des dernières pages
physiques 35 et 186 ont été vérifiés sur leurs documents respectifs.

Les **256 fragments** de lecture reconstituent encore exactement les 221 pages,
soit 486098 points de code Unicode, avec contrôle des SHA du texte, du PDF, de
l'index et du manifeste. Ces fichiers n'ont aucune page sans texte indexé ; le
cas d'une page sans texte est couvert par une fixture synthétique, y compris
l'ouverture de son fragment vide et le SHA UTF-8 correspondant.

Il s'agit d'une conformité à l'index, **pas d'une validation du contenu natif
contre le rendu visuel du PDF**. Pas extraction fraîche, OCR ou authentification.
Les droits réels n'ont pas été ouverts pour cette recette sur compte de test.
Preuve : [CATALOGUE_LOIS_RECUES.json](CATALOGUE_LOIS_RECUES.json).

## Tests et intégrité

| Contrôle | Résultat |
|---|---|
| Sélection ciblée | 95 réussis, 0 échec |
| Recette documentaire | 2327 réussis, 0 échec, 0 ignoré |
| Scénarios JSDOM de cette zone | 23 réussis |
| API isolée sur les copies réelles | 1 cas réussi, 221 métadonnées et pages contrôlées |
| Suite complète locale | 4482 réussis, 2 échecs historiques, 1 ignoré |
| Ruff ciblé, syntaxe JS, whitespace patch | Réussis |
| CI de la révision du code | Success, run 42481017950 |
| Empreintes historiques | 26/27, strictement identiques au 100 |

Les sélections se recouvrent, leurs nombres ne s'additionnent pas. Les deux
échecs historiques sont `test_indra_engine_availability` et
`test_selection_prefers_native_when_present`. L'avertissement connu
Starlette/httpx persiste. Aucun écart historique n'est corrigé en écrasant les
données préexistantes, ni présenté comme un contrôle intégralement conforme.

Code testé et poussé : `7f7b7827c3c52763b48a84a1af521a71eac4b653`, branche
`arena/2cd4c91a-ocr-universal`.
CI : https://github.com/boa-crypto/ocr-universal/actions/runs/42481017950
Détails et empreintes des preuves : [RECETTE_LOT101.json](RECETTE_LOT101.json).
Journaux/XML et script de recette réelle : `/home/user/recettes-unocr/lot101/`.

## Limites et exploitation

Les deux PDF, le manifeste, le registre et l'index sont inchangés. SHA index :
`e055e6dafccb2eb4f56e2b75917be81f1773c9658a8758f284572d3de40a85c5`.
Le paquet PDF/index précédent reste utilisable. Aucun article juridiquement
qualifié ou relation juridique n'est créé ; aucune publication.

L'inventaire ne couvre que cet index, pas toutes les sources juridiques. Une
page sans texte indexé peut contenir une image ou une extraction défaillante :
ce n'est pas une preuve de page PDF vide. La pagination est physique, pas celle
imprimée sur la page. Défauts de caractères et ordre des colonnes conservés.
JSDOM et HTTP isolé ne constituent pas une recette de navigateurs réels.

Le backend partagé 76 sur 8000 n'a pas été redémarré ; cette route n'est pas
annoncée comme déployée. Une actualisation contrôlée du backend et une identité
nominativement habilitée sont nécessaires à l'utilisation réelle. Aucun compte
ou droit réel modifié. La qualification juridique des sources reste à mener
par une revue compétente. La compilation 2017 n'est ni l'original 1979 ni une
consolidation à aujourd'hui. La mission globale reste partielle et non
recevable comme moteur fiscal de production.
