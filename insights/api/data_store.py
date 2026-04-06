import frappe

from insights.decorators import insights_whitelist, validate_type
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name


@insights_whitelist()
@validate_type
def get_data_store_tables(data_source: str | None = None, search_term: str | None = None, limit: int = 100):
    Table = frappe.qb.DocType("Insights Table v3")
    DataSource = frappe.qb.DocType("Insights Data Source v3")

    tables = (
        frappe.qb.from_(Table)
        .left_join(DataSource)
        .on(Table.data_source == DataSource.name)
        .select(
            Table.name,
            Table.table,
            Table.label,
            Table.data_source,
            Table.last_synced_on,
            Table.sync_mode,
            DataSource.database_type,
        )
        .where(
            (Table.stored == 1)
            & (Table.data_source == data_source if data_source else Table.data_source.like("%"))
            & (
                (Table.label == search_term if search_term else Table.label.like("%"))
                | (Table.table == search_term if search_term else Table.table.like("%"))
            )
        )
        .orderby(Table.last_synced_on, order=frappe.qb.desc)
        .limit(limit)
        .run(as_dict=True)
    )

    ret = []
    for table in tables:
        ret.append(
            frappe._dict(
                {
                    "name": table.name,
                    "label": table.label,
                    "table_name": table.table,
                    "data_source": table.data_source,
                    "database_type": table.database_type,
                    "last_synced_on": table.last_synced_on,
                    "sync_mode": table.sync_mode or "Incremental Sync",
                }
            )
        )
    return ret


@insights_whitelist()
@validate_type
def get_last_sync_log(data_source: str, table_name: str):
    log = frappe.get_all(
        "Insights Table Import Log",
        filters={"data_source": data_source, "table_name": table_name},
        fields=["status", "rows_imported", "time_taken", "started_at", "ended_at", "error", "output"],
        order_by="creation desc",
        limit=1,
    )
    return log[0] if log else None


@insights_whitelist(role="Insights Admin")
@validate_type
def import_table(data_source: str, table_name: str, sync_mode: str = ""):
    from insights.insights.doctype.insights_data_source_v3.data_warehouse import WarehouseTable

    if sync_mode:
        name = get_table_name(data_source, table_name)
        if frappe.db.exists("Insights Table v3", name):
            frappe.db.set_value("Insights Table v3", name, "sync_mode", sync_mode)

    wt = WarehouseTable(data_source, table_name)
    wt.enqueue_import(sync_mode=sync_mode)


def sync_tables():
    # called daily via hooks
    tables = frappe.get_all(
        "Insights Table v3",
        filters={"stored": 1},
        fields=["name", "data_source", "table", "sync_mode"],
    )

    for table in tables:
        import_table(table.data_source, table.table, sync_mode=table.sync_mode or "Incremental Sync")


def handle_warehouse_deletes():
    from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
        WarehouseTable,
    )
    from insights.insights.doctype.insights_data_source_v3.delete_tracker import handle_deletes

    tables = frappe.get_all(
        "Insights Table v3",
        filters={"stored": 1, "sync_mode": "Incremental Sync"},
        fields=["data_source", "table"],
    )

    for t in tables:
        try:
            wt = WarehouseTable(t.data_source, t.table)
            doctype = t.table.replace("tab", "", 1) if t.table.startswith("tab") else t.table
            handle_deletes(doctype=doctype, warehouse_table=wt.warehouse_table_name, schema=wt.schema)
        except Exception:
            frappe.log_error(title=f"Delete failed for {t.data_source}/{t.table}")


def update_failed_sync_status():
    from frappe.query_builder import Interval
    from frappe.query_builder.functions import Now

    Log = frappe.qb.DocType("Insights Table Import Log")
    logs = frappe.db.get_values(
        Log,
        ((Log.status == "In Progress") & (Log.creation < (Now() - Interval(hours=1)))),
        pluck="name",
    )

    if not logs:
        return

    for log in logs:
        frappe.db.set_value("Insights Table Import Log", log, "status", "Failed")
