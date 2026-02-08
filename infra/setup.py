import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import os
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _read_root_env():
    p = ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

def main():
    _read_root_env()

    client = os.getenv("CLIENT_NAME", "").strip()
    if not client:
        raise SystemExit("CLIENT_NAME missing. Put CLIENT_NAME=syskill in root .env")

    mod = importlib.import_module(f"clients.{client}.env")
    env_mode = getattr(mod, "ENV", os.getenv("ENV", "dev"))
    sources = getattr(mod, "SOURCES")

    out = ROOT / "clients" / client / "infra"
    out.mkdir(parents=True, exist_ok=True)

    # Default: generate scripts always
    (out / "start.sh").write_text(f"""#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIR="$(cd "$(dirname "$0")" && pwd)"

# load root env (CLIENT_NAME, optional ENV)
set -a
[ -f "$ROOT/.env" ] && source "$ROOT/.env"
set +a

export ENV="${{ENV:-dev}}"

if [[ "${{ENV}}" == "dev" && -f "$DIR/docker-compose.yml" ]]; then
  docker compose --env-file "$DIR/.env" -f "$DIR/docker-compose.yml" up -d
fi

source "$ROOT/.venv/bin/activate"
pkill -f "uvicorn app.main:app" || true
exec uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
""")

    (out / "up.sh").write_text("""#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
docker compose --env-file "$DIR/.env" -f "$DIR/docker-compose.yml" up -d
""")

    (out / "down.sh").write_text("""#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
docker compose --env-file "$DIR/.env" -f "$DIR/docker-compose.yml" down
""")

    # Only generate docker compose for dev/local
    if env_mode == "dev":
        enable_pg = any(cfg.get("enabled", True) and cfg.get("kind") == "postgres" for cfg in sources.values())
        enable_es = any(cfg.get("enabled", True) and cfg.get("kind") == "elasticsearch" for cfg in sources.values())

        env_lines = [f"COMPOSE_PROJECT_NAME={client}"]
        services = []

        if enable_pg:
            env_lines += [
                "PG_IMAGE=postgres:16",
                "PG_PORT=5432",
                "PG_DB=appdb",
                "PG_USER=app",
                "PG_PASSWORD=app",
                f"PG_VOLUME_NAME={client}_pg_data",
            ]
            services.append("""  postgres:
    image: ${PG_IMAGE}
    container_name: ${COMPOSE_PROJECT_NAME}-postgres
    restart: unless-stopped
    ports:
      - "${PG_PORT}:5432"
    environment:
      POSTGRES_DB: ${PG_DB}
      POSTGRES_USER: ${PG_USER}
      POSTGRES_PASSWORD: ${PG_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
""")

        if enable_es:
            env_lines += [
                "ES_IMAGE=docker.elastic.co/elasticsearch/elasticsearch:8.13.4",
                "ES_PORT=9200",
                f"ES_VOLUME_NAME={client}_es_data",
                "ES_XPACK_SECURITY_ENABLED=false",
                "ES_JAVA_OPTS=-Xms1g -Xmx1g",
            ]
            services.append("""  elasticsearch:
    image: ${ES_IMAGE}
    container_name: ${COMPOSE_PROJECT_NAME}-es
    restart: unless-stopped
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=${ES_XPACK_SECURITY_ENABLED}
      - ES_JAVA_OPTS=${ES_JAVA_OPTS}
    ports:
      - "${ES_PORT}:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
""")

        (out / ".env").write_text("\n".join(env_lines) + "\n")

        vols = ["volumes:"]
        if enable_pg:
            vols.append("  pg_data:\n    name: ${PG_VOLUME_NAME}")
        if enable_es:
            vols.append("  es_data:\n    name: ${ES_VOLUME_NAME}")

        (out / "docker-compose.yml").write_text(
            "name: ${COMPOSE_PROJECT_NAME}\n\nservices:\n"
            + "".join(services)
            + "\n"
            + "\n".join(vols)
            + "\n"
        )
    else:
        # prod: no compose needed, but keep a tiny .env so scripts don't fail
        (out / ".env").write_text(f"COMPOSE_PROJECT_NAME={client}\n")

    print(f"✅ Generated: {out}")
    print(f"Next:\n  chmod +x {out}/*.sh\n  ENV=dev {out}/start.sh")

if __name__ == "__main__":
    main()
