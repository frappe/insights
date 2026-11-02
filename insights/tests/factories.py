import unittest
from contextlib import contextmanager, suppress

import frappe
from duckdb import CatalogException

import insights
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections


class DT:
    DATA_SOURCE = "Insights Data Source v3"
    TABLE = "Insights Table v3"
    WORKBOOK = "Insights Workbook"
    QUERY = "Insights Query v3"
    CHART = "Insights Chart v3"
    DASHBOARD = "Insights Dashboard v3"
    TEAM = "Insights Team"
    SETTINGS = "Insights Settings"
    USER = "User"


USER_1 = "workbook_flow_user@test.com"
TEST_WORKBOOK_TITLE = "Workbook Flow Test Workbook"
TEST_QUERY_TITLE = "Workbook Flow Test Query"
TEST_CHART_TITLE = "Workbook Flow Test Chart"
TEST_DASHBOARD_TITLE = "Workbook Flow Test Dashboard"
UUID_DOCTYPE = "Insights Test UUID Name"


@contextmanager
def as_user(user):
    original_user = frappe.session.user
    frappe.set_user(user)
    try:
        yield
    finally:
        frappe.set_user(original_user)


def create_user(
    email,
    first_name="Test",
    last_name="User",
    roles=None,
    user_type="System User",
    **kwargs,
):
    if frappe.db.exists(DT.USER, email):
        user = frappe.get_doc(DT.USER, email)
    else:
        user = frappe.get_doc(
            {
                "doctype": DT.USER,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "send_welcome_email": 0,
                "user_type": user_type,
                "enabled": 1,
                **kwargs,
            }
        ).insert(ignore_permissions=True)

    if roles and not isinstance(roles, list | tuple | set):
        roles = [roles]

    for role in roles or []:
        if not frappe.db.exists("Has Role", {"parent": email, "role": role}):
            user.add_roles(role)

    return frappe.get_doc(DT.USER, email)


def create_test_user(email=USER_1, role="Insights User"):
    return create_user(
        email,
        first_name="Workbook",
        last_name="Flow User",
        roles=role,
    )


def delete_users(*emails):
    for email in emails:
        frappe.delete_doc(DT.USER, email, force=True)


def delete_test_users():
    delete_users(USER_1)


def create_test_workbook(owner, title=TEST_WORKBOOK_TITLE):
    with as_user(owner):
        return frappe.get_doc({"doctype": DT.WORKBOOK, "title": title}).insert()


def create_test_query(owner, workbook, title=TEST_QUERY_TITLE, operations=None):
    with as_user(owner):
        return frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": title,
                "workbook": workbook,
                "use_live_connection": 1,
                "is_builder_query": 1,
                "operations": operations
                or [
                    {
                        "type": "source",
                        "table": {
                            "type": "table",
                            "data_source": "Site DB",
                            "table_name": "tabToDo",
                        },
                    }
                ],
            }
        ).insert()


def create_test_chart(owner, workbook, query=None, title=TEST_CHART_TITLE):
    with as_user(owner):
        chart = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": title,
                "workbook": workbook,
                "query": query,
                "chart_type": "Bar",
                "config": {},
            }
        ).insert()
    return frappe.get_doc(DT.CHART, chart.name)


def create_test_dashboard(owner, workbook, chart=None, title=TEST_DASHBOARD_TITLE):
    with as_user(owner):
        items = []
        if chart:
            items.append({"id": "chart-1", "type": "chart", "chart": chart})

        dashboard = frappe.get_doc(
            {
                "doctype": DT.DASHBOARD,
                "title": title,
                "workbook": workbook,
                "items": items,
            }
        ).insert()
    return frappe.get_doc(DT.DASHBOARD, dashboard.name)


def execute_test_query(query_name):
    query = frappe.get_doc(DT.QUERY, query_name)
    with db_connections():
        return query.execute()


def is_visible(doctype, name):
    return bool(frappe.get_list(doctype, filters={"name": name}, pluck="name", limit=1))


def delete_workbooks(title_prefix=None, owners=None):
    if not title_prefix and not owners:
        raise ValueError("delete_workbooks requires a title_prefix or owners")

    filters = {}
    if title_prefix:
        filters["title"] = ["like", f"{title_prefix}%"]
    if owners:
        filters["owner"] = ["in", list(owners)]

    workbooks = frappe.get_all(DT.WORKBOOK, filters=filters, pluck="name")
    for workbook in workbooks:
        frappe.delete_doc(DT.WORKBOOK, workbook, force=True)


def delete_test_workbooks():
    delete_workbooks(title_prefix=TEST_WORKBOOK_TITLE)


def cleanup_workbook_flow_fixtures():
    delete_test_workbooks()
    delete_test_users()


def skip_without_uuid_type():
    # MariaDB has a `uuid` type from 10.7; CI's server tests run on 10.6
    version = frappe.db.sql("select version()")[0][0].split("-")[0]
    if frappe.db.db_type != "mariadb" or tuple(map(int, version.split(".")[:2])) < (10, 7):
        raise unittest.SkipTest(f"needs MariaDB 10.7 or later for a uuid name, found {version}")


def create_uuid_doctype(name=UUID_DOCTYPE):
    """A DocType named by a MariaDB `uuid`, whose rows an Insights User reads only when they own them."""
    if not frappe.db.exists("DocType", name):
        frappe.get_doc(
            {
                "doctype": "DocType",
                "name": name,
                "module": "Insights",
                "custom": 1,
                "autoname": "UUID",
                "fields": [{"fieldname": "title", "fieldtype": "Data", "label": "Title"}],
                "permissions": [
                    {"role": "System Manager", "read": 1, "write": 1, "create": 1},
                    {"role": "Insights User", "read": 1, "if_owner": 1},
                ],
            }
        ).insert()

    table = {"data_source": "Site DB", "table": f"tab{name}"}
    if not frappe.db.exists(DT.TABLE, table):
        frappe.get_doc({"doctype": DT.TABLE, "label": name, **table}).insert(ignore_permissions=True)


def delete_uuid_doctype(name=UUID_DOCTYPE):
    # the data store has no schema for Site DB until its first import
    with suppress(CatalogException):
        insights.warehouse.get_table("Site DB", f"tab{name}").drop()
    frappe.db.delete("Insights Table Import Log", {"data_source": "Site DB", "table_name": f"tab{name}"})
    frappe.db.delete(DT.TABLE, {"data_source": "Site DB", "table": f"tab{name}"})
    frappe.delete_doc("DocType", name, force=True, ignore_permissions=True)
    # deleting a DocType keeps its table, and the next run would read its rows
    frappe.db.sql_ddl(f"drop table if exists `tab{name}`")
