import os
from typing import Any, Dict
from sqlalchemy import create_engine, MetaData
from sources.base import BaseSource
from sources.registry import register_source

@register_source("postgres")
class PostgresSource(BaseSource):
    kind = "postgres"

    def connect(self) -> None:
        host = self.cfg["host"]
        port = self.cfg.get("port", 5432)
        db = self.cfg["database"]

        user = os.getenv(self.cfg.get("username_env", ""), "")
        pwd  = os.getenv(self.cfg.get("password_env", ""), "")

        dialect = self.cfg.get("dialect", "postgresql")
        driver  = self.cfg.get("driver", "psycopg")  # psycopg or psycopg2
        url = f"{dialect}+{driver}://{user}:{pwd}@{host}:{port}/{db}"

        connect_cfg = self.cfg.get("connect", {})
        self.engine = create_engine(url, **connect_cfg)

        # reflect metadata if you want out-of-box
        self.meta = MetaData()
        if self.cfg.get("reflect", True):
            self.meta.reflect(bind=self.engine)

    def get_handle(self):
        return self.engine

    def health(self) -> Dict[str, Any]:
        try:
            with self.engine.connect() as c:
                c.exec_driver_sql("select 1")
            return {"ok": True, "kind": self.kind, "name": self.name}
        except Exception as e:
            return {"ok": False, "kind": self.kind, "name": self.name, "error": str(e)}

    def close(self) -> None:
        if getattr(self, "engine", None):
            self.engine.dispose()
