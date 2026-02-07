from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class JoinSpec:
    type: str
    table: str
    alias: str
    on_left: str
    on_right: str

@dataclass
class EntitySpec:
    name: str
    source: str
    crud: str
    table: Optional[str]
    pk: str

    # read
    fields: Dict[str, str]          # key -> "table_or_alias.col"
    joins: List[JoinSpec]
    search_keys: List[str]

    # write
    write_mode: str
    allowed_write_keys: List[str]

    custom_query_id: Optional[str] = None

def parse_entity_spec(name: str, cfg: Dict[str, Any]) -> EntitySpec:
    storage = cfg.get("storage", {})
    read = cfg.get("read", {})
    write = cfg.get("write", {})

    joins_cfg = read.get("joins", [])
    joins: List[JoinSpec] = []
    for j in joins_cfg:
        joins.append(
            JoinSpec(
                type=j.get("type", "left"),
                table=j["table"],
                alias=j.get("alias") or j["table"],
                on_left=j["on"][0],
                on_right=j["on"][1],
            )
        )

    return EntitySpec(
        name=name,
        source=storage["source"],
        crud=storage.get("crud", "sql_row"),
        table=storage.get("table"),
        pk=storage.get("pk", "id"),

        fields=read.get("fields", {}),
        joins=joins,
        search_keys=read.get("search", []),

        write_mode=write.get("mode", "default"),
        allowed_write_keys=write.get("allowed", []),

        custom_query_id=read.get("custom_query_id"),
    )
