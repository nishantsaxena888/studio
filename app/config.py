import os
import importlib
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")  # root .env: only CLIENT_NAME (and optionally ENV)

from sources.manager import SourceManager
from entities.loader import load_entities

_mgr: SourceManager | None = None
_entities: dict | None = None


def _client_name() -> str:
    name = os.getenv("CLIENT_NAME", "").strip()
    if not name:
        raise RuntimeError("CLIENT_NAME missing in root .env (expected CLIENT_NAME=syskill)")
    return name


def _client_env_module():
    client = _client_name()
    # expects clients/<client>/env.py
    return importlib.import_module(f"clients.{client}.env")


def get_manager() -> SourceManager:
    global _mgr
    if _mgr is None:
        mod = _client_env_module()
        sources = getattr(mod, "SOURCES", None)
        routing = getattr(mod, "ROUTING", None)

        if not isinstance(sources, dict) or not isinstance(routing, dict):
            raise RuntimeError(f"clients/{_client_name()}/env.py must define SOURCES and ROUTING dicts")

        cfg = {
            "client_name": _client_name(),
            "env": getattr(mod, "ENV", os.getenv("ENV", "dev")),
            "routing": routing,
            "sources": sources,
        }

        _mgr = SourceManager.from_dict(cfg)
        _mgr.init_all()
    return _mgr


def get_entities() -> dict:
    global _entities
    if _entities is None:
        # keep existing entities_config.json for now (no refactor needed)
        client = _client_name()
        entities_path = ROOT / "clients" / client / "entities_config.json"
        _entities = load_entities(str(entities_path))
    return _entities
