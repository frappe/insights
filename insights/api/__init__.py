# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from pypika import CustomFunction

from insights import notify


@frappe.whitelist()
def get_app_version():
    return frappe.get_attr("insights" + ".__version__")


@frappe.whitelist()
def get_data_sources():
    return frappe.get_list(
        "Insights Data Source",
        filters={"status": "Active"},
        fields=["name", "title", "status", "database_type", "modified"],
    )


@frappe.whitelist()
def get_data_source(name):
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
        },
        fields=["name", "table", "label", "hidden"],
        order_by="hidden asc, label asc",
    )


@frappe.whitelist()
def get_table_columns(data_source, table):
    doc = frappe.get_doc(
        "Insights Table",
        {
            "data_source": data_source,
            "table": table,
        },
    )
    return {"columns": doc.columns}


@frappe.whitelist()
def update_data_source_table(name, table, hidden):
    table = frappe.get_doc(
        "Insights Table",
        {
            "data_source": name,
            "table": table,
        },
    )
    table.hidden = hidden
    table.save()


@frappe.whitelist()
def get_tables(data_source=None):
    if not data_source:
        return []

    return frappe.get_list(
        "Insights Table",
        filters={
            "hidden": 0,
            "data_source": data_source,
        },
        fields=["name", "table", "label"],
        order_by="label asc",
    )


@frappe.whitelist()
def get_dashboard_list():
    return frappe.get_list(
        "Insights Dashboard",
        fields=["name", "title", "modified"],
    )


@frappe.whitelist()
def create_dashboard(title):
    dashboard = frappe.get_doc(
        {"doctype": "Insights Dashboard", "title": title}
    ).insert()
    return {
        "name": dashboard.name,
        "title": dashboard.title,
    }


@frappe.whitelist()
def get_queries():
    frappe.has_permission("Insights Query", throw=True)
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
            Query.modified,
            QueryChart.type.as_("chart_type"),
        )
        .groupby(Query.name)
        .orderby(Query.modified, order=frappe.qb.desc)
    ).run(as_dict=True)


@frappe.whitelist()
def create_query(title, data_source, table):
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
    DashboardItem = frappe.qb.DocType("Insights Dashboard Item")

    exclude_dashboards = (
        frappe.qb.from_(DashboardItem)
        .select(DashboardItem.parent)
        .distinct()
        .where(DashboardItem.chart == chart)
        .run(pluck="parent")
    )
    return frappe.get_list(
        "Insights Dashboard",
        filters={"name": ["not in", exclude_dashboards]},
        fields=["name as value", "title as label"],
    )


def get_csv_from_base64(encoded_string):
    import base64
    from io import StringIO

    data = encoded_string.split(",")[1]  # remove data uri
    data = base64.b64decode(data)
    data = StringIO(data.decode("utf-8"))
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
    file_doc.save()
    return file_doc


@frappe.whitelist()
def upload_csv(label, file, if_exists, columns):
    table_import = frappe.new_doc("Insights Table Import")
    table_import.data_source = "Site DB"
    table_import.table_name = frappe.scrub(label)
    table_import.table_label = label
    table_import.if_exists = if_exists
    table_import.source = create_csv_file(file).file_url
    for column in columns:
        table_import.append(
            "columns",
            {
                "column": frappe.scrub(column.get("label")),
                "label": column.get("label"),
                "type": column.get("data_type"),
            },
        )
    table_import.save()
    table_import.submit()


@frappe.whitelist()
def sync_data_source(data_source):
    data_source = frappe.get_doc("Insights Data Source", data_source)
    notify("Syncing Tables")
    data_source.sync_tables.enqueue(self=data_source)
    notify("Tables Synced Successfully")


@frappe.whitelist()
def get_query_data(query):
    return frappe.db.get_value("Insights Query", query, "result")
