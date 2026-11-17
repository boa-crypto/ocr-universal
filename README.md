# UniOCR — Moteur OCR universel

Système OCR professionnel, modulaire, multimoteur et traçable : transforme des
documents hétérogènes (PDF natifs/scannés/hybrides, images, DOCX, ODT, TXT, RTF,
CSV, XLS, XLSX) en données structurées exploitables — texte, structure, champs,
tableaux, coordonnées, scores de confiance, anomalies — exportables en
**JSON, TXT, CSV, XLSX, XML et PDF consultable**.

> Règle absolue du projet : **aucune fonctionnalité n'est déclarée opérationnelle
> sans avoir été implémentée et testée**. Les limites sont documentées dans
> [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## Démarrage rapide

```bash
# 1. dépendances système (Debian/Ubuntu) : Tesseract + langues + Poppler
sudo apt-get install -y tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng \
    tesseract-ocr-ara tesseract-ocr-spa tesseract-ocr-deu tesseract-ocr-ita \
    tesseract-ocr-por tesseract-ocr-tur tesseract-ocr-rus tesseract-ocr-chi-sim \
    tesseract-ocr-osd poppler-utils

# 2. dépendances Python
pip install -r requirements.txt

# 3. tests
python -m pytest tests/ -q

# 4. serveur API + interface web
./scripts/run_server.sh          # UI : http://localhost:8000  ·  API : /docs
```

Aperçu dans un bac à sable distant (écoute sur `0.0.0.0`, UI affichable en
iframe, hôte `*.e2b.app` autorisé — **usage aperçu uniquement**) :

```bash
./scripts/run_preview.sh         # UNOCR_PREVIEW=1, port 8000
```

Ou en une commande avec Docker (embarque Tesseract + 11 langues + Poppler + zbar) :

```bash
docker compose up --build        # UI : http://localhost:8000  ·  API : /docs
```

Benchmark complet et reproductible (tests + suites synthétique et terrain,
rapport horodaté dans `benchmarks/results/`) :

```bash
./benchmarks/run_all.sh
```

Traitement en ligne de commande :

```bash
PYTHONPATH=src python -m unocr.cli process document.pdf --profile port_bl --export json,txt,xlsx
PYTHONPATH=src python -m unocr.cli diagnose
```

## Capacités (testées)
| Domaine | Fonctionnalités |
|---|---|
| Entrées | PDF natif / scanné / hybride / multipage, PNG, JPG, TIFF (multi-frames), BMP, WEBP, DOCX, ODT, TXT, RTF, CSV, XLSX, XLS |
| Prétraitement | orientation (OSD), redressement, perspective, recadrage, ombres, contraste (CLAHE), débruitage, binarisation adaptative ciblée, agrandissement, détection de colonnes, pages vides — **comparaison de variantes** (original vs prétraité) |
| OCR | Tesseract 5 (10 langues installées), couche texte native PDF (pdfminer), registre multi-moteurs avec adaptateurs **EasyOCR/PaddleOCR activables** si installés, consensus pondéré par la confiance (pas de vote majoritaire aveugle) |
| Langues | fra, eng, ara, spa, deu, ita, por, tur, chi_sim, rus (modèles tessdata **vérifiés**), détection automatique (langdetect), RTL arabe, multilingue par page, sélection manuelle |
| Tableaux | avec filets (OpenCV) et sans filets (clustering de mots), multipages, cellules fusionnées (col_span), en-têtes, cellules avec géométrie + confiance |
| Champs | dates (multi-formats ISO), e-mails, téléphones, URLs, IBAN, montants/devises, %, quantités+unités, TVA, n° facture/contrat/série, n° conteneur… jamais de valeur inventée |
| Profils métier | `generic`, `invoice`, `port_bl` (Bill of Lading), `packing_list`, `container` (photo ISO 6346), `vehicle_plate` (plaque/VIN, 11 pays), `carte_grise` (FR/DZ : 19 champs dont n° moteur, cylindrée, poids à vide, genre) — JSON, ajoutables **sans toucher au noyau** ; validateurs ISO 6346 (chiffre de contrôle), plaques (FR, DZ, ES, DE, IT, PT/NL, BE, UK, TR, MA, TN), VIN (ISO 3779) + check digit position 9, énergie/carburant, Luhn, IBAN (mod 97), dates |
| Qualité | confiance moteur ≠ confiance globale, anomalies (flou, dates incohérentes, somme, champ requis absent, ambiguïté O/0), désaccords moteurs, contenu injecté signalé **jamais exécuté** |
| Exports | TXT, JSON, CSV (anti-injection de formules), XLSX (5 feuilles), XML (échappé), PDF consultable (couche texte invisible positionnée) |
| API REST | upload, **lots multi-documents**, jobs asynchrones, pagination, texte par page, extraction par schéma, PATCH de validation humaine, exports (dont **export ciblé**), retry, stats, **recherche plein texte** (`/api/search`), **file de révision** (`/api/review`), **dossier surveillé** (`/api/watch`), **journal d'audit** (`/api/audit`), **ressources machine** (`/api/resources`), **profils utilisateur** (`/api/profiles`), **calibration** (`/api/calibration`), **authentification optionnelle** (`UNIOCR_TOKEN`), **chiffrement au repos** (optionnel, AES-256-GCM) — OpenAPI sur `/docs` |
| UI | glisser-déposer, explorateur, liste des documents, visionneuse avec zones OCR surlignées, texte, champs (validation humaine), tableaux, qualité/anomalies, comparaison moteurs, configuration, tableau de bord, **file de révision au clavier** (`j/k`, Entrée, `o`), **recherche globale** (documents, champs, mots, avec extraits surlignés), raccourcis clavier (`/`, `g`+chiffre, `t`, `?`), thème clair/sombre, **interface multilingue** (fr/en/ar, miroir RTL), **installable hors ligne** (PWA), **éditeur de profils**, **polices embarquées — aucune ressource réseau** |
| Qualité dev. | suite pytest, lint `ruff`, contrôle statique de l'UI (`tests/ui_stub_check.js`), CI GitHub Actions (tests + lint + benchmark + build Docker), tests isolés du `data/` réel, rapport de benchmark horodaté reproductible |
| Traçabilité | journal d'audit JSONL consultable et filtrable (`/api/audit`), validation humaine tracée |
| Sécurité | signatures magiques, limites de taille, garde zip-bomb, noms de fichiers assainis, anti-injection CSV/XML, texte extrait non fiable (prompt-injection signalée), audit JSONL, suppression contrôlée, **authentification par jeton optionnelle**, **chiffrement au repos optionnel**, **garde-fou RAM** (un moteur trop lourd n'est jamais activé) |
| Performance | **traitement parallèle des pages** (gain mesuré ×1,18 sur 4 pages, 2 cœurs), workers bornés par la RAM |
| Automatisation | **dossier surveillé** (traitement à l'arrivée d'un fichier), déduplication par empreinte SHA-256, **lots** avec export groupé (XLSX multi-feuilles, CSV long, ZIP) |
| Local | 100 % offline une fois installé, CPU seul, mémoire ~300 Mo pour le benchmark complet |
| Confiance | calibration des scores (Platt/isotonique) implémentée et testée — **désactivée par défaut** tant qu'aucune photo réelle ne permet de l'apprendre |

## Benchmarks mesurés (jeu de 9 fichiers générés, 2026-10-17)

Voir [benchmarks/results/latest.md](benchmarks/results/latest.md) — mesures
complètes et reproductibles (`python benchmarks/run_benchmark.py`) :
CER moyen **0.016**, WER moyen **0.046**, exactitude des champs BL **7/7**,
mémoire RSS fin de run **~300 Mo**. Scores sur jeu synthétique uniquement —
voir les limites du document de résultats.

## Benchmark terrain (photos de capture)

`python benchmarks/run_field_benchmark.py` mesure CER/WER + exactitude des
champs sur photos de capture. **Deux sources, distinguées dans le rapport** :
- suite **synth** : photos synthétiques dégradées (rotation, perspective,
  flou, bruit, faible lumière) — conditions terrain *simulées*, résultat
  2026-10-17 : CER moyen **0.008**, champs **31/32** (16 échantillons) ;
- suite **real** : déposez de vraies photos dans `benchmarks/field/` avec un
  `ground_truth.json` — tant qu'aucune photo n'est fournie, le rapport le
  stipule et **aucun chiffre « terrain réel » n'est produit**.

## Architecture

Voir [PLAN.md](PLAN.md) (audit de l'environnement, choix technologiques,
séparation des modules) et [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Documentation

- [docs/INSTALLATION.md](docs/INSTALLATION.md) — installation et configuration
- [docs/GUIDE_UTILISATEUR.md](docs/GUIDE_UTILISATEUR.md) — UI, CLI, profils
- [docs/API.md](docs/API.md) — référence de l'API REST
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md) — limites connues, assumées

## Licence des dépendances

Tesseract (Apache-2.0), OpenCV (Apache-2.0), pdfminer.six (MIT), pypdfium2
(BSD/Apache-2.0), reportlab (BSD), zxing-cpp (Apache-2.0), FastAPI (MIT)…
Toutes compatibles usage local et redistribution prudente.


## Référentiels douaniers algériens — chantier réglementaire

Le [socle douanier et son état de complétude](docs/customs/README.md) distinguent
les sources vérifiées des préparations en quarantaine. **Les deux référentiels
nationaux complets ne sont pas encore livrés.** L'ancien calcul avec taux
hypothétiques est désactivé ; aucun taux de remplacement n'est supposé.
Voir [audit et blocages documentaires](docs/customs/AUDIT_INITIAL.md) et
[rapport de recette partielle](docs/customs/RAPPORT_AVANCEMENT.md).

Recherche documentaire des descriptions de mesures (lot 32, non applicable au calcul) : [guide](docs/customs/RECHERCHE_MESURES.md), [rapport](docs/customs/RAPPORT_LOT32.md).

Lot 33 : la recherche Code conserve ses aperçus et ajoute des [extraits contextualisés](docs/customs/EXTRAITS_RECHERCHE_CODE.md) originaux avec positions Unicode, exportables et ouvrables par lecture exacte. Pas de fidélité PDF ou droit applicable déduits.

Lot 34 : [inventaire local des sources déclarées](docs/customs/INVENTAIRE_SOURCES.md) via `customs-sources` et `GET /lots/{lot_id}/sources`, filtres/recherche métadonnées et export partiel audité. Aucun corpus exhaustif ou document authentifié déduit.

Lot 35 : [téléchargement contrôlé du PDF archivé](docs/customs/COPIE_PDF_SOURCE.md) via `GET /lots/{lot_id}/pdf-source?document_id=…`, audit obligatoire et SHA navigateur, pièce jointe non validée (pas antivirus).

Lot 36 : [préparer/rejouer des mesures JSON indépendantes de la nomenclature](docs/customs/MESURES_AUTONOMES.md) via CLI explicite, sans activation ni calcul.

Lot 37 : [revue intégrée des mesures autonomes](docs/customs/REVUE_MESURES_AUTONOMES.md), type de registre `mesures`. Contrôle/recherche de mesures/sources/couverture et exports existants, autres opérations explicitement refusées ; aucun rapprochement fiscal.

Lot 38 : [consultation nomenclature et mesures autonomes](docs/customs/CONSULTATION_TARIF_MESURES.md), CLI `customs-tariff-measures`, API racine `/tariff-measures`. Paire tarif/mesures explicitement autorisée pour cette seule opération, sources/paginations séparées et export à double provenance. Aucun rattachement juridique établi.
