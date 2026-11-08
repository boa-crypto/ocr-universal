# Rapport 99 — Repères candidats et lecture du contexte PDF

## Résultat

La navigation des deux copies reçues est enrichie : recherche d'en-têtes
candidats, filtrage du numéro littéral, pagination et ouverture directe de leur
contexte dans le texte natif déjà indexé. Les résultats de recherche textuelle
proposent également **Lire la page**.

**591 occurrences typographiques candidates** observées, pas 591 articles
qualifiés : 140 dans la copie de la loi 17-04 et 451 dans la compilation du Code
portant la mention Juin 2017. Ces PDF restent non authentifiés.

Le numéro 137 est repéré page physique 35 de la copie 17-04 et page physique 89
de la compilation. L'API a relu ces deux passages sur des copies isolées des
vrais fichiers, avec les mêmes SHA de texte. **Aucune équivalence juridique
entre ces numéros n'est déduite.**

## Fonctions livrées

- Détection française bornée de formes en début de ligne `Art.`, `Art`, `Article`
  suivies d'un numéro, en conservant en-tête et numéro littéraux.
- Positions Unicode exactes, identifiant déterministe, SHA PDF/page/index,
  contexte borné et avertissement de non-validation.
- Deux GET protégés : `pdf-article-markers` et `pdf-index-page`.
- Lecture de la copie indexée, sans nouvelle extraction ou OCR susceptible de
  modifier le texte sur lequel le repère a été calculé.
- Contrôles nominatifs, archive allowlistée et revalidée, audit obligatoire,
  no-store, erreurs 404/409/422 selon le cas.
- Interface texte/repères : contexte affiché comme texte, jamais HTML.
- Refus d'un index changé pendant la pagination ; refus d'un contexte dont les
  empreintes diffèrent du résultat choisi ; invalidation des réponses tardives
  et effacement sur révocation d'accès.

## Fichiers principaux

`src/unocr/customs_reference/pdf_markers.py` implémente détection et lecture ;
`pdf_index.py` mutualise le chargement validé. `routes/customs_review.py`
porte les routes. `web/customs-legal-pages.js` et `web/sw.js` portent l'interface
et la version de cache 99. Tests Python, JSDOM, pont HTTP et workflow dédiés
actualisés. Contrat et limites dans
[REPERES_ARTICLES_CANDIDATS.md](REPERES_ARTICLES_CANDIDATS.md).

## Vérification

| Contrôle | Résultat |
|---|---:|
| Sélection ciblée | 72 réussis, 0 échec |
| Recette documentaire large | 2304 réussis, 0 échec, 0 ignoré |
| Scénarios JSDOM de cette zone | 8 réussis |
| API sur copies des vrais PDF | 1 cas réussi, deux repères 137 relus ; anonyme 401 |
| Suite complète locale | 4459 réussis, 2 échecs historiques, 1 ignoré |
| Ruff ciblé, syntaxe JS, whitespace patch | Réussis |
| CI GitHub du code livré | Success, run 42479137420 |
| Empreintes historiques | 26/27 ; écart strictement identique au 98 |

Ces sélections se recouvrent : leurs nombres ne s'additionnent pas.
La suite complète a pris 374, 14 secondes. Les deux échecs sont ceux déjà présents
au 98 : `test_indra_engine_availability` et
`test_selection_prefers_native_when_present`. Ils ne sont pas masqués. Un
avertissement Starlette/httpx connu persiste. L'écart du référentiel historique
n'a pas été restauré ou réécrit.

Révision du code testée et poussée :
`0eabb8b123c8726398c6e00cd55357339bd2f58f`, branche
`arena/2cd4c91a-ocr-universal`.
CI : https://github.com/boa-crypto/ocr-universal/actions/runs/42479137420

Preuves synthétiques : [RECETTE_LOT99.json](RECETTE_LOT99.json) et
[REPERES_LOIS_RECUES.json](REPERES_LOIS_RECUES.json).
Journaux/XML locaux : `/home/user/recettes-unocr/lot99/`.

## Préservation et limites

Les deux PDF, le manifeste et l'index épinglé n'ont pas changé. L'index conserve
221 pages, 486098 caractères et le SHA
`e055e6dafccb2eb4f56e2b75917be81f1773c9658a8758f284572d3de40a85c5`.
Le paquet `documents_juridiques_1979_2017_indexes.zip` livré au 98 reste valable.
Les repères sont calculés à la lecture, sans ajout d'article ou de relation au
référentiel. Registre et habilitations réelles inchangés.

La reconnaissance n'est pas exhaustive : seulement certains en-têtes français,
pas de reconstruction des colonnes ni correction de caractères dégradés. Une
citation/remplacement peut être un candidat sans être un article autonome.
L'interface ouvre un fragment borné ; l'API permet la pagination du texte, mais
la vue n'offre pas encore le parcours de tous les fragments d'une longue page.
JSDOM et HTTP isolé ne remplacent pas une recette de navigateurs réels.

## Exploitation et intervention restante

Le backend partagé 76 sur 8000 n'a pas été redémarré. Ces nouvelles routes ne sont
**pas annoncées comme déployées**. Leur utilisation réelle requiert une mise à
jour contrôlée du backend et une habilitation nominative appropriée, sans
ouverture automatique du registre actuellement fermé.

La qualification juridique des sources et des articles requiert toujours une
revue compétente. La compilation 2017 ne constitue pas l'original 1979 ni une
consolidation du droit à aujourd'hui. **0 article juridiquement validé, 0 relation
créée, publication désactivée.** Le module documentaire est livré et testé ; la
mission globale demeure partielle et non recevable comme moteur fiscal de
production.
