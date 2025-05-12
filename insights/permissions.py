# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from functools import cached_property

import frappe
import frappe.share

from insights.insights.doctype.insights_team.insights_team import (
    get_allowed_resources_for_user,
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
]

# if team permissions are not enabled,
# then these doctypes are accessible to all insights users
TEAM_BASED_PERMISSION_DOCTYPES = [
    "Insights Data Source v3",
    "Insights Table v3",
    "Insights Team",
]


class InsightsPermissions:
    def __init__(self, user=None):
        self.user = user or frappe.session.user

    @cached_property
    def is_admin(self):
        return is_admin(self.user)

    @cached_property
    def team_permissions_enabled(self):
        return frappe.db.get_single_value("Insights Settings", "enable_permissions")

    def get_permission_query_conditions(self, doctype: str) -> str:
        if doctype not in PERMISSION_DOCTYPES:
            return ""

        if (
            doctype in TEAM_BASED_PERMISSION_DOCTYPES
            and not self.team_permissions_enabled
        ):
            return ""

        if self.is_admin:
            return ""

        if doctype == "Insights Data Source v3" or doctype == "Insights Table v3":
            allowed_docs = get_allowed_resources_for_user(doctype, self.user)
            return self._build_name_in_condition(doctype, allowed_docs)

        if doctype == "Insights Team":
            user_teams = get_teams(self.user)
            return self._build_name_in_condition(doctype, user_teams)

        if doctype in [
            "Insights Workbook",
            "Insights Dashboard v3",
            "Insights Chart v3",
            "Insights Query v3",
            "Insights Alert",
        ]:
            docs = self._get_ptype_access_docs_query(doctype, "read")
            return f"(`tab{doctype}`.name in ({docs}))"

        return ""

    def _build_name_in_condition(self, doctype: str, items: list) -> str:
        if not items:
            return f"(`tab{doctype}`.name is NULL)"

        item_list = [frappe.db.escape(item) for item in items]
        items_sql = ", ".join(item_list)
        return f"(`tab{doctype}`.name in ({items_sql}))"

    def has_doc_permission(self, doc, ptype):
        if doc.doctype not in PERMISSION_DOCTYPES:
            return True

        if (
            doc.doctype in TEAM_BASED_PERMISSION_DOCTYPES
            and not self.team_permissions_enabled
        ):
            return True

        if self.is_admin:
            return True

        if not doc.name and doc.doctype in TEAM_BASED_PERMISSION_DOCTYPES:
            # for new_doc, let further permission checks handle it
            return True

        if (
            doc.doctype == "Insights Data Source v3"
            or doc.doctype == "Insights Table v3"
        ):
            allowed_docs = get_allowed_resources_for_user(doc.doctype, self.user)
            return doc.name in allowed_docs

        if doc.doctype == "Insights Team":
            user_teams = get_teams(self.user)
            return doc.name in user_teams

        is_new = not doc.name or doc.is_new()
        is_owner = doc.owner == self.user
        access_type = "write" if ptype not in ["read", "share"] else ptype

        if doc.doctype in [
            "Insights Workbook",
            "Insights Dashboard v3",
            "Insights Chart v3",
            "Insights Query v3",
            "Insights Alert",
        ]:
            if is_new and hasattr(doc, "workbook") and doc.workbook:
                # when creating a new query/chart/dashboard
                # if it is linked to a workbook, check if user has access to the workbook
                docs = self._get_ptype_access_docs_query(
                    "Insights Workbook", access_type
                )
                return (
                    docs.where(
                        frappe.qb.DocType("Insights Workbook").name == doc.workbook
                    )
                    .limit(1)
                    .run(pluck="name")
                )

            if is_new or is_owner:
                return True

            docs = self._get_ptype_access_docs_query(doc.doctype, access_type)
            return (
                docs.where(frappe.qb.DocType(doc.doctype).name == doc.name)
                .limit(1)
                .run(pluck="name")
            )

        return False

    def _get_ptype_access_docs_query(self, doctype, ptype):
        """Returns a query to get docs with `ptype`  permission"""
        query = None
        if doctype == "Insights Workbook":
            query = self._get_ptype_access_workbooks_query(ptype)
        if doctype == "Insights Dashboard v3":
            query = self._get_ptype_access_dashboards_query(ptype)
        if doctype == "Insights Chart v3":
            query = self._get_ptype_access_charts_query(ptype)
        if doctype == "Insights Query v3":
            query = self._get_ptype_access_queries_query(ptype)
        if doctype == "Insights Alert":
            query = self._get_ptype_access_alerts_query(ptype)
        return query

    def _get_ptype_access_workbooks_query(self, ptype):
        DocShare = frappe.qb.DocType("DocShare")
        Workbook = frappe.qb.DocType("Insights Workbook")

        OwnedWorkbooks = (
            frappe.qb.from_(Workbook)
            .select(Workbook.name)
            .where(Workbook.owner == self.user)
        )

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
            .where(
                OwnedWorkbooks.name.isnotnull() | SharedWorkbooks.share_name.isnotnull()
            )
        )

    def _get_ptype_access_dashboards_query(self, ptype):
        DocShare = frappe.qb.DocType("DocShare")
        Dashboard = frappe.qb.DocType("Insights Dashboard v3")

        WorkbookWithWriteAccess = self._get_ptype_access_workbooks_query(ptype)

        OwnedDashboards = (
            frappe.qb.from_(Dashboard)
            .select(Dashboard.name)
            .where(Dashboard.owner == self.user)
        )

        SharedDashboards = (
            frappe.qb.from_(DocShare)
            .select(DocShare.share_name)
            .where(
                (DocShare.share_doctype == "Insights Dashboard v3")
                & (DocShare[ptype] == 1)
                & ((DocShare.user == self.user) | (DocShare.everyone == 1))
            )
        )

        LinkedWithWorkbookWithWriteAccess = (
            frappe.qb.from_(Dashboard)
            .select(Dashboard.name)
            .left_join(WorkbookWithWriteAccess)
            .on(Dashboard.workbook == WorkbookWithWriteAccess.name)
            .where(WorkbookWithWriteAccess.name.isnotnull())
        )

        return (
            frappe.qb.from_(Dashboard)
            .select(Dashboard.name)
            .left_join(OwnedDashboards)
            .on(Dashboard.name == OwnedDashboards.name)
            .left_join(SharedDashboards)
            .on(Dashboard.name == SharedDashboards.share_name)
            .left_join(LinkedWithWorkbookWithWriteAccess)
            .on(Dashboard.name == LinkedWithWorkbookWithWriteAccess.name)
            .where(
                OwnedDashboards.name.isnotnull()
                | SharedDashboards.share_name.isnotnull()
                | LinkedWithWorkbookWithWriteAccess.name.isnotnull()
            )
        )

    def _get_ptype_access_charts_query(self, ptype):
        DocShare = frappe.qb.DocType("DocShare")
        Chart = frappe.qb.DocType("Insights Chart v3")
        DashboardChart = frappe.qb.DocType("Insights Dashboard Chart v3")

        OwnedCharts = (
            frappe.qb.from_(Chart).select(Chart.name).where(Chart.owner == self.user)
        )

        SharedCharts = (
            frappe.qb.from_(DocShare)
            .select(DocShare.share_name)
            .where(
                (DocShare.share_doctype == "Insights Chart v3")
                & (DocShare[ptype] == 1)
                & ((DocShare.user == self.user) | (DocShare.everyone == 1))
            )
        )

        WorkbookWithWriteAccess = self._get_ptype_access_workbooks_query(ptype)

        LinkedWithWorkbookWithWriteAccess = (
            frappe.qb.from_(Chart)
            .select(Chart.name)
            .left_join(WorkbookWithWriteAccess)
            .on(Chart.workbook == WorkbookWithWriteAccess.name)
            .where(WorkbookWithWriteAccess.name.isnotnull())
        )

        DashboardWithWriteAccess = self._get_ptype_access_dashboards_query(ptype)

        DashboardChartsLinkedWithDashboardWithWriteAccess = (
            frappe.qb.from_(DashboardChart)
            .select(DashboardChart.chart)
            .left_join(DashboardWithWriteAccess)
            .on(DashboardChart.parent == DashboardWithWriteAccess.name)
            .where(DashboardWithWriteAccess.name.isnotnull())
        )

        LinkedWithDashboardWithWriteAccess = (
            frappe.qb.from_(Chart)
            .select(Chart.name)
            .left_join(DashboardChartsLinkedWithDashboardWithWriteAccess)
            .on(Chart.name == DashboardChartsLinkedWithDashboardWithWriteAccess.chart)
            .where(DashboardChartsLinkedWithDashboardWithWriteAccess.chart.isnotnull())
        )

        return (
            frappe.qb.from_(Chart)
            .select(Chart.name)
            .left_join(OwnedCharts)
            .on(Chart.name == OwnedCharts.name)
            .left_join(SharedCharts)
            .on(Chart.name == SharedCharts.share_name)
            .left_join(LinkedWithWorkbookWithWriteAccess)
            .on(Chart.name == LinkedWithWorkbookWithWriteAccess.name)
            .left_join(LinkedWithDashboardWithWriteAccess)
            .on(Chart.name == LinkedWithDashboardWithWriteAccess.name)
            .where(
                OwnedCharts.name.isnotnull()
                | SharedCharts.share_name.isnotnull()
                | LinkedWithWorkbookWithWriteAccess.name.isnotnull()
                | LinkedWithDashboardWithWriteAccess.name.isnotnull()
            )
        )

    def _get_ptype_access_queries_query(self, ptype):
        Query = frappe.qb.DocType("Insights Query v3")

        OwnedQueries = (
            frappe.qb.from_(Query).select(Query.name).where(Query.owner == self.user)
        )

        WorkbookWithWriteAccess = self._get_ptype_access_workbooks_query(ptype)

        LinkedWithWorkbookWithWriteAccess = (
            frappe.qb.from_(Query)
            .select(Query.name)
            .left_join(WorkbookWithWriteAccess)
            .on(Query.workbook == WorkbookWithWriteAccess.name)
            .where(WorkbookWithWriteAccess.name.isnotnull())
        )

        Chart = frappe.qb.DocType("Insights Chart v3")
        ChartWithWriteAccess = self._get_ptype_access_charts_query(ptype)
        ChartWithWriteAccess = ChartWithWriteAccess.select(
            Chart.data_query, Chart.query
        )

        LinkedWithChartWithWriteAccess = (
            frappe.qb.from_(Query)
            .select(Query.name)
            .left_join(ChartWithWriteAccess)
            .on(
                (Query.name == ChartWithWriteAccess.data_query)
                | (Query.name == ChartWithWriteAccess.query)
            )
            .where(ChartWithWriteAccess.name.isnotnull())
        )

        return (
            frappe.qb.from_(Query)
            .select(Query.name)
            .left_join(OwnedQueries)
            .on(Query.name == OwnedQueries.name)
            .left_join(LinkedWithWorkbookWithWriteAccess)
            .on(Query.name == LinkedWithWorkbookWithWriteAccess.name)
            .left_join(LinkedWithChartWithWriteAccess)
            .on(Query.name == LinkedWithChartWithWriteAccess.name)
            .where(
                OwnedQueries.name.isnotnull()
                | LinkedWithWorkbookWithWriteAccess.name.isnotnull()
                | LinkedWithChartWithWriteAccess.name.isnotnull()
            )
        )

    def _get_ptype_access_alerts_query(self, ptype):
        Alert = frappe.qb.DocType("Insights Alert")

        OwnedAlerts = (
            frappe.qb.from_(Alert).select(Alert.name).where(Alert.owner == self.user)
        )

        QueryWithWriteAccess = self._get_ptype_access_queries_query(ptype)

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
            .where(
                OwnedAlerts.name.isnotnull()
                | LinkedWithQueryWithWriteAccess.name.isnotnull()
            )
        )


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
