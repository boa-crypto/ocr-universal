# Rapport de tests — écrans UniOCR

Date : 2026-11-04. Branche `arena/2cd4c91a-ocr-universal`, état après la passe 31.

Ce document liste **uniquement des résultats obtenus**, avec la commande qui
les produit. Les sections de passes ci-dessous conservent les résultats historiques.

---

## 1. Résultat d'ensemble

| Commande | Résultat | Commentaire |
|---|---|---|
| `ruff check src tests` | **All checks passed** | 0 erreur de style |
| `python -m pytest -q` | **1098 passed, 23 failed, 11 skipped** | les 23 échecs sont environnementaux (voir §6) |
| `python -m pytest tests/test_ui_premium.py -q` | **56 passed** | tests de contrat et intégrité UI |
| `python -m pytest tests/test_historique.py -q` | **5 passed** 🆕 | ordre, filtrage par document, événements inconnus, journal illisible |
| `python -m pytest tests/test_rbac_ecritures.py -q` | **18 passed** | 14 familles d'écriture refusées à un lecteur, refus tracés |
| `python -m pytest tests/test_referentiels_base.py -q` | **6 passed** | amorçage idempotent, non destructif, tracé, borné |
| `python -m pytest tests/test_stats_comparaison.py -q` | **18 passed** | hausse/baisse/stable, période vide, dates manquantes, bornes et limites |
| `npm run ui:smoke` | **15/15 vérifications** 🆕 | 8 écrans, 4 interactions, 0 écriture, 0 erreur JS ou 5xx |
| `python -m pytest tests/test_interface_jsdom.py -q` | **1 passed** (ou sauté sans jsdom/serveur) 🆕 | rejoue le harnais depuis pytest |
| `python -m pytest tests/test_parametres.py -q` | **10 passed** 🆕 | écriture, bornes, persistance, effet réel sur l'import |
| `python -m pytest tests/test_referentiels.py -q` | **7 passed** 🆕 | CRUD, persistance, doublons, audit |
| `python -m pytest tests/test_route_ordering.py -q` | **4 passed** 🆕 | détection des routes masquées |

Bilan historique à la passe 19 : 945 → **1008 tests passants**
(+7 référentiels, +4 ordre des routes, +10 écrans rôles/utilisateurs, +4
intégrité UI, moins un test de service worker réécrit pour être
version-agnostique).

## 1 bis. Mesures d'écrans (passe 13)

Les écrans ne se prouvent pas seulement par des tests serveur. Un harnais
jsdom (`docs/implementation-screens/outils/dump_interface.js` + scripts
jetables) a parcouru les 99 routes :

