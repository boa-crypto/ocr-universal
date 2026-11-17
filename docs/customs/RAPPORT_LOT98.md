# Rapport98 — recherche dans les deux PDF juridiques reçus

## Réalisation sur les copies réelles

Les **221 pages** des deux PDF sont désormais indexées avec conservation de
**486098 caractères** de texte natif, sans OCR ni correction silencieuse :

-35 pages pour la copie de la loi17-04 ;
-186 pages pour la compilation du Code affichant « Mise à jour Juin2017 ».

Le registre local épingle le SHA256 de l'index dérivé en plus du manifeste du lot.
Les PDF et le lot de réception ne sont pas modifiés. La recherche contrôle cette
liaison et les empreintes, puis restitue pages physiques, références et extraits
avec positions Unicode. Elle ne fabrique ni article transcrit ni droit consolidé.

Contrat : [recherche de pages](RECHERCHE_PAGES_LOIS_RECUES.md).
Reçu des PDF : [réception](RECEPTION_LOIS_1979_2017.md).

### Vérifications sur les vrais documents

| Requête | Pages correspondantes |
|---|---:|
| douanes |175 |
| déclaration |87 |
| abrogées |1 |

Ces recherches ont été vérifiées par les fonctions locales **et par l'API sur
copies isolées**, avec autorisation de recette, sans modifier les droits du
magasin réel. Les appels sans authentification sont refusés. Les extraits restent
ceux du texte natif, y compris ses défauts d'encodage et l'ordre d'extraction.

## Interface et sécurité

Zone de recherche ajoutée à la revue administrative, pour les lots Code :
requête explicite, document exact facultatif et pagination. Aucun GET ne construit
un index ni n'active une règle. Les réponses sont rendues en texte, pas en HTML.
Changements de lot/requête/compte/route invalident les réponses tardives ; refus
d'accès efface le composant. Index absent ou incohérent : refus explicite, pas de
recherche silencieusement dégradée.

Route `GET /api/v1/customs-review/lots/{lot_id}/pdf-search`. Autorisation nominative,
allowlist, contrôle intégral de l'archive et audit conservés. Nouveau champ
facultatif `index_pdf_sha256` du registre ; schéma régénéré. Les lots anciens
sans index restent utilisables pour leurs fonctions historiques.

## Fichiers principaux

- `src/unocr/customs_reference/pdf_index.py` : construction locale bornée, intégrité,
  recherche et extraits ; index externe au lot immuable.
- `review_registry.py`, `routes/customs_review.py`, schéma `RegistreRevue` : épingle
  et route autorisée.
- `web/customs-legal-pages.js`, `customs-review.js`, `index.html`, `sw.js` : module
  UI, chargement et cache98.
- `tests/test_customs_pdf_index.py`, scénarios JSDOM/HTTP, test d'ordre de scripts,
  commande npm et sélection CI.

Code **b56c302534565c80bbd53bd19cd7a87afd217f1f**, poussé sur la branche de session.
Aucun fichier de données ou journal partagé inclus dans ce commit.

## Validation

| Vérification | Résultat |
|---|---|
| Nouveaux cas Python de recherche/index | **14** |
| Sélection index/provenance/revue/UI | **70 réussis** |
| Recette documentaire | **2290 réussis**, aucun échec/ignoré |
| Nouveau module JSDOM | **6 scénarios réussis** |
| Modules dossiers/historique | **28 /212 scénarios réussis**, sélections distinctes |
| API sur copies des vrais PDF | **1 cas supplémentaire réussi**, trois recherches et refus sans authentification |
| Suite complète | **4445 réussis,2 échecs Indra préexistants,1 ignoré**,382,52s |
| CI ciblée | [42478038172 réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42478038172), SHA exact |
| Ruff source/tests/recette, syntaxe JS, diff | Réussis |
| Empreintes historiques | **26/27**, même écart du référentiel partagé préservé |

Ne pas additionner les sélections recouvrantes. Les deux échecs complets restent
`tests/test_indra_ocr.py::test_indra_engine_availability` et
`tests/test_ocr.py::test_selection_prefers_native_when_present` ; reconnaissance
Indra ignorée, aucun échec masqué.

Tests couvrant normalisation FR/AR, tous les termes sur une même page, filtres,
pagination, paramètres invalides, absence d'index, source/index altérés même avec
recalcul d'un hash interne, liaison à un autre manifeste, empreinte/continuité de
pages, refus d'écraser un fichier, construction depuis un vrai PDF synthétique,
autorisations et UI sur HTTP. Une première vérification a révélé un mauvais nom
de champ passé au helper d'extraits : corrigé, puis recherches réelles avec
extraits et recettes finales réexécutées.

Preuves : [RECETTE_LOT98.json](RECETTE_LOT98.json),
[INDEX_LOIS_RECUES.json](INDEX_LOIS_RECUES.json), artefacts bruts
`/home/user/recettes-unocr/lot98/`. L'écart SHA est celui déjà connu de
`data/referentiels.json` ; aucune restauration destinée à rendre les tests verts.

## Livraison locale et limites

Paquet actualisé :
`/home/user/livraisons/documents_juridiques_1979_2017_indexes.zip`.
Il contient les PDF, métadonnées, extractions, lot, index, registre fermé et
schémas. Les fichiers documentaires sont **hors Git**, dans le workspace persistant ;
le paquet est à conserver pour une autre installation. Ne pas écraser un registre
existant avec celui du paquet : les épingles et habilitations doivent être contrôlées.

**Recherche documentaire, pas validation juridique.** La compilation ne devient
pas l'édition originale de1979 ; la copie17-04 n'est pas authentifiée par son
entête. Pas de traduction, correction typographique, découpage d'articles,
interprétation d'abrogations, consolidation à date, IA ou calcul fiscal applicable.
Un résultat compte une page, pas une occurrence ni un article ; une absence de
résultat ne prouve pas une absence de droit. Bornes et worker séparé ne sont pas
un antivirus, un bac à sable OS complet ou une qualification en charge.

L'API du serveur partagé reste backend76 : **aucun redémarrage, déploiement ou
nouvelle habilitation réelle**. Les fichiers statiques sur disque ont changé,
mais l'usage de l'API98 en interface nécessite un backend actualisé et un compte
habilité. Ne pas assimiler les recettes isolées à un service déjà activé dans cet
aperçu. La mission globale reste partielle et non recevable pour production fiscale.
