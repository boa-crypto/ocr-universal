# API REST UniOCR

Base URL : `http://localhost:8000` · OpenAPI interactif : `/docs` · JSON : `/openapi.json`

Toutes les réponses sont en JSON. Erreurs : `4xx/5xx` avec `{"detail": "..."}`.

**74 routes** sous `/api/` (dont 35 pour le Connecteur Hub) + 8 routes hors API
(`/`, `/docs`, `/openapi.json`, `/redoc`, `/icon.svg`, `/manifest.webmanifest`,
`/sw.js`, `/docs/oauth2-redirect`).

## Santé et configuration

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/health` | État + moteurs actifs |
| GET | `/api/engines` | Liste des moteurs OCR, disponibilité réelle, langues |
| GET | `/api/languages` | Modèles tessdata installés (uniquement ceux vérifiés) + `catalog` (noms d'affichage) |
| GET | `/api/profiles` | Profils métier chargés |
| GET | `/api/stats` | Tableau de bord : jobs, erreurs, CPU/mémoire |
| GET | `/api/observabilite` | État de la limitation de débit (diagnostiquer un 429) |
| GET/POST | `/api/backups`, `/api/backups/verify`, `/api/backups/restore` | Sauvegarde vérifiable du magasin |

## Documents et jobs

### `GET /api/jobs/stale` — jobs interrompus

Jobs restés `processing` sans mise à jour depuis 10 minutes, ou `queued` depuis
1 heure (serveur arrêté, traitement tué net). Renvoie `count` et la liste des
jobs ; la reprise se fait avec `POST /api/jobs/{job_id}/retry`.

> Route littérale déclarée **avant** `/api/jobs/{job_id}` — sinon `stale` serait
> pris pour un identifiant de job.

### `POST /api/admin/cleanup` — purge des jobs terminés

Applique `security.retention_days` (30 jours par défaut). Paramètres :
`days` (forcer la rétention) et `dry_run` (annoncer sans supprimer). Chaque job
supprimé laisse un événement `job_deleted` dans le journal d'audit, et la purge
elle-même est consignée sous `jobs_purged`.

Équivalent en ligne de commande : `unocr clean [--days N] [--dry-run]`.

### `POST /api/documents` — envoi d'un document

`multipart/form-data` :

| champ | type | défaut | description |
|---|---|---|---|
| `file` | fichier | — | document (PDF, image, DOCX, ODT, TXT, RTF, CSV, XLSX, XLS) |
| `profile` | string | `generic` | profil métier (`invoice`, `port_bl`, `packing_list`, `container`, `vehicle_plate`, `carte_grise`…) |
| `languages` | string | `` (auto) | ex. `fra,eng,ara` — vide = auto-détection |
| `quality_mode` | string | `accurate` | `fast` ou `accurate` (comparaison de variantes) |
| `preprocess` | bool | `true` | prétraitement intelligent (équivalent `preprocess_mode!=off`) |
| `preprocess_mode` | string | `standard` | `off` \| `standard` \| `aggressive` |
| `variant_comparison` | bool | `true` | compare prétraité/origine en mode `accurate` |
| `export_formats` | string | `json,txt` | ex. `json,txt,csv,xlsx,xml,pdf` — générés en fin de traitement |
| `page_range` | string | `` (toutes) | ex. `1-3, 5` ; hors document = erreur `SecurityError` |
| `render_dpi` | int | `200` | résolution de rendu des PDF scannés (72–400) |
| `engine` | string | `auto` | `auto` \| `tesseract` \| `native` (couche texte PDF ; repli Tesseract si absente) |
| `extract_fields` | bool | `true` | extraction champs + profil métier |
| `extract_tables` | bool | `true` | reconstruction des tableaux |
| `extract_barcodes` | bool | `true` | codes-barres 1D / QR |
| `min_confidence_review` | float | `0.7` | seuil (0–1) sous lequel champs/pages sont signalés pour revue humaine |

Réponse `200` : `{"job_id": "job_...", "status": "queued", "filename": "..."}`
Refus immédiat `400` (format/taille/signature invalide) ou `413` (trop volumineux).

Le traitement est **asynchrone** (thread serveur). Suivre l'avancement via
`GET /api/jobs/{id}` (`status`, `progress` 0–1, `stage`).

### `GET /api/jobs?limit=50&offset=0` — liste paginée

### `GET /api/jobs/{id}` — état d'un job

### `POST /api/jobs/{id}/retry` — relance un job (reprise après échec/interruption)

### `DELETE /api/jobs/{id}` — suppression contrôlée (journalisée dans l'audit)

## Résultats

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/jobs/{id}/result` | Résultat complet (pages, mots, blocs, champs, tableaux, qualité, timings) |
| GET | `/api/jobs/{id}/text?page=1` | Texte par page (`page` optionnel) |
| GET | `/api/jobs/{id}/fields` | Champs extraits (brut, normalisé, corrigé, confirmé, confiances, bbox) |
| GET | `/api/jobs/{id}/tables` | Tableaux reconstruits (cellules, lignes, colonnes, confiances) |
| GET | `/api/jobs/{id}/quality` | Confiances, anomalies, désaccords moteurs |
| GET | `/api/jobs/{id}/page/{n}/image` | Image de la page (visionneuse + surbrillance des zones) |

