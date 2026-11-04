#!/usr/bin/env bash
# UniOCR — installation complète (Debian/Ubuntu)
set -euo pipefail

echo "== 1/3 Dépendances système =="
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  tesseract-ocr tesseract-ocr-osd \
  tesseract-ocr-fra tesseract-ocr-eng tesseract-ocr-ara tesseract-ocr-spa \
  tesseract-ocr-deu tesseract-ocr-ita tesseract-ocr-por tesseract-ocr-tur \
  tesseract-ocr-rus tesseract-ocr-chi-sim \
  poppler-utils

echo "== 2/3 Dépendances Python =="
python3 -m pip install -r requirements.txt

echo "== 3/3 Vérification =="
PYTHONPATH=src python3 -m unocr.cli diagnose
PYTHONPATH=src python3 -m pytest tests/ -q

echo "Installation terminée. Lancer : ./scripts/run_server.sh"
