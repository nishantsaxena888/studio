import os

ENV = os.getenv("ENV", "dev")  # dev | prod | cloud

def env(name: str, default=None, *, required: bool = False):
    val = os.getenv(name, default)
    if required and (val is None or val == ""):
        raise RuntimeError(f"Missing required env var: {name}")
    return val

ROUTING = {
    "active_source": "db_main",
    "search_source": "search_main",
}

if ENV == "dev":
    # Out-of-the-box local config
    SOURCES = {
        "db_main": {
            "kind": "postgres",
            "enabled": True,
            "host": "localhost",
            "port": 5432,
            "database": "appdb",
            "username": "app",
            "password": "app",
            "reflect": True,
            "connect": {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20},
        },
        "search_main": {
            "kind": "elasticsearch",
            "enabled": True,
            "hosts": ["http://localhost:9200"],
            "connect": {"request_timeout": 30, "max_retries": 3, "retry_on_timeout": True},
        },
    }
else:
    # Cloud/prod config (endpoints from env; creds via env names)
    SOURCES = {
        "db_main": {
            "kind": "postgres",
            "enabled": True,
            "host": env("DB_HOST", required=True),
            "port": int(env("DB_PORT", 5432)),
            "database": env("DB_NAME", "appdb"),
            "username_env": "DB_USER",
            "password_env": "DB_PASSWORD",
            "reflect": True,
            "connect": {"pool_pre_ping": True},
        },
        "search_main": {
            "kind": "elasticsearch",
            "enabled": True,
            "hosts": [env("ES_HOST", required=True)],
            "username_env": "ES_USER",
            "password_env": "ES_PASSWORD",
            "connect": {"request_timeout": int(env("ES_TIMEOUT", 30))},
        },
    }