`409` si le résultat n'est pas encore disponible ; `404` si le job/page est absent.

## Validation humaine

`PATCH /api/jobs/{id}/fields/{name}`

```json
{"confirmed_value": "CSQU3054383", "status": "validated"}
```

- `confirmed_value` : valeur confirmée par l'utilisateur (prioritaire, tracée)
- `corrected_value` : correction manuelle
- `status` : `validated` | `detected` | `ambiguous` | `invalid`

La transcription d'origine (`raw_value`) est **toujours conservée**. Chaque
validation est journalisée dans `logs/audit.log`.

## Sauvegarde et restauration

Le magasin local est la seule trace des documents traités, des corrections
humaines et des transmissions. Ces routes en font une sauvegarde vérifiable.

### `POST /api/backups` — créer une sauvegarde

Corps : `{"tag": "avant-migration", "keep": 5}`. `keep` ne conserve que les N
plus récentes (une sauvegarde qu'on ne purge jamais remplit le disque et fait
échouer la suivante). Réponse :

```json
{
  "chemin": "/…/sauvegardes/sauvegarde-20261018-213000.zip",
  "fichiers": 1105, "octets": 41230566, "taille": 38112203,
  "empreinte": "9f2c…", "purgees": []
}
```

### `GET /api/backups` — lister les sauvegardes

Sauvegardes disponibles, la plus récente d'abord, avec leur taille.

### `POST /api/backups/verify` — vérifier avant de restaurer

Corps : `{"chemin": "…"}`. Relit l'archive et contrôle **chaque** empreinte du
manifeste. Refuse une archive altérée, tronquée ou sans manifeste.

### `POST /api/backups/restore` — restaurer

Corps : `{"chemin": "…", "force": true}`. Sans `force`, la restauration est
refusée si le magasin contient déjà des données : restaurer par-dessus ferait
disparaître des documents plus récents que la sauvegarde. Le journal d'audit
est restauré dans `log_dir`, jamais dans `data/`.

## Recherche et révision

### `GET /api/search?q=…&limit=20` — recherche plein texte inter-documents

Cherche dans les **dossiers**, les **champs extraits** — valeur brute,
normalisée, confirmée *et corrigée*, car c'est celle que l'opérateur retient —
et dans le **texte reconnu** de tous les documents traités.

```json
{
  "query": "1HGBH41JXMN109187",
  "returned": 3,
  "truncated": false,
  "hits": [
    {"job_id": "job_…", "filename": "carte_grise.png", "kind": "field",
     "field": "vin", "label": "VIN", "value": "1HGBH41JXMN109187",
     "status": "detected"},
    {"job_id": "job_…", "filename": "carte_grise.png", "kind": "text",
     "page": 1, "snippet": "… VIN 1HGBH41JXMN109187 …"}
  ]
}
```

