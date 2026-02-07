from typing import Any, Callable, Dict

QUERY_REGISTRY: Dict[str, Callable[..., Any]] = {}

def register_query(query_id: str):
    def deco(fn):
        QUERY_REGISTRY[query_id] = fn
        return fn
    return deco
