import frappe
from pypika.terms import CustomFunction


def execute():
    if not frappe.db.count("Insights Notebook Page", {"content": ["like", '%"query-builder"%']}):
        return

    pages = frappe.get_all(
        "Insights Notebook Page",
        filters={"content": ["like", '%"query-builder"%']},
        pluck="name",
    )
    for page in pages:
        content = frappe.get_value("Insights Notebook Page", page, "content")
        content = content.replace('"query-builder"', '"query-editor"')
        frappe.db.set_value(
            "Insights Notebook Page", page, "content", content, update_modified=False
        )
