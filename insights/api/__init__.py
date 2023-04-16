# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from insights import notify
from insights.api.permissions import is_private
from insights.decorators import check_role
from insights.insights.doctype.insights_team.insights_team import (
    check_data_source_permission,
    check_table_permission,
    get_allowed_resources_for_user,
    get_permission_filter,
)


@frappe.whitelist()
@check_role("Insights User")
def get_app_version():
    return frappe.get_attr("insights" + ".__version__")


@frappe.whitelist()
@check_role("Insights User")
def get_data_sources():
    return frappe.get_list(
        "Insights Data Source",
        filters={
            "status": "Active",
            **get_permission_filter("Insights Data Source"),
        },
        fields=["name", "title", "status", "database_type", "creation", "is_site_db"],
        order_by="creation desc",
    )


@frappe.whitelist()
@check_role("Insights User")
def get_table_columns(data_source, table):
    check_table_permission(data_source, table)

    doc = frappe.get_doc(
        "Insights Table",
        {
            "data_source": data_source,
            "table": table,
        },
    )

    return {"columns": doc.columns}


@frappe.whitelist()
@check_role("Insights User")
def get_table_name(data_source, table):
    check_table_permission(data_source, table)
    return frappe.get_value(
        "Insights Table", {"data_source": data_source, "table": table}, "name"
    )


@frappe.whitelist()
@check_role("Insights User")
def get_tables(data_source=None, with_query_tables=False):
    if not data_source:
        return []

    check_data_source_permission(data_source)
    filters = {
        "hidden": 0,
        "data_source": data_source,
        **get_permission_filter("Insights Table"),
    }
    if not with_query_tables:
        filters["is_query_based"] = 0

    return frappe.get_list(
        "Insights Table",
        filters=filters,
        fields=["name", "table", "label", "is_query_based"],
        order_by="is_query_based asc, label asc",
    )


@frappe.whitelist()
@check_role("Insights User")
def get_dashboard_list():
    dashboards = frappe.get_list(
        "Insights Dashboard",
        filters={**get_permission_filter("Insights Dashboard")},
        fields=["name", "title", "modified", "_liked_by"],
    )
    for dashboard in dashboards:
        if dashboard._liked_by:
            dashboard["is_favourite"] = frappe.session.user in frappe.as_json(
                dashboard._liked_by
            )
        dashboard["charts"] = frappe.get_all(
            "Insights Dashboard Item",
            filters={
                "parent": dashboard.name,
                "item_type": ["not in", ["Text", "Filter"]],
            },
            pluck="parent",
        )
        dashboard["charts_count"] = len(dashboard["charts"])

        dashboard["is_private"] = is_private("Insights Dashboard", dashboard.name)

    return dashboards


@frappe.whitelist()
@check_role("Insights User")
def create_dashboard(title):
    dashboard = frappe.get_doc({"doctype": "Insights Dashboard", "title": title})
    dashboard.insert()
    return {
        "name": dashboard.name,
        "title": dashboard.title,
    }


@frappe.whitelist()
@check_role("Insights User")
def get_queries():
    allowed_queries = get_allowed_resources_for_user("Insights Query")
    if not allowed_queries:
        return []

    Query = frappe.qb.DocType("Insights Query")
    return (
        frappe.qb.from_(Query)
        .select(
            Query.name, Query.title, Query.data_source, Query.creation, Query.is_stored
        )
        .where(Query.name.isin(allowed_queries))
        .groupby(Query.name)
        .orderby(Query.creation, order=frappe.qb.desc)
    ).run(as_dict=True)


@frappe.whitelist()
@check_role("Insights User")
def create_query(data_source, table=None, title=None):
    query = frappe.new_doc("Insights Query")
    query.title = title or "Untitled Query"
    query.data_source = data_source
    if table:
        query.append(
            "tables",
            {
                "table": table.get("value"),
                "label": table.get("label"),
            },
        )
    query.save()
    return query.name


@frappe.whitelist()
@check_role("Insights User")
def get_running_jobs(data_source):
    return []


@frappe.whitelist()
@check_role("Insights User")
def kill_running_job(data_source, query_id):
    return


@frappe.whitelist()
@check_role("Insights User")
def get_user_info():
    is_admin = frappe.db.exists(
        "Has Role", {"parent": frappe.session.user, "role": "Insights Admin"}
    )
    is_user = frappe.db.exists(
        "Has Role", {"parent": frappe.session.user, "role": "Insights User"}
    )

    return {
        "user_id": frappe.session.user,
        "is_admin": is_admin or frappe.session.user == "Administrator",
        "is_user": is_user,
    }


