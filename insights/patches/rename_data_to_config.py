import frappe


def execute():
    Chart = frappe.qb.DocType("Insights Query Chart")
    frappe.qb.update(Chart).set(Chart.config, Chart.data).run()
