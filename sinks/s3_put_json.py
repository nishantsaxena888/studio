from __future__ import annotations
import json
from typing import Any, Dict
from sinks.base import Sink
from sinks.registry import register_sink

@register_sink("s3_put_json")
class S3PutJsonSink(Sink):
    kind = "s3_put_json"

    def _client(self):
        s3_source = self.manager.get_source(self.cfg["source"])  # "files"
        return s3_source.client

    def _bucket(self) -> str:
        return self.cfg["bucket"]

    def _key(self, entity: str, row: Dict[str, Any]) -> str:
        pattern = self.cfg.get("key_pattern", "{entity}/{id}.json")
        id_key = self.cfg.get("id_key", "id")
        return pattern.format(entity=entity, id=row.get(id_key))

    def on_create(self, entity: str, row: Dict[str, Any]) -> None:
        s3 = self._client()
        s3.put_object(
            Bucket=self._bucket(),
            Key=self._key(entity, row),
            Body=json.dumps(row).encode("utf-8"),
            ContentType="application/json",
        )

    def on_update(self, entity: str, row: Dict[str, Any]) -> None:
        self.on_create(entity, row)

    def on_delete(self, entity: str, id_value: Any) -> None:
        # optional: delete object if you want
        pass
