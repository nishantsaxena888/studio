from typing import Any, Dict
from google.cloud import bigquery
from sources.base import BaseSource
from sources.registry import register_source

@register_source("bigquery")
class BigQuerySource(BaseSource):
    kind = "bigquery"

    def connect(self) -> None:
        project = self.cfg.get("project")
        self.client = bigquery.Client(project=project)

    def get_handle(self):
        return self.client

    def health(self) -> Dict[str, Any]:
        try:
            _ = list(self.client.list_datasets(max_results=1))
            return {"ok": True, "kind": self.kind, "name": self.name}
        except Exception as e:
            return {"ok": False, "kind": self.kind, "name": self.name, "error": str(e)}
