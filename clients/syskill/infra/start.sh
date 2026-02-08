#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIR="$(cd "$(dirname "$0")" && pwd)"

# load root env (CLIENT_NAME, optional ENV)
set -a
[ -f "$ROOT/.env" ] && source "$ROOT/.env"
set +a

export ENV="${ENV:-dev}"

if [[ "${ENV}" == "dev" && -f "$DIR/docker-compose.yml" ]]; then
  docker compose --env-file "$DIR/.env" -f "$DIR/docker-compose.yml" up -d
fi

source "$ROOT/.venv/bin/activate"
pkill -f "uvicorn app.main:app" || true
exec uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
