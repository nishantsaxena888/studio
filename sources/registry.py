from typing import Dict, Type
from sources.base import BaseSource

SOURCE_REGISTRY: Dict[str, Type[BaseSource]] = {}

def register_source(kind: str):
    def decorator(cls: Type[BaseSource]):
        SOURCE_REGISTRY[kind] = cls
        return cls
    return decorator
