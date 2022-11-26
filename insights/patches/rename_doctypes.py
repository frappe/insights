import click
import frappe


def execute():
    rename_map = {
        "Query": "Insights Query",
        "Table": "Insights Table",
        "Table Link": "Insights Table Link",
        "Query Visualization": "Insights Query Chart",
        "Data Source": "Insights Data Source",
        "Query Table": "Insights Query Table",
        "Query Column": "Insights Query Column",
    }
    for oldname, newname in rename_map.items():
        if frappe.db.exists("DocType", {"module": "Insights", "name": oldname}):
            try:
                frappe.rename_doc("DocType", oldname, newname, force=True)
            except Exception as e:
                frappe.log_error(title=f"Insights: Error renaming DocType {oldname}")
                click.echo(
                    f"Error renaming {oldname} to {newname}: {str(e)}", color="orange"
                )
