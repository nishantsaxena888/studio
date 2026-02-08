#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_ROOT"

# load root env (ONLY CLIENT_NAME + optional ENV)
set -a
[ -f ".env" ] && source ".env"
set +a

if [[ -z "${CLIENT_NAME:-}" ]]; then
  echo "❌ CLIENT_NAME not set in .env"
  exit 1
fi

CLIENT_START="$APP_ROOT/clients/$CLIENT_NAME/infra/start.sh"

if [[ ! -f "$CLIENT_START" ]]; then
  echo "❌ Client infra not generated for '$CLIENT_NAME'"
  echo "👉 Run: python infra/setup.py"
  exit 1
fi

exec "$CLIENT_START"
