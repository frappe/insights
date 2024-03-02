import frappe
from frappe.utils.caching import redis_cache

from insights import notify
from insights.api.telemetry import track
from insights.decorators import check_role
from insights.insights.doctype.insights_query.utils import infer_type_from_list
from insights.insights.doctype.insights_team.insights_team import (
    check_data_source_permission,
    check_table_permission,
    get_permission_filter,
)
from insights.utils import InsightsTable, detect_encoding


@frappe.whitelist()
@check_role("Insights User")
def get_data_sources():
    return frappe.get_list(
        "Insights Data Source",
        filters={
            "status": "Active",
            **get_permission_filter("Insights Data Source"),
        },
        fields=[
            "name",
            "title",
            "status",
            "database_type",
            "creation",
            "is_site_db",
        ],
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
    return frappe.get_value("Insights Table", {"data_source": data_source, "table": table}, "name")


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
def create_table_link(data_source, primary_table, foreign_table, primary_key, foreign_key):
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
def get_columns_from_uploaded_file(filename):
    import pandas as pd

    file = frappe.get_doc("File", filename)
    parts = file.get_extension()
    if "csv" not in parts[1]:
        frappe.throw("Only CSV files are supported")

    file_path = file.get_full_path()
    encoding = detect_encoding(file_path)
    df = pd.read_csv(file_path, encoding=encoding)
    columns = df.columns.tolist()
    columns_with_types = []
    for column in columns:
        column_type = infer_type_from_list(df[column].dropna().head(1000).tolist())
        columns_with_types.append({"label": column, "type": column_type})
    return columns_with_types


def create_data_source_for_csv():
    if not frappe.db.exists("Insights Data Source", {"title": "File Uploads"}):
        data_source = frappe.new_doc("Insights Data Source")
        data_source.database_type = "SQLite"
        data_source.database_name = "file_uploads"
        data_source.title = "File Uploads"
        data_source.allow_imports = 1
        data_source.insert(ignore_permissions=True)


@frappe.whitelist()
@check_role("Insights User")
def import_csv(table_label, table_name, filename, if_exists, columns, data_source):
    create_data_source_for_csv()

    table_import = frappe.new_doc("Insights Table Import")
    table_import.data_source = data_source
    table_import.table_label = table_label
    table_import.table_name = table_name
    table_import.if_exists = if_exists
    table_import.source = frappe.get_doc("File", filename).file_url
    table_import.save()
    table_import.columns = []
    for column in columns:
        table_import.append(
            "columns",
            {
                "column": column.get("name"),
                "label": column.get("label"),
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
    track("delete_data_source")
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
@redis_cache()
def fetch_column_values(data_source, table, column, search_text=None):
    if not data_source or not isinstance(data_source, str):
        frappe.throw("Data Source is required")
    if not table or not isinstance(table, str):
        frappe.throw("Table is required")
    if not column or not isinstance(column, str):
        frappe.throw("Column is required")
    doc = frappe.get_doc("Insights Data Source", data_source)
    return doc.get_column_options(table, column, search_text)


@frappe.whitelist()
def get_relation(data_source, table_one, table_two):
    table_one_doc = InsightsTable.get_doc({"data_source": data_source, "table": table_one})
    if not table_one_doc:
        frappe.throw(f"Table {table_one} not found")

    table_two_doc = InsightsTable.get_doc({"data_source": data_source, "table": table_two})
    if not table_two_doc:
        frappe.throw(f"Table {table_two} not found")

    if relation := table_one_doc.get({"foreign_table": table_two}):
        return {
            "primary_table": table_one,
            "primary_table_label": table_one_doc.label,
            "primary_column": relation[0].primary_key,
            "foreign_table": table_two,
            "foreign_column": relation[0].foreign_key,
            "foreign_table_label": table_two_doc.label,
            "cardinality": relation[0].cardinality,
        }

    if relation := table_two_doc.get({"foreign_table": table_one}):
        reverse_cardinality = get_reverse_cardinality(relation[0].cardinality)
        return {
            "primary_table": table_one,
            "primary_table_label": table_one_doc.label,
            "primary_column": relation[0].foreign_key,
            "foreign_table": table_two,
            "foreign_column": relation[0].primary_key,
            "foreign_table_label": table_two_doc.label,
            "cardinality": reverse_cardinality,
        }


def get_reverse_cardinality(cardinality):
    if cardinality == "1:N":
        return "N:1"
    if cardinality == "N:1":
        return "1:N"
    return cardinality