@frappe.whitelist()
@check_role("Insights User")
def create_table_link(
    data_source, primary_table, foreign_table, primary_key, foreign_key
):

    check_table_permission(data_source, primary_table.get("value"))
    check_table_permission(data_source, foreign_table.get("value"))

    primary = frappe.get_doc(
        "Insights Table",
        {
            "data_source": data_source,
            "table": primary_table.get("table"),
        },
    )
    link = {
        "primary_key": primary_key,
        "foreign_key": foreign_key,
        "foreign_table": foreign_table.get("table"),
        "foreign_table_label": foreign_table.get("label"),
    }
    if not primary.get("table_links", link):
        primary.append("table_links", link)
        primary.save()

    foreign = frappe.get_doc(
        "Insights Table",
        {
            "data_source": data_source,
            "table": foreign_table.get("table"),
        },
    )
    link = {
        "primary_key": foreign_key,
        "foreign_key": primary_key,
        "foreign_table": primary_table.get("table"),
        "foreign_table_label": primary_table.get("label"),
    }
    if not foreign.get("table_links", link):
        foreign.append("table_links", link)
        foreign.save()


@frappe.whitelist()
@check_role("Insights User")
def get_onboarding_status():
    return {
        "is_onboarded": frappe.db.get_single_value(
            "Insights Settings", "onboarding_complete"
        ),
        "query_created": bool(frappe.db.a_row_exists("Insights Query")),
        "dashboard_created": bool(frappe.db.a_row_exists("Insights Dashboard")),
        "chart_created": bool(frappe.db.a_row_exists("Insights Dashboard Item")),
        "chart_added": bool(frappe.db.a_row_exists("Insights Dashboard Item")),
    }


@frappe.whitelist()
@check_role("Insights User")
def skip_onboarding():
    frappe.db.set_value("Insights Settings", None, "onboarding_complete", 1)


@frappe.whitelist()
@check_role("Insights User")
def get_dashboard_options(chart):
    allowed_dashboards = get_allowed_resources_for_user("Insights Dashboard")
    if not allowed_dashboards:
        return []

    # find all dashboards that don't have the chart within the allowed dashboards
    Dashboard = frappe.qb.DocType("Insights Dashboard")
    DashboardItem = frappe.qb.DocType("Insights Dashboard Item")

    return (
        frappe.qb.from_(Dashboard)
        .left_join(DashboardItem)
        .on(Dashboard.name == DashboardItem.parent)
        .select(Dashboard.name.as_("value"), Dashboard.title.as_("label"))
        .where(Dashboard.name.isin(allowed_dashboards) & (DashboardItem.chart != chart))
        .groupby(Dashboard.name)
        .run(as_dict=True)
    )


def get_csv_from_base64(encoded_string):
    import base64
    from io import StringIO

    data = encoded_string.split(",")[1]  # remove data uri
    data = base64.b64decode(data)
    data = StringIO(data.decode("unicode_escape"))
    return data


@frappe.whitelist()
@check_role("Insights User")
def get_columns_from_csv(file):
    import csv

    file_type = file.get("type")
    data = file.get("data")  # base64 encoded

    if file_type == "text/csv":
        data = get_csv_from_base64(data)
        reader = csv.reader(data)
        return next(reader)


def create_csv_file(file):
    file_doc = frappe.new_doc("File")
    file_doc.file_name = file.get("name")
    file_doc.content = get_csv_from_base64(file.get("data")).read()
    file_doc.save(ignore_permissions=True)
    return file_doc


@frappe.whitelist()
@check_role("Insights User")
def upload_csv(data_source, label, file, if_exists, columns):
    table_import = frappe.new_doc("Insights Table Import")
    table_import.data_source = data_source
    table_import.table_name = frappe.scrub(label)
    table_import.table_label = label
    table_import.if_exists = if_exists
    table_import.source = create_csv_file(file).file_url
    table_import.save()
    table_import.columns = []
    for column in columns:
        table_import.append(
            "columns",
            {
                "column": frappe.scrub(column.get("column")),
                "label": frappe.unscrub(column.get("column")),
                "type": column.get("type"),
            },
        )
    table_import.submit()
    notify(
        **{
            "title": "Success",
            "message": "Table Imported",
            "type": "success",
        }
    )


