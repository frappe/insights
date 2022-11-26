import frappe
from pypika import Criterion


def execute():
    if not frappe.db.a_row_exists("Insights Query"):
        return

    frappe.db.sql(
        """
        UPDATE
            `tabInsights Query Column`
        SET
            `column` = '*'
        WHERE
            `column` = '__count' OR `column` = 'count'
        """
    )
