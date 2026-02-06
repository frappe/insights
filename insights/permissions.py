# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from functools import cached_property

import frappe
import frappe.share

from insights.insights.doctype.insights_team.insights_team import (
    get_teams,
    is_admin,
)

PERMISSION_DOCTYPES = [
    "Insights Data Source v3",
    "Insights Table v3",
    "Insights Team",
    "Insights Workbook",
    "Insights Query v3",
    "Insights Chart v3",
    "Insights Dashboard v3",
    "Insights Alert"
]

# if team permissions are not enabled,
# then these doctypes are accessible to all insights users
TEAM_BASED_PERMISSION_DOCTYPES = [
    "Insights Data Source v3",
    "Insights Table v3",
    "Insights Team",
    "Insights Dashboard v3",
    "Insights Chart v3",
]


class InsightsPermissions:
    def __init__(self, user=None):
        self.user = user or frappe.session.user
        self.user_teams = []
        if self.team_permissions_enabled:
            self.user_teams = get_teams(self.user)

    @cached_property
    def is_admin(self):
        return is_admin(self.user)

    @cached_property
    def team_permissions_enabled(self):
        return frappe.db.get_single_value("Insights Settings", "enable_permissions")

    def get_permission_query_conditions(self, doctype: str) -> str:
        if doctype not in PERMISSION_DOCTYPES:
            return ""

        if self.is_admin:
            return ""

        if doctype == "Insights Team":
            if not self.user_teams:
                return "(`tabInsights Team`.name is NULL)"

            item_list = [frappe.db.escape(item) for item in self.user_teams]
            items_sql = ", ".join(item_list)
            return f"(`tabInsights Team`.name in ({items_sql}))"

        docs = self._build_permission_query(doctype, "read")
        if not docs:
            return ""

        return f"(`tab{doctype}`.name in ({docs}))"

    def has_doc_permission(self, doc, ptype):
        if doc.doctype not in PERMISSION_DOCTYPES:
            return True

        if self.is_admin:
            return True

        is_new = not doc.name or doc.is_new()
        if is_new and doc.doctype in ["Insights Data Source v3", "Insights Table v3"]:
            # let further permission checks handle it
            return True

        if doc.doctype == "Insights Team":
            return doc.name in self.user_teams

        is_owner = doc.owner == self.user
        access_type = "write" if ptype not in ["read", "share"] else ptype

        if is_new and hasattr(doc, "workbook") and doc.workbook:
            # when creating a new query/chart/dashboard
            # if it is linked to a workbook, check if user has access to the workbook
            docs = self._build_permission_query("Insights Workbook", access_type)
            return (
                docs.where(frappe.qb.DocType("Insights Workbook").name == doc.workbook)
                .limit(1)
                .run(pluck="name")
            )

        if is_new or is_owner:
            return True

        docs = self._build_permission_query(doc.doctype, access_type)
        return docs.where(frappe.qb.DocType(doc.doctype).name == doc.name).limit(1).run(pluck="name")

    def _build_permission_query(self, doctype, ptype):
        """Returns a query to get docs with `ptype`  permission"""
        query = None
        if doctype == "Insights Data Source v3":
            query = self._build_source_permission_query(ptype)
        if doctype == "Insights Table v3":
            query = self._build_table_permission_query(ptype)
        if doctype == "Insights Workbook":
            query = self._build_workbook_permission_query(ptype)
        if doctype == "Insights Dashboard v3":
            query = self._build_dashboard_permission_query(ptype)
        if doctype == "Insights Chart v3":
            query = self._build_chart_permission_query(ptype)
        if doctype == "Insights Query v3":
            query = self._build_query_permission_query(ptype)
        if doctype == "Insights Alert":
            query = self._build_alert_permission_query(ptype)
        return query

    def _build_source_permission_query(self, ptype):
        # if team permissions are not enabled, all data sources are accessible
        if not self.team_permissions_enabled:
            return

        # if team permissions are enabled, allow data sources of allowed tables
        Table = frappe.qb.DocType("Insights Table v3")
        AllowedTables = self._build_table_permission_query(ptype)

        return (
            frappe.qb.from_(Table)
            .select(Table.data_source)
            .left_join(AllowedTables)
            .on(Table.name == AllowedTables.name)
            .where(AllowedTables.name.isnotnull())
            .distinct()
        )

    def _build_table_permission_query(self, ptype):
        # if team permissions are not enabled, all tables are accessible
        if not self.team_permissions_enabled:
            return

        # if team permissions are enabled,
        # tables linked to user's teams are accessible
        # & all tables of data sources linked to user's teams
        AllowedTables = self._build_resource_query("Insights Table v3")

        Table = frappe.qb.DocType("Insights Table v3")
        AllowedSources = self._build_resource_query("Insights Data Source v3")
        TablesOfAllowedSources = (
            frappe.qb.from_(Table)
            .select(Table.name.as_("name"))
            .left_join(AllowedSources)
            .on(Table.data_source == AllowedSources.name)
            .where(AllowedSources.name.isnotnull())
        )

        return (
            frappe.qb.from_(Table)
            .select(Table.name)
            .left_join(AllowedTables)
            .on(Table.name == AllowedTables.name)
            .left_join(TablesOfAllowedSources)
            .on(Table.name == TablesOfAllowedSources.name)
            .where(AllowedTables.name.isnotnull() | TablesOfAllowedSources.name.isnotnull())
        )

    def _build_workbook_permission_query(self, ptype):
        DocShare = frappe.qb.DocType("DocShare")
        Workbook = frappe.qb.DocType("Insights Workbook")

        OwnedWorkbooks = frappe.qb.from_(Workbook).select(Workbook.name).where(Workbook.owner == self.user)

        SharedWorkbooks = (
            frappe.qb.from_(DocShare)
            .select(DocShare.share_name)
            .where(
                (DocShare.share_doctype == "Insights Workbook")
                & (DocShare[ptype] == 1)
                & ((DocShare.user == self.user) | (DocShare.everyone == 1))
            )
        )

        return (
            frappe.qb.from_(Workbook)
            .select(Workbook.name)
            .left_join(OwnedWorkbooks)
            .on(Workbook.name == OwnedWorkbooks.name)
            .left_join(SharedWorkbooks)
            .on(Workbook.name == SharedWorkbooks.share_name)
            .where(OwnedWorkbooks.name.isnotnull() | SharedWorkbooks.share_name.isnotnull())
        )

    def _build_dashboard_permission_query(self, ptype):
        Dashboard = frappe.qb.DocType("Insights Dashboard v3")
        OwnedDashboards = (
            frappe.qb.from_(Dashboard).select(Dashboard.name).where(Dashboard.owner == self.user)
        )

        DocShare = frappe.qb.DocType("DocShare")
        SharedDashboards = (
            frappe.qb.from_(DocShare)
            .select(DocShare.share_name)
            .where(
                (DocShare.share_doctype == "Insights Dashboard v3")
                & (DocShare[ptype] == 1)
                & ((DocShare.user == self.user) | (DocShare.everyone == 1))
            )
        )

        AllowedWorkbooks = self._build_workbook_permission_query(ptype)

        LinkedWithAllowedWorkbooks = (
            frappe.qb.from_(Dashboard)
            .select(Dashboard.name)
            .left_join(AllowedWorkbooks)
            .on(Dashboard.workbook == AllowedWorkbooks.name)
            .where(AllowedWorkbooks.name.isnotnull())
        )

        AllowedDashboards = self._build_resource_query("Insights Dashboard v3")

        return (
            frappe.qb.from_(Dashboard)
            .select(Dashboard.name)
            .left_join(OwnedDashboards)
            .on(Dashboard.name == OwnedDashboards.name)
            .left_join(SharedDashboards)
            .on(Dashboard.name == SharedDashboards.share_name)
            .left_join(LinkedWithAllowedWorkbooks)
            .on(Dashboard.name == LinkedWithAllowedWorkbooks.name)
            .left_join(AllowedDashboards)
            .on(Dashboard.name == AllowedDashboards.name)
            .where(
                OwnedDashboards.name.isnotnull()
                | SharedDashboards.share_name.isnotnull()
                | LinkedWithAllowedWorkbooks.name.isnotnull()
                | AllowedDashboards.name.isnotnull()
            )
        )

    def _build_chart_permission_query(self, ptype):
        DocShare = frappe.qb.DocType("DocShare")
        Chart = frappe.qb.DocType("Insights Chart v3")
        DashboardChart = frappe.qb.DocType("Insights Dashboard Chart v3")

        OwnedCharts = frappe.qb.from_(Chart).select(Chart.name).where(Chart.owner == self.user)

        SharedCharts = (
            frappe.qb.from_(DocShare)
            .select(DocShare.share_name)
            .where(
                (DocShare.share_doctype == "Insights Chart v3")
                & (DocShare[ptype] == 1)
                & ((DocShare.user == self.user) | (DocShare.everyone == 1))
            )
        )

        AllowedWorkbooks = self._build_workbook_permission_query(ptype)

        LinkedWithAllowedWorkbooks = (
            frappe.qb.from_(Chart)
            .select(Chart.name)
            .left_join(AllowedWorkbooks)
            .on(Chart.workbook == AllowedWorkbooks.name)
            .where(AllowedWorkbooks.name.isnotnull())
        )

        AllowedDashboards = self._build_dashboard_permission_query(ptype)

        LinkedWithAllowedDashboards = (
            frappe.qb.from_(Chart)
            .select(Chart.name)
            .left_join(DashboardChart)
            .on(Chart.name == DashboardChart.chart)
            .left_join(AllowedDashboards)
            .on(DashboardChart.parent == AllowedDashboards.name)
            .where(AllowedDashboards.name.isnotnull())
        )

        AllowedCharts = self._build_resource_query("Insights Chart v3")

        return (
            frappe.qb.from_(Chart)
            .select(Chart.name)
            .left_join(OwnedCharts)
            .on(Chart.name == OwnedCharts.name)
            .left_join(SharedCharts)
            .on(Chart.name == SharedCharts.share_name)
            .left_join(LinkedWithAllowedWorkbooks)
            .on(Chart.name == LinkedWithAllowedWorkbooks.name)
            .left_join(LinkedWithAllowedDashboards)
            .on(Chart.name == LinkedWithAllowedDashboards.name)
            .left_join(AllowedCharts)
            .on(Chart.name == AllowedCharts.name)
            .where(
                OwnedCharts.name.isnotnull()
                | SharedCharts.share_name.isnotnull()
                | LinkedWithAllowedWorkbooks.name.isnotnull()
                | LinkedWithAllowedDashboards.name.isnotnull()
                | AllowedCharts.name.isnotnull()
            )
        )

    def _build_query_permission_query(self, ptype):
        Query = frappe.qb.DocType("Insights Query v3")

        OwnedQueries = frappe.qb.from_(Query).select(Query.name).where(Query.owner == self.user)

        AllowedWorkbooks = self._build_workbook_permission_query(ptype)

        LinkedWithAllowedWorkbooks = (
            frappe.qb.from_(Query)
            .select(Query.name)
            .left_join(AllowedWorkbooks)
            .on(Query.workbook == AllowedWorkbooks.name)
            .where(AllowedWorkbooks.name.isnotnull())
        )

        Chart = frappe.qb.DocType("Insights Chart v3")
        AllowedCharts = self._build_chart_permission_query(ptype)
        AllowedCharts = AllowedCharts.select(Chart.data_query, Chart.query)

        LinkedWithAllowedCharts = (
            frappe.qb.from_(Query)
            .select(Query.name)
            .left_join(AllowedCharts)
            .on((Query.name == AllowedCharts.data_query) | (Query.name == AllowedCharts.query))
            .where(AllowedCharts.name.isnotnull())
        )

        return (
            frappe.qb.from_(Query)
            .select(Query.name)
            .left_join(OwnedQueries)
            .on(Query.name == OwnedQueries.name)
            .left_join(LinkedWithAllowedWorkbooks)
            .on(Query.name == LinkedWithAllowedWorkbooks.name)
            .left_join(LinkedWithAllowedCharts)
            .on(Query.name == LinkedWithAllowedCharts.name)
            .where(
                OwnedQueries.name.isnotnull()
                | LinkedWithAllowedWorkbooks.name.isnotnull()
                | LinkedWithAllowedCharts.name.isnotnull()
            )
        )

    def _build_alert_permission_query(self, ptype):
        Alert = frappe.qb.DocType("Insights Alert")

        OwnedAlerts = frappe.qb.from_(Alert).select(Alert.name).where(Alert.owner == self.user)

        QueryWithWriteAccess = self._build_query_permission_query(ptype)

        LinkedWithQueryWithWriteAccess = (
            frappe.qb.from_(Alert)
            .select(Alert.name)
            .left_join(QueryWithWriteAccess)
            .on(Alert.query == QueryWithWriteAccess.name)
            .where(QueryWithWriteAccess.name.isnotnull())
        )

        return (
            frappe.qb.from_(Alert)
            .select(Alert.name)
            .left_join(OwnedAlerts)
            .on(Alert.name == OwnedAlerts.name)
            .left_join(LinkedWithQueryWithWriteAccess)
            .on(Alert.name == LinkedWithQueryWithWriteAccess.name)
            .where(OwnedAlerts.name.isnotnull() | LinkedWithQueryWithWriteAccess.name.isnotnull())
        )

    def _build_resource_query(self, doctype):
        Resource = frappe.qb.DocType("Insights Resource Permission")

        condition = (Resource.resource_type == doctype) & (Resource.resource_name.isnotnull())
        if not self.user_teams:
            condition = condition & (Resource.parent.isnotnull())
        else:
            condition = condition & (Resource.parent.isin(self.user_teams))

        return frappe.qb.from_(Resource).select(Resource.resource_name.as_("name")).where(condition)


def has_doc_permission(doc, ptype, user):
    return InsightsPermissions(user).has_doc_permission(doc, ptype)


def get_permission_query_conditions(user, doctype):
    return InsightsPermissions(user).get_permission_query_conditions(doctype)


def check_app_permission():
    if frappe.session.user == "Administrator":
        return True

    roles = frappe.get_roles()
    if any(role in ["Insights User", "Insights Admin"] for role in roles):
        return True

    return False
