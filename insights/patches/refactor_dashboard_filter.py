# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import click
import frappe


def execute():
    dashboards = frappe.get_all(
        "Insights Dashboard Item", filters={"item_type": "Filter"}, pluck="parent"
    )
    for dashboard in dashboards:
        try:
            doc = frappe.get_doc("Insights Dashboard", dashboard)
            chart = [item for item in doc.items if item.item_type == "Chart"][0]
            data_source = frappe.db.get_value(
                "Insights Query", chart.query, "data_source"
            )
            modified = False
            for item in doc.items:
                if item.item_type == "Filter":
                    filter_links = frappe.parse_json(item.filter_links)
                    filter_column = list(filter_links.values())[0]
                    filter_column["data_source"] = data_source
                    item.filter_column = frappe.as_json(filter_column)
                    modified = True
            if modified:
                doc.save()
        except Exception:
            click.secho(f"Error in dashboard {dashboard}", fg="red")