@frappe.whitelist()
@check_role("Insights User")
def delete_data_source(data_source):
    try:
        frappe.delete_doc("Insights Data Source", data_source)
        notify(
            **{
                "title": "Success",
                "message": "Data Source Deleted",
                "type": "success",
            }
        )
    except frappe.LinkExistsError:
        notify(
            **{
                "type": "error",
                "title": "Cannot delete Data Source",
                "message": "Data Source is linked to a Query or Dashboard",
            }
        )
    except Exception as e:
        notify(
            **{
                "type": "error",
                "title": "Error",
                "message": e,
            }
        )


@frappe.whitelist()
def create_alert(alert):
    alert = frappe._dict(alert)
    alert_doc = frappe.new_doc("Insights Alert")
    alert_doc.update(alert)
    alert_doc.save()
    return alert_doc


@frappe.whitelist()
def test_alert(alert):
    alert_doc = frappe.new_doc("Insights Alert")
    alert_doc.update(alert)
    should_send = alert_doc.evaluate_condition()
    if should_send:
        alert_doc.send_alert()
        return True
    return False


@frappe.whitelist()
def get_public_key(resource_type, resource_name):
    from insights.insights.doctype.insights_chart.insights_chart import (
        get_chart_public_key,
    )
    from insights.insights.doctype.insights_dashboard.insights_dashboard import (
        get_dashboard_public_key,
    )

    if resource_type == "Insights Dashboard":
        return get_dashboard_public_key(resource_name)
    if resource_type == "Insights Chart":
        return get_chart_public_key(resource_name)


@frappe.whitelist(allow_guest=True)
def get_public_dashboard(public_key):
    if not public_key or not isinstance(public_key, str):
        frappe.throw("Public Key is required")

    dashboard_name = frappe.db.exists(
        "Insights Dashboard", {"public_key": public_key, "is_public": 1}
    )
    if not dashboard_name:
        frappe.throw("Invalid Public Key")

    return frappe.get_cached_doc("Insights Dashboard", dashboard_name).as_dict(
        no_default_fields=True
    )


@frappe.whitelist(allow_guest=True)
def get_public_chart(public_key):
    if not public_key or not isinstance(public_key, str):
        frappe.throw("Public Key is required")

    chart_name = frappe.db.exists(
        "Insights Chart", {"public_key": public_key, "is_public": 1}
    )
    if not chart_name:
        frappe.throw("Invalid Public Key")

    chart = frappe.get_cached_doc("Insights Chart", chart_name).as_dict(
        no_default_fields=True
    )
    chart_data = frappe.get_cached_doc("Insights Query", chart.query).fetch_results()
    chart["data"] = chart_data
    return chart


@frappe.whitelist(allow_guest=True)
def get_public_dashboard_chart_data(public_key, *args, **kwargs):
    if not public_key or not isinstance(public_key, str):
        frappe.throw("Public Key is required")

    dashboard_name = frappe.db.exists(
        "Insights Dashboard", {"public_key": public_key, "is_public": 1}
    )
    if not dashboard_name:
        frappe.throw("Invalid Public Key")

    kwargs.pop("cmd")
    return frappe.get_cached_doc("Insights Dashboard", dashboard_name).fetch_chart_data(
        *args, **kwargs
    )


@frappe.whitelist()
def fetch_column_values(column, search_text=None):
    if not column.get("data_source"):
        frappe.throw("Data Source is required")
    data_source = frappe.get_doc("Insights Data Source", column.get("data_source"))
    return data_source.get_column_options(
        column.get("table"), column.get("column"), search_text
    )


@frappe.whitelist()
def get_notebooks():
    # TODO: Add permission check
    return frappe.get_list(
        "Insights Notebook",
        fields=["name", "title", "creation", "modified"],
        order_by="creation desc",
    )


@frappe.whitelist()
def create_notebook(title):
    notebook = frappe.new_doc("Insights Notebook")
    notebook.title = title
    notebook.save()
    return notebook.name


@frappe.whitelist()
def create_notebook_page(notebook):
    notebook_page = frappe.new_doc("Insights Notebook Page")
    notebook_page.notebook = notebook
    notebook_page.title = "Untitled"
    notebook_page.save()
    return notebook_page.name


@frappe.whitelist()
def get_notebook_pages(notebook):
    return frappe.get_list(
        "Insights Notebook Page",
        filters={"notebook": notebook},
        fields=["name", "title", "creation", "modified"],
        order_by="creation desc",
    )
