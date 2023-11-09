import frappe

from insights.insights.doctype.insights_data_source.sources.frappe_db import FrappeDB


def execute():
    data_sources = frappe.get_all("Insights Data Source", pluck="name")
    for data_source in data_sources:
        doc = frappe.get_doc("Insights Data Source", data_source)
        if not isinstance(doc.db, FrappeDB) and not doc.is_site_db:
            continue
        try:
            doc.db.sync_tables(force=True)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            print(f"Failed to sync tables for {data_source}")
