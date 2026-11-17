# P4 — Finance transit historique et hygiène du dépôt

**Date :** 14 novembre 2026 (travail poursuivi le 15 novembre dans le bac à sable)  
**Branche :** `arena/a4e8bc76-ocr-universal`, base `1ea71dad`  
**Périmètre annoncé :** finance legacy `routes/transit.py`, configuration de
requête sur les routes de frais, inventaire / secrets du dépôt sans purge des
données métier.

## 1. Réalisé

### 1.1. Finance `/transit/*` persistante et cloisonnée

- `POST /transit/dossiers/{id}/frais` crée un objet `Frais` dans
  `BusinessStore(cfg.data_dir / "metier.sqlite3", "frais", Frais)`, sous
  transaction et avec `exiger_dossier`. La réponse porte un identifiant réel ;
  le frais est immédiatement visible via `/api/frais` et le résumé financier.
- `POST /transit/dossiers/{id}/paiement` accepte `frais_id` et l'alias historique
  `frai_id`, vérifie l'appartenance au dossier, refuse un paiement partiel ou
  divergent, refuse un second paiement (`409`) et met à jour le même magasin.
- Validation serveur : montant fini strictement positif, devise ISO à trois
  lettres, type de frais non vide, identifiant de frais requis. Les charges
  invalides renvoient `422` sans écriture.
- RBAC : action dédiée `paiement_frais` (`responsable_financier` ou
  `administrateur`). La création reste sur `frais_creation` ; les refus de rôle
  et de périmètre sont audités avec l'acteur serveur.
- Les routes `/transit/*` passent désormais par le middleware d'authentification
  central comme `/api/*` : jeton inconnu ou absent → `401` quand RBAC est actif.
- `api.RBAC_ACTIONS` ne référence plus le rôle inexistant
  `responsable_transport` pour `resolution_anomalies`.

### 1.2. Autres défauts legacy corrigés dans le même module

- Les cinq appels à `Config.get_current_timestamp()` — méthode inexistante —
  ont disparu. Clôture, archivage, restauration et liaison de conteneur
  n'écrivent plus des champs fantômes dans une vue JSON partielle.
- `Dossier.as_storage_dict()` persiste tous les champs du dataclass ;
  `Dossier.as_dict()` reste une vue API et expose désormais les champs
  maritimes nécessaires (`numero_conteneur`, `statut_documentaire`, etc.).
- Clôture : action `cloture_dossier` (administrateur), état
  `statut_documentaire="cloture"` persistant, journal daté, double clôture
  refusée.
- Archivage : réutilise `tracabilite.archiver_dossier`, état réel `archive`,
  avertissements de pièces manquantes, double archivage refusé.
- Restauration : action `restauration_dossier` (administrateur), restaure l'état
  précédent tracé ou `en_preparation` par défaut.
- Conteneurs transit : création / liste / suppression dans
  `BusinessStore[Conteneur]`, doublon refusé, conflit inter-dossier refusé,
  référence terminal protégée, alias `numero` conservé pour l'UI.
- Historique transit : lit `history`, pas une clé `historique` inexistante.
- Audit transit : filtrage par périmètre, les entrées sans dossier ne sont
  visibles que par un administrateur ; recherche par `action` ou `event`.
- Recherche de doublons transit : résultats limités aux dossiers visibles.
- `routes/transit.py` utilise la configuration de requête (`app.state.cfg`) au
  lieu du singleton `get_config()` dans ses routes.

### 1.3. Routes `/api/frais` sans singleton de module

- `routes/frais.py` ne conserve plus `cfg = get_config()` au niveau module.
- Magasins, audits, imports bancaires, rapprochements et justificatifs lisent
  `_cfg(request)`.
- Les helpers de chemin de justificatif reçoivent explicitement la
  configuration.
- `tests/conftest.py`, les tests de justificatifs et le worker de suppression
  sacrifiable ont été adaptés pour injecter la configuration par l'application.

### 1.4. Hygiène du dépôt

- Désindexation de **1 133 fichiers** suivis mais non source : `.agentic-qe/`,
  `data/keys/`, `logs/`, `src/unocr.egg-info/`, `tmp_packages/`, caches Python
  hors vendor, journaux racine, scratch historique et réglage local Claude.
  Les fichiers restent sur le disque de travail.
