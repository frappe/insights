# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from urllib.parse import quote

import frappe
from frappe.utils import split_emails, validate_email_address
from frappe.utils.user import get_users_with_role

from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_team.insights_team import (
    get_teams as get_user_teams,
)
from insights.insights.doctype.insights_team.insights_team import is_admin
from insights.insights.doctype.insights_user_invitation.insights_user_invitation import (
    get_invitation_by_key,
)
from insights.permissions import get_insights_users
from insights.utils import get_app_url

# the roster is a directory to share from, so it carries what a picker shows
# and nothing else
USER_FIELDS = ["name", "full_name", "email", "last_active", "user_image", "enabled"]


def user_lookup_allowed():
    """Whether members may look each other up. On unless a site turns it off.

    The setting reads as off, not unset, on a site that never saved it: a Check
    is absent from `tabSingles` until the doc is first saved, and
    `get_single_value` casts a missing value to 0. Naming the setting for the
    exception is what keeps the default on.
    """
    return not frappe.db.get_single_value("Insights Settings", "disable_user_lookup")


@insights_whitelist()
def get_users(search_term: str | None = None):
    """Returns full_name, email, type, last_active; admins also get teams and pending invites"""

    caller_is_admin = is_admin(frappe.session.user)
    if not caller_is_admin and not user_lookup_allowed():
        # sharing still works on a site that opted out - the owner names an
        # address instead of picking one
        own_profile = frappe.db.get_value("User", frappe.session.user, USER_FIELDS, as_dict=True)
        own_profile["type"] = "User"
        return [own_profile]

    or_filters = {}
    if search_term:
        # a name or an address, not both - the picker offers "search by name or
        # email", so a match on either is a hit
        or_filters = {
            "full_name": ["like", f"%{search_term}%"],
            "email": ["like", f"%{search_term}%"],
        }

    # read without a permission check on purpose: `insights_whitelist` has
    # already settled that the caller belongs here, the cohort filter bounds the
    # rows, and USER_FIELDS bounds the columns. Listing `User` through the
    # framework instead would need a `select` grant that no field permission can
    # narrow, because `User` is a core doctype and those skip field filtering
    users = frappe.get_all(
        "User",
        fields=USER_FIELDS,
        filters={"name": ["in", list(get_insights_users())]},
        or_filters=or_filters,
    )

    insights_admins = get_users_with_role("Insights Admin")
    for user in users:
        user["type"] = "Admin" if user.name in insights_admins else "User"

    # team membership and pending invitations are for managing users, not sharing
    if not caller_is_admin:
        return users

    for user in users:
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
def get_teams(search_term: str | None = None):
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
        team.team_members = [{"user": member.user} for member in members if member.parent == team.name]
        team.team_permissions = [
            permission for permission in source_permissions if permission.parent == team.name
        ]
        team.team_permissions += [
            permission for permission in table_permissions if permission.parent == team.name
        ]

    return teams


@insights_whitelist(role="Insights Admin")
def create_team(team_name: str):
    team = frappe.new_doc("Insights Team")
    team.team_name = team_name
    team.insert()
    return team


@insights_whitelist(role="Insights Admin")
def update_team(team: dict):
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


@insights_whitelist(role="Insights Admin")
def delete_team(team_name: str):
    frappe.delete_doc("Insights Team", team_name)


@insights_whitelist()
def add_insights_user(user: str):
    raise NotImplementedError


@frappe.whitelist(allow_guest=True)  # nosemgrep - an invitee follows this link before they have
# an account, so it cannot require a session
def accept_invitation(key: str):
    if not key:
        frappe.throw("Invalid or expired key")

    invitation_name = get_invitation_by_key(key)
    if not invitation_name:
        frappe.throw("Invalid or expired key")

    invitation = frappe.get_doc("Insights User Invitation", invitation_name)
    account_was_created = invitation.accept()
    invitation.reload()

    if invitation.status != "Accepted":
        return

    frappe.local.response["type"] = "redirect"

    if not account_was_created:
        # the address already had an account. The invitation grants it access to
        # Insights; signing in is for the account holder to do. The login page
        # carries them the rest of the way, so the link still ends in Insights.
        frappe.local.response["location"] = f"/login?redirect-to={quote(get_app_url())}"
        return

    # a new account has no password yet, so the invitation link is how the
    # invitee gets in the first time
    frappe.local.login_manager.login_as(invitation.email)
    frappe.local.response["location"] = get_app_url()


@insights_whitelist(role="Insights Admin")
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


@insights_whitelist()
def update_user(email: str, fields: dict):
    if frappe.session.user != email and not is_admin(frappe.session.user):
        frappe.throw("Not permitted to update another user's profile", frappe.PermissionError)

    first_name, last_name = fields.get("first_name"), fields.get("last_name")

    user = frappe.get_doc("User", email)
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name

    user.save()
