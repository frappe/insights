import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import after_request


def execute():
    """
    Table links for Frappe DB data sources were stored using the raw doctype name
    (e.g. "HD Ticket") instead of the actual MariaDB table name (e.g. "tabHD Ticket").
    This caused join column auto-selection to fail because `op.table.table_name` uses
    the `tab`-prefixed name from `Insights Table v3`.

    This patch regenerates all table links with the correct `tab`-prefixed names.
    """
    frappe_db_sources = frappe.get_all(
        "Insights Data Source v3",
        filters=[["is_frappe_db", "=", 1]],
        pluck="name",
    )

    for source in frappe_db_sources:
        try:
            doc = frappe.get_doc("Insights Data Source v3", source)
            doc.update_table_links(force=True)
            frappe.db.commit()
        except Exception:
            frappe.log_error(title=f"Error updating table links for {source}")
            frappe.db.rollback()

    after_request()
