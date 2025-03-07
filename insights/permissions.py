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

        allowed_workbooks = self._get_allowed_workbooks()
        if doctype == "Insights Workbook":
            return self._build_name_in_condition(doctype, allowed_workbooks)

        if (
            doctype == "Insights Query v3"
            or doctype == "Insights Chart v3"
            or doctype == "Insights Dashboard v3"
        ):
            return self._build_workbook_in_condition(doctype, allowed_workbooks)

        return ""

    def _get_allowed_workbooks(self):
        owned = frappe.get_all(
            "Insights Workbook", filters={"owner": self.user}, pluck="name"
        )
        shared = frappe.share.get_shared("Insights Workbook", self.user)
        return list(set(owned + shared))

    def _build_name_in_condition(self, doctype: str, items: list) -> str:
        if not items:
            return f"(`tab{doctype}`.name is NULL)"

        item_list = [frappe.db.escape(item) for item in items]
        items_sql = ", ".join(item_list)
        return f"(`tab{doctype}`.name in ({items_sql}))"

    def _build_workbook_in_condition(self, doctype: str, items: list) -> str:
        if not items:
            return f"(`tab{doctype}`.name is NULL)"

        item_list = [frappe.db.escape(item) for item in items]
        items_sql = ", ".join(item_list)
        return f"(`tab{doctype}`.workbook in ({items_sql}))"

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

        if doc.doctype in TEAM_BASED_PERMISSION_DOCTYPES and not doc.name:
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

        if doc.doctype == "Insights Workbook":
            if not doc.name:
                return True

            if doc.owner == self.user:
                return True

            return self._has_workbook_permission(doc.name, ptype)

        if (
            doc.doctype == "Insights Query v3"
            or doc.doctype == "Insights Chart v3"
            or doc.doctype == "Insights Dashboard v3"
        ):
            # this also makes sure that a user cannot create a query/chart/dashboard
            # for a workbook that they don't have access to
            return self._has_workbook_permission(doc.workbook, ptype)

        return False

    def _has_workbook_permission(self, workbook_name, ptype):
        shared_with_user = frappe.db.get_value(
            "DocShare",
            {
                "user": self.user,
                "share_name": workbook_name,
                "share_doctype": "Insights Workbook",
            },
            ["read", "write"],
            as_dict=1,
        )
        if shared_with_user and shared_with_user.get(ptype):
            return True

        shared_with_everyone = frappe.db.get_value(
            "DocShare",
            {
                "everyone": 1,
                "share_name": workbook_name,
                "share_doctype": "Insights Workbook",
            },
            ["read", "write"],
            as_dict=1,
        )
        if shared_with_everyone and shared_with_everyone.get(ptype):
            return True

        return False


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
