#!/usr/bin/env bash
# Works even if invoked as: sh start.sh
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_ROOT"

# root env: CLIENT_NAME (+ optional ENV)
set -a
[ -f ".env" ] && source ".env"
set +a

CLIENT_NAME="${CLIENT_NAME:-syskill}"
ENV="${ENV:-dev}"
APP_PORT=8000

INFRA_DIR="$APP_ROOT/clients/$CLIENT_NAME/infra"
COMPOSE_FILE="$INFRA_DIR/docker-compose.yml"

die(){ echo "❌ $*"; exit 1; }
info(){ echo "ℹ️ $*"; }
ok(){ echo "✅ $*"; }

need(){ command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"; }
need docker
need curl

# ---------- docker helpers ----------
exists_container() {
  local name="$1"
  docker ps -a --format '{{.Names}}' | grep -qx "$name"
}

is_running() {
  local name="$1"
  docker ps --format '{{.Names}}' | grep -qx "$name"
}

start_container() {
  local name="$1"
  docker start "$name" >/dev/null
}

container_using_host_port() {
  local port="$1"
  docker ps --format '{{.ID}}\t{{.Ports}}' | awk -v p=":${port}->" '$0 ~ p {print $1}'
}

kill_container_ids() {
  local ids="$1"
  [[ -n "$ids" ]] || return 0
  info "Removing conflicting docker container(s): $ids"
  # shellcheck disable=SC2086
  docker rm -f $ids >/dev/null 2>&1 || true
}

ensure_infra_compose() {
  if [[ ! -f "$COMPOSE_FILE" ]]; then
    if [[ -f "$APP_ROOT/infra/setup.py" ]]; then
      info "Infra compose missing → generating via infra/setup.py (CLIENT_NAME=$CLIENT_NAME)"
      local PY="$APP_ROOT/.venv/bin/python"
      if [[ ! -x "$PY" ]]; then PY="$(command -v python3 || command -v python || true)"; fi
      [[ -n "${PY:-}" ]] || die "python not found"
      "$PY" "$APP_ROOT/infra/setup.py"
      chmod +x "$INFRA_DIR"/*.sh 2>/dev/null || true
    else
      die "Missing $COMPOSE_FILE and infra/setup.py not found"
    fi
  fi
}
# -----------------------------------

# ---------- local port kill (uvicorn only) ----------
kill_local_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      info "Killing local process(es) on port ${port}: $pids"
      # shellcheck disable=SC2086
      kill -9 $pids >/dev/null 2>&1 || true
    fi
  fi
}
# -----------------------------------

# ---------- INFRA LOGIC (exactly as you asked) ----------
if [[ "$ENV" == "dev" ]]; then
  ensure_infra_compose

  EXPECT_PG="syskill-postgres"
  EXPECT_ES="syskill-es"

  # 1) If expected containers exist:
  #    - running: do nothing
  #    - stopped: start them
  if exists_container "$EXPECT_PG"; then
    if is_running "$EXPECT_PG"; then
      ok "$EXPECT_PG already running (reuse)."
    else
      info "$EXPECT_PG exists but stopped → starting..."
      start_container "$EXPECT_PG"
      ok "$EXPECT_PG started."
    fi
  fi

  if exists_container "$EXPECT_ES"; then
    if is_running "$EXPECT_ES"; then
      ok "$EXPECT_ES already running (reuse)."
    else
      info "$EXPECT_ES exists but stopped → starting..."
      start_container "$EXPECT_ES"
      ok "$EXPECT_ES started."
    fi
  fi

  # 2) If both expected are now running, infra done.
  if is_running "$EXPECT_PG" && is_running "$EXPECT_ES"; then
    ok "Infra OK (expected containers running)."
  else
    # 3) Otherwise expected missing (or only one). Now ensure ports are free by killing ONLY conflicts.
    CONFLICT_PG="$(container_using_host_port 5432 || true)"
    CONFLICT_ES="$(container_using_host_port 9200 || true)"

    # if conflict exists and it's NOT our expected container(s), remove it
    if [[ -n "$CONFLICT_PG" ]] && ! is_running "$EXPECT_PG"; then
      kill_container_ids "$CONFLICT_PG"
    fi
    if [[ -n "$CONFLICT_ES" ]] && ! is_running "$EXPECT_ES"; then
      kill_container_ids "$CONFLICT_ES"
    fi

    info "Starting infra fresh via docker compose..."
    docker compose -f "$COMPOSE_FILE" up -d
    ok "Infra started."
  fi
fi
# ------------------------------------------------------

# ---------- APP (uvicorn fixed port; kill if busy) ----------
kill_local_port "$APP_PORT"
pkill -f "uvicorn" >/dev/null 2>&1 || true

source "$APP_ROOT/.venv/bin/activate"

HEALTH_URL="http://127.0.0.1:${APP_PORT}/health/sources"
info "Starting app on http://127.0.0.1:${APP_PORT}"
uvicorn app.main:app --host 127.0.0.1 --port "$APP_PORT" --reload &
UVICORN_PID=$!

info "Waiting for: $HEALTH_URL"
for i in $(seq 1 80); do
  if OUT="$(curl -fsS "$HEALTH_URL" 2>/dev/null)"; then
    ok "Sources health:"
    echo "$OUT" | python -m json.tool
    break
  fi
  sleep 0.25
done

wait "$UVICORN_PID"
