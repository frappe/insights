import frappe

import insights


def _esc(value: str) -> str:
    return value.replace("'", "''")


def handle_deletes(doctype: str, warehouse_table: str, schema: str, log_fn=None):
    _log = log_fn or (lambda msg: None)
    batch_size = 10_000

    with insights.warehouse.get_write_connection() as db:
        db.raw_sql(f"USE '{_esc(schema)}'")

        if warehouse_table not in db.list_tables():
            _log("warehouse table not found, skipping")
            return 0

        wh_names = db.table(warehouse_table).select("name").execute()["name"].tolist()

        stale = []
        for i in range(0, len(wh_names), batch_size):
            batch = wh_names[i : i + batch_size]
            existing = set(frappe.get_all(doctype, filters={"name": ("in", batch)}, pluck="name"))
            stale.extend(n for n in batch if n not in existing)

        if not stale:
            _log("no stale rows found")
            return 0

        for i in range(0, len(stale), batch_size):
            batch = stale[i : i + batch_size]
            values = ", ".join(f"'{_esc(n)}'" for n in batch)
            db.raw_sql(f'DELETE FROM "{_esc(warehouse_table)}" WHERE "name" IN ({values})')

        _log(f"deleted {len(stale)} stale rows")
        return len(stale)