- `kind` : `field` (valeur de champ) ou `text` (extrait du texte reconnu)
- `q` : obligatoire, 1 caractère minimum (`422` si vide)
- Coût proportionnel au nombre de documents stockés — acceptable pour un
  déploiement local ; à remplacer par un index dédié au-delà de quelques
  centaines de documents.

### `GET /api/review?threshold=0.75&include_undetected=false` — file de révision

Remonte, sur l'ensemble des documents terminés, les seuls champs qu'un humain
doit trancher.

| Paramètre | Défaut | Effet |
|---|---|---|
| `threshold` | `0.75` | seuil de confiance en dessous duquel un champ est signalé |
| `include_undetected` | `false` | inclure les champs `not_detected` |
| `limit` | `50` | nombre de documents parcourus |

```json
{
  "documents": 12,
  "fields": 23,
  "threshold": 0.75,
  "include_undetected": false,
  "items": [
    {"job_id": "job_…", "filename": "carte_grise.png", "created_at": 1729…,
     "profile": "carte_grise",
     "fields": [{"field": "vin", "label": "VIN", "value": "1HGBH41JXMN1091B7",
                 "status": "invalid", "confidence": 0.91,
                 "reasons": ["invalid"]}]}
  ]
}
```

- Les champs déjà `validated` par un humain sont **exclus**.
- Les champs `not_detected` sont **exclus par défaut** : mesuré sur le jeu de
  test, ils représentent ~83 % des entrées et noieraient la file. Les activer
  avec `include_undetected=true`.

### `GET /api/jobs/{id}/export/{fmt}/selected?fields=a,b` — export ciblé

Export limité aux champs listés (séparés par des virgules). Généré à la volée,
non mis en cache : la sélection est propre à une demande. Un champ inconnu est
ignoré ; si aucun champ de la sélection n'existe, la réponse est `400`.

## Traitement par lots

### `POST /api/batches` — envoi de plusieurs documents

Corps : `multipart/form-data`, champ `files` répété, plus les mêmes options que
`POST /api/documents`.

```json
{
  "batch_id": "batch_…",
  "accepted": 2,
  "jobs": [{"job_id": "job_…", "filename": "a.pdf", "status": "queued", "cached": false}],
  "rejected": [{"filename": "virus.exe", "error": "extension non autorisée: .exe"}]
}
```

- Un fichier dont l'empreinte correspond à un document déjà traité est
  **réutilisé** (`cached: true`) au lieu d'être recalculé.
- Un fichier invalide est écarté et signalé dans `rejected` ; il ne fait pas
  échouer le lot.

### `GET /api/batches/export/{fmt}?ids=job_1,job_2` — export groupé

| Format | Contenu |
|---|---|
| `xlsx` | une feuille par document (feuilles unitaires concaténées, suffixes `~2`, `~3`…) |
| `csv` | fichier long, colonne `document` en première position |
| `json` | tableau des résultats complets |
| `txt` | concaténation séparée par document |
| autre | archive ZIP des exports unitaires |

Limites : 200 documents maximum par lot (`413` au-delà) ; `409` si un résultat
n'est pas encore disponible, `404` si un job est inconnu.

## Dossier surveillé

### `GET /api/watch` — état

```json
{"enabled": false, "path": "data/watch", "running": false, "processed": 0,
 "skipped_duplicates": 0, "rejected": 0, "last_job_id": null}
```

### `PUT /api/watch` — configuration

```json
{"enabled": true, "path": "data/watch", "profile": "invoice",
 "languages": "fra,eng", "quality_mode": "accurate",
 "poll_seconds": 5.0, "move_done": false}
```

- Traitement automatique à l'arrivée d'un fichier, avec la même validation de
  sécurité que l'upload.
- Un fichier n'est traité qu'une fois sa taille stabilisée (deux balayages
  consécutifs), pour ne pas lire une copie en cours.
- `move_done: true` range les fichiers traités dans `<dossier>/done/`.
- La déduplication par empreinte s'applique : un fichier déjà traité n'est pas
  recalculé.

