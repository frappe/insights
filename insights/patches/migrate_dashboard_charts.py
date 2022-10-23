import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Dashboard Item"):
        return

    Item = frappe.qb.DocType("Insights Dashboard Item")
    frappe.qb.update(Item).set(Item.item_type, "Chart").set(
        Item.chart, Item.query_chart
    ).run()
