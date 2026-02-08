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

        # ---------- creds ----------
        user = ""
        pwd = ""

        if self.cfg.get("username_env"):
            user = os.getenv(self.cfg["username_env"], "")
        if self.cfg.get("password_env"):
            pwd = os.getenv(self.cfg["password_env"], "")

        if not user and not pwd:
            auth_cfg = self.cfg.get("auth", {}) or {}
            if auth_cfg.get("username_env"):
                user = os.getenv(auth_cfg["username_env"], "")
            if auth_cfg.get("password_env"):
                pwd = os.getenv(auth_cfg["password_env"], "")

        if not user:
            user = self.cfg.get("username", "")
        if not pwd:
            pwd = self.cfg.get("password", "")

        basic_auth = (user, pwd) if (user and pwd) else None

        connect_cfg = dict(self.cfg.get("connect", {}))

        self.client = Elasticsearch(
            hosts,
            basic_auth=basic_auth,
            **connect_cfg,
        )

        # ---------- detect OpenSearch ----------
        try:
            info = self.client.info()
            version = info.get("version", {})
            dist = version.get("distribution") or version.get("build_flavor")

            self.distribution = "opensearch" if dist == "opensearch" else "elasticsearch"
        except Exception:
            self.distribution = "unknown"

    def get_handle(self):
        return self.client

    def health(self) -> Dict[str, Any]:
        try:
            info = self.client.info()
            return {
                "ok": True,
                "kind": self.kind,
                "name": self.name,
                "distribution": getattr(self, "distribution", "unknown"),
                "cluster": info.get("cluster_name"),
            }
        except Exception as e:
            return {
                "ok": False,
                "kind": self.kind,
                "name": self.name,
                "error": str(e),
            }

    def close(self) -> None:
        if getattr(self, "client", None):
            self.client.close()
