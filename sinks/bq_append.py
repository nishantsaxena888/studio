from __future__ import annotations
from typing import Any, Dict
from sinks.base import Sink
from sinks.registry import register_sink

@register_sink("bq_append")
class BigQueryAppendSink(Sink):
    kind = "bq_append"

    def _client(self):
        bq_source = self.manager.get_source(self.cfg["source"])  # "analytics"
        return bq_source.client

    def _table(self) -> str:
        return self.cfg["table"]  # dataset.table

    def on_create(self, entity: str, row: Dict[str, Any]) -> None:
        bq = self._client()
        errors = bq.insert_rows_json(self._table(), [row])
        if errors:
            raise RuntimeError(f"BigQuery insert errors: {errors}")

    def on_update(self, entity: str, row: Dict[str, Any]) -> None:
        # analytics sinks are usually append-only, so also append
        self.on_create(entity, row)

    def on_delete(self, entity: str, id_value: Any) -> None:
        # typically no-op
        pass
