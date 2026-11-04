# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install system dependencies (Debian/Ubuntu)
sudo apt-get install -y tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng \
    tesseract-ocr-ara tesseract-ocr-spa tesseract-ocr-deu tesseract-ocr-ita \
    tesseract-ocr-por tesseract-ocr-tur tesseract-ocr-rus tesseract-ocr-chi-sim \
    tesseract-ocr-osd poppler-utils libzbar0

# Install Python dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -q

# Run single test
python -m pytest tests/test_specific.py -q

# Start API server + UI
./scripts/run_server.sh          # UI: http://localhost:8000  ·  API: /docs

# Run benchmarks
./benchmarks/run_all.sh

# CLI usage
PYTHONPATH=src python -m unocr.cli process document.pdf --profile port_bl --export json,txt,xlsx
PYTHONPATH=src python -m unocr.cli diagnose
```

## Architecture

**UniOCR** — Universal OCR engine transforming heterogeneous documents (PDF, images, DOCX, ODT, etc.) into structured data (text, structure, fields, tables, barcodes).

**Stack**: Python 3.13, FastAPI, Uvicorn, Tesseract 5.5, pdfminer.six, pypdfium2, OpenCV, zxing-cpp, FastAPI/Uvicorn, vanilla HTML/JS/CSS frontend.

**Architecture** (`src/unocr/`):
```
unocr/
├── models.py         # Pydantic models: Document, Page, Word, Table, Field, Anomaly
├── config.py         # Configuration (JSON), paths, limits
├── logging_setup.py  # Structured logging + audit
├── security.py       # Validation, zip-bomb, filename sanitization, anti-injection
├── ingest.py         # Format detection + loading (PDF, images, DOCX, ODT, TXT, RTF, CSV, XLSX)
├── preprocess.py     # Quality analysis + selected ops + variant comparison
├── ocr_engines.py    # OCR interface + Tesseract + PDF native + registry + selection + consensus
├── layout.py         # Columns, reading order, RTL, word→line→block grouping
├── extract_fields.py # Generic fields (dates, amounts, emails, phones, IBAN, IDs)
├── extract_tables.py # Tables with/without borders, multipage, merged cells
├── profiles.py       # Business profiles + validators (ISO 6346, Luhn, IBAN, dates)
├── quality.py        # Engine/global confidence, anomalies, consistency checks
├── exporters.py      # TXT, JSON, CSV, XLSX, XML, PDF (with invisible text layer)
├── storage.py        # Jobs (creation, state, resume), artifacts, audit log
├── pipeline.py       # Orchestrator: ingest → preprocess → OCR → layout → extract → quality → export
└── api.py            # REST API FastAPI + UI serving
```

**Flow**: `ingest → preprocess → ocr_engines → layout → extract_* → quality → exporters → storage`

**Constraints**: 2 CPU cores, 2GB RAM, no GPU → Tesseract only (EasyOCR/PaddleOCR optional adapters), no CUDA, no handwriting transcription.

## Development

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
mypy src/
```

## Key Files

- `PLAN.md` — Implementation plan, audit, architecture decisions
- `docs/ARCHITECTURE.md` — Detailed architecture
- `docs/LIMITATIONS.md` — Known limitations
- `src/unocr/config.py` — Central configuration
- `src/unocr/pipeline.py` — Main orchestration logic
- `web/index.html` — Main UI entry point
- `styles.css` — All styling
- `src/unocr/pipeline.py` — Main orchestration entry point

## Testing

```bash
# Run all tests
python -m pytest tests/ -q

# Run with coverage
python -m pytest tests/ --cov=src/unocr --cov-report=term-missing

# UI stub check
node tests/ui_stub_check.js
```

## Key Principles

1. **No unimplemented features declared operational** — everything must be implemented and tested
2. **Measured benchmarks only** — CER/WER on generated test set with ground truth
3. **No GPU/ML dependencies** — Tesseract only, EasyOCR/PaddleOCR as optional runtime adapters
4. **Security first** — zip-bomb protection, filename sanitization, CSV/XLSX formula injection prevention, audit logging
5. **Offline-first** — 100% local, no external dependencies at runtime
6. **Traceability** — JSONL audit log, human validation tracked
7. **Modular architecture** — each module has pure interfaces, tested in isolation