- Deux secrets identifiés et retirés de l'index :
  `.agentic-qe/witness-keys/84ee584133ad3af5.key.pem` et
  `data/keys/master.key`. **Rotation / révocation et purge d'historique restent
  à conduire** ; voir `HYGIENE_DEPOT_20261114.md`.
- `.gitignore` étendu ; `scripts/audit_repo_hygiene.py` ajouté ;
  CI bloquante sur `--strict-secrets` ; tests d'hygiène ajoutés.
- Aucune donnée métier `data/` n'a été purgée : 1 879 fichiers locaux restent
  suivis, en attente d'une décision de sauvegarde / qualification.
- `.venv-agency/` reste suivi (19 905 fichiers) : dette explicitement reportée à
  un changement dédié pour éviter une revue de 19 905 suppressions mélangée au
  correctif métier.

## 2. Validations exécutées

| Contrôle | Résultat |
|---|---|
| `ruff check src tests benchmarks` | réussi |
| `ruff check scripts/audit_repo_hygiene.py tests/test_hygiene_depot.py` | réussi |
| `pip check` | `No broken requirements found` |
| Tests ciblés P4 / finance / RBAC / dossiers / hygiène | **337 passed** |
| Suite complète isolée, `HF_HUB_OFFLINE=1`, après `npm ci` | **4 569 passed, 15 failed, 14 skipped** en 433 s |
| `npm run ui:product` sur aperçu isolé | **412 routes, 4 viewports, 32 captures, 0 erreur JS, 0 mutation** |
| `node --check` sur `web/dossiers.js`, `web/ecrans.js`, `web/navigation.js`, `tests/ui_finance_banque.js` | réussi |
| `python scripts/audit_repo_hygiene.py --strict-secrets` | réussi, **0 secret suivi détectable** |
| `git diff --check` et `git diff --cached --check` | réussis |

Les **15 échecs** restants sont la limite environnementale déjà documentée :
Tesseract / Poppler absents et modèles Indra non téléchargés
(`test_api`, `test_indra_ocr`, `test_ocr`, `test_options`, `test_pipeline`,
`test_resources`, `test_wave4`). Les **14 skips** incluent les skips OCR /
serveur / Chromium opt-in déjà connus. Aucun échec métier P4 ne subsiste dans
la suite complète.

## 3. Ce que ce lot ne revendique pas

- Pas de rotation effective des clés compromises, pas de purge de l'historique
  Git, pas de suppression des données métier.
- Pas de désindexation massive de `.venv-agency/` dans ce patch.
- Pas de build Docker rejoué ici, pas de qualification OCR terrain, pas de
  corpus douanier officiel, pas de taux de change ni connecteur externe réel.
- Pas d'alignement complet des scripts d'installation sur les verrous P3 ;
  `uvloop` rend le verrou Linux inadapté tel quel à Windows.
- L'export transit XLSX reste une indication historique, pas un fichier XLSX
  qualifié ; le rapprochement bancaire P1/P2 reste le chemin finance de
  référence.

## 4. Backlog restant après P4

1. **Secrets / historique :** révoquer / faire tourner les deux clés identifiées,
   sauvegarder puis purger l'historique Git de manière coordonnée.
2. **`.venv-agency/` :** changement dédié de désindexation, puis vérification
   qu'aucun outillage ne dépend du chemin suivi.
3. **Données `data/` :** qualifier fixtures vs données locales, sauvegarder,
   décider ce qui reste hors Git.
4. **Installation :** brancher `scripts/install.sh` sur le verrou dev Linux ;
   définir une cible Windows séparée si nécessaire.
5. **Transit / UI :** remplacer les exports simulés restants, rejouer les
   parcours mutants création → contrôle → validation → export → clôture.
6. **Terrain / réglementaire :** corpus OCR réel, CER/WER, modèles et binaires
   épinglés ; corpus douanier FR/AR et tarif 10 chiffres ; intégrations externes
   autorisées ; i18n des modules récents.

## 5. État Git

Travail conservé sur la branche courante, **sans commit ni push**. Le patch
cumulé contient les modifications métier P0→P4, les nouveaux fichiers de tests /
documentation / scripts, et les désindexations d'hygiène décrites ci-dessus.
