import os
from typing import Any, Dict
import firebase_admin
from firebase_admin import credentials
from sources.base import BaseSource
from sources.registry import register_source

@register_source("firebase")
class FirebaseSource(BaseSource):
    kind = "firebase"

    def connect(self) -> None:
        sa_env = self.cfg.get("service_account_json_env")
        sa_path = os.getenv(sa_env, "") if sa_env else ""
        if not sa_path:
            raise ValueError("Firebase requires service_account_json_env")

        cred = credentials.Certificate(sa_path)
        app_name = self.cfg.get("app_name", self.name)
        try:
            self.app = firebase_admin.get_app(app_name)
        except Exception:
            self.app = firebase_admin.initialize_app(cred, name=app_name)

    def get_handle(self):
        return self.app

    def health(self) -> Dict[str, Any]:
        return {"ok": True, "kind": self.kind, "name": self.name}
