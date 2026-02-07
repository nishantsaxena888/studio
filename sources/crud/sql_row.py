from __future__ import annotations
from typing import Any, Dict, Optional, List, Tuple
from sqlalchemy import Table, select, insert, update, delete, func, or_
from sqlalchemy.sql import Select

from sources.crud.base import CrudBackend
from entities.spec import EntitySpec
from sources.queries.registry import QUERY_REGISTRY

class SqlRowCrud(CrudBackend):
    def __init__(self, engine, meta, entity_specs: Dict[str, EntitySpec]):
        self.engine = engine
        self.meta = meta
        self.entity_specs = entity_specs

    def _spec(self, entity: str) -> EntitySpec:
        if entity not in self.entity_specs:
            raise ValueError(f"Unknown entity: {entity}")
        return self.entity_specs[entity]

    def _table(self, table_name: str) -> Table:
        return Table(table_name, self.meta)

    def _parse_col(self, token: str):
        # token = "alias_or_table.col"
        left, col = token.split(".", 1)
        # meta reflects tables by real table names, not aliases
        # For alias, we create alias() from base Table in query builder
        return left, col

    def _build_select_default(self, spec: EntitySpec, *, q: Optional[str], filters: Optional[Dict[str, Any]]) -> Tuple[Select, Select]:
        base = self._table(spec.table)
        from_clause = base

        # build aliases
        alias_map = {spec.table: base}
        for j in spec.joins:
            jt = self._table(j.table).alias(j.alias)
            alias_map[j.alias] = jt
            # join condition
            l_tbl, l_col = self._parse_col(j.on_left)
            r_tbl, r_col = self._parse_col(j.on_right)
            left_expr = (alias_map.get(l_tbl) or self._table(l_tbl)).c[l_col]
            right_expr = (alias_map.get(r_tbl) or self._table(r_tbl)).c[r_col]

            if j.type == "left":
                from_clause = from_clause.outerjoin(jt, left_expr == right_expr)
            else:
                from_clause = from_clause.join(jt, left_expr == right_expr)

        # select columns
        cols = []
        for out_key, src in spec.fields.items():
            tbl, col = self._parse_col(src)
            t = alias_map.get(tbl) or self._table(tbl)
            cols.append(t.c[col].label(out_key))

        stmt = select(*cols).select_from(from_clause)
        count_stmt = select(func.count()).select_from(from_clause)

        where_clauses = []
        filters = filters or {}
        # filters only on configured fields keys (safe)
        for k, v in filters.items():
            if k in spec.fields:
                tbl, col = self._parse_col(spec.fields[k])
                t = alias_map.get(tbl) or self._table(tbl)
                where_clauses.append(t.c[col] == v)

        # q search across configured search_keys
        if q and spec.search_keys:
            like = f"%{q}%"
            ors = []
            for key in spec.search_keys:
                if key in spec.fields:
                    tbl, col = self._parse_col(spec.fields[key])
                    t = alias_map.get(tbl) or self._table(tbl)
                    ors.append(t.c[col].ilike(like))
            if ors:
                where_clauses.append(or_(*ors))

        for w in where_clauses:
            stmt = stmt.where(w)
            count_stmt = count_stmt.where(w)

        return stmt, count_stmt

    def create(self, entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        spec = self._spec(entity)
        if spec.write_mode != "default":
            raise ValueError(f"Write disabled or custom for entity: {entity}")

        base = self._table(spec.table)
        payload = {k: v for k, v in data.items() if k in spec.allowed_write_keys}
        stmt = insert(base).values(**payload).returning(base)

        with self.engine.begin() as conn:
            row = conn.execute(stmt).mappings().first()
        return dict(row)

    def get_one(self, entity: str, id_value: Any) -> Optional[Dict[str, Any]]:
        spec = self._spec(entity)

        # custom query read
        if spec.custom_query_id:
            builder = QUERY_REGISTRY.get(spec.custom_query_id)
            if not builder:
                raise ValueError(f"Unknown custom_query_id: {spec.custom_query_id}")
            stmt = builder(self.meta, None, None, None)
            # we expect "id" in selected columns
            stmt = stmt.where(stmt.selected_columns["id"] == id_value)  # type: ignore
            with self.engine.connect() as conn:
                row = conn.execute(stmt).mappings().first()
            return dict(row) if row else None

        # default: build from fields/joins and filter by id key if present
        if spec.pk not in spec.fields and "id" in spec.fields:
            pk_key = "id"
        else:
            pk_key = spec.pk

        stmt, _ = self._build_select_default(spec, q=None, filters={pk_key: id_value})
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
        return dict(row) if row else None

    def update(self, entity: str, id_value: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        spec = self._spec(entity)
        if spec.write_mode != "default":
            raise ValueError(f"Write disabled or custom for entity: {entity}")

        base = self._table(spec.table)
        payload = {k: v for k, v in data.items() if k in spec.allowed_write_keys}
        stmt = update(base).where(base.c[spec.pk] == id_value).values(**payload).returning(base)

        with self.engine.begin() as conn:
            row = conn.execute(stmt).mappings().first()

        if not row:
            raise ValueError(f"{entity} not found id={id_value}")
        return dict(row)

    def delete(self, entity: str, id_value: Any) -> Dict[str, Any]:
        spec = self._spec(entity)
        if spec.write_mode != "default":
            raise ValueError(f"Write disabled or custom for entity: {entity}")

        base = self._table(spec.table)
        stmt = delete(base).where(base.c[spec.pk] == id_value)

        with self.engine.begin() as conn:
            res = conn.execute(stmt)

        return {"ok": True, "deleted": res.rowcount}

    def list(self, entity: str, *, page: int, size: int, q: Optional[str]=None, filters: Optional[Dict[str, Any]]=None) -> Dict[str, Any]:
        spec = self._spec(entity)

        # custom query list
        if spec.custom_query_id:
            builder = QUERY_REGISTRY.get(spec.custom_query_id)
            if not builder:
                raise ValueError(f"Unknown custom_query_id: {spec.custom_query_id}")
            stmt = builder(self.meta, filters, q, None)
            # count: wrap as subquery
            subq = stmt.subquery()
            count_stmt = select(func.count()).select_from(subq)
            stmt = select(subq).offset((page - 1) * size).limit(size)

            with self.engine.connect() as conn:
                total = conn.execute(count_stmt).scalar_one()
                items = [dict(r) for r in conn.execute(stmt).mappings().all()]
            return {"items": items, "total": int(total)}

        stmt, count_stmt = self._build_select_default(spec, q=q, filters=filters)
        stmt = stmt.offset((page - 1) * size).limit(size)

        with self.engine.connect() as conn:
            total = conn.execute(count_stmt).scalar_one()
            items = [dict(r) for r in conn.execute(stmt).mappings().all()]

        return {"items": items, "total": int(total)}
