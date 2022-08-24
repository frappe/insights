# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from pypika import CustomFunction


@frappe.whitelist()
def get_app_version():
    return frappe.get_attr("insights" + ".__version__")


@frappe.whitelist()
def get_data_sources():
    return frappe.get_list(
        "Data Source",
        filters={"status": "Active"},
        fields=["name", "title", "status", "database_type", "modified", "username"],
    )


@frappe.whitelist()
def get_data_source(name):
    doc = frappe.get_doc("Data Source", name)
    tables = get_all_tables(name)
    return {
        "doc": doc.as_dict(),
        "tables": tables,
    }


@frappe.whitelist()
def get_data_source_table(name, table):
    table = frappe.get_doc(
        "Table",
        {
            "data_source": name,
            "table": table,
        },
    )
    columns, data, no_of_rows = table.preview()
    return {
        "doc": table.as_dict(),
        "no_of_rows": no_of_rows,
        "columns": columns,
        "rows": data,
    }


@frappe.whitelist()
def update_data_source_table(name, table, hidden):
    table = frappe.get_doc(
        "Table",
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

    def _get_tables():
        return frappe.get_all(
            "Table",
            filters={
                "hidden": 0,
                "data_source": data_source,
            },
            fields=["table", "label"],
            order_by="label asc",
        )

    return frappe.cache().hget(
        "insights",
        "get_tables_" + data_source,
        generator=_get_tables,
    )


def get_all_tables(data_source=None):
    if not data_source:
        return []

    def _get_all_tables():
        return frappe.get_all(
            "Table",
            filters={
                "data_source": data_source,
            },
            fields=["table", "label", "hidden"],
            order_by="hidden asc, label asc",
        )

    return frappe.cache().hget(
        "insights",
        "get_all_tables_" + data_source,
        generator=_get_all_tables,
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
    return dashboard.name


@frappe.whitelist()
def get_queries():
    frappe.has_permission("Query", throw=True)
    Query = frappe.qb.DocType("Query")
    QueryTable = frappe.qb.DocType("Query Table")
    GroupConcat = CustomFunction("Group_Concat", ["column"])
    return (
        frappe.qb.from_(Query)
        .left_join(QueryTable)
        .on(Query.name == QueryTable.parent)
        .select(
            Query.name,
            Query.title,
            GroupConcat(QueryTable.label).as_("tables"),
            Query.data_source,
            Query.modified,
        )
        .groupby(Query.name)
        .orderby(Query.modified, order=frappe.qb.desc)
    ).run(as_dict=True)


@frappe.whitelist()
def create_query(title, data_source, table):
    query = frappe.new_doc("Query")
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
def get_running_queries(data_source):
    data_source = frappe.get_doc("Data Source", data_source)
    return data_source.get_running_queries()


@frappe.whitelist()
def kill_query(data_source, query_id):
    data_source = frappe.get_doc("Data Source", data_source)
    return data_source.kill_query(query_id)


@frappe.whitelist()
def update_user_default(key, value):
    keys = ["hide_sidebar"]
    if key not in keys:
        return
    frappe.defaults.set_user_default(key, value)
    print(frappe.defaults.get_user_default(key))


@frappe.whitelist()
def get_user_defaults():
    defaults = frappe.defaults.get_defaults()
    keys = ["hide_sidebar"]
    return {key: defaults.get(key) for key in keys}


@frappe.whitelist()
def create_table_link(
    data_source, primary_table, foreign_table, primary_key, foreign_key
):
    primary = frappe.get_doc(
        "Table",
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
        "Table",
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
