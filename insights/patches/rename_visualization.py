import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
    try:
        rename_field("Insights Dashboard Item", "visualization", "query_chart")
        InsightsDashboardItem = frappe.qb.DocType("Insights Dashboard Item")
        (
            frappe.qb.update(InsightsDashboardItem)
            .set(InsightsDashboardItem.parentfield, "items")
            .where(InsightsDashboardItem.parentfield == "visualizations")
            .run()
        )

    except Exception as e:
        if e.args[0] != 1054:
            raise
