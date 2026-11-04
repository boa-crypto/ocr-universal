# Architecture technique

## Vue d'ensemble

```
Fichier source (JAMAIS modifié)
   │
   ▼
security.validate_file ──► ingest.load_document ──► pages (image + texte natif + mots)
   │
   ▼
preprocess.analyze_quality / preprocess_page  (variantes original | prétraitée)
   │
   ▼
ocr_engines.EngineRegistry.select ──► Tesseract | native_pdf | easyocr? | paddleocr?
   │                                   consensus_merge (confiance, désaccords)
   ▼
layout.group_words_into_lines / build_blocks  (colonnes, RTL, ordre de lecture)
   │
   ├─► extract_tables  (ruled: filets OpenCV + mots | clustering) ──► Table[]
   ├─► extract_fields  (regex + localisation floue) ──► FieldValue{}
   ├─► profiles.apply_profile + check_required (validateurs, relations) ──► champs métier
   └─► zxing-cpp (codes-barres / QR)
   │
   ▼
quality.build_quality_report  (confiance moteur ≠ globale, anomalies, cohérence)
   │
   ▼
exporters.export_all  (txt json csv xlsx xml pdf)  +  storage.JobStore (audit)
```

## Modules (séparation stricte)

| Module | Responsabilité | Interface principale |
|---|---|---|
| `security.py` | validation fichiers, zip-bomb, anti-injection | `validate_file(path) -> FileInfo` |
| `ingest.py` | détection format + chargement pages | `load_document(path, dpi) -> LoadedDocument` |
| `preprocess.py` | qualité + opérations adaptatives | `preprocess_page(img) -> PreprocessResult` |
| `ocr_engines.py` | moteurs OCR + registre + consensus | `OCREngine.recognize(img, langs) -> EngineOutput` |
| `layout.py` | lignes, blocs, colonnes, RTL | `build_blocks(lines, w, h) -> [TextBlock]` |
| `extract_tables.py` | tableaux filets / sans filets / multipages | `extract_ruled_table(...) -> Table` |
| `extract_fields.py` | champs génériques + localisation | `extract_generic_fields(pages)` |
| `profiles.py` | profils métier JSON + validateurs | `apply_profile(text, profile)` |
| `quality.py` | confiances, anomalies | `build_quality_report(result)` |
| `exporters.py` | 6 formats de sortie | `export_all(result, dir, fmts)` |
| `storage.py` | jobs, artefacts, audit | `JobStore.create_job / update / delete` |
| `pipeline.py` | orchestration | `Pipeline.process_file(path, options)` |
| `api.py` | REST FastAPI | `POST /api/documents` … |
| `cli.py` | ligne de commande | `unocr process | serve | diagnose` |

## Modèle de confiance

```
engine_confidence  = moyenne confiance Tesseract par mot (0–1)
                     (0.95 pour la couche texte native : caractères du fichier)
quality_factor     = f(flou, dpi, contraste, éclairage) ∈ [0.5 ; 1.0]
global_confidence  = engine_confidence × quality_factor (× 0.85 si désaccord moteurs)
```

Une **valeur** porte toujours : `raw_value` (transcription), `normalized_value`,
`corrected_value` (règle métier, tracée), `confirmed_value` (humain) — la
propriété `value` renvoie la plus prioritaire disponible, la provenance étant
conservée.

## Modèle de données (extrait)

- `Word` : texte, `BBox` pixels, confiance, moteur, page
- `TextLine` / `TextBlock` : ordre, colonne, direction ltr/rtl
- `Table` / `Cell` : ligne, colonne, spans, page, bbox, confiance, méthode
- `FieldValue` : 4 niveaux de valeur, confiance moteur/globale, statut, anomalies
- `PageResult` : texte, mots, blocs, qualité, opérations de prétraitement,
  `EngineRun` par moteur (temps, confiance, erreurs)
- `DocumentResult` : infos, champs, tableaux, catégories, codes-barres,
  `QualityReport`, engines_used, timings, hash SHA-256 de la source, exports

## Extensibilité

1. **Nouveau moteur OCR** : sous-classez `OCREngine`, enregistrez dans
   `EngineRegistry` — la sélection, le consensus et la comparaison UI s'appliquent.
2. **Nouveau profil métier** : déposez un JSON dans `profiles/` — zéro code.
3. **Nouveau validateur** : ajoutez-le dans `profiles.VALIDATORS`.
4. **Nouveau format d'entrée** : ajoutez le chargeur dans `ingest.py` + signature
   magique dans `security.py`.
5. **Nouveau format de sortie** : fonction dans `exporters.py` + case dans
   `export_all`.

## Sécurité by design

- Texte extrait = **non fiable** : jamais `eval`, jamais shell, XML échappé,
  CSV/XLSX neutralisés contre les formules, injection de prompt → anomalie
  `UNTRUSTED_CONTENT` (signalée, ignorée).
- Source préservée : `data/jobs/<id>/original/` en lecture seule logique.
- Toute opération sensible (upload, validation humaine, suppression) → `logs/audit.log`.
