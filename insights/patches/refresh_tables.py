# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import click
import frappe


def execute():
    # demo data is now merged with site db
    Tables = frappe.qb.DocType("Insights Table")
    (
        frappe.qb.update(Tables)
        .set(Tables.data_source, "Site DB")
        .where(Tables.data_source == "Demo Data")
        .run()
    )
    Query = frappe.qb.DocType("Insights Query")
    (
        frappe.qb.update(Query)
        .set(Query.data_source, "Site DB")
        .where(Query.data_source == "Demo Data")
        .run()
    )

    frappe.delete_doc("Insights Data Source", "Demo Data")
    if not frappe.db.exists("Insights Data Source", "Site DB"):
        site_db = frappe.new_doc("Insights Data Source")
        site_db.title = "Site DB"
        site_db.is_site_db = 1
        site_db.save()
    else:
        site_db = frappe.get_doc("Insights Data Source", "Site DB")
    site_db.sync_tables()
    site_db.save()
