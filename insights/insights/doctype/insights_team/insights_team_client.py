# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.user import get_users_with_role

from insights import notify
from insights.decorators import check_permission, check_role


class InsightsTeamClient:
    @frappe.whitelist()
    def get_members_and_resources(self):
        members = self.get_members()

        resources = []
        for resource in self.team_permissions:
            title_field = (
                "label" if resource.resource_type == "Insights Table" else "title"
            )
            resources.append(
                {
                    "type": resource.resource_type,
                    "name": resource.resource_name,
                    "title": frappe.db.get_value(
                        resource.resource_type, resource.resource_name, title_field
                    ),
                }
            )

        return {
            "members": members,
            "resources": resources,
        }

    @frappe.whitelist()
    def search_team_members(self, query):
        # get all users who are not in the team
        members = [m.user for m in self.team_members]
        insights_users = get_users_with_role("Insights User")
        insights_users = list(set(insights_users) - set(members))

        if not insights_users:
            return []

        User = frappe.qb.DocType("User")

        conditions = (User.name.isin(insights_users)) & (User.enabled == 1)
        if query:
            conditions &= (User.full_name.like(f"%{query}%")) | (
                User.email.like(f"%{query}%")
            )

        return (
            frappe.qb.from_(User)
            .select(User.name, User.full_name, User.email, User.user_image)
            .where(conditions)
            .run(as_dict=True)
        )

    @frappe.whitelist()
    def search_team_resources(self, resource_type, query):
        resources = []

        if resource_type == "Insights Data Source":
            InsightsDataSource = frappe.qb.DocType("Insights Data Source")
            exclude_sources = [
                r.resource_name
                for r in self.team_permissions
                if r.resource_type == "Insights Data Source"
            ]
            conditions = InsightsDataSource.title.like(f"%{query}%") | (
                InsightsDataSource.database_type.like(f"%{query}%")
            )
            if exclude_sources:
                conditions = conditions & (
                    InsightsDataSource.name.notin(exclude_sources)
                )
            data_sources = (
                frappe.qb.from_(InsightsDataSource)
                .select(
                    InsightsDataSource.name,
                    InsightsDataSource.title,
                    InsightsDataSource.database_type,
                )
                .where(conditions)
                .limit(25)
                .run(as_dict=True)
            )

            for source in data_sources:
                resources.append(
                    {
                        "name": source.name,
                        "title": source.title,
                        "database_type": source.database_type,
                        "type": "Insights Data Source",
                    }
                )

        if resource_type == "Insights Table":
            # get all tables
            InsightsTable = frappe.qb.DocType("Insights Table")
            exclude_tables = [
                r.resource_name
                for r in self.team_permissions
                if r.resource_type == "Insights Table"
            ]
            conditions = InsightsTable.label.like(f"%{query}%") | (
                InsightsTable.data_source.like(f"%{query}%")
            )
            if exclude_tables:
                conditions = conditions & (InsightsTable.name.notin(exclude_tables))
            tables = (
                frappe.qb.from_(InsightsTable)
                .select(
                    InsightsTable.name,
                    InsightsTable.label,
                    InsightsTable.data_source,
                )
                .where(conditions)
                .limit(25)
                .run(as_dict=True)
            )
            for table in tables:
                resources.append(
                    {
                        "name": table.name,
                        "title": table.label,
                        "type": "Insights Table",
                        "data_source": table.data_source,
                    }
                )

        if resource_type == "Insights Query":
            InsightsQuery = frappe.qb.DocType("Insights Query")
            exclude_queries = [
                r.resource_name
                for r in self.team_permissions
                if r.resource_type == "Insights Query"
            ]
            conditions = InsightsQuery.title.like(f"%{query}%") | (
                InsightsQuery.data_source.like(f"%{query}%")
            )
            if exclude_queries:
                conditions = conditions & (InsightsQuery.name.notin(exclude_queries))
            queries = (
                frappe.qb.from_(InsightsQuery)
                .select(
                    InsightsQuery.name,
                    InsightsQuery.title,
                    InsightsQuery.data_source,
                )
                .where(conditions)
                .limit(25)
                .run(as_dict=True)
            )

            for query in queries:
                resources.append(
                    {
                        "name": query.name,
                        "title": query.title,
                        "data_source": query.data_source,
                        "type": "Insights Query",
                    }
                )

        if resource_type == "Insights Dashboard":
            InsightsDashboard = frappe.qb.DocType("Insights Dashboard")
            exclude_dashboards = [
                r.resource_name
                for r in self.team_permissions
                if r.resource_type == "Insights Dashboard"
            ]
            conditions = InsightsDashboard.title.like(f"%{query}%")
            if exclude_dashboards:
                conditions = conditions & (
                    InsightsDashboard.name.notin(exclude_dashboards)
                )
            dashboards = (
                frappe.qb.from_(InsightsDashboard)
                .select(InsightsDashboard.name, InsightsDashboard.title)
                .where(conditions)
                .limit(25)
                .run(as_dict=True)
            )

            for dashboard in dashboards:
                resources.append(
                    {
                        "name": dashboard.name,
                        "title": dashboard.title,
                        "type": "Insights Dashboard",
                    }
                )

        return resources

    @frappe.whitelist()
    def add_team_member(self, user):
        self.append("team_members", {"user": user})
        self.save()

    @frappe.whitelist()
    def add_team_members(self, users):
        for user in users:
            self.append("team_members", {"user": user})
        self.save()

    @frappe.whitelist()
    def remove_team_member(self, user):
        for member in self.team_members:
            if member.user == user:
                self.remove(member)
                break
        self.save()

    @frappe.whitelist()
    def add_team_resource(self, resource):
        resource = frappe._dict(resource)
        self.append(
            "team_permissions",
            {"resource_type": resource.type, "resource_name": resource.name},
        )
        self.save()

    @frappe.whitelist()
    def add_team_resources(self, resources):
        for resource in resources:
            resource = frappe._dict(resource)
            self.append(
                "team_permissions",
                {"resource_type": resource.type, "resource_name": resource.name},
            )
        self.save()

    @frappe.whitelist()
    def remove_team_resource(self, resource):
        resource = frappe._dict(resource)
        for permission in self.team_permissions:
            if (
                permission.resource_type == resource.type
                and permission.resource_name == resource.name
            ):
                self.remove(permission)
                break
        self.save()

    @frappe.whitelist()
    def delete_team(self):
        frappe.delete_doc("Insights Team", self.name)
        notify(
            type="success",
            message=f"Team {self.team_name} deleted successfully",
        )


