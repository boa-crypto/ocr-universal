# Déploiement, configuration et retour arrière

Ce document rassemble ce qui est éparpillé ailleurs : toutes les variables de
configuration, ce qu'un déploiement existant doit faire (rien, pour la plupart),
et comment revenir en arrière lot par lot.

---

## 1. Variables d'environnement

| Variable | Défaut | Effet |
|---|---|---|
| `UNOCR_DATA_DIR` | `./data` | Où vivent les documents, résultats, dossiers, profils et `rbac.json` |
| `UNOCR_LOG_DIR` | `./logs` | Où vit `audit.log` |
| `UNOCR_ROOT` | racine du projet | Point de référence des chemins relatifs |
| `UNOCR_USER_PROFILES_DIR` | `data/profiles` | Profils métier créés par l'utilisateur (jamais écrasés par une mise à jour) |
| `UNIOCR_TOKEN` | *vide* | Jeton unique comparé à temps constant. **Vide = aucun jeton exigé** |

`UNIOCR_TOKEN` est le seul lié à la sécurité. Tant qu'il est vide **et** que
`data/rbac.json` n'existe pas, l'API n'exige aucune authentification. C'est le
comportement d'un outil local, assumé et documenté — voir `docs/LIMITATIONS.md`.

---

## 2. Fichier `config/default.json`

### Limites et qualité

| Clé | Défaut | Rôle |
|---|---|---|
| `max_file_size_mb` | 50 | Taille maximale d'un document importé |
| `max_batch_size_mb` | 200 | Taille maximale cumulée des fichiers d'un lot |
| `max_pages` | 500 | Nombre maximal de pages traitées |
| `render_dpi` | 200 | Résolution de rendu des pages |
| `quality_mode` | `accurate` | Mode de contrôle qualité |
| `default_languages` | `["fra", "eng"]` | Langues OCR par défaut |

### Moteurs OCR

| Clé | Défaut | Rôle |
|---|---|---|
| `ocr.engine_order` | `["native_pdf", "tesseract"]` | Ordre de tentative des moteurs |
| `ocr.tesseract_psm` | 3 | Mode de segmentation Tesseract |
| `ocr.min_word_confidence` | 45.0 | Seuil de confiance mot |

### Prétraitement

| Clé | Défaut | Rôle |
|---|---|---|
| `preprocess.enabled` | `true` | Active le prétraitement |
| `preprocess.variant_comparison` | `true` | Compare les variantes de rendu |
| `preprocess.auto_binarize` | `true` | Binarisation automatique |
| `preprocess.target_dpi` | 200 | DPI cible |

### Extraction

| Clé | Défaut | Rôle |
|---|---|---|
| `extraction.profiles_dir` | `profiles` | Répertoire des profils livrés |
| `extraction.default_profile` | `generic` | Profil appliqué par défaut |

### Sécurité

| Clé | Défaut | Rôle |
|---|---|---|
| `security.max_zip_uncompressed_mb` | 200 | Plafond anti zip-bomb |
| `security.max_zip_ratio` | 100 | Rapport de compression maximal |
| `security.retention_days` | 30 | Durée de conservation des documents |
| `security.encryption.enabled` | `false` | Chiffrement au repos (AES-256-GCM) |

Le chiffrement au repos est **désactivé par défaut** et ne modifie aucune donnée
existante tant qu'il n'est pas activé. Voir `src/unocr/crypto_store.py` : perdre
la clé signifie perdre les données.

### Travail et API

| Clé | Défaut | Rôle |
|---|---|---|
| `jobs.data_dir` | `data` | Répertoire du magasin |
| `jobs.workers` | 2 | Workers demandés — **borné ensuite par la RAM disponible** |
| `api.host` | `127.0.0.1` | Interface d'écoute hors conteneur |
| `api.port` | 8000 | Port d'écoute |
| `log_dir` | `logs` | Répertoire des journaux |

Le fichier Compose publie le port uniquement sur `127.0.0.1` et le conteneur
exécute l'API comme utilisateur non privilégié. Pour une exposition réseau,
ne changez pas seulement l'adresse de publication : placez l'API derrière un
reverse proxy TLS authentifié, définissez `UNIOCR_TOKEN` et configurez
explicitement les hosts et origines CORS autorisés. Une publication Docker sur
`0.0.0.0` sans ces contrôles rend les documents accessibles sur le réseau.

`jobs.workers` est un *maximum*, pas une garantie : le nombre de pipelines
simultanés est borné par la mémoire réellement disponible (~600 Mo par pipeline).
C'est la mitigation du crash natif — voir `tests/test_concurrence_jobs.py`.

### Cohérence (lot 4)

