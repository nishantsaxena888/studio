from __future__ import annotations
from typing import Any, Dict, Optional

class DocumentCrud:
    def __init__(self, es_client):
        self.es = es_client

    def upsert(self, index: str, id_value: Any, doc: Dict[str, Any]) -> Dict[str, Any]:
        return self.es.index(index=index, id=str(id_value), document=doc)

    def delete(self, index: str, id_value: Any) -> Dict[str, Any]:
        return self.es.delete(index=index, id=str(id_value), ignore=[404])

    def search(self, index: str, *, q: str, page: int, size: int, filters: Optional[Dict[str, Any]]=None) -> Dict[str, Any]:
        filters = filters or {}

        must = []
        if q:
            must.append({"multi_match": {"query": q, "fields": ["*"]}})

        # simple term filters
        filter_terms = [{"term": {k: v}} for k, v in filters.items()]

        body = {
            "query": {
                "bool": {
                    "must": must if must else [{"match_all": {}}],
                    "filter": filter_terms
                }
            },
            "from": (page - 1) * size,
            "size": size
        }

        res = self.es.search(index=index, body=body)
        hits = res.get("hits", {})
        total = hits.get("total", {}).get("value", 0) if isinstance(hits.get("total"), dict) else hits.get("total", 0)
        items = [h.get("_source", {}) for h in hits.get("hits", [])]
        return {"items": items, "total": int(total)}
