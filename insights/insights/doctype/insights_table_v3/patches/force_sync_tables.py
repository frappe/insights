import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    after_request,
    before_request,
)


def execute():
    """
    `name` of Insights Table v3 is changed from `autoincrement` to `varchar(140)`
     This patch will delete all the tables and recreate them with the new name
     The new name will be a reproducible hash of the data_source and table name
    """

    data_sources = frappe.get_all(
        "Insights Data Source v3", filters={"status": "Active"}, pluck="name"
    )

    doctype_doc = frappe.get_doc("DocType", "Insights Table v3")
    doctype_doc.setup_autoincrement_and_sequence()

    before_request()

    for source in data_sources:
        doc = frappe.get_doc("Insights Data Source v3", source)
        try:
            doc.update_table_list(force=True)
        except Exception:
            print(f"Error syncing {source}")
            frappe.db.rollback()
            frappe.db.delete("Insights Table v3", {"data_source": source})
        finally:
            frappe.db.commit()

    after_request()
