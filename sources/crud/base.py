from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class CrudBackend(ABC):
    @abstractmethod
    def create(self, entity: str, data: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def get_one(self, entity: str, id_value: Any) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def update(self, entity: str, id_value: Any, data: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def delete(self, entity: str, id_value: Any) -> Dict[str, Any]: ...

    @abstractmethod
    def list(self, entity: str, *, page: int, size: int, q: Optional[str]=None, filters: Optional[Dict[str, Any]]=None) -> Dict[str, Any]:
        """return { items: [...], total: N }"""
