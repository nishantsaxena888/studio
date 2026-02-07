from sqlalchemy import Table, select, func
from sources.queries.registry import register_query

@register_query("po_with_totals_v1")
def build_po_with_totals(meta, filters: dict | None, q: str | None, sort: list | None):
    po = Table("purchase_orders", meta)
    items = Table("purchase_order_items", meta)

    total = func.coalesce(func.sum(items.c.qty * items.c.price), 0).label("items_total")

    stmt = (
        select(po.c.id, po.c.po_number, po.c.status, total)
        .select_from(po.outerjoin(items, items.c.purchase_order_id == po.c.id))
        .group_by(po.c.id, po.c.po_number, po.c.status)
    )
    return stmt
