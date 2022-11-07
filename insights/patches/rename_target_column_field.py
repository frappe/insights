# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import click
import frappe


def execute():
    for chart in frappe.get_all(
        "Insights Query Chart",
        filters={"config": ("like", "%targetColumn%")},
        fields=["name", "config"],
    ):
        try:
            chart_doc = frappe.get_doc("Insights Query Chart", chart.name)
            config = frappe.parse_json(chart_doc.config)
            config.target = config.targetColumn
            config.targetType = "Column"
            del config.targetColumn
            chart_doc.config = frappe.as_json(config)
            chart_doc.save()
        except Exception:
            click.secho(f"Failed to update {chart.name}", fg="red")
            frappe.log_error(title="Insights: Failed to update chart")
