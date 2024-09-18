# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from insights.insights.doctype.insights_team.insights_team import (
    get_allowed_resources_for_user,
    get_teams,
    is_admin,
)


def has_doc_permission(doc, ptype, user):
    if doc.doctype not in [
        "Insights Data Source v3",
        "Insights Table v3",
    ]:
        return True

    # only check if doc exists
    if not doc.name:
        return True

    if not frappe.db.get_single_value("Insights Settings", "enable_permissions"):
        return True

    if not user:
        user = frappe.session.user

    if is_admin(user):
        return True

    allowed_resources = get_allowed_resources_for_user(doc.doctype, user)
    if doc.name in allowed_resources:
        return True

    return False


def get_data_source_query_conditions(user):
    allowed_sources = get_allowed_resources_for_user("Insights Data Source v3", user)
    if not allowed_sources:
        return """(`tabInsights Data Source v3`.name is NULL)"""

    return """(`tabInsights Data Source v3`.name in ({sources}))""".format(
        sources=", ".join(frappe.db.escape(sources) for sources in allowed_sources)
    )


def get_table_query_conditions(user):
    allowed_tables = get_allowed_resources_for_user("Insights Table v3", user)
    if not allowed_tables:
        return """(`tabInsights Table v3`.name is NULL)"""

    return """(`tabInsights Table v3`.name in ({tables}))""".format(
        tables=", ".join(frappe.db.escape(tables) for tables in allowed_tables)
    )


def get_team_query_conditions(user):
    if is_admin(user):
        return ""

    user_teams = get_teams(user)
    if not user_teams:
        return """(`tabInsights Team`.name is NULL)"""

    return """(`tabInsights Team`.name in ({teams}))""".format(
        teams=", ".join(frappe.db.escape(team) for team in user_teams)
    )
