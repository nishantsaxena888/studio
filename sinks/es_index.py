from __future__ import annotations
from typing import Any, Dict
from sinks.base import Sink
from sinks.registry import register_sink

@register_sink("es_index")
class ElasticsearchIndexSink(Sink):
    kind = "es_index"

    def _client(self):
        source_name = self.cfg["source"]  # e.g. "search_main"
        es_source = self.manager.get_source(source_name)
        return es_source.client

    def _index_name(self, entity: str) -> str:
        # per-entity override else pattern
        return self.cfg.get("index") or f"{entity}_index"

    def _doc(self, entity: str, row: Dict[str, Any]) -> Dict[str, Any]:
        # allow choosing subset of fields
        fields = self.cfg.get("fields")
        if fields:
            return {k: row.get(k) for k in fields}
        return row

    def on_create(self, entity: str, row: Dict[str, Any]) -> None:
        es = self._client()
        idx = self._index_name(entity)
        doc_id_key = self.cfg.get("id_key", "id")
        es.index(index=idx, id=str(row[doc_id_key]), document=self._doc(entity, row))

    def on_update(self, entity: str, row: Dict[str, Any]) -> None:
        # same as create => upsert
        self.on_create(entity, row)

    def on_delete(self, entity: str, id_value: Any) -> None:
        es = self._client()
        idx = self._index_name(entity)
        es.delete(index=idx, id=str(id_value), ignore=[404])
