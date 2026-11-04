# UniOCR — Plan d'implémentation (Phase 1 : Audit)

## 1. Audit de l'environnement réel (mesuré le 2026-10-17)

| Élément | Valeur mesurée |
|---|---|
| OS | Debian GNU/Linux 13 (trixie), noyau 6.1, x86_64 |
| CPU | 2 cœurs |
| RAM | 1.9 Gio (≈1.4 Gio disponibles) |
| Disque | 25 Gio (≈21 Gio libres) |
| GPU | **aucun** (pas de nvidia-smi, pas de GPU détecté) |
| Python | 3.13.16, pip 26.2.1 |
| Réseau | disponible (pip + apt fonctionnels) |
| Droits | utilisateur `user`, groupe `sudo` actif |
| Projet existant | **aucun** (workspace vide) → création from scratch |

### Dépendances système installées pendant l'audit
- `tesseract-ocr` **5.5.0** (leptonica 1.84.1) + paquets de langues : **ara, chi_sim, deu, eng, fra, ita, por, rus, spa, tur + osd**.
- `poppler-utils` 25.03.0 (pdftoppm/pdfinfo).
- `libzbar0` (installé mais **pyzbar ne décode rien** sur QR de test → abandonné au profit de `zxing-cpp`).
- ImageMagick (`convert`/`magick`) déjà présent.

### Dépendances Python installées et vérifiées par import
pytesseract, pypdfium2, pdfminer.six, reportlab, fastapi, uvicorn, python-multipart,
aiofiles, rapidfuzz, striprtf, odfpy (import `odf`), xlrd, zxing-cpp, langdetect,
psutil, segno, pillow, opencv-python, numpy, scikit-image, pandas, openpyxl,
python-docx, pydantic v2, pytest, httpx, lxml, python-dateutil.

