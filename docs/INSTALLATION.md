# Installation

## 1. Prérequis système

- OS : Linux (Debian/Ubuntu testé), Windows 10/11, macOS (non testés ici)
- Python 3.11+ (testé sur 3.13)
- RAM : 2 Go minimum (4 Go recommandés pour de gros lots)
- Disque : ~1 Go (dont ~200 Mo de modèles tessdata)
- **Aucun GPU requis** ; aucune accélération matérielle n'est utilisée

### Dépendances système (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y \
  tesseract-ocr tesseract-ocr-osd \
  tesseract-ocr-fra tesseract-ocr-eng tesseract-ocr-ara tesseract-ocr-spa \
  tesseract-ocr-deu tesseract-ocr-ita tesseract-ocr-por tesseract-ocr-tur \
  tesseract-ocr-rus tesseract-ocr-chi-sim \
  poppler-utils
```

Retirez les paquets de langues inutiles, ou ajoutez-les (ex. `tesseract-ocr-nld`).
La liste exacte des langues **réellement disponibles** est toujours retournée par
`GET /api/languages` (ou `python -m unocr.cli diagnose`) — le système ne déclare
jamais une langue supportée si son modèle est absent.

### Windows (indications)

```powershell
# installer Tesseract 5.x via l'installateur UB Mannheim, cocher les langues
# puis : pip install -r requirements.txt
# ajouter le dossier d'installation de Tesseract au PATH
```

## 2. Dépendances Python

```bash
python -m venv .venv
source .venv/bin/activate       # Windows : .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements.lock.txt   # versions exactes verrouillées (recommandé)
```

## 3. Vérification

```bash
PYTHONPATH=src python -m unocr.cli diagnose
python -m pytest tests/ -q
```

`diagnose` affiche : OS, CPU, RAM, moteurs OCR disponibles, langues tessdata
installées, binaires système. **Lisez-le avant toute demande de support.**

## 4. Lancement

```bash
./scripts/run_server.sh                 # API + UI sur http://localhost:8000
# ou
PYTHONPATH=src python -m unocr.cli serve --host 0.0.0.0 --port 8000
```

- Interface web : `http://localhost:8000/`
- Swagger OpenAPI : `http://localhost:8000/docs`
- JSON OpenAPI : `http://localhost:8000/openapi.json`

## 5. Configuration

`config/default.json` (facultatif — les valeurs par défaut sont dans le code) :

```json
{
  "max_file_size_mb": 50,
  "render_dpi": 200,
  "quality_mode": "accurate",
  "default_languages": ["fra", "eng"],
  "ocr": {"tesseract_psm": 3, "min_word_confidence": 45},
  "preprocess": {"enabled": true, "variant_comparison": true},
  "extraction": {"default_profile": "generic"},
  "security": {"max_zip_uncompressed_mb": 200, "max_zip_ratio": 100, "retention_days": 30},
  "api": {"host": "0.0.0.0", "port": 8000}
}
```

Variables d'environnement :
- `UNOCR_ROOT` : racine du projet (config, profils, données, logs)
- `UNOCR_DATA_DIR` : répertoire des données (documents, résultats, exports).
  Sort les données de la racine du projet — montage de volume Docker, disque dédié
- `UNOCR_LOG_DIR` : répertoire des journaux (`unocr.log`, `audit.log`)
- `UNOCR_HOST` / `UNOCR_PORT` : interface et port d'écoute du serveur

## 6. Stockage et journaux

- `data/jobs/<job_id>/` : `original/` (jamais modifié), `work/`, `exports/`, `result.json`, `job.json`
- `logs/unocr.log` : journal applicatif (rotation 5 Mo)
- `logs/audit.log` : journal d'audit JSONL (uploads, validations humaines, suppressions)

## 6bis. Déploiement Docker

```bash
docker compose up --build     # → http://localhost:8000 (UI) · /docs (API)
```

- L'image embarque Tesseract 5 et **11 modèles de langue**, poppler et zbar.
- Les documents et journaux sont écrits dans le volume `unocr-data` monté sur
  `/data` (via `UNOCR_DATA_DIR`), jamais dans l'image.
- `HEALTHCHECK` interroge `/api/health` ; un healthcheck est aussi présent dans
  la CI GitHub Actions (`.github/workflows/ci.yml`).

## 6ter. Windows

Deux scripts PowerShell équivalents aux scripts bash :

```powershell
.\scripts\install.ps1      # dépendances Python + diagnostic
.\scripts\run.ps1          # démarre le serveur (http://localhost:8000)
.\scripts\run.ps1 -Port 8080 -DataDir D:\unocr-data
```

Les binaires système (Tesseract, Poppler) ne sont **pas** installés
automatiquement : ils demandent des droits administrateur. `install.ps1` les
détecte et affiche la commande d'installation (`winget install
UB-Mannheim.TesseractOCR`, `winget install oschwartz10612.Poppler`).

> Ces scripts n'ont pas pu être exécutés lors de la rédaction (aucun
> PowerShell dans l'environnement de développement) : leur syntaxe n'est pas
> vérifiée automatiquement. À essayer sur une machine Windows.

## 7. Mode sans Internet

Une fois les paquets installés, **aucun accès réseau n'est nécessaire** :
aucune télémétrie, aucun modèle cloud, aucun appel externe. Les documents
confidentiels ne quittent jamais la machine.

## 8. Moteurs optionnels

| Moteur | Installation | État |
|---|---|---|
| EasyOCR | `pip install easyocr` (installe torch, ≥2 Go) | adaptateur prêt, **non installé** dans l'environnement de référence (RAM insuffisante) |
| PaddleOCR | `pip install paddleocr paddlepaddle` | idem |

Ces moteurs s'activent automatiquement dans le registre dès qu'ils sont
importables ; leur absence est affichée honnêtement dans `/api/engines` et l'UI.
