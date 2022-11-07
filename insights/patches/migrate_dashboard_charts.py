import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Dashboard Item"):
        return

    frappe.db.sql(
        """
        UPDATE
            `tabInsights Dashboard Item`
        SET
            `item_type` = 'Chart',
            `chart` = `query_chart`
        WHERE
            `item_type` IS NULL
            OR `item_type` = ''
        """
    )
