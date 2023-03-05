import click
import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Query"):
        return

    for query in frappe.get_all("Insights Query", pluck="name"):
        try:
            frappe.get_doc("Insights Query", query).update_insights_table()
        except Exception as e:
            click.secho(f"Failed to create table for {query}: {e}", fg="orange")
