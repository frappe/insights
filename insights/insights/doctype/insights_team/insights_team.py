# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.caching import site_cache

from .insights_team_client import InsightsTeamClient


class InsightsTeam(InsightsTeamClient, Document):
    def on_trash(self):
        _get_user_teams.clear_cache()

    def on_change(self):
        _get_user_teams.clear_cache()

    def get_members(self):
        return frappe.get_all(
            "User",
            filters={"name": ["in", [m.user for m in self.team_members]]},
            fields=["full_name", "email", "user_image", "name"],
        )

    def get_sources(self):
        return [
            d.resource_name
            for d in self.team_permissions
            if d.resource_type == "Insights Data Source"
        ]

    def get_tables(self):
        return [
            d.resource_name
            for d in self.team_permissions
            if d.resource_type == "Insights Table"
        ]

    def get_queries(self):
        return [
            d.resource_name
            for d in self.team_permissions
            if d.resource_type == "Insights Query"
        ]

    def get_dashboards(self):
        return [
            d.resource_name
            for d in self.team_permissions
            if d.resource_type == "Insights Dashboard"
        ]

    def get_allowed_resources(self, resource_type):
        if not self.team_permissions:
            return []
        if resource_type == "Insights Data Source":
            return self.get_allowed_sources()
        elif resource_type == "Insights Table":
            return self.get_allowed_tables()
        elif resource_type == "Insights Query":
            return self.get_allowed_queries()
        elif resource_type == "Insights Dashboard":
            return self.get_allowed_dashboards()
        else:
            return []

    def get_allowed_sources(self):
        unrestricted_sources = [
            d.resource_name
            for d in self.team_permissions
            if d.resource_type == "Insights Data Source"
        ]
        table_sources = frappe.get_all(
            "Insights Table",
            filters={"name": ["in", self.get_tables()]},
            pluck="data_source",
        )
        return list(set(unrestricted_sources + table_sources))

    def get_allowed_tables(self):
        unrestricted_sources = self.get_sources()
        unrestricted_tables = frappe.get_all(
            "Insights Table",
            filters={"data_source": ["in", unrestricted_sources]},
            pluck="name",
        )

        allowed_tables = self.get_tables()
        return list(set(unrestricted_tables + allowed_tables))

    def get_allowed_queries(self):
        return self.get_queries()

    def get_allowed_dashboards(self):
        return self.get_dashboards()


def get_user_teams(user=None):
    if not user:
        user = frappe.session.user
    return _get_user_teams(user)


@site_cache(ttl=60 * 60 * 24)
def _get_user_teams(user):
    Team = frappe.qb.DocType("Insights Team")
    TeamMember = frappe.qb.DocType("Insights Team Member")
    return (
        frappe.qb.from_(Team)
        .select(Team.name)
        .distinct()
        .join(TeamMember)
        .on(Team.name == TeamMember.parent)
        .where((TeamMember.user == user))
        .run(pluck=True)
    ) or []


def has_role(user: str, role: str):
    return frappe.db.exists("Has Role", {"parent": user, "role": role})


def is_insights_admin(user=None):
    user = user or frappe.session.user
    if user == "Administrator" or has_role(user, "Insights Admin"):
        return True


def get_allowed_resources_for_user(resource_type=None, user=None):
    user = user or frappe.session.user
    permsisions_disabled = not frappe.db.get_single_value(
        "Insights Settings", "enable_permissions"
    )
    if permsisions_disabled or is_insights_admin(user):
        return frappe.get_list(resource_type, pluck="name")

    teams = get_user_teams(user)
    if not teams:
        return []

    resources = []
    for team in teams:
        team = frappe.get_cached_doc("Insights Team", team)
        resources.extend(team.get_allowed_resources(resource_type))

    if resource_type == "Insights Data Source":
        return list(set(resources))

    owned_resources = frappe.get_all(
        resource_type, filters={"owner": user}, pluck="name"
    )

    return list(set(resources + owned_resources))


def get_permission_filter(resource_type, user=None):
    if not frappe.db.get_single_value("Insights Settings", "enable_permissions"):
        return {}

    if is_insights_admin(user):
        return {}

    allowed_resource = get_allowed_resources_for_user(resource_type, user)
    if not allowed_resource:
        return {"name": "0000000"}
    return {"name": ["in", allowed_resource]}


def check_data_source_permission(source_name, user=None, raise_error=True):
    if not frappe.db.get_single_value("Insights Settings", "enable_permissions"):
        return {}

    if is_insights_admin(user):
        return True

    allowed_sources = get_allowed_resources_for_user("Insights Data Source", user)

    if source_name not in allowed_sources:
        if raise_error:
            frappe.throw(
                "You do not have permission to access this data source",
                exc=frappe.PermissionError,
            )
        else:
            return False


def check_table_permission(data_source, table, user=None, raise_error=True):
    if not frappe.db.get_single_value("Insights Settings", "enable_permissions"):
        return {}

    if is_insights_admin(user):
        return True

    # since everywhere we use table name & data source as the primary key not the name
    table_name = frappe.db.get_value(
        "Insights Table", {"data_source": data_source, "table": table}, "name"
    )
    allowed_tables = get_allowed_resources_for_user("Insights Table", user)

    if table_name not in allowed_tables:
        if raise_error:
            frappe.throw(
                "You do not have permission to access this table",
                exc=frappe.PermissionError,
            )
        else:
            return False
