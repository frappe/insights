# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import split_emails, validate_email_address
from frappe.utils.user import get_users_with_role

from insights import notify
from insights.decorators import check_role
from insights.insights.doctype.insights_team.insights_team import get_user_teams


@frappe.whitelist()
@check_role("Insights Admin")
def get_users():
    """Returns full_name, email, type, teams, last_active"""
    insights_users = get_users_with_role("Insights User")
    insights_admins = get_users_with_role("Insights Admin")

    users = frappe.get_all(
        "User",
        fields=["name", "full_name", "email", "last_active"],
        filters={"name": ["in", list(set(insights_users + insights_admins))]},
        order_by="last_active desc",
    )
    for user in users:
        teams = frappe.get_all(
            "Insights Team",
            filters={"name": ["in", get_user_teams(user.name)]},
            pluck="team_name",
        )
        user["type"] = "Admin" if user.name in insights_admins else "User"
        user["teams"] = teams

    return users


@frappe.whitelist()
@check_role("Insights Admin")
def add_insights_user(user):
    email_strings = validate_email_address(user.get("email"), throw=True)
    email_strings = split_emails(email_strings)
    if user.get("role") not in ["User", "Admin"]:
        frappe.throw("Invalid Role")

    doc = frappe.get_doc(
        {
            "doctype": "User",
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "email": email_strings[0],
            "user_type": "Website User",
            "send_welcome_email": 1,
        }
    )
    doc.append_roles("Insights User")
    if user.get("role") == "Admin":
        doc.append_roles("Insights Admin")
    doc.insert()
    frappe.db.commit()
    notify(
        type="success",
        title="User Added",
        message=f"{user.get('first_name')} {user.get('last_name')} has been added as an Insights {user.get('role')}",
    )

    if user.get("team"):
        try:
            team = frappe.get_doc("Insights Team", user.get("team"))
            team.append("team_members", {"user": doc.name})
            team.save()
        except frappe.DoesNotExistError:
            notify(
                type="error",
                title="Team Not Found",
                message=f"Team {user.get('team')} does not exist. Please create a new team or add the user to an existing team.",
            )
