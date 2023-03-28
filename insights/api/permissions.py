import frappe
from frappe.query_builder.functions import Count

from insights.decorators import check_role


@frappe.whitelist()
@check_role("Insights User")
def get_resource_access_info(resource_type, resource_name):
    # returns a list of authorized and unauthorized teams for a resource
    InsightsTeam = frappe.qb.DocType("Insights Team")
    InsightsTeamMember = frappe.qb.DocType("Insights Team Member")
    InsightsResourcePermission = frappe.qb.DocType("Insights Resource Permission")

    authorized_teams = (
        frappe.qb.from_(InsightsTeam)
        .join(InsightsTeamMember)
        .on(InsightsTeam.name == InsightsTeamMember.parent)
        .join(InsightsResourcePermission)
        .on(InsightsTeam.name == InsightsResourcePermission.parent)
        .where(
            (InsightsResourcePermission.resource_type == resource_type)
            & (InsightsResourcePermission.resource_name == resource_name)
        )
        .select(
            InsightsTeam.name,
            InsightsTeam.team_name,
            Count(InsightsTeamMember.user).as_("members_count"),
        )
        .groupby(InsightsTeam.name)
        .run(as_dict=True)
    )

    unauthorized_teams = (
        frappe.qb.from_(InsightsTeam)
        .left_join(InsightsTeamMember)
        .on(InsightsTeam.name == InsightsTeamMember.parent)
        .where(
            ~(
                InsightsTeam.name.isin(
                    frappe.qb.from_(InsightsResourcePermission)
                    .where(
                        (InsightsResourcePermission.resource_type == resource_type)
                        & (InsightsResourcePermission.resource_name == resource_name)
                    )
                    .select(InsightsResourcePermission.parent)
                )
            )
        )
        .select(
            InsightsTeam.name,
            InsightsTeam.team_name,
            Count(InsightsTeamMember.user).as_("members_count"),
        )
        .groupby(InsightsTeam.name)
        .run(as_dict=True)
    )

    return {
        "authorized_teams": authorized_teams,
        "unauthorized_teams": unauthorized_teams,
    }


@frappe.whitelist()
@check_role("Insights User")
def grant_access(resource_type, resource_name, team):
    if (
        frappe.db.get_value(resource_type, resource_name, "owner")
        == frappe.session.user
    ):
        team_doc = frappe.get_doc("Insights Team", team)
        team_doc.append(
            "team_permissions",
            {
                "resource_type": resource_type,
                "resource_name": resource_name,
            },
        )
        team_doc.save(ignore_permissions=True)

    else:
        frappe.throw(
            "You are not authorized to grant access to this resource.",
            frappe.PermissionError,
        )


@frappe.whitelist()
@check_role("Insights User")
def revoke_access(resource_type, resource_name, team):
    if (
        frappe.db.get_value(resource_type, resource_name, "owner")
        == frappe.session.user
    ):
        team_doc = frappe.get_doc("Insights Team", team)
        for permission in team_doc.team_permissions:
            if (
                permission.resource_type == resource_type
                and permission.resource_name == resource_name
            ):
                team_doc.remove(permission)
        team_doc.save(ignore_permissions=True)


def is_private(resource_type, resource_name):
    if not frappe.db.get_single_value("Insights Settings", "enable_permissions"):
        return False
    return bool(
        get_resource_access_info(resource_type, resource_name).get("authorized_teams")
    )