- `dump_interface.js` → 99 routes, **0 page vide** ;
- matrice régénérée → **99 entrées, 98 conformes, 1 partiel** ;
- création de dossier par le dialogue : **POST /api/dossiers 200** (dossier
  d'essai supprimé ensuite, 715 dossiers retrouvés) ;
- « Marquer payée » sur une liquidation : **PUT 200** (liquidation d'essai
  supprimée ensuite) ;
- `dossiers/clients` : 3 boutons, état vide explicite (plus de page héritée
  muette) ;
- `#referentiels/parametres` supprimée puis rétablie en passe 14 sur une API réelle ;
- formulaires : pays/ports alimentés par les référentiels, état vide expliqué ;
- `#rapports/graphes` : 6 cartes, 3 séries SVG réelles, 3 états vides expliqués ;
- `#finance/cloture` : archivage exercé sur un dossier jetable (POST 200),
  dossier supprimé ensuite — 715 dossiers de démonstration intacts.

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
| rôles (passe 12) | catalogue contre rôles locaux | **9 rôles livrés sans bouton ; création POST 200, édition PUT 200, suppression DELETE 200 d'un rôle personnalisé** |
| utilisateurs RBAC (passe 11) | création du premier compte | **POST 200 avec rôles en liste, jeton affiché une fois ; PUT 200 (rôles modifiés) ; DELETE 200** ; serveur isolé sur données temporaires |
| résultat et qualité (passe 10) | point d'entrée depuis la liste | **document `done` → GET /result 200, texte affiché, jauges 100 % / 3 anomalies ; document `queued` → action refusée, 0 requête ; aucun document → message d'état vide** |
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
npm install                       # jsdom, une fois
npm run ui:smoke                  # 15 vérifications, aucune écriture
.venv/bin/python -m pytest tests/test_interface_jsdom.py -q

# régénération de la matrice (serveur démarré sur :8000)
node docs/implementation-screens/outils/dump_interface.js http://127.0.0.1:8000 > /tmp/ui.json
python3 docs/implementation-screens/outils/generer_matrice.py /tmp/ui.json
```

### Passe 23 — choix des objets existants

- `pytest tests/test_ui_premium.py -q` : **55 passed**.
- `npm run ui:registres` : 715 dossiers proposés, identifiant inconnu refusé,
  aucune requête d'écriture ; exige un serveur et un dossier existant.
- `npm run ui:smoke` : **15/15**.
- `ruff check src tests` : aucune erreur.
- Suite complète : **1028 passed, 23 failed, 11 skipped** (les 23 échecs environnementaux OCR déjà connus persistent).

### Passe 24 — fiabilité des mesures

- `pytest tests/test_stats_comparaison.py -q` : **18 passed**.
- `npm run ui:comparaison` : six lignes, limites visibles, 131 documents réussis
  au lieu des 200 jobs tous états, aucune erreur réseau et aucune écriture.
- Suite complète : **1036 passed, 23 failed, 11 skipped** ; les échecs OCR
  environnementaux connus persistent. Smoke UI : **15/15**. Ruff : aucune erreur.

### Passe 25 — préparation des déclarations

- `npm run ui:declarations` : navigation, avertissement mémoire, refus inconnu,
  POST simulé, fermeture du formulaire et liste actualisée. Aucune écriture réelle.
- Suite complète : **1037 passed, 23 failed, 11 skipped** ; échecs OCR connus.
- Smoke UI : **15/15** ; Ruff : aucune erreur.
- Matrice régénérée : **100 conformes, 1 partielle** sur 101 entrées (CRUD de
  l'entrée Déclarations non entièrement re-certifié ; ne pas annoncer 101 conformes).

### Passe 26 — persistance métier

- `pytest tests/test_business_persistence.py -q` : **9 passed**, répertoires
  temporaires uniquement (CRUD trois collections, workflow, autre processus,
  champs conservés, sauvegarde/restauration et validation avant écriture).
- Suite complète : **1046 passed, 23 failed, 11 skipped** ; échecs OCR connus.
- Le test navigateur Déclarations utilise maintenant la vraie clé `id`.
- Harnais Déclarations : succès avec clé `id` et message de stockage local ; smoke UI **15/15** ; Ruff sans erreur.

### Passe 27 — CRUD Déclarations réel et redémarrages

- `python -m pytest tests/test_declarations_e2e.py -q` : **1 passed** (9,98 s).
  API uvicorn réelle et jsdom, données/logs/profils temporaires, trois démarrages.
  Création, modification, persistance, annulation de suppression, suppression et
  persistance de la suppression. Aucune réponse API simulée.
- Dépendances : `npm install`, puis commande pytest ci-dessus ; aucun serveur
  préalable requis. Sans node/jsdom : saut explicite.
- Suite complète : **1047 passed, 23 failed, 11 skipped** ; les 23 échecs OCR
  environnementaux connus persistent. Ruff sans erreur.
- Matrice parcourue et régénérée : **101 conformes, 0 partiel**.

### Passe 28 — transitions terminal

- `python -m pytest tests/test_terminal_workflow.py -q` : **16 passed**,
  refus de saut d'étape, contournement PUT, prérequis/date invalides,
  immutabilité après autorisation, audit et relecture des données inchangées.
- `npm run ui:terminal` : quatre états, boutons autorisés par état, clé `id`,
  aucune écriture (réponses terminal simulées, fichiers UI réels).
- Suite complète : **1063 passed, 23 failed, 11 skipped** ; échecs OCR connus.
- Ruff : aucune erreur. Pas de nouvel écran ; matrice inchangée.

### Passe 29 — intégrité des liens liquidation/déclaration

- `pytest tests/test_liquidation_integrity.py -q` : **12 passed**, API et SQLite
  temporaires : parents inexistants, dossiers incohérents, modifications invalides,
  suppression/déplacement protégés, réaffectation cohérente, rollback multi-collection
  et cinq courses création/suppression sans orphelin.
- Suite complète : **1075 passed, 23 failed, 11 skipped** ; échecs OCR connus.
- Smoke UI : **15/15** ; Ruff sans erreur. Matrice inchangée, aucun nouvel écran.

### Passe 30 — liens vers les dossiers et suppression protégée

- `pytest tests/test_dossier_business_links.py -q` : **15 passed**, API et
  répertoires temporaires, dont dix courses concurrentes référence/suppression.
- Suite complète : **1090 passed, 23 failed, 11 skipped** ; échecs OCR connus.
- Smoke UI : **15/15** ; Ruff sans erreur. Aucun nouvel écran, matrice inchangée.
- Les fixtures de persistance et d'intégrité créent des fichiers dossiers réels.

### Passe 31 — expéditions persistantes

- `pytest tests/test_business_persistence.py tests/test_dossier_business_links.py -q` :
  **32 passed** (11 persistance et 21 liens dossier), dont expéditions CRUD après
  réouverture, date d'émission, sauvegarde/restauration et courses concurrentes.
- Suite complète : **1098 passed, 23 failed, 11 skipped** ; échecs OCR connus.
- Smoke UI **15/15**, Ruff sans erreur. Matrice inchangée, pas de nouvel écran.
