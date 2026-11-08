# Rapport 100 — Parcours intégral des pages indexées

## Résultat livré

Les pages longues ne sont plus limitées au premier fragment dans l'interface.
Après **Lire la page**, trois commandes permettent de parcourir le texte :
**Fragment précédent**, **Fragment suivant**, **Revenir au contexte sélectionné**.
L'intervalle Unicode et la longueur totale sont affichés ; les commandes sont
désactivées à leurs bornes. La navigation reste dans la même page physique.

Chaque fragment conserve les empreintes du document, de la page, de l'index et
du manifeste du résultat choisi. Une longueur modifiée, un curseur qui ne
progresse pas, une chaîne tronquée, une unité incorrecte ou un index différent
font effacer le contexte et désactiver sa navigation. Les réponses tardives ne
restaurent pas les données après changement de recherche ou d'identité.
Le texte est affiché sans interprétation HTML ni stockage persistant navigateur.

## Vérification sur les copies réelles

Une API isolée, alimentée par des copies des PDF et de leur index existant, a
reconstitué exactement **221 pages et 486098 points de code Unicode**, au moyen
de **256 fragments HTTP** :

| Copie | Pages | Fragments | Points de code Unicode |
|---|---:|---:|---:|
| Loi17-04 | 35 | 70 | 178086 |
| Compilation portant Juin 2017 | 186 | 186 | 308012 |

La concaténation des fragments de chaque page reproduit son texte indexé et son
SHA UTF-8, sans trou ni duplication. Cela vérifie la pagination de la **copie
indexée**, pas la qualité de l'extraction PDF ou l'authenticité du document.
Aucune extraction fraîche ou OCR n'a été effectuée. Les droits réels ne sont
pas utilisés ou élargis par cette recette sur compte de test.

Preuve : [RECONSTRUCTION_PAGES_LOIS_RECUES.json](RECONSTRUCTION_PAGES_LOIS_RECUES.json).

## Réalisation et fichiers

- `web/customs-legal-pages.js` : état de lecture borné, commandes, validation
  stricte des curseurs/longueurs et maintien des empreintes d'origine.
- `web/sw.js` : cache `unocr-shell-v100-legal-fragments`.
- `tests/test_customs_pdf_markers.py` : cinq nouveaux cas, reconstitution
  Unicode, HTTP avec no-store et pont navigateur JSDOM vers la vraie API.
- `tests/ui_customs_legal_pages.js` : parcours complet avec emoji hors BMP,
  retour au contexte, métadonnées corrompues, révocation et réponses tardives.
- `tests/ui_customs_legal_pages_integration.js` : lectures suivant/précédent
  sur une longue page synthétique via HTTP, en plus des scénarios courts.
- `tests/test_ui_engine_provenance.py` : version du cache contrôlée.

Aucune modification du backend ou de son contrat au 100 ; les GET protégés du 99
sont réutilisés. Guide : [PARCOURS_FRAGMENTS_INDEXES.md](PARCOURS_FRAGMENTS_INDEXES.md).

## Qualification technique

| Contrôle | Résultat |
|---|---|
| Sélection ciblée | 77 réussis, 0 échec |
| Recette documentaire | 2309 réussis, 0 échec, 0 ignoré |
| Scénarios JSDOM de cette zone | 17 réussis |
| API isolée, pages réelles reconstituées | 1 cas réussi, 221 pages |
| Suite complète locale | 4464 réussis, 2 échecs historiques, 1 ignoré |
| Ruff ciblé et syntaxe JS | Réussis |
| CI GitHub de la révision du code | Success, run 42480093223 |
| Empreintes historiques | 26/27, strictement identiques au 99 |

Les sélections se recouvrent ; ne pas additionner leurs nombres. La suite
complète a duré 377, 27 secondes. Les deux échecs connus restent
`test_indra_engine_availability` et `test_selection_prefers_native_when_present`.
Un avertissement Starlette/httpx connu persiste. Aucun écart historique n'est
restauré ou masqué.

Code testé et poussé : `e3116732839c272a6e550fe128a6fa43a7942392`, branche
`arena/2cd4c91a-ocr-universal`.
CI : https://github.com/boa-crypto/ocr-universal/actions/runs/42480093223
Bilan structuré : [RECETTE_LOT100.json](RECETTE_LOT100.json).
Journaux/XML et recette réelle : `/home/user/recettes-unocr/lot100/`.

## Préservation et limites

PDF, manifeste, index et registre réel inchangés. SHA de l'index toujours
`e055e6dafccb2eb4f56e2b75917be81f1773c9658a8758f284572d3de40a85c5`.
Le paquet PDF/index livré au 98 reste valable. Les 591 repères candidats du 99
ne deviennent pas des articles validés : aucun ajout d'article ou de relation,
aucune correction du texte natif, aucune publication.

Un fragment est une tranche Unicode, pas une unité juridique. L'ordre des
colonnes et les caractères dégradés restent ceux de l'index. Les indices ne
sont pas des positions visuelles de glyphes. Le précédent peut recouvrir du
texte déjà lu ; suivant depuis 0 reconstitue exactement la page. La navigation
ne saute pas automatiquement vers une autre page ou un autre article.
JSDOM et HTTP ne constituent pas une recette de navigateurs réels ou de charge.

## Exploitation et suite humaine

Le serveur partagé 76 sur 8000 n'a pas été redémarré ; les fonctions livrées ne
sont pas présentées comme déjà déployées. Leur utilisation requiert un backend
actualisé avec les routes 99 et une identité habilitée. Aucun compte ou droit
réel n'a été créé ou modifié.

La qualification juridique des sources reste à effectuer par une revue
compétente. La compilation 2017 n'est ni l'original 1979 ni une consolidation à
aujourd'hui. Pour ces copies : **0 article juridiquement validé, 0 relation créée,
publication désactivée**. Le parcours documentaire est terminé et testé ; la
mission globale reste partielle et non recevable comme moteur fiscal de
production.
