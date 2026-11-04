#!/usr/bin/env bash
# UniOCR — lancement du serveur API + interface web
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:src"
HOST="${UNOCR_HOST:-127.0.0.1}"
PORT="${UNOCR_PORT:-8000}"
echo "UniOCR → http://${HOST}:${PORT}  (UI + API /docs)"
exec python3 -m unocr.cli serve --host "$HOST" --port "$PORT"
