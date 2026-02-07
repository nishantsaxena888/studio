#!/usr/bin/env bash
set -e

APP_ROOT="$(cd "$(dirname "$0")" && pwd)"

cd "$APP_ROOT"

# activate venv
source .venv/bin/activate

# load env
set -a
source .env
set +a

# kill existing uvicorn (if any)
pkill -f "uvicorn app.main:app" || true

# start uvicorn
exec uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