### `POST /api/watch/scan` — balayage immédiat

Les compteurs renvoyés portent sur **ce balayage** ; les totaux cumulés sont
dans `totals`.

## Journal d'audit

### `GET /api/audit?limit=100&event=&q=`

Événements les plus récents d'abord, issus de `logs/audit.log` (JSONL).
`event` filtre sur le type exact, `q` sur l'ensemble du contenu de la ligne.
Le journal n'est jamais modifié ni reformaté.

## Exports

`GET /api/jobs/{id}/export/{fmt}` avec `fmt ∈ {json, txt, csv, xlsx, xml, pdf}`

- **Génération à la demande** : si l'export n'a pas été produit au moment du job,
  il est généré automatiquement depuis le résultat stocké — aucun 404 pour un
  format non demandé à l'origine (sauf résultat pas encore disponible : `409`).
- `csv` : un seul fichier s'il existe, sinon **bundle ZIP** (`fields.csv` + tableaux)
- `pdf` : PDF consultable (image source + couche texte invisible) ; `422` pour un
  document purement numérique sans image
- Réponse `200` avec `Content-Disposition: attachment` (téléchargement direct)

## Exemple complet

```bash
curl -F "file=@facture.pdf" -F "profile=invoice" -F "export_formats=json,xlsx" \
     http://localhost:8000/api/documents
# -> {"job_id":"job_abc123","status":"queued",...}

curl http://localhost:8000/api/jobs/job_abc123          # suivi
curl http://localhost:8000/api/jobs/job_abc123/result   # résultat complet
curl -X PATCH -H 'Content-Type: application/json' \
     -d '{"confirmed_value":"2024-001"}' \
     http://localhost:8000/api/jobs/job_abc123/fields/invoice_number
curl -OJ http://localhost:8000/api/jobs/job_abc123/export/xlsx
```

## Profils d'extraction (B5)

### `GET /api/profiles/catalog` — validateurs et normalisations disponibles

```json
{"normalizations": ["upper", "no_space", ...], "validators": ["vin_check", ...],
 "aux_validators": ["vin_check"]}
```

### `POST /api/profiles/test` — essai à blanc d'un profil

Corps : `{"profile": "mon_profil", "job_id": "job_x"}` **ou**
`{"profile": {...définition...}, "text": "texte brut"}`.

Réponse : `{"profile": "...", "fields": {"champ": "valeur"}, "detected": 3, "total": 5}`.

### `PUT /api/profiles/{name}` — enregistre un profil utilisateur

Écrit dans `data/profiles/<nom>.json` — **jamais** dans `profiles/` (profils livrés).
Garde-fous : nom assaini (pas de traversée de chemin), au plus 60 champs,
motif regex de 500 caractères maximum, recompilé à l'enregistrement,
validateur obligatoirement connu (sinon 400).

### `GET /api/profiles/{name}` · `DELETE /api/profiles/{name}`

`GET` renvoie le profil fusionné (`source: "user"` ou `"builtin"`).
`DELETE` renvoie 404 si le profil est livré (non supprimable).

## Calibration des confiances (A2)

### `GET /api/calibration` — état de la courbe de calibration

```json
{"method": "identity", "active": false, "n_samples": 0, "synthetic": true,
 "note": "", "fitted_at": 0.0, "fitted_at_iso": null}
```

### `POST /api/calibration/fit` — réajuste sur les échantillons étiquetés

Corps : `{"force": false}`. Réponse inclut `suite` (`"synthétique"` ou `"réelle"`),
`n_samples`, `method` (`platt` | `isotonic` | `identity`), `active`, `note`.

> **Garde-fou d'honnêteté.** Un ajustement appris sur des échantillons
> *synthétiques* est enregistré mais **laissé inactif** : mieux vaut une
> confiance brute connue qu'une probabilité inventée. L'activation exige
> `force: true` ou un corpus de photos réelles. Le champ
> `calibrated_confidence` de chaque champ extrait reste égal à `confidence`
> tant que la calibration n'est pas active.

## Authentification optionnelle (D3)

