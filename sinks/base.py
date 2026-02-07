from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class Sink(ABC):
    kind: str

    def __init__(self, name: str, cfg: Dict[str, Any], manager):
        self.name = name
        self.cfg = cfg
        self.manager = manager  # SourceManager

    @abstractmethod
    def on_create(self, entity: str, row: Dict[str, Any]) -> None: ...

    @abstractmethod
    def on_update(self, entity: str, row: Dict[str, Any]) -> None: ...

    @abstractmethod
    def on_delete(self, entity: str, id_value: Any) -> None: ...