@frappe.whitelist()
@check_role("Insights Admin")
@check_permission("Insights Team")
def get_teams():
    User = frappe.qb.DocType("User")
    Team = frappe.qb.DocType("Insights Team")
    TeamMember = frappe.qb.DocType("Insights Team Member")
    # get all teams and their member's full name, email and user image
    team_users = (
        frappe.qb.from_(Team)
        .select(Team.name, Team.team_name, User.full_name, User.email, User.user_image)
        .left_join(TeamMember)
        .on(Team.name == TeamMember.parent)
        .left_join(User)
        .on(TeamMember.user == User.name)
        .run(as_dict=True)
    )

    teams = {}
    for team_user in team_users:
        if (team_user.name, team_user.team_name) not in teams:
            team_doc = frappe.get_cached_doc("Insights Team", team_user.name)
            teams[(team_user.name, team_user.team_name)] = {
                "name": team_user.name,
                "team_name": team_user.team_name,
                "source_count": len(team_doc.get_allowed_sources() or []),
                "table_count": len(team_doc.get_allowed_tables() or []),
                "query_count": len(team_doc.get_allowed_queries() or []),
                "dashboard_count": len(team_doc.get_allowed_dashboards() or []),
                "members": [],
            }

        if not team_user.full_name:
            continue

        teams[(team_user.name, team_user.team_name)]["members"].append(
            {
                "full_name": team_user.full_name,
                "user_image": team_user.user_image,
                "email": team_user.email,
            }
        )

    return list(teams.values())


@frappe.whitelist()
def add_new_team(team_name):
    doc = frappe.new_doc("Insights Team")
    doc.team_name = team_name
    doc.save()
    notify(
        type="success",
        message=f"Team {team_name} has been created",
    )
