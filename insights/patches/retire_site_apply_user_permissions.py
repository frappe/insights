import frappe

SETTINGS = "Insights Settings"
FIELD = "apply_user_permissions"


def execute():
    """Delete the retired site-wide switch.

    The field is gone from the doctype, so frappe leaves its `Singles` row
    behind, and nothing reads it any more.

    It writes nothing to charts. The switch held only frappe's row and permlevel
    filter, while a chart's own Check moves the team grants and Table
    Restrictions with it. Carrying the switch onto charts made a reader's grants
    the owner's, which the switch never did. So every chart keeps running as
    its reader, and a site that had the switch off gains the frappe filter.
    """
    frappe.db.delete("Singles", {"doctype": SETTINGS, "field": FIELD})
