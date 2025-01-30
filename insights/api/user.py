# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import split_emails, validate_email_address
from frappe.utils.user import get_users_with_role

from insights.decorators import insights_whitelist, validate_type
from insights.insights.doctype.insights_team.insights_team import (
    get_teams as get_user_teams,
)
from insights.insights.doctype.insights_team.insights_team import is_admin


@insights_whitelist()
def get_users(search_term=None):
    """Returns full_name, email, type, teams, last_active"""

    perm_enabled = frappe.db.get_single_value("Insights Settings", "enable_permissions")
    if perm_enabled and not is_admin(frappe.session.user):
        user_info = frappe.db.get_value(
            "User",
            frappe.session.user,
            ["name", "full_name", "email", "last_active", "user_image", "enabled"],
            as_dict=True,
        )
        user_info["type"] = "User"
        user_info["teams"] = get_user_teams(frappe.session.user)
        return [user_info]

    insights_admins = get_users_with_role("Insights Admin")
    insights_users = get_users_with_role("Insights User")

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
        user["type"] = "Admin" if user.name in insights_admins else "User"
        user["teams"] = get_user_teams(user.name)

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
def get_teams(search_term=None):
    teams = frappe.get_list(
        "Insights Team",
        filters={
            "name": ["like", f"%{search_term}%"] if search_term else ["is", "set"],
        },
        fields=[
            "name",
            "team_name",
            "owner",
            "creation",
        ],
    )

    members = frappe.get_all(
        "Insights Team Member",
        fields=["parent", "user"],
        filters={"parent": ["in", [team.name for team in teams]]},
    )

    ResourcePermission = frappe.qb.DocType("Insights Resource Permission")
    table_permissions = (
        frappe.qb.from_(ResourcePermission)
        .select(
            ResourcePermission.parent,
            ResourcePermission.resource_name,
            ResourcePermission.resource_type,
            ResourcePermission.table_restrictions,
        )
        .where(
            ResourcePermission.parent.isin([team.name for team in teams])
            & (ResourcePermission.resource_type == "Insights Table v3")
        )
        .run(as_dict=True)
    )

    source_permissions = (
        frappe.qb.from_(ResourcePermission)
        .select(
            ResourcePermission.parent,
            ResourcePermission.resource_name,
            ResourcePermission.resource_type,
        )
        .where(
            ResourcePermission.parent.isin([team.name for team in teams])
            & (ResourcePermission.resource_type == "Insights Data Source v3")
        )
        .run(as_dict=True)
    )

    for team in teams:
        team.team_members = [
            {"user": member.user} for member in members if member.parent == team.name
        ]
        team.team_permissions = [
            permission
            for permission in source_permissions
            if permission.parent == team.name
        ]
        team.team_permissions += [
            permission
            for permission in table_permissions
            if permission.parent == team.name
        ]

    return teams


@insights_whitelist()
@validate_type
def create_team(team_name: str):
    frappe.only_for("Insights Admin")

    team = frappe.new_doc("Insights Team")
    team.team_name = team_name
    team.insert()
    return team


@insights_whitelist()
@validate_type
def update_team(team: dict):
    frappe.only_for("Insights Admin")

    team = frappe._dict(team)
    doc = frappe.get_doc("Insights Team", team.name)
    if team.name != "Admin" and doc.team_name != team.team_name:
        doc.rename(team.team_name)
    doc.set("team_members", [])
    for member in team.team_members:
        doc.append(
            "team_members",
            {
                "user": member["user"],
            },
        )

    team.team_permissions = sorted(
        team.team_permissions, key=lambda x: (x["resource_type"], x["resource_name"])
    )
    doc.set("team_permissions", [])
    for permission in team.team_permissions:
        permission = frappe._dict(permission)
        if permission.resource_type not in [
            "Insights Data Source v3",
            "Insights Table v3",
        ]:
            continue
        doc.append(
            "team_permissions",
            {
                "resource_type": permission.resource_type,
                "resource_name": permission.resource_name,
                "table_restrictions": permission.table_restrictions.strip()
                if permission.table_restrictions
                else None,
            },
        )
    doc.save()


@insights_whitelist()
def add_insights_user(user):
    raise NotImplementedError


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
    frappe.only_for("Insights Admin")

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


@insights_whitelist()
def update_user(email: str, fields: dict):
    first_name, last_name = fields.get("first_name"), fields.get("last_name")

    user = frappe.get_doc("User", email)
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name

    user.save()
