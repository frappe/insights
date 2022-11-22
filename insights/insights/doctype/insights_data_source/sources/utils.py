# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.pool import NullPool

MARIADB_TO_GENERIC_TYPES = {
    "int": "Integer",
    "bigint": "Long Int",
    "decimal": "Decimal",
    "text": "Text",
    "longtext": "Long Text",
    "date": "Date",
    "datetime": "Datetime",
    "time": "Time",
    "varchar": "String",
}


def get_sqlalchemy_engine(**kwargs) -> Engine:

    dialect = kwargs.pop("dialect")
    driver = kwargs.pop("driver")
    user = kwargs.pop("username")
    password = kwargs.pop("password")
    database = kwargs.pop("database")
    host = kwargs.pop("host", "localhost")
    port = kwargs.pop("port") or 3306
    extra_params = "&".join([f"{k}={v}" for k, v in kwargs.items()])

    uri = f"{dialect}+{driver}://{user}:{password}@{host}:{port}/{database}?{extra_params}"

    # TODO: cache the engine by uri
    return create_engine(uri, poolclass=NullPool)


def create_insights_table(table, force=False):
    exists = frappe.db.exists(
        "Insights Table",
        {
            "data_source": table.data_source,
            "table": table.table,
        },
    )

    if docname := exists:
        doc = frappe.get_doc("Insights Table", docname)
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Insights Table",
                "data_source": table.data_source,
                "table": table.table,
                "label": table.label,
            }
        )

    doc.label = table.label
    if force:
        doc.columns = []
        doc.table_links = []

    for table_link in table.table_links or []:
        if not doc.get("table_links", table_link):
            doc.append("table_links", table_link)

    for column in table.columns or []:
        if not doc.get("columns", column):
            doc.append("columns", column)

    column_names = [c.column for c in table.columns]
    for column in doc.columns:
        if column.column not in column_names:
            doc.remove(column)

    doc.save()
    return doc.name
