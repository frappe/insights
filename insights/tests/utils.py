# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe


def create_data_source(
    title,
    source_type="Database",
    db_type="MariaDB",
    host="localhost",
    port=3306,
    db_name=None,
    username=None,
    password=None,
):
    frappe.delete_doc("Insights Data Source", title, force=True)
    data_source = frappe.new_doc("Insights Data Source")
    data_source.source_type = source_type
    data_source.title = title
    data_source.database_type = db_type
    data_source.host = host
    data_source.port = port
    data_source.database_name = db_name or frappe.conf.db_name
    data_source.username = username or frappe.conf.db_name
    data_source.password = password or frappe.conf.db_password
    data_source.save()
    return data_source


def create_insights_query(title, data_source):
    query = frappe.new_doc("Insights Query")
    query.title = title or "Test Query"
    query.data_source = data_source
    query.save()
    return query


def create_insights_table(table, label, data_source):
    frappe.delete_doc(
        "Insights Table", {"table": table, "data_source": data_source}, force=True
    )
    insights_table = frappe.new_doc("Insights Table")
    insights_table.table = table or "tabUser"
    insights_table.label = label or "User"
    insights_table.data_source = data_source
    insights_table.save()
    return insights_table
