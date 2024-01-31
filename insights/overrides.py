# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from insights.insights.doctype.insights_team.insights_team import (
    get_allowed_resources_for_user,
    is_insights_admin,
)


def has_permission(doc, ptype, user):
    if doc.doctype not in [
        "Insights Data Source",
        "Insights Table",
        "Insights Query",
        "Insights Dashboard",
    ]:
        return True

    # only check if doc exists
    if not doc.name:
        return True

    if not frappe.db.get_single_value("Insights Settings", "enable_permissions"):
        return True

    if not user:
        user = frappe.session.user

    if is_insights_admin(user):
        return True

    allowed_resources = get_allowed_resources_for_user(doc.doctype, user)
    if doc.name in allowed_resources:
        return True

    return False
