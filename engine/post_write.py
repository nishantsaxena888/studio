from __future__ import annotations
from typing import Any, Dict, List, Optional
from sinks.registry import SINK_REGISTRY

class PostWritePipeline:
    def __init__(self, manager, entity_specs: Dict[str, Any]):
        self.manager = manager
        self.entity_specs = entity_specs
        self._sink_cache: Dict[str, Any] = {}

    def _build_sink(self, sink_cfg: Dict[str, Any]):
        kind = sink_cfg["kind"]
        name = sink_cfg.get("name", kind)
        key = f"{kind}:{name}"

        if key in self._sink_cache:
            return self._sink_cache[key]

        cls = SINK_REGISTRY[kind]
        inst = cls(name=name, cfg=sink_cfg, manager=self.manager)
        self._sink_cache[key] = inst
        return inst

    def run(self, entity: str, action: str, *, row: Optional[Dict[str, Any]] = None, id_value: Any = None) -> List[Dict[str, Any]]:
        """
        Returns warnings list: [{sink, error}]
        """
        spec = self.entity_specs[entity]
        post = spec.get("post_write", {})
        sinks = post.get("sinks", [])
        policy = post.get("policy", "best_effort")  # best_effort | strict

        warnings: List[Dict[str, Any]] = []

        for s_cfg in sinks:
            sink = self._build_sink(s_cfg)
            try:
                if action == "create":
                    sink.on_create(entity, row or {})
                elif action == "update":
                    sink.on_update(entity, row or {})
                elif action == "delete":
                    sink.on_delete(entity, id_value)
            except Exception as e:
                if policy == "strict":
                    raise
                warnings.append({"sink": s_cfg.get("name") or s_cfg["kind"], "error": str(e)})

        return warnings
