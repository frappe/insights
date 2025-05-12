import frappe
from frappe.utils.caching import redis_cache, site_cache

from insights import notify
from insights.decorators import insights_whitelist, validate_type
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    execute_ibis_query,
    get_columns_from_schema,
    to_insights_type,
)
from insights.insights.doctype.insights_query.utils import infer_type_from_list
from insights.insights.doctype.insights_table_link_v3.insights_table_link_v3 import (
    InsightsTableLinkv3,
)
from insights.insights.doctype.insights_team.insights_team import (
    check_data_source_permission,
    check_table_permission,
    get_permission_filter,
)
from insights.utils import InsightsTable, detect_encoding


@insights_whitelist()
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


@insights_whitelist()
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


@insights_whitelist()
def get_table_name(data_source, table):
    check_table_permission(data_source, table)
    return frappe.get_value(
        "Insights Table", {"data_source": data_source, "table": table}, "name"
    )


@insights_whitelist()
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


@insights_whitelist()
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


@insights_whitelist()
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


@insights_whitelist()
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


@insights_whitelist()
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


@insights_whitelist()
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


@insights_whitelist()
def get_relation(data_source, table_one, table_two):
    table_one_doc = InsightsTable.get_doc(
        {"data_source": data_source, "table": table_one}
    )
    if not table_one_doc:
        frappe.throw(f"Table {table_one} not found")

    table_two_doc = InsightsTable.get_doc(
        {"data_source": data_source, "table": table_two}
    )
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


# v3 APIs


@insights_whitelist()
def get_all_data_sources():
    return frappe.get_list(
        "Insights Data Source v3",
        fields=[
            "name",
            "status",
            "title",
            "owner",
            "is_frappe_db",
            "is_site_db",
            "creation",
            "modified",
            "database_type",
        ],
    )


@insights_whitelist()
@validate_type
def get_data_source_tables(data_source=None, search_term=None, limit=100):
    tables = frappe.get_list(
        "Insights Table v3",
        filters={
            "data_source": data_source or ["is", "set"],
        },
        or_filters={
            "label": ["is", "set"] if not search_term else ["like", f"%{search_term}%"],
            "table": ["is", "set"] if not search_term else ["like", f"%{search_term}%"],
        },
        fields=["name", "table", "label", "data_source", "last_synced_on"],
        limit=limit,
    )

    ret = []
    for table in tables:
        ret.append(
            frappe._dict(
                {
                    "name": table.name,
                    "label": table.label,
                    "table_name": table.table,
                    "data_source": table.data_source,
                    "last_synced_on": table.last_synced_on,
                }
            )
        )
    return ret


@insights_whitelist()
@validate_type
def get_data_source_table(data_source: str, table_name: str):
    check_table_permission(data_source, table_name)
    ds = frappe.get_doc("Insights Data Source v3", data_source)
    q = ds.get_ibis_table(table_name).head(100)
    data, time_taken = execute_ibis_query(q, cache_expiry=24 * 60 * 60)

    return {
        "table_name": table_name,
        "data_source": data_source,
        "columns": get_columns_from_schema(q.schema()),
        "rows": data.to_dict(orient="records"),
    }


@insights_whitelist()
@validate_type
def get_data_source_table_row_count(data_source: str, table_name: str):
    check_table_permission(data_source, table_name)
    ds = frappe.get_doc("Insights Data Source v3", data_source)
    table = ds.get_ibis_table(table_name)
    result = table.count().execute()
    return int(result)


@insights_whitelist()
@site_cache
@validate_type
def get_data_source_table_columns(data_source: str, table_name: str):
    check_table_permission(data_source, table_name)
    ds = frappe.get_doc("Insights Data Source v3", data_source)
    table = ds.get_ibis_table(table_name)
    return [
        frappe._dict(
            column=column,
            label=column,
            type=to_insights_type(datatype),
        )
        for column, datatype in table.schema().items()
    ]


@insights_whitelist()
@validate_type
def update_data_source_tables(data_source: str):
    check_data_source_permission(data_source)
    ds = frappe.get_doc("Insights Data Source v3", data_source)
    ds.update_table_list()


@insights_whitelist()
@validate_type
def get_table_links(data_source: str, left_table: str, right_table: str):
    check_table_permission(data_source, left_table)
    return InsightsTableLinkv3.get_links(data_source, left_table, right_table)


@insights_whitelist()
@validate_type
def update_table_links(data_source: str):
    check_data_source_permission(data_source)
    ds = frappe.get_doc("Insights Data Source v3", data_source)
    ds.update_table_links(force=True)


def make_data_source(data_source):
    data_source = frappe._dict(data_source)
    ds = frappe.new_doc("Insights Data Source v3")
    ds.database_type = data_source.database_type
    ds.title = data_source.title
    ds.host = data_source.host
    ds.port = data_source.port
    ds.username = data_source.username
    ds.password = data_source.password
    ds.database_name = data_source.database_name
    ds.use_ssl = data_source.use_ssl
    ds.connection_string = data_source.connection_string
    return ds


@insights_whitelist()
def test_connection(data_source):
    frappe.only_for("Insights Admin")
    ds = make_data_source(data_source)
    return ds.test_connection(raise_exception=True)


@insights_whitelist()
def create_data_source(data_source):
    frappe.only_for("Insights Admin")
    ds = make_data_source(data_source)
    ds.save()
    return ds.name


@insights_whitelist()
def get_data_sources_of_tables(table_names: list[str]):
    if not table_names:
        return {}
    if not isinstance(table_names, list):
        frappe.throw("Table names should be a list")
    if not all(isinstance(table_name, str) for table_name in table_names):
        frappe.throw("Table names should be a list of strings")

    tables = frappe.get_list(
        "Insights Table v3",
        filters={"name": ["in", table_names]},
        fields=["data_source", "name"],
    )
    data_sources = {}
    for table in tables:
        data_sources[table.data_source] = data_sources.get(table.data_source, [])
        data_sources[table.data_source].append(table.name)

    return data_sources


@insights_whitelist()
@site_cache(ttl=24 * 60 * 60)
@validate_type
def get_schema(data_source: str):
    check_data_source_permission(data_source)
    ds = frappe.get_doc("Insights Data Source v3", data_source)

    tables = get_data_source_tables(data_source)
    schema = {}

    for table in tables:
        table_name = table.table_name
        schema[table_name] = {
            "table": table_name,
            "label": table.label,
            "data_source": data_source,
            "columns": [],
        }
        _table = ds.get_ibis_table(table_name)
        for column, datatype in _table.schema().items():
            schema[table_name]["columns"].append(
                frappe._dict(
                    column=column,
                    label=column,
                    type=to_insights_type(datatype),
                )
            )

    return schema
