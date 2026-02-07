from typing import Dict, Type
from sinks.base import Sink

SINK_REGISTRY: Dict[str, Type[Sink]] = {}

def register_sink(kind: str):
    def decorator(cls: Type[Sink]):
        SINK_REGISTRY[kind] = cls
        return cls
    return decorator
