# Rapport de tests — écrans UniOCR

Date : 2026-11-04. Branche `arena/2cd4c91a-ocr-universal`, commit `929766cb`.

Ce document liste **uniquement des résultats obtenus**, avec la commande qui
les produit. Les tests ajoutés dans cette passe sont marqués 🆕.

---

## 1. Résultat d'ensemble

| Commande | Résultat | Commentaire |
|---|---|---|
| `ruff check src tests` | **All checks passed** | 0 erreur de style |
| `python -m pytest -q` | **959 passed, 23 failed, 11 skipped** | les 23 échecs sont environnementaux (voir §6) |
| `python -m pytest tests/test_ui_premium.py -q` | **37 passed** | 33 avant la passe, 4 ajoutés 🆕 |
| `python -m pytest tests/test_referentiels.py -q` | **7 passed** 🆕 | CRUD, persistance, doublons, audit |
| `python -m pytest tests/test_route_ordering.py -q` | **4 passed** 🆕 | détection des routes masquées |

Comparaison avec l'état initial de la passe : 945 → **959 tests passants**
(+14 : 7 référentiels, 4 ordre des routes, 4 intégrité UI, moins un test de
service worker réécrit pour être version-agnostique).

## 2. Tests serveur ajoutés

### `tests/test_referentiels.py` (7 tests)

| Test | Ce qu'il prouve |
|---|---|
| catalogue | 12 collections exposées avec titre, description, champs et totaux |
| création + persistance | l'entrée est écrite dans `data/referentiels.json`, relue par une requête suivante |
| code dupliqué | 409, message explicite, aucune entrée ajoutée |
| modification + suppression | PUT met à jour libellé et attributs, DELETE vide la collection, GET renvoie 404 |
| collection/entrée inconnue | 404 explicites |
| recherche | filtre sur le contenu, casse ignorée |
| audit | `referentiel_cree` présent dans `audit.log` avec le libellé |

### `tests/test_route_ordering.py` (4 tests) 🆕

| Test | Ce qu'il prouve |
|---|---|
| aucune route masquée | parcourt les **314 routes effectives** et échoue si une route littérale est capturée par une route paramétrique antérieure |
| le détecteur détecte | un témoin volontairement mal ordonné est bien signalé (sinon le test précédent ne vaudrait rien) |
| listes liquidation/facture | `GET /api/declarations/liquidation` et `GET /api/frais/facture` répondent 200 avec une liste |
| template workflow | `GET /api/workflow/workflow/template` répond 200 avec ses 8 étapes |

### `tests/_routes.py` 🆕

Helper d'énumération : FastAPI n'aplatit plus les routeurs inclus, donc
`app.routes` ne montre que les routes locales. Le helper descend dans les
`_IncludedRouter` en composant les préfixes (314 entrées vs 122 auparavant).

## 3. Tests d'intégrité de l'interface ajoutés 🆕

Dans `tests/test_ui_premium.py` :

| Test | Ce qu'il prouve |
|---|---|
| chaque écran est relié à une section réelle | les 43 routes du catalogue existent dans `routePages` → `tab-ecran`, la section et le script sont présents dans `index.html` |
| chaque écran est atteignable depuis le menu | aucune route d'écran n'existe sans entrée de menu correspondante |
| les URLs appelées existent côté serveur | chaque `/api/…` littéral de `web/ecrans.js` correspond à une route réellement déclarée (aucune URL fantôme) |
| le moteur a son stylesheet | toutes les classes produites (`.ecran`, `.ecran__titre`, `.ecran__card`, `.ecran__voile`…) sont définies dans `uniocr-ds.css` |

## 4. Vérifications de comportement dans un navigateur simulé (jsdom)

Deux harnais ont été exécutés contre le serveur réel (`http://127.0.0.1:8000`),
en chargeant `index.html` comme un navigateur (scripts actifs, `fetch` réel) :

