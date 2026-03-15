import frappe
from frappe.utils.caching import site_cache

from insights.decorators import insights_whitelist, validate_type
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    execute_ibis_query,
    get_columns_from_schema,
    to_insights_type,
)
from insights.insights.doctype.insights_table_link_v3.insights_table_link_v3 import (
    InsightsTableLinkv3,
)
from insights.insights.doctype.insights_team.insights_team import (
    check_data_source_permission,
    check_table_permission,
)


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
def get_data_source_tables(data_source: str | None = None, search_term: str | None = None, limit: int = 100):
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
    data, _ = execute_ibis_query(q, cache_expiry=24 * 60 * 60)

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


@insights_whitelist(role="Insights Admin")
def test_connection(data_source: dict):
    ds = make_data_source(data_source)
    return ds.test_connection(raise_exception=True)


@insights_whitelist(role="Insights Admin")
def create_data_source(data_source: dict):
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
        try:
            _table = ds.get_ibis_table(table_name)
        except Exception:
            continue
        for column, datatype in _table.schema().items():
            schema[table_name]["columns"].append(
                frappe._dict(
                    column=column,
                    label=column,
                    type=to_insights_type(datatype),
                )
            )

    return schema
