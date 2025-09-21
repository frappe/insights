import frappe


def execute():
    # set chart name for existing insights query
    frappe.db.sql(
        """
            UPDATE `tabInsights Query` q
            SET chart = (select name from `tabInsights Chart` where query = q.name limit 1)
            WHERE chart IS NULL
        """
    )
