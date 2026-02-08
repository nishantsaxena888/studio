#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_ROOT"

# load root env (ONLY CLIENT_NAME + optional ENV / APP_PORT)
set -a
[ -f ".env" ] && source ".env"
set +a

if [[ -z "${CLIENT_NAME:-}" ]]; then
  echo "❌ CLIENT_NAME not set in .env"
  exit 1
fi

export ENV="${ENV:-dev}"
export APP_PORT="${APP_PORT:-8000}"

# ---------- helpers ----------
port_in_use_by_docker() {
  local port="$1"
  docker ps --format '{{.Ports}}' | grep -qE "(^|, )0\.0\.0\.0:${port}->|(\[::\]):${port}->"
}

port_in_use_local() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  return 1
}

pick_free_port() {
  local start="${1:-8000}"
  local end="${2:-8010}"
  local p
  for ((p=start; p<=end; p++)); do
    if ! port_in_use_local "$p"; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

wait_http() {
  local url="$1"
  local tries="${2:-60}"   # 60 * 0.25s = ~15s
  local i=1
  while (( i <= tries )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
    i=$((i+1))
  done
  return 1
}
# --------------------------------

start_app_with_postcheck() {
  local port="$1"
  local health_url="http://127.0.0.1:${port}/health/sources"

  echo "🚀 Starting app: http://127.0.0.1:${port}"
  echo "🔎 Will check source health after start: $health_url"

  # Start uvicorn in background so we can hit health after it's up
  uvicorn app.main:app --host 127.0.0.1 --port "$port" --reload &
  UVICORN_PID=$!

  if wait_http "$health_url" 60; then
    echo "✅ Sources health:"
    curl -s "$health_url" | python -m json.tool
  else
    echo "⚠️ Health endpoint not ready yet: $health_url"
  fi

  wait "$UVICORN_PID"
}

# -------- reuse existing infra if present --------
if [[ "${ENV}" == "dev" ]]; then
  PG_BUSY=0
  ES_BUSY=0

  if port_in_use_by_docker 5432; then PG_BUSY=1; fi
  if port_in_use_by_docker 9200; then ES_BUSY=1; fi

  if [[ "$PG_BUSY" == "1" && "$ES_BUSY" == "1" ]]; then
    echo "✅ Detected Postgres(5432) + ES(9200) already running. Reusing existing infra."

    # resolve APP_PORT clash
    if port_in_use_local "$APP_PORT"; then
      echo "⚠️ APP_PORT=${APP_PORT} already in use. Selecting a free port..."
      APP_PORT="$(pick_free_port 8000 8010)"
      if [[ -z "${APP_PORT:-}" ]]; then
        echo "❌ No free app port available (8000–8010)"
        exit 1
      fi
      echo "✅ Using APP_PORT=${APP_PORT}"
    fi

    source "$APP_ROOT/.venv/bin/activate"
    pkill -f "uvicorn" || true

    # start + hit health after start
    start_app_with_postcheck "$APP_PORT"
    exit 0
  fi
fi
# -----------------------------------------------

CLIENT_INFRA_DIR="$APP_ROOT/clients/$CLIENT_NAME/infra"
CLIENT_START="$CLIENT_INFRA_DIR/start.sh"

# -------- generate client infra if missing --------
if [[ ! -f "$CLIENT_START" ]]; then
  echo "ℹ️ Client infra missing for '$CLIENT_NAME' → generating via infra/setup.py"

  PY="$APP_ROOT/.venv/bin/python"
  if [[ ! -x "$PY" ]]; then
    PY="$(command -v python3 || command -v python || true)"
  fi
  if [[ -z "${PY:-}" ]]; then
    echo "❌ python not found"
    exit 1
  fi
  if [[ ! -f "$APP_ROOT/infra/setup.py" ]]; then
    echo "❌ infra/setup.py not found"
    exit 1
  fi

  "$PY" "$APP_ROOT/infra/setup.py"
  chmod +x "$CLIENT_INFRA_DIR"/*.sh 2>/dev/null || true
fi
# -----------------------------------------------

if [[ ! -f "$CLIENT_START" ]]; then
  echo "❌ Still missing $CLIENT_START after generation"
  exit 1
fi

echo "ℹ️ Delegating to client start: $CLIENT_START"
echo "🔎 After start, check: curl -s http://127.0.0.1:${APP_PORT}/health/sources | python -m json.tool"

exec "$CLIENT_START"


