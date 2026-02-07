import os
from typing import Any, Dict
import boto3
from sources.base import BaseSource
from sources.registry import register_source

@register_source("s3")
class S3Source(BaseSource):
    kind = "s3"

    def connect(self) -> None:
        region = self.cfg.get("region")
        ak = os.getenv(self.cfg.get("access_key_env", ""), "")
        sk = os.getenv(self.cfg.get("secret_key_env", ""), "")
        token = os.getenv(self.cfg.get("session_token_env", ""), "")

        kwargs = {}
        if region: kwargs["region_name"] = region
        if ak and sk:
            kwargs["aws_access_key_id"] = ak
            kwargs["aws_secret_access_key"] = sk
        if token:
            kwargs["aws_session_token"] = token

        self.session = boto3.session.Session(**kwargs)
        self.client = self.session.client("s3")

    def get_handle(self):
        return self.client

    def health(self) -> Dict[str, Any]:
        try:
            self.client.list_buckets()
            return {"ok": True, "kind": self.kind, "name": self.name}
        except Exception as e:
            return {"ok": False, "kind": self.kind, "name": self.name, "error": str(e)}