| Clé | Défaut | Rôle |
|---|---|---|
| `coherence.tolerances.gross_weight` | 0.02 | Écart de poids brut toléré (2 %) |
| `coherence.tolerances.net_weight` | 0.02 | Écart de poids net toléré |
| `coherence.tolerances.quantity` | 0.05 | Écart de quantité toléré |
| `coherence.tolerances.packages_count` | 0.05 | Écart de nombre de colis |
| `coherence.tolerances.amount` | 0.01 | Écart de montant toléré |
| `coherence.tolerances.total_ttc` | 0.01 | Écart de total TTC |
| `coherence.regles_bloquantes` | `[]` | Règles dont un constat non tranché interdit la transmission |
| `coherence.regles_desactivees` | `[]` | Règles désactivées (nom exact exigé) |
| `coherence.cles_reference` | `["invoice_number"]` | Clés servant au rapprochement |

La configuration réellement appliquée est visible via `GET /api/coherence/regles`.

---

## 3. `data/rbac.json` (lot 6)

Absent par défaut. Voir `docs/GUIDE_UTILISATEUR.md` § 8 pour le format complet.

---

## 4. Ce qu'un déploiement existant doit faire

**Rien.** Aucune migration de schéma n'est nécessaire :

- Les nouveaux champs de `config/default.json` (`coherence.*`) sont lus avec des
  valeurs par défaut si le fichier est ancien.
- `data/rbac.json` n'existe pas ⇒ rôles et cloisonnement inactifs, comportement
  identique à avant.
- Les résultats et dossiers existants restent lisibles : les champs ajoutés
  (`confirmed_value`, `arbitrages`, …) sont optionnels à la lecture.
- Le chiffrement au repos est désactivé par défaut et ne touche à rien.

**La seule action recommandée** après mise à jour : lancer
`python3 -m pytest tests/` et vérifier que le nombre d'échecs n'a pas augmenté
(23 échecs attendus si `tesseract` n'est pas installé).

---

## 5. Retour arrière, lot par lot

Chaque lot est indépendant et réversible sans toucher aux données.

| Lot | Pour revenir en arrière |
|---|---|
| 4 — cohérence configurable | Vider la section `coherence` de `config/default.json` (les défauts du code reprennent) |
| 5 — annulation des corrections | Retirer le bouton « Annuler » de `web/index.html` ; la route `POST .../undo` devient inutilisée mais inoffensive |
| 6 — rôles et cloisonnement | **Supprimer `data/rbac.json`** puis `POST /api/rbac/recharger`. Le registre redevient inactif et l'API repasse en accès libre — y compris pour les jetons qui existaient avant |
| 7 — cloisonnement sauvegardé | Retirer `"rbac.json"` de `FICHIERS` dans `src/unocr/backup.py`. Les sauvegardes redeviennent plus petites ; aucune donnée n'est perdue |
| 8 — garde au niveau document | Retirer les appels `_exige_job(request, job_id)` des routes `/api/jobs/{id}…` |
| 9 — tests de concurrence | Supprimer `tests/test_concurrence_jobs.py` |

**Retour arrière complet** : restaurer une sauvegarde antérieure à la mise à jour
(`POST /api/backups/restore`, administrateur seul). La restauration recharge
aussi `data/rbac.json` — c'est voulu, un cloisonnement perdu en silence serait
pire que pas de cloisonnement.

### Ce que le retour arrière ne restaure pas

- Les **corrections humaines** portées après la sauvegarde : elles sont dans le
  magasin, pas dans l'archive. C'est pourquoi la restauration exige `force`.
- Le **journal d'audit** est restauré avec l'archive ; les événements postérieurs
  à la sauvegarde ne sont pas dedans.

---

## 6. Vérification après déploiement

```bash
# 1. le service répond
curl -s http://localhost:8000/api/health

# 2. les moteurs réellement disponibles
curl -s http://localhost:8000/api/engines

# 3. la configuration de cohérence appliquée
curl -s http://localhost:8000/api/coherence/regles

# 4. l'identité et les droits (si RBAC actif)
curl -s -H "Authorization: Bearer <jeton>" http://localhost:8000/api/rbac/moi

# 5. la non-régression
python3 -m pytest tests/
```

---

## 7. Ordre de priorité appliqué

Le plan suivi, dans l'ordre P0→P4 du cahier des charges :

| Priorité | Lot | Sujet |
|---|---|---|
| P0 | 1 | Sauvegarde et restauration du magasin |
| P1 | 2 | Limitation de débit, identifiant de corrélation |
| P1 | 9 | Mitigation du crash natif, testée |
| P2 | 4 | Règles de rapprochement configurables |
| P2 | 6 | Rôles et cloisonnement par dossier |
| P2 | 7 | Cloisonnement survivant à une reprise |
| P2 | 8 | Cloisonnement au niveau du document |
| P3 | 3 | Recherche globale inter-documents |
| P3 | 5 | Raccourcis clavier et annulation |
| P2 | 11 | Provenance complète dans les exports |

P4 (IA expérimentale) n'a pas été développée : le cahier des charges la conditionne
à un bénéfice mesuré, et aucun n'a été démontré ici.