### `GET /api/auth/status` — indique si un jeton est exigé (sans le révéler)

L'authentification est **désactivée par défaut**. Définir la variable
d'environnement `UNIOCR_TOKEN` active un jeton unique, comparé à temps
constant, exigé sur toutes les routes `/api/*` via l'en-tête
`Authorization: Bearer <jeton>`. Les jetons dans l'URL sont refusés car ils
peuvent être copiés dans l'historique et les journaux. `/`, `/docs`,
`/openapi.json`, `/redoc`, `/api/health` et
`/api/auth/status` restent ouverts — aucune n'expose de donnée.

## Progressive Web App (C4)

- `GET /manifest.webmanifest` — manifeste d'installation
- `GET /sw.js` — service worker (coquille hors ligne uniquement)
- `GET /icon.svg` — icône

Le service worker **ne met jamais en cache les réponses `/api/*`** : un
document, un export ou un résultat vient toujours du serveur local.

## Ressources et moteurs (E1)

### `GET /api/resources` — ressources réelles de la machine

```json
{"ram_available_mb": 1416, "ram_total_mb": 1982, "cpu_count": 2,
 "disk_free_mb": 20328,
 "engine_requirements_mb": {"tesseract": 120, "native": 20,
                            "easyocr": 2200, "paddleocr": 1800}}
```

`GET /api/engines` renvoie pour chaque moteur `ram_required_mb` et, quand il
n'est pas disponible, `unavailable_reason` (« non installé » ou « mémoire
insuffisante »). Un moteur dont la bibliothèque est présente mais qui dépasse
la RAM disponible **n'est jamais activé** : il ferait tuer le processus par
l'OOM killer.

## Chiffrement au repos (E3)

### `GET /api/encryption` — état (ne révèle jamais la clé)

```json
{"enabled": false, "algorithm": "AES-256-GCM", "kdf": null, "key_length_bits": 0}
```

**Désactivé par défaut.** Activation dans `config/default.json` :

```json
"security": {"encryption": {"enabled": true, "key_file": "keys/master.key"}}
```

ou avec une phrase de passe (aucun secret stocké) :

```json
"security": {"encryption": {"enabled": true,
                            "passphrase": "…", "salt": "16 octets exactement"}}
```

Deux garde-fous : un chiffrement « activé » sans clé valide **reste inactif**
(mieux vaut rien qu'un faux sentiment de sécurité), et perdre la clé rend les
données définitivement illisibles — aucune porte dérobée n'existe.

## Traitement parallèle des pages (E4)

Les pages d'un document multipage sont traitées en parallèle (threads :
Tesseract tourne en sous-processus, le GIL est donc libéré). Le nombre de
workers est borné par `jobs.workers`, par le nombre de cœurs **et** par la RAM
disponible (~450 Mo/page). Le nombre réellement utilisé est tracé dans
`timings_ms.ocr_workers`. L'ordre des pages et le résultat sont identiques au
traitement séquentiel (testé).

## Connecteur Hub — 35 routes

Toutes les routes sont préfixées par `/api/connectors`. Aucune ne contacte un
système externe réel : les deux adaptateurs livrés sont locaux (simulateur et
export assisté).

### Catalogue et cycle de vie

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/connectors` | vue d'ensemble : résumé, catalogue, instances |
| GET | `/api/connectors/catalog` | adaptateurs disponibles |
| GET | `/api/connectors/configured` | instances configurées + état réel |
| POST | `/api/connectors/{id}` | crée/met à jour une instance (repart à « à tester ») |
| GET | `/api/connectors/{id}` | fiche détaillée (aucun secret) |
| DELETE | `/api/connectors/{id}` | supprime configuration et secrets |
| POST | `/api/connectors/{id}/disable` | désactive — configuration et historique conservés |
| POST | `/api/connectors/{id}/enable` | réactive — repart à « à tester » |
| POST | `/api/connectors/{id}/test` | **test réel** : l'état évolue selon la preuve |

### Interface commune par connecteur

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/connectors/{id}/status` | état issu du dernier test documenté |
| POST | `/api/connectors/{id}/auth` | vérification d'authentification (sans révéler de secret) |
| GET | `/api/connectors/{id}/metadata` | métadonnées déclarées |
| GET | `/api/connectors/{id}/forms` | formulaires découverts (`source` = declared/discovered/documented) |
| GET | `/api/connectors/{id}/submission/{ref}` | statut + accusé de réception + erreurs |
| POST | `/api/connectors/{id}/export` | mode C : CSV + correspondance + traçabilité |
| POST | `/api/connectors/{id}/cancel/{ref}` | annulation |
| POST | `/api/connectors/{id}/resume/{ref}` | reprise |

