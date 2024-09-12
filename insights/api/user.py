# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import split_emails, validate_email_address
from frappe.utils.user import get_users_with_role

from insights import notify
from insights.decorators import insights_whitelist, validate_type
from insights.insights.doctype.insights_team.insights_team import get_user_teams


@insights_whitelist()
def get_users(search_term=None):
    """Returns full_name, email, type, teams, last_active"""
    insights_users = get_users_with_role("Insights User")
    insights_admins = get_users_with_role("Insights Admin")

    additional_filters = {}
    if search_term:
        additional_filters = {
            "full_name": ["like", f"%{search_term}%"],
            "email": ["like", f"%{search_term}%"],
        }

    users = frappe.get_list(
        "User",
        fields=["name", "full_name", "email", "last_active", "user_image", "enabled"],
        filters={
            "name": ["in", list(set(insights_users + insights_admins))],
            **additional_filters,
        },
    )
    for user in users:
        teams = frappe.get_list(
            "Insights Team",
            filters={"name": ["in", get_user_teams(user.name)]},
            pluck="team_name",
        )
        user["type"] = "Admin" if user.name in insights_admins else "User"
        user["teams"] = teams

    invitations = frappe.get_list(
        "Insights User Invitation",
        fields=["email", "status"],
        filters={"status": ["in", ["Pending", "Expired"]]},
    )
    for invitation in invitations:
        users.append(
            {
                "name": invitation.email,
                "full_name": invitation.email.split("@")[0],
                "email": invitation.email,
                "last_active": None,
                "user_image": None,
                "enabled": 0,
                "type": "User",
                "teams": [],
                "invitation_status": invitation.status,
            }
        )

    return users


@insights_whitelist()
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


@frappe.whitelist(allow_guest=True)
@validate_type
def accept_invitation(key: str):
    if not key:
        frappe.throw("Invalid or expired key")

    invitation_name = frappe.db.exists("Insights User Invitation", {"key": key})
    if not invitation_name:
        frappe.throw("Invalid or expired key")

    invitation = frappe.get_doc("Insights User Invitation", invitation_name)
    invitation.accept()
    invitation.reload()

    if invitation.status == "Accepted":
        frappe.local.login_manager.login_as(invitation.email)
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/insights"


@insights_whitelist()
@validate_type
def invite_users(emails: str):
    if not emails:
        return

    email_string = validate_email_address(emails, throw=False)
    email_list = split_emails(email_string)
    if not email_list:
        return

    existing_invites = frappe.db.get_all(
        "Insights User Invitation",
        filters={
            "email": ["in", email_list],
            "status": ["in", ["Pending", "Accepted"]],
        },
        pluck="email",
    )

    new_invites = list(set(email_list) - set(existing_invites))
    for email in new_invites:
        invite = frappe.new_doc("Insights User Invitation")
        invite.email = email
        invite.insert(ignore_permissions=True)