| Harnais | Mesure | Résultat |
|---|---|---|
| parcours des 99 routes de menu | page vide ? erreur JS ? | **99 routes, 0 page vide, 0 erreur JS** |
| parcours des 52 écrans déclaratifs | en-tête, liste ou état vide, erreurs HTTP | **52/52 rendus, 0 erreur, 0 réponse non-200** |
| écrans de dossiers et d'espace de travail (passe 2) | lignes réelles, bandeau d'absence, navigation « Ouvrir » | **7/7 rendus avec données (25 lignes/page), compteurs réels : 164 bloqués, 186 tâches, 435 en attente de pièces, 30 récents** |
| redirections corrigées (passe 2) | bandeau supprimé, page réellement affichée | **6/6 sans bandeau** (`dossiers/tous`, `dossiers/nouveau`, `dossiers/clients`, `workspace/valider`, `referentiels/profiles`, `referentiels/parametres`) ; le dialogue de création `#dos-create` s'ouvre bien sur `#dossiers/nouveau` |
| action « Ouvrir » d'une liste de dossiers | navigation vers l'espace dossier | **hash → `#dossiers/tous`, section dossiers affichée, 0 erreur JS** |
| référentiels et CRUD (passe 9) | 11 écrans créés/édités/supprimés | **création 200 partout ; édition PUT 200 sur 6 écrans ; suppression 200 partout** ; pays invalide → **422** (auparavant 500) ; test unitaire ajouté |
| profils d'extraction (passe 8) | CRUD complet | **11 profils listés ; création PUT 200 ; essai à blanc 1/1 détecté ; suppression DELETE 200** |
| rapports et exports (passe 8) | graphiques et téléchargements | **7 graphiques SVG alimentés ; export CSV/JSON → 200 avec toast** ; boutons inertes supprimés |
| administration (passe 7) | création réelle + contrôles | **workflow créé depuis l'interface → POST 200, ligne affichée** ; moteurs OCR : 6 lignes ; journal : état vide explicite, aucun « Chargement… » résiduel ; sauvegardes : 8 lignes |
| sortie portuaire et livraisons (passe 6) | 5 actions d'écriture avec paramètres | **autoriser sortie, enregistrer sortie, démarrer, arrivée, confirmer → POST 200** (auparavant 422) ; preuve de livraison affichée ; enregistrements d'essai supprimés ensuite |
| écrans Documents hérités (passe 5) | données et interactions | **boîte de réception : 25 lignes, recherche 25→0, page 2 = 25 ; classification : 21 lignes, recherche → 0 ; archives : 25 lignes, page 2 = 24, « Ouvrir » → dossier ; vérification : idem ; révision : file chargée seule, « Actualiser » → GET 200** |
| actions de contrôle documentaire (passe 4) | écriture et verdict serveur | **Contrôler → POST 200, Verdict → GET 200 + panneau** |
| action de rapprochement financier (passe 4) | dialogue paramétré | **formulaire (dossier, période) → POST 200 (avant correction : 422), verdict affiché** |
| actions de l'écran Extraction OCR (passe 3) | lecture et écriture réelles | **Texte → GET 200 + panneau de texte, Résultat → GET 200, Relancer → POST 200 + liste rechargée** ; sur un document non terminé, Texte renvoie 409 et l'interface affiche l'erreur |
| CRUD complet sur `#referentiels/ports` | création, recherche, tri, export | **formulaire → POST 201 → liste rafraîchie (1 → 2 lignes), recherche « zzz » → état vide, tri OK, export OK** |

Ces harnais ne sont pas dans la suite pytest (ils exigent `jsdom`, qui n'est
pas une dépendance du projet). Ils sont reproductibles via les outils de
`docs/implementation-screens/outils/`.

## 5. Ce qui n'est pas testé

À dire clairement, pour ne pas gonfler les chiffres :

- **les actions contextuelles** des écrans (analyse de contrôle, rapprochement
  automatique, sortie portuaire, démarrage/arrivée de livraison) ne sont pas
  exercées par un test automatisé — elles sont branchées sur des routes
  existantes, rien de plus n'est prouvé ;
- **les écrans hérités** (`#tab-dossiers`, `#tab-jobs`, `#tab-profiles`…) ne
  sont pas re-testés dans cette passe ;
- **les permissions** ne sont testées qu'à travers le RBAC existant, désactivé
  sur ce poste (`data/rbac.json` absent) : le cas « rôle lecteur » n'est pas
  couvert par un test d'écran ;
- **l'accessibilité** n'est vérifiée que par des règles structurelles
  (libellés, `aria-*` sur les dialogues), pas par un audit automatisé complet.

## 6. Les 23 échecs de la suite complète

Ils sont **antérieurs à cette passe** et tous liés à l'environnement, pas au
code applicatif :

- moteur Tesseract indisponible (`libGL` manquant) : `test_ocr.py`,
  `test_pipeline.py`, `test_options.py`, `test_routing_and_security.py` ;
- moteur OCR natif absent ou non chargeable : `test_resources.py`,
  `test_wave4.py`, `test_indra_ocr.py` ;
- adaptateurs de connecteurs externes absents : `test_connector_core.py`.

Un seul échec avait été **introduit** par cette passe : le test du service
worker vérifiait un nom de cache en dur (`unocr-shell-v10-menu`). Il a été
réécrit pour vérifier le versionnement du cache et la présence du nouveau
module dans la liste précachée — c'est le test lui-même qui était trop rigide.

## 7. Reproductibilité

```bash
cd /home/user/ocr-universal
.venv/bin/ruff check src tests
.venv/bin/python -m pytest -q

# vérifications navigateur (serveur démarré sur :8000)
npm install --no-save jsdom
node docs/implementation-screens/outils/dump_interface.js http://127.0.0.1:8000 > /tmp/ui.json
python3 docs/implementation-screens/outils/generer_matrice.py /tmp/ui.json
```
