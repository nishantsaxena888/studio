import json

# register built-in sources
import sources.connect.postgres  # noqa: F401
import sources.connect.elasticsearch  # noqa: F401
import sources.connect.s3  # noqa: F401
import sources.connect.bigquery  # noqa: F401
import sources.connect.firebase  # noqa: F401


# register built-in sources
import sources.connect.postgres  # noqa: F401
import sources.connect.elasticsearch  # noqa: F401
import sources.connect.s3  # noqa: F401
import sources.connect.bigquery  # noqa: F401
import sources.connect.firebase  # noqa: F401

from typing import Any, Dict
from sources.registry import SOURCE_REGISTRY

class SourceManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sources: Dict[str, Any] = {}

    @classmethod
    def from_file(cls, path: str) -> "SourceManager":
        with open(path, "r") as f:
            return cls(json.load(f))

    def init_all(self) -> None:
        for name, cfg in self.config.get("sources", {}).items():
            if not cfg.get("enabled", True):
                continue
            kind = cfg["kind"]
            if kind not in SOURCE_REGISTRY:
                raise ValueError(f"Unknown source kind: {kind}")
            src = SOURCE_REGISTRY[kind](name=name, cfg=cfg)
            src.connect()
            self.sources[name] = src

    def get_source(self, name: str):
        return self.sources[name]

    def active(self):
        key = self.config["routing"]["active_source"]
        return self.sources[key]

    def search(self):
        key = self.config["routing"].get("search_source")
        return self.sources[key] if key else None

    def health(self) -> Dict[str, Any]:
        return {k: v.health() for k, v in self.sources.items()}

    def close(self) -> None:
        for s in self.sources.values():
            s.close()