### Contraintes fortes retenues pour la conception
1. **2 cœurs / 2 Gio RAM / pas de GPU** → impossible d'installer torch/PaddlePaddle
   (≥2 Gio chacun) sans risque d'OOM. Les moteurs EasyOCR/PaddleOCR sont intégrés
   comme **adaptateurs optionnels** (détection de disponibilité à l'exécution) mais
   **ne sont pas installés dans cet environnement** — ils ne seront jamais déclarés actifs.
2. Moteur OCR raster actif : **Tesseract** (seul moteur installable dans les contraintes).
   L'architecture multi-moteurs est réelle (registre, sélection, consensus) et testable
   avec des moteurs simulés dans la suite de tests.
3. Pas de CUDA/Vulkan → aucunement revendiqué. Accélération matérielle : non.
4. Écriture manuscrite : **aucun modèle installé** (pas de torch) → détection de zones
   manuscrites possible, mais **pas de transcription manuscrite**. Limitation documentée.

## 2. Technologies retenues et raisons

| Besoin | Choix | Raison |
|---|---|---|
| OCR raster | Tesseract 5.5 via pytesseract | Licence Apache-2, multi-langues, tournant sur CPU 2 cœurs, données de confiance par mot |
| Texte natif PDF | pdfminer.six (+ pypdfium2) | Boîtes de caractères précises pour la couche texte ; pdfium pour le rendu image |
| Rendu PDF/TIFF | pypdfium2 | Wheel autonome, sans dépendance système, rapide |
| Prétraitement | OpenCV 4.11 + numpy | Standard industrie, déjà installé, fonctions deskew/perspective/CLAHE/binarisation |
| Codes-barres / QR | zxing-cpp | Wheel autonome ; couvre QR + 1D ; pyzbar défaillant dans cet environnement |
| Détection langue | langdetect + `tesseract --list-langs` | La disponibilité des langues est **prouvée par les modèles tessdata réellement installés** |
| Modèles métier | Profils JSON (schéma validé par pydantic) | Ajout de profils sans modifier le noyau |
| API | FastAPI + uvicorn | Async, OpenAPI généré automatiquement, multipart natif |
| UI | HTML/JS/CSS vanilla servi par FastAPI | Pas de build Node, fonctionne en mode local/offline |
| Exports | stdlib + openpyxl + reportlab | TXT/JSON/CSV/XML/XLSX/PDF consultable (couche texte invisible) |
| Stockage | Système de fichiers + JSON atomique + SQLite (jobs) | Simple, reprise après interruption, zéro service externe |
| Tests | pytest | Déjà installé |
| Benchmarks | CER/WER par distance de Levenshtein (rapidfuzz) | Mesuré sur jeu généré avec vérité terrain écrite à la main |

## 3. Architecture modulaire (séparation stricte)

```
unocr/
├── models.py         # Modèles de données (pydantic) : Document, Page, Mot, Table, Champ, Anomalie…
├── config.py         # Configuration chargée (JSON), chemins, limites
├── logging_setup.py  # Journalisation structurée + audit
├── security.py       # Validation formats/tailles, zip-bomb, noms de fichiers, anti-injection
├── ingest.py         # Détection de format + chargement (PDF natif/scanné/hybride, images, DOCX, ODT, TXT, RTF, CSV, XLS, XLSX)
├── preprocess.py     # Analyse qualité + opérations sélectionnées + comparaison de variantes
├── ocr_engines.py    # Interface OCR + Tesseract + PDF natif + registre + sélection + consensus
├── layout.py         # Colonnes, ordre de lecture, RTL, regroupement mots→lignes→blocs
├── extract_fields.py # Champs génériques (dates, montants, e-mails, téléphones, IBAN, identifiants…)
├── extract_tables.py # Tables à filets (OpenCV) + sans filets (clustering de mots), multipages, cellules fusionnées
├── profiles.py       # Moteur de profils métier + validateurs (ISO 6346, Luhn, IBAN, dates)
├── quality.py        # Scores confiance moteur/global, anomalies, contrôles de cohérence
├── exporters.py      # TXT, JSON, CSV, XLSX, XML, PDF consultable
├── storage.py        # Jobs (création, état, reprise), artefacts, journal d'audit
├── pipeline.py       # Orchestrateur : ingestion → prétraitement → OCR → extraction → qualité → export
└── api.py            # API REST FastAPI + service de l'UI
```

Flux : `ingest → preprocess → ocr_engines → layout → extract_* → quality → exporters → storage`.
Chaque étape expose une interface pure (entrée/sortie typée) et est testée isolément.

## 4. Modèle de confiance (traçable)

- `engine_confidence` : moyenne des confiances Tesseract par mot (0–1), ou 0.95 pour la
  couche texte native PDF (documenté : les caractères sont ceux du fichier, pas une hypothèse OCR).
- `global_confidence` = `engine_confidence × quality_factor` où `quality_factor` dépend
  du flou, de la résolution effective et de l'éclairage de la page (borné à [0.5 ; 1.0]).
  En cas de désaccord entre moteurs, le facteur est réduit et une anomalie est émise.
- Toute correction automatique est journalisée (`raw_value` conservé, `normalized_value`
  et `corrected_value` distincts, `confirmed_value` réservé à l'humain).

## 5. Sécurité

- En-têtes magiques + liste blanche d'extensions, taille max, garde zip-bomb (DOCX/ODT/XLSX).
- Texte extrait traité comme **non fiable** : jamais exécuté, jamais injecté dans une
  commande ; XML échappé ; CSV/XLSX protégés contre l'injection de formules (`=`, `+`, `-`, `@`).
- Journal d'audit JSONL (uploads, suppressions, validations humaines).
- Suppression contrôlée des temporaires ; conservation de l'original jamais modifié.

## 6. Phases et état

| Phase | Contenu | État |
|---|---|---|
| 1 Audit | Environnement, dépendances, contraintes | ✅ fait (ce document) |
| 2 Conception | Architecture, modèles, interfaces | ✅ fait (ce document + code) |
| 3 Prototype | Import, prétraitement, OCR, résultats | ✅ implémenté + tests |
| 4 Extraction | Champs, tableaux, profils, cohérence | ✅ implémenté + tests |
| 5 Qualité | Multi-moteurs, scores, anomalies, validation humaine | ✅ implémenté + tests (consensus testé via moteurs simulés) |
| 6 API/Exports | 6 formats de sortie + REST + OpenAPI | ✅ implémenté + tests |
| 7 Sécurité/Optim. | Erreurs, mémoire, gros fichiers, local | ✅ implémenté + tests sécurité |
| 8 Validation | Suite de tests, benchmark, limitations | ✅ tests exécutés, benchmark mesuré publié |

## 7. Limitations assumées dès la conception
- Pas de GPU → pas d'accélération matérielle, pas d'EasyOCR/PaddleOCR installés ici.
- Tamazight : pas de modèle tessdata installé → **non supporté** tant que le modèle absent.
- Arabe algérien : l'arabe standard (tessdata `ara`) est disponible ; les spécificités
  dialectales ne sont pas modélisées.
- Manuscrit : détection de zones uniquement, pas de transcription.
- Chinois : modèle `chi_sim` installé (simplifié seulement).
- CER/WER publiés = mesures sur le jeu de test généré (documenté), pas une promesse générale.
