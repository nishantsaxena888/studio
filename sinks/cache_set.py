from __future__ import annotations
from typing import Any, Dict
from sinks.base import Sink
from sinks.registry import register_sink

@register_sink("cache_set")
class CacheSetSink(Sink):
    kind = "cache_set"

    def on_create(self, entity: str, row: Dict[str, Any]) -> None:
        # plug redis/memcached later
        return

    def on_update(self, entity: str, row: Dict[str, Any]) -> None:
        return

    def on_delete(self, entity: str, id_value: Any) -> None:
        return
