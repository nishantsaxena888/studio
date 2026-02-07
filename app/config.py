import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from sources.manager import SourceManager
from entities.loader import load_entities

_mgr: SourceManager | None = None
_entities: dict | None = None

def get_manager() -> SourceManager:
    global _mgr
    if _mgr is None:
        path = os.getenv("CLIENT_CONFIG_PATH", str(ROOT / "clients" / "syskill" / "client_config.json"))
        _mgr = SourceManager.from_file(path)
        _mgr.init_all()
    return _mgr

def get_entities() -> dict:
    global _entities
    if _entities is None:
        entities_path = os.getenv("ENTITIES_CONFIG_PATH", str(ROOT / "clients" / "syskill" / "entities_config.json"))
        _entities = load_entities(entities_path)
    return _entities
