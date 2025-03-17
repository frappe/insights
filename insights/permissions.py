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

        if doctype == "Insights Workbook":
            allowed_workbooks = self._get_allowed_workbooks_query()
            return f"(`tab{doctype}`.name in ({allowed_workbooks}))"

        if doctype == "Insights Dashboard v3":
            allowed_dashboards = self._get_allowed_dashboards_query()
            return f"(`tab{doctype}`.name in ({allowed_dashboards}))"

        if doctype == "Insights Chart v3":
            allowed_charts = self._get_allowed_charts_query()
            return f"(`tab{doctype}`.name in ({allowed_charts}))"

        if doctype == "Insights Query v3":
            allowed_queries = self._get_allowed_queries_query()
            return f"(`tab{doctype}`.name in ({allowed_queries}))"

        return ""

    def _get_allowed_workbooks(self):
        owned = frappe.get_all(
            "Insights Workbook", filters={"owner": self.user}, pluck="name"
        )
        shared = frappe.share.get_shared("Insights Workbook", self.user)
        return list(set(owned + shared))

    def _get_allowed_workbooks_query(self):
        Workbook = frappe.qb.DocType("Insights Workbook")
        DocShare = frappe.qb.DocType("DocShare")

        shared_workbooks = (
            frappe.qb.from_(DocShare)
            .select(DocShare.share_name)
            .where(
                (DocShare.share_doctype == "Insights Workbook")
                & ((DocShare.user == self.user) | (DocShare.everyone == 1))
            )
        )

        return (
            frappe.qb.from_(Workbook)
            .select(Workbook.name)
            .where(
                (Workbook.owner == self.user) | (Workbook.name.isin(shared_workbooks))
            )
        )

    def _get_allowed_dashboards_query(self):
        Dashboard = frappe.qb.DocType("Insights Dashboard v3")
        DocShare = frappe.qb.DocType("DocShare")

        shared_dashboards = (
            frappe.qb.from_(DocShare)
            .select(DocShare.share_name)
            .where(
                (DocShare.share_doctype == "Insights Dashboard v3")
                & ((DocShare.user == self.user) | (DocShare.everyone == 1))
            )
        )

        allowed_workbooks = self._get_allowed_workbooks_query()

        return (
            frappe.qb.from_(Dashboard)
            .select(Dashboard.name)
            .where(
                (Dashboard.owner == self.user)
                | (Dashboard.name.isin(shared_dashboards))
                | (Dashboard.workbook.isin(allowed_workbooks))
            )
        )

    def _get_allowed_charts_query(self):
        Dashboard = frappe.qb.DocType("Insights Dashboard v3")
        Chart = frappe.qb.DocType("Insights Chart v3")
        DocShare = frappe.qb.DocType("DocShare")

        shared_charts = (
            frappe.qb.from_(DocShare)
            .select(DocShare.share_name)
            .where(
                (DocShare.share_doctype == "Insights Chart v3")
                & ((DocShare.user == self.user) | (DocShare.everyone == 1))
            )
        )

        allowed_dashboards = self._get_allowed_dashboards_query()
        charts_linked_with_dashboards = (
            frappe.qb.from_(Dashboard)
            .select(Dashboard.linked_charts)
            .where(Dashboard.name.isin(allowed_dashboards))
            .run(pluck="linked_charts")
        )
        charts_linked_with_dashboards = [
            frappe.parse_json(charts) for charts in charts_linked_with_dashboards
        ]
        charts_linked_with_dashboards = [
            item for sublist in charts_linked_with_dashboards for item in sublist
        ]

        return (
            frappe.qb.from_(Chart)
            .select(Chart.name)
            .where(
                (Chart.owner == self.user)
                | (Chart.name.isin(shared_charts))
                | (Chart.name.isin(charts_linked_with_dashboards))
            )
        )

    def _get_allowed_queries_query(self):
        Query = frappe.qb.DocType("Insights Query v3")
        Chart = frappe.qb.DocType("Insights Chart v3")

        allowed_workbooks = self._get_allowed_workbooks_query()
        allowed_charts = self._get_allowed_charts_query()

        queries_linked_with_charts = (
            frappe.qb.from_(Chart)
            .select(Chart.query)
            .where(Chart.name.isin(allowed_charts))
        )
        data_queries_linked_with_charts = (
            frappe.qb.from_(Chart)
            .select(Chart.data_query)
            .where(Chart.name.isin(allowed_charts))
        )

        return (
            frappe.qb.from_(Query)
            .select(Query.name)
            .where(
                (Query.owner == self.user)
                | (Query.workbook.isin(allowed_workbooks))
                | (Query.name.isin(queries_linked_with_charts))
                | (Query.name.isin(data_queries_linked_with_charts))
            )
        )

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

        is_new = not doc.name
        is_owner = doc.owner == self.user
        access_type = "write" if ptype not in ["read", "share"] else ptype

        if doc.doctype == "Insights Workbook":
            if is_new or is_owner:
                return True

            return self._has_access_to_any(doc.doctype, doc.name, access_type)

        if doc.doctype == "Insights Dashboard v3":
            if is_owner:
                return True

            if is_new:
                return self._has_access_to_any(
                    "Insights Workbook", doc.workbook, access_type
                )

            return (
                self._has_access_to_any(doc.doctype, doc.name, access_type)
                or self._has_access_to_any(
                    "Insights Workbook", doc.workbook, access_type
                )
                or False  # to break the line
            )

        if doc.doctype == "Insights Chart v3":
            if is_owner:
                return True

            if is_new:
                return self._has_access_to_any(
                    "Insights Workbook", doc.workbook, access_type
                )

            dashboards = lambda: frappe.get_all(
                "Insights Dashboard v3",
                filters={"linked_charts": ["like", f"%{doc.name}%"]},
                pluck="name",
            )

            return (
                self._has_access_to_any(doc.doctype, doc.name, access_type)
                or self._has_access_to_any(
                    "Insights Workbook", doc.workbook, access_type
                )
                or self._has_access_to_any(
                    "Insights Dashboard v3", dashboards(), access_type
                )
            )

        if doc.doctype == "Insights Query v3":
            if is_owner:
                return True

            if is_new:
                return self._has_access_to_any(
                    "Insights Workbook", doc.workbook, access_type
                )

            charts = lambda: frappe.get_all(
                "Insights Chart v3",
                filters={"query": doc.name},
                pluck="name",
            ) + frappe.get_all(
                "Insights Chart v3",
                filters={"data_query": doc.name},
                pluck="name",
            )

            return (
                self._has_access_to_any(doc.doctype, doc.name, access_type)
                or self._has_access_to_any(
                    "Insights Workbook", doc.workbook, access_type
                )
                or self._has_access_to_any("Insights Chart v3", charts(), access_type)
            )

        return False

    def _has_access_to_any(self, doctype, names, access_type):
        names = [names] if isinstance(names, str) else names
        if not names:
            return False

        allowed_docs = None
        if doctype == "Insights Workbook":
            Workbook = frappe.qb.DocType("Insights Workbook")
            allowed_docs = self._get_allowed_workbooks_query()
            allowed_docs = allowed_docs.where(Workbook.name.isin(names))
        if doctype == "Insights Dashboard v3":
            Dashboard = frappe.qb.DocType("Insights Dashboard v3")
            allowed_docs = self._get_allowed_dashboards_query()
            allowed_docs = allowed_docs.where(Dashboard.name.isin(names))
        if doctype == "Insights Chart v3":
            Chart = frappe.qb.DocType("Insights Chart v3")
            allowed_docs = self._get_allowed_charts_query()
            allowed_docs = allowed_docs.where(Chart.name.isin(names))
        if doctype == "Insights Query v3":
            Query = frappe.qb.DocType("Insights Query v3")
            allowed_docs = self._get_allowed_queries_query()
            allowed_docs = allowed_docs.where(Query.name.isin(names))

        if not allowed_docs:
            return False

        if access_type == "read":
            return allowed_docs.limit(1).run(pluck="name")

        DocShare = frappe.qb.DocType("DocShare")
        docshare_with_ptype = (
            frappe.qb.from_(DocShare)
            .select(DocShare.name)
            .where(
                (DocShare[access_type] == 1)
                & (DocShare.share_name.isin(names))
                & (DocShare.share_doctype == doctype)
                & ((DocShare.user == self.user) | (DocShare.everyone == 1))
            )
        )

        return (
            docshare_with_ptype.where(
                DocShare.share_name.isin(allowed_docs),
            )
            .limit(1)
            .run(pluck="name")
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
