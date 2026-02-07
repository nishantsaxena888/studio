from __future__ import annotations
from fastapi import FastAPI, HTTPException, Query
from typing import Any, Dict, Optional

from app.config import get_manager, get_entities
from entities.spec import parse_entity_spec
from sources.crud.sql_row import SqlRowCrud

# load custom queries
import sources.queries.sample_po_with_totals  # noqa: F401

# load sinks (register)
import sinks.es_index  # noqa: F401
import sinks.s3_put_json  # noqa: F401
import sinks.bq_append  # noqa: F401
import sinks.cache_set  # noqa: F401

from engine.post_write import PostWritePipeline

app = FastAPI(title="Low-code Backend V1")

def build_sql_crud_and_pipeline():
    mgr = get_manager()
    entities_cfg = get_entities()

    specs = {name: parse_entity_spec(name, cfg) for name, cfg in entities_cfg.items()}

    db_source = mgr.get_source(mgr.config["routing"]["active_source"])
    engine = db_source.engine
    meta = db_source.meta

    sql = SqlRowCrud(engine=engine, meta=meta, entity_specs=specs)
    pipeline = PostWritePipeline(manager=mgr, entity_specs=entities_cfg)  # NOTE: raw cfg for post_write
    return sql, pipeline

@app.get("/health/sources")
def health_sources():
    return get_manager().health()

@app.get("/api/{entity}")
def list_entity(
    entity: str,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=500),
    q: Optional[str] = None
):
    try:
        sql, _ = build_sql_crud_and_pipeline()
        return sql.list(entity, page=page, size=size, q=q, filters=None)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/{entity}/{id_value}")
def get_one(entity: str, id_value: str):
    try:
        sql, _ = build_sql_crud_and_pipeline()
        row = sql.get_one(entity, id_value)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/{entity}")
def create_entity(entity: str, payload: Dict[str, Any]):
    try:
        sql, pipeline = build_sql_crud_and_pipeline()
        row = sql.create(entity, payload)  # DB commit happens inside begin()
        warnings = pipeline.run(entity, "create", row=row)
        out = {"row": row, "ok": True}
        if warnings:
            out["warnings"] = warnings
        return out
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/{entity}/{id_value}")
def update_entity(entity: str, id_value: str, payload: Dict[str, Any]):
    try:
        sql, pipeline = build_sql_crud_and_pipeline()
        row = sql.update(entity, id_value, payload)
        warnings = pipeline.run(entity, "update", row=row)
        out = {"row": row, "ok": True}
        if warnings:
            out["warnings"] = warnings
        return out
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/{entity}/{id_value}")
def delete_entity(entity: str, id_value: str):
    try:
        sql, pipeline = build_sql_crud_and_pipeline()
        res = sql.delete(entity, id_value)
        warnings = pipeline.run(entity, "delete", id_value=id_value)
        out = {"ok": True, "result": res}
        if warnings:
            out["warnings"] = warnings
        return out
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
