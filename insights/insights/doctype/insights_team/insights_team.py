# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InsightsTeam(Document):
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

    def get_table_sources(self):
        return frappe.get_all(
            "Insights Table",
            filters={"name": ["in", self.get_tables()]},
            pluck="data_source",
        )

    def get_tables(self):
        return [
            d.resource_name
            for d in self.team_permissions
            if d.resource_type == "Insights Table"
        ]

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
        return unrestricted_sources + table_sources

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

    def get_allowed_tables(self):
        unrestricted_sources = self.get_sources()
        unrestricted_tables = frappe.get_all(
            "Insights Table",
            filters={"data_source": ["in", unrestricted_sources]},
            pluck="name",
        )

        allowed_tables = self.get_tables()
        return unrestricted_tables + allowed_tables

    def get_allowed_queries(self):
        from frappe.query_builder.functions import CustomFunction

        allowed_tables = self.get_allowed_tables()
        allowed_table_names = frappe.get_all(
            "Insights Table",
            filters={"name": ["in", allowed_tables]},
            pluck="table",
        )
        InsightsQuery = frappe.qb.DocType("Insights Query")
        InsightsQueryTable = frappe.qb.DocType("Insights Query Table")
        JSONExtract = CustomFunction("JSON_EXTRACT", ["json", "path"])

        conditions = InsightsQuery.data_source.isin(self.get_allowed_sources())
        if allowed_table_names:
            conditions &= InsightsQueryTable.table.isin(
                allowed_table_names
            ) | JSONExtract(InsightsQueryTable.join, "$.with.value").isin(
                allowed_table_names
            )

        return (
            frappe.qb.from_(InsightsQuery)
            .join(InsightsQueryTable)
            .on(InsightsQuery.name == InsightsQueryTable.parent)
            .where(conditions)
            .select(InsightsQuery.name)
            .distinct()
            .run(pluck=True)
        ) or []

    def get_allowed_dashboards(self):
        allowed_queries = self.get_allowed_queries()
        InsightsDashboard = frappe.qb.DocType("Insights Dashboard")
        InsightsDashboardItem = frappe.qb.DocType("Insights Dashboard Item")
        return (
            frappe.qb.from_(InsightsDashboard)
            .select(InsightsDashboard.name)
            .distinct()
            .join(InsightsDashboardItem)
            .on(InsightsDashboard.name == InsightsDashboardItem.parent)
            .where(InsightsDashboardItem.query.isin(allowed_queries))
            .run(pluck=True)
        ) or []


def get_user_teams(user=None):
    if not user:
        user = frappe.session.user

    Team = frappe.qb.DocType("Insights Team")
    TeamMember = frappe.qb.DocType("Insights Team Member")
    return (
        frappe.qb.from_(Team)
        .select(Team.name)
        .distinct()
        .join(TeamMember)
        .on(Team.name == TeamMember.parent)
        .where((Team.disabled == 0) & (TeamMember.user == user))
        .run(pluck=True)
    ) or []


def get_allowed_resources_for_user(resource_type=None, user=None):
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return frappe.get_all(resource_type, pluck="name")

    teams = get_user_teams(user)
    if not teams:
        return []

    resources = []
    for team in teams:
        team = frappe.get_doc("Insights Team", team)
        resources.extend(team.get_allowed_resources(resource_type))

    return resources
