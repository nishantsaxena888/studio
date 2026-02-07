from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseSource(ABC):
    kind: str

    def __init__(self, name: str, cfg: Dict[str, Any]):
        self.name = name
        self.cfg = cfg

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def health(self) -> Dict[str, Any]: ...

    def close(self) -> None:
        pass

    def get_handle(self) -> Any:
        raise NotImplementedError
