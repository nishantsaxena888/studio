import os
from typing import Any, Dict
from elasticsearch import Elasticsearch
from sources.base import BaseSource
from sources.registry import register_source

@register_source("elasticsearch")
class ElasticsearchSource(BaseSource):
    kind = "elasticsearch"

    def connect(self) -> None:
        hosts = self.cfg["hosts"]
        auth_cfg = self.cfg.get("auth", {})

        user = os.getenv(auth_cfg.get("username_env", ""), "")
        pwd  = os.getenv(auth_cfg.get("password_env", ""), "")
        basic_auth = (user, pwd) if (user or pwd) else None

        connect_cfg = self.cfg.get("connect", {})
        self.client = Elasticsearch(hosts, basic_auth=basic_auth, **connect_cfg)

    def get_handle(self):
        return self.client

    def health(self) -> Dict[str, Any]:
        try:
            info = self.client.info()
            return {"ok": True, "kind": self.kind, "name": self.name, "cluster": info.get("cluster_name")}
        except Exception as e:
            return {"ok": False, "kind": self.kind, "name": self.name, "error": str(e)}

    def close(self) -> None:
        if getattr(self, "client", None):
            self.client.close()
