# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from pypika import CustomFunction

from insights import notify
from insights.insights.doctype.insights_team.insights_team import (
    check_data_source_permission,
    check_table_permission,
    get_allowed_resources_for_user,
    get_permission_filter,
)


@frappe.whitelist()
def get_app_version():
    return frappe.get_attr("insights" + ".__version__")


@frappe.whitelist()
def get_data_sources():
    return frappe.get_list(
        "Insights Data Source",
        filters={
            "status": "Active",
            **get_permission_filter("Insights Data Source"),
        },
        fields=["name", "title", "status", "database_type", "creation"],
        order_by="creation desc",
    )


@frappe.whitelist()
def get_data_source(name):
    check_data_source_permission(name)
    doc = frappe.get_doc("Insights Data Source", name)
    tables = get_all_tables(name)
    return {
        "doc": doc.as_dict(),
        "tables": tables,
    }


def get_all_tables(data_source=None):
    if not data_source:
        return []

    return frappe.get_list(
        "Insights Table",
        filters={
            "data_source": data_source,
            **get_permission_filter("Insights Table"),
        },
        fields=["name", "table", "label", "hidden"],
        order_by="hidden asc, label asc",
    )


@frappe.whitelist()
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
def get_tables(data_source=None):
    if not data_source:
        return []

    check_data_source_permission(data_source)

    return frappe.get_list(
        "Insights Table",
        filters={
            "hidden": 0,
            "data_source": data_source,
            **get_permission_filter("Insights Table"),
        },
        fields=["name", "table", "label"],
        order_by="label asc",
    )


@frappe.whitelist()
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
            filters={"parent": dashboard.name, "item_type": "Chart"},
            pluck="parent",
        )
    return dashboards


@frappe.whitelist()
def create_dashboard(title):
    dashboard = frappe.get_doc({"doctype": "Insights Dashboard", "title": title})
    dashboard.insert()
    return {
        "name": dashboard.name,
        "title": dashboard.title,
    }


@frappe.whitelist()
def get_queries():
    allowed_queries = get_allowed_resources_for_user("Insights Query")
    if not allowed_queries:
        return []

    Query = frappe.qb.DocType("Insights Query")
    QueryTable = frappe.qb.DocType("Insights Query Table")
    QueryChart = frappe.qb.DocType("Insights Query Chart")
    GroupConcat = CustomFunction("Group_Concat", ["column"])
    return (
        frappe.qb.from_(Query)
        .left_join(QueryTable)
        .on(Query.name == QueryTable.parent)
        .left_join(QueryChart)
        .on(QueryChart.query == Query.name)
        .select(
            Query.name,
            Query.title,
            GroupConcat(QueryTable.label).as_("tables"),
            Query.data_source,
            Query.creation,
            QueryChart.type.as_("chart_type"),
        )
        .where(Query.name.isin(allowed_queries))
        .groupby(Query.name)
        .orderby(Query.creation, order=frappe.qb.desc)
    ).run(as_dict=True)


@frappe.whitelist()
def create_query(title, data_source, table):
    check_table_permission(data_source, table.get("value"))

    query = frappe.new_doc("Insights Query")
    query.title = title
    query.data_source = data_source
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
def get_running_jobs(data_source):
    return []


@frappe.whitelist()
def kill_running_job(data_source, query_id):
    return


@frappe.whitelist()
def get_user_info():
    return {
        "user_id": frappe.session.user,
        "permissions": {
            "Query": frappe.has_permission("Insights Query", throw=False),
            "Dashboard": frappe.has_permission("Insights Dashboard", throw=False),
        },
    }


@frappe.whitelist()
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
def get_onboarding_status():
    return {
        "is_onboarded": frappe.db.get_single_value(
            "Insights Settings", "onboarding_complete"
        ),
        "query_created": bool(frappe.db.a_row_exists("Insights Query")),
        "dashboard_created": bool(frappe.db.a_row_exists("Insights Dashboard")),
        "chart_created": bool(
            frappe.db.exists(
                "Insights Query Chart", {"data": ["is", "set"], "type": ["is", "set"]}
            )
        ),
        "chart_added": bool(frappe.db.a_row_exists("Insights Dashboard Item")),
    }


@frappe.whitelist()
def skip_onboarding():
    frappe.db.set_value("Insights Settings", None, "onboarding_complete", 1)


@frappe.whitelist()
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
def sync_data_source(data_source: str):
    if not frappe.has_permission("Insights Data Source", "write"):
        frappe.throw("Not allowed", frappe.PermissionError)

    from frappe.utils.scheduler import is_scheduler_inactive

    if is_scheduler_inactive():
        notify(
            **{
                "title": "Error",
                "message": "Scheduler is inactive",
                "type": "error",
            }
        )

    frappe.enqueue(
        _sync_data_source,
        data_source=data_source,
        job_name="sync_data_source",
        queue="long",
        timeout=3600,
        now=True,
    )


def _sync_data_source(data_source):
    notify(
        **{
            "title": "Info",
            "message": "Syncing Data Source",
            "type": "info",
        }
    )
    source = frappe.get_doc("Insights Data Source", data_source)
    source.sync_tables()
    notify(
        **{
            "title": "Success",
            "message": "Data Source Synced",
            "type": "success",
        }
    )


@frappe.whitelist()
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
