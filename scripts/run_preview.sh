#!/usr/bin/env bash
# UniOCR — serveur UI + API pour un aperçu navigateur (bac à sable distant).
#
# Différences avec scripts/run_server.sh, strictement limitées à l'aperçu :
#   - écoute sur 0.0.0.0 (le proxy d'aperçu joint le port depuis l'extérieur) ;
#   - UNOCR_PREVIEW=1 autorise l'hôte *.e2b.app et l'affichage en iframe.
# Le déploiement réel doit continuer d'utiliser run_server.sh (127.0.0.1,
# X-Frame-Options DENY).
set -euo pipefail
cd "$(dirname "$0")/.."

export PYTHONPATH="${PYTHONPATH:-}:src"
export UNOCR_PREVIEW="${UNOCR_PREVIEW:-1}"

HOST="${UNOCR_HOST:-0.0.0.0}"
PORT="${UNOCR_PORT:-8000}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "UniOCR (aperçu) → http://${HOST}:${PORT}  (UI + API /docs)"
exec "$PYTHON_BIN" -m unocr.cli serve --host "$HOST" --port "$PORT"
