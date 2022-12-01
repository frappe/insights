from json import dumps

import click
import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Query"):
        return

    queries = frappe.get_all("Insights Query", pluck="name")
    for query in queries:
        try:
            doc = frappe.get_doc("Insights Query", query)
            results = frappe.parse_json(doc.results)
            if not results or "::" in str(results[0][0]):
                continue
            columns = [f"{c.label or c.column}::{c.type}" for c in doc.get_columns()]
            results.insert(0, columns)
            frappe.db.set_value(
                "Insights Query", query, "result", dumps(results), update_modified=False
            )
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title="Error while adding column row for - " + query)
            click.secho("Error while adding column row for - " + query, fg="red")