### Mapping, validation, transmission

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/api/connectors/preview` | préremplit + valide, **n'envoie rien** |
| POST | `/api/connectors/transmit` | transmet — refus serveur si validation non conforme |
| GET | `/api/connectors/transmissions` | historique + statistiques |
| POST | `/api/connectors/transmissions/{transmission_id}/reconcile` | rapproche **avant** toute reprise |
| POST | `/api/connectors/transmissions/{transmission_id}/retry` | reprise (`auto=false` manuelle) |
| POST | `/api/connectors/transmissions/{transmission_id}/cancel` | annulation |

### Modèles de formulaires

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/connectors/forms` | modèles actifs (+ trames proposées) |
| GET | `/api/connectors/forms/templates` | trames de départ |
| GET | `/api/connectors/forms/{form_id}` | détail + schéma consommable |
| POST | `/api/connectors/forms` | création (10 types de champs) |
| POST | `/api/connectors/forms/{form_id}` | modification → **nouvelle version** |
| POST | `/api/connectors/forms/{form_id}/disable` | désactive sans supprimer |
| POST | `/api/connectors/forms/{form_id}/from-template` | copie une trame |
| DELETE | `/api/connectors/forms/{form_id}` | suppression |

### Secrets

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/connectors/secrets/status` | état du coffre (AES-256-GCM), aucun secret |
| GET | `/api/connectors/{id}/secrets` | **noms** des secrets, jamais les valeurs |
| PUT | `/api/connectors/{id}/secrets` | enregistre un secret chiffré |
| DELETE | `/api/connectors/{id}/secrets/{key}` | supprime un secret |

### Verrous côté serveur (testés)

1. `POST /api/connectors/transmit` renvoie **409** si la validation n'est pas
   conforme : champs obligatoires manquants, erreur de format, suggestion non
   validée, ou confirmation humaine absente pour un risque élevé.
2. **409** si aucun connecteur n'est opérationnel (test réel réussi).
3. Un contenu déjà accepté n'est **jamais renvoyé** : `create()` détecte le
   doublon par clé d'idempotence et `send()` refuse l'envoi
   (`send_skipped_duplicate`).
4. `retry(auto=true)` est refusé après un rejet métier, et limité à 3 tentatives.
5. Un rejet métier reste visible dans l'historique avec son motif.

## Sécurité de l'API

- Validation stricte des fichiers (signatures magiques, taille, zip-bomb) avant job
- Aucune commande ni expression n'est jamais évaluée depuis un contenu extrait
- Texte extrait = donnée non fiable : les instructions détectées dans un document
  sont signalées (`UNTRUSTED_CONTENT`) et **jamais exécutées**
- Exports CSV/XLSX protégés contre l'injection de formules ; XML échappé
- Journal d'audit pour chaque opération sensible

### Annulation d'une correction

```
POST /api/jobs/{job_id}/fields/{name}/undo
{ "motif": "erreur de saisie de ma part" }
```

Restitue l'état d'avant la dernière correction humaine et renvoie ce qui a été
restauré. L'annulation **n'efface rien** : la correction d'origine reste dans le
journal d'audit, et l'annulation y est tracée à son tour (`field_correction_annulee`,
avec acteur, motif, valeur annulée et valeur restaurée).

Restaurer exige d'avoir tracé l'état précédent — c'est ce que fait
`field_validated` (champs `ancienne_valeur`, `ancienne_origine`, `ancien_statut`).
La valeur restaurée suit la même priorité que l'affichage (confirmée > corrigée >
normalisée > brute) : annuler ne fait pas perdre la normalisation du moteur.

- `409` si aucune correction humaine n'a été faite sur ce champ, ou si l'état
  antérieur est introuvable dans l'audit.
- Le motif est exigé : une annulation sans explication serait une trace
  d'audit inexpliquée.

### Configuration des contrôles de cohérence

```
GET /api/coherence/regles
```

Renvoie la configuration **réellement appliquée** : tolérances par clé, règles
bloquantes, règles désactivées, clés de référence. Un constat qui surprend ou
qui manque doit pouvoir être expliqué en consultant cette route.

### Rôles et cloisonnement par dossier

Tout est piloté par `data/rbac.json`. **Tant que ce fichier n'existe pas, aucune
route n'exige de jeton et aucun cloisonnement n'est appliqué** : un déploiement
existant n'a rien à migrer.

```json
{
  "utilisateurs": [
    {"nom": "marie", "roles": ["operateur"], "dossiers": ["*"], "jeton": "…"},
    {"nom": "audit", "roles": ["lecteur"], "dossiers": ["D1", "D2"], "jeton": "…"},
    {"nom": "admin", "roles": ["administrateur"], "dossiers": ["*"], "jeton": "…"}
  ]
}
```

**Rôles**, du plus restreint au plus large — chaque rôle couvre les précédents :
`lecteur` (consulter) < `operateur` (valider et corriger les champs, créer des
dossiers) < `superviseur` (arbitrer les constats, transmettre) <
`administrateur` (sauvegardes, restauration, gestion des utilisateurs).

**Périmètre.** `dossiers: ["*"]` autorise tout ; une liste d'identifiants
limite à ces dossiers ; une liste vide n'en autorise aucun (échec fermé). La
liste des dossiers est filtrée : un dossier hors périmètre n'apparaît pas.

**Routes.**

| Route | Rôle requis |
|---|---|
| `GET /api/rbac/moi` | aucun — identité de l'appelant |
| `GET /api/rbac/utilisateurs` | administrateur |
| `POST /api/rbac/utilisateurs` | administrateur — crée et **renvoie le jeton une fois** |
| `PUT /api/rbac/utilisateurs/{nom}` | administrateur — rôles et périmètre |
| `POST /api/rbac/utilisateurs/{nom}/jeton` | administrateur — régénère le jeton |
| `DELETE /api/rbac/utilisateurs/{nom}` | administrateur — révocation immédiate |
| `POST /api/rbac/recharger` | administrateur — relit le fichier après édition manuelle |

Les jetons ne sont **jamais** renvoyés par une route de lecture. Un jeton perdu
se régénère, il ne se consulte pas.

**Le jeton d'environnement reste un passe-partout.** `UNIOCR_TOKEN`, s'il est
défini, vaut `administrateur` sur tous les dossiers — comportement historique
conservé pour ne pas casser les scripts existants. Chaque utilisation est
tracée (`acces_jeton_environnement`).

**Événements d'audit** : `acces_refuse_role`, `acces_refuse_dossier`,
`acces_refuse_jeton`, `acces_jeton_environnement`, `rbac_utilisateur_cree`,
`rbac_utilisateur_modifie`, `rbac_utilisateur_retire`, `rbac_jeton_regene`,
`rbac_perimetre_etendu`, `rbac_recharge`.

**Limites assumées.** Pas de SSO, pas de LDAP, pas d'expiration de jeton. Les
jetons sont des secrets porteurs stockés dans un fichier local (chmod 0600),
comparés à temps constant. C'est la frontière de menace d'un outil local. Un
rôle inconnu dans le fichier fait **échouer le chargement** plutôt que d'être
ignoré : une faute de frappe ignorée donnerait plus de droits que prévu.

**Ce que ce module ne fait pas.** Il ne chiffre rien (voir le chiffrement au
repos) et il ne remplace pas `UNIOCR_TOKEN` quand aucun fichier de rôles n'existe.
