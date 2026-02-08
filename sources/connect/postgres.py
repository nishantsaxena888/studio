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

        # ✅ Support BOTH:
        # - dev/local: inline username/password in cfg
        # - prod/cloud: username_env/password_env pointing to env var names
        if "username_env" in self.cfg and self.cfg["username_env"]:
            user = os.getenv(self.cfg["username_env"], "")
        else:
            user = self.cfg.get("username", "")

        if "password_env" in self.cfg and self.cfg["password_env"]:
            pwd = os.getenv(self.cfg["password_env"], "")
        else:
            pwd = self.cfg.get("password", "")

        # ✅ Fail fast (avoid silent blank creds)
        if user == "" or pwd == "":
            raise RuntimeError(
                f"Postgres creds missing for source '{self.name}'. "
                f"Provide username/password (dev) OR set env vars via username_env/password_env (prod)."
            )

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
