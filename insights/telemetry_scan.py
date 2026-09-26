"""The daily scan of what the site holds: `site_profile`, `site_queries`, `site_tables`.

`docs/telemetry.md` defines every property. Nothing here runs on the query or
import path. The scheduler is the only caller. A catalog read is the only
question it asks a data source.
"""

import json
import re
from collections import Counter, defaultdict

import frappe
from frappe.utils import add_days, getdate, now_datetime
from frappe.utils.telemetry import is_pulse_enabled, site_age

from insights.insights.doctype.insights_chart_v3.chart_query import CHART_TYPES
from insights.insights.doctype.insights_data_source_v3.data_warehouse import row_limit
from insights.insights.doctype.insights_data_source_v3.ibis.utils import get_functions
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    AGGREGATIONS,
    FILTER_OPERATORS,
    JOIN_TYPES,
)
from insights.insights.doctype.insights_table_v3.insights_table_v3 import strip_schema_prefix
from insights.insights.query_utils import source_tables
from insights.permissions import INSIGHTS_ROLES
from insights.telemetry import capture, default_properties, is_standard_app

PROPERTY_CAP = 4096
LIST_LIMIT = 50

CHART_DOCTYPE = "Insights Chart v3"
DASHBOARD_DOCTYPE = "Insights Dashboard v3"
DATA_SOURCE_DOCTYPE = "Insights Data Source v3"
EXECUTION_LOG_DOCTYPE = "Insights Query Execution Log"
QUERY_DOCTYPE = "Insights Query v3"
TABLE_DOCTYPE = "Insights Table v3"
WORKBOOK_DOCTYPE = "Insights Workbook"

UPLOADS_SOURCE = "uploads"
DEMO_SOURCE = "demo_data"

OPERATION_KINDS = {
    "source": "source",
    "select": "select",
    "remove": "remove",
    "rename": "rename",
    "cast": "cast",
    "filter": "filter",
    "filter_group": "filter",
    "join": "join",
    "union": "union",
    "mutate": "mutate",
    "summarize": "summarize",
    "order_by": "order_by",
    "limit": "limit",
    "pivot_wider": "pivot_wider",
    "custom_operation": "custom",
    "sql_column": "sql_column",
    "window_operation": "window",
}

# the symbols, spelled, so a property name stays a name
FILTER_VARIANTS = {
    "=": "eq",
    "!=": "neq",
    ">": "gt",
    ">=": "gte",
    "<": "lt",
    "<=": "lte",
}

FUNCTION_CALL = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")


def run_site_scan():
    """Send the three scan events. One that fails leaves the others alone.

    The scan asks a site with telemetry off nothing. Building the events reads
    every data source's catalog. That is load on a customer's own database for
    an event Pulse then drops.

    No `interval`: the daily scheduler job is the gate. Pulse compares elapsed
    seconds against the interval. A tick that arrives a second early drops the
    event, and the site loses that day.
    """
    if not is_pulse_enabled():
        return

    for event, build in (
        ("site_profile", site_profile),
        ("site_queries", site_queries),
        ("site_tables", site_tables),
    ):
        try:
            capture(event, **within_cap(build()))
        except Exception:
            frappe.log_error(title=f"Insights site scan: {event}", message=frappe.get_traceback())


def within_cap(props: dict) -> dict:
    """Cut lists until the properties serialize under Pulse's 4096 bytes.

    `capture` adds the properties every event includes, so the room they take is
    off the cap before the first list is measured.
    """
    cap = PROPERTY_CAP - serialized_size(default_properties())
    props = {k: v[:LIST_LIMIT] if isinstance(v, list) else v for k, v in props.items()}
    while serialized_size(props) > cap:
        longest = max(
            (k for k, v in props.items() if isinstance(v, list) and v),
            key=lambda k: len(props[k]),
            default=None,
        )
        if not longest:
            break
        props[longest] = props[longest][:-1]
    return props


def serialized_size(props: dict) -> int:
    return len(json.dumps(props, default=str).encode())


def site_profile() -> dict:
    installed = frappe.get_installed_apps()
    standard = sorted(app for app in installed if is_standard_app(app))

    props = {
        "frappe_cloud": bool(frappe.conf.get("fc_team")),
        "apps": standard,
        "custom_apps": len(installed) - len(standard),
        "site_age_days": site_age(),
    }
    props.update(timeline())
    props.update(footprint())
    props.update(people())
    return props


def timeline() -> dict:
    ages = {
        "insights_installed_days_ago": installed_on(),
        "first_data_source_days_ago": oldest(DATA_SOURCE_DOCTYPE, {"is_site_db": 0}),
        "first_workbook_days_ago": oldest(WORKBOOK_DOCTYPE),
        "first_dashboard_days_ago": oldest(DASHBOARD_DOCTYPE),
        "last_query_run_days_ago": newest(EXECUTION_LOG_DOCTYPE),
    }
    return {key: days_ago(value) for key, value in ages.items() if value}


def installed_on():
    """Installing an app logs every patch it ships as run. A migrate rewrites
    the `Installed Application` rows, so their creation is the last migrate."""
    return oldest("Patch Log", {"patch": ["like", "insights.%"]})


def oldest(doctype, filters=None):
    rows = frappe.get_all(doctype, filters=filters, fields=["creation"], order_by="creation asc", limit=1)
    return rows[0].creation if rows else None


def newest(doctype, filters=None):
    rows = frappe.get_all(doctype, filters=filters, fields=["creation"], order_by="creation desc", limit=1)
    return rows[0].creation if rows else None


def days_ago(timestamp) -> int:
    return (getdate() - getdate(timestamp)).days


def footprint() -> dict:
    sources = frappe.get_all(DATA_SOURCE_DOCTYPE, fields=["name", "database_type", "is_site_db"])
    kinds = Counter(source_kind(source) for source in sources)

    charts = Counter(
        known(chart_type, CHART_TYPES)
        for chart_type in frappe.get_all(
            CHART_DOCTYPE, pluck="chart_type", filters={"chart_type": ["is", "set"]}
        )
    )

    props = {
        "data_sources_site_db": kinds["site_db"],
        "data_sources_mariadb": kinds["mariadb"],
        "data_sources_postgresql": kinds["postgresql"],
        "data_sources_clickhouse": kinds["clickhouse"],
        "data_sources_duckdb": kinds["duckdb"],
        "data_sources_file": kinds["file"],
        "data_sources_demo": kinds["demo"],
        "data_sources_other": kinds["other"],
        "workbooks": frappe.db.count(WORKBOOK_DOCTYPE),
        "queries": frappe.db.count(QUERY_DOCTYPE),
        "charts": frappe.db.count(CHART_DOCTYPE),
        "dashboards": frappe.db.count(DASHBOARD_DOCTYPE),
        "alerts": frappe.db.count("Insights Alert"),
        "dashboards_with_filters": dashboards_with_filters(),
    }
    for chart_type, count in charts.items():
        props[f"charts_{frappe.scrub(chart_type)}"] = count
    return props


def source_kind(source) -> str:
    if source.is_site_db:
        return "site_db"
    if source.name == UPLOADS_SOURCE:
        return "file"
    if source.name == DEMO_SOURCE:
        return "demo"
    return {
        "MariaDB": "mariadb",
        "PostgreSQL": "postgresql",
        "ClickHouse": "clickhouse",
        "DuckDB": "duckdb",
    }.get(source.database_type, "other")


def dashboards_with_filters() -> int:
    with_filters = 0
    for items in frappe.get_all(DASHBOARD_DOCTYPE, pluck="items"):
        parsed = frappe.parse_json(items) or []
        if any(item.get("type") == "filter" for item in parsed):
            with_filters += 1
    return with_filters


def people() -> dict:
    """Who uses the site, from the execution log and the View Log.

    `track_view` writes one row per user per dashboard per five-minute window,
    and every guest is the user `Guest`. The public number counts windows and is
    a floor on views.
    """
    holders = frappe.get_all(
        "Has Role",
        filters={"role": ["in", list(INSIGHTS_ROLES)], "parenttype": "User"},
        pluck="parent",
        distinct=True,
    )
    enabled = frappe.db.count("User", {"name": ["in", holders], "enabled": 1}) if holders else 0

    since = add_days(now_datetime(), -30)
    views = frappe.get_all(
        "View Log",
        filters={"reference_doctype": DASHBOARD_DOCTYPE, "creation": [">", since]},
        fields=["viewed_by", "reference_name"],
    )

    return {
        "users_with_access": enabled,
        "authors_last_30d": len(
            frappe.get_all(
                EXECUTION_LOG_DOCTYPE, filters={"creation": [">", since]}, pluck="owner", distinct=True
            )
        ),
        "viewers_last_30d": len({v.viewed_by for v in views if v.viewed_by != "Guest"}),
        "dashboards_viewed_last_30d": len({v.reference_name for v in views}),
        "public_view_windows_last_30d": sum(1 for v in views if v.viewed_by == "Guest"),
    }


def site_queries() -> dict:
    queries = frappe.get_all(
        QUERY_DOCTYPE,
        fields=["operations", "use_live_connection", "is_native_query", "is_script_query"],
    )

    props = Counter()
    expressions = []
    for query in queries:
        if query.is_native_query:
            props["queries_sql"] += 1
        elif query.is_script_query:
            props["queries_script"] += 1
        else:
            props["queries_builder"] += 1
        if not query.use_live_connection:
            props["queries_on_store"] += 1

        operations = frappe.parse_json(query.operations) or []
        for kind in {OPERATION_KINDS[op["type"]] for op in operations if op.get("type") in OPERATION_KINDS}:
            props[f"queries_with_{kind}"] += 1
        for op in operations:
            count_operation(op, props, expressions)

    known_functions = get_functions()
    functions = Counter(
        name
        for expression in expressions
        for name in FUNCTION_CALL.findall(expression)
        if name in known_functions
    )
    return {
        "queries_builder": props.pop("queries_builder", 0),
        "queries_sql": props.pop("queries_sql", 0),
        "queries_script": props.pop("queries_script", 0),
        "queries_on_store": props.pop("queries_on_store", 0),
        **props,
        "expression_count": len(expressions),
        "expression_functions": [name for name, _ in functions.most_common(LIST_LIMIT)],
    }


def known(value: str | None, closed_list, spelled: dict | None = None) -> str:
    """The name a value may leave the site under, from a list the engine owns.

    `operations` is free-form JSON that nothing validates, so a key built from it
    can hold any word a client wrote. Anything the engine would refuse is
    counted as `other`.
    """
    if value not in closed_list:
        return "other"
    return (spelled or {}).get(value, value)


def count_operation(op: dict, props: Counter, expressions: list):
    kind = OPERATION_KINDS.get(op.get("type"))
    if not kind:
        return

    props[f"operations_{kind}"] += 1

    if kind == "filter":
        for rule in op.get("filters", [op]):
            props[f"filter_{filter_variant(rule)}"] += 1
            collect_expression(rule.get("expression"), expressions)
    elif kind == "join":
        props[f"join_{known(op.get('join_type'), JOIN_TYPES)}"] += 1
        collect_expression((op.get("join_condition") or {}).get("join_expression"), expressions)
    elif kind == "summarize":
        for measure in op.get("measures") or []:
            if measure.get("aggregation"):
                props[f"agg_{known(measure['aggregation'], AGGREGATIONS)}"] += 1
            collect_expression(measure.get("expression"), expressions)
    elif kind in ("mutate", "custom"):
        collect_expression(op.get("expression"), expressions)


def filter_variant(rule: dict) -> str:
    if rule.get("expression"):
        return "expression"
    return known(rule.get("operator"), FILTER_OPERATORS, FILTER_VARIANTS)


def collect_expression(expression, expressions: list):
    text = (expression or {}).get("expression") if isinstance(expression, dict) else None
    if text:
        expressions.append(text)


def site_tables() -> dict:
    operations_by_query = all_query_operations()
    queries_per_table = tables_queries_read(operations_by_query)
    estimates = row_estimates(queries_per_table.keys())
    settings = table_settings(queries_per_table.keys())
    limit = row_limit()

    named = standard_doctypes(queries_per_table.keys())
    by_reads = sorted(named, key=lambda key: queries_per_table[key], reverse=True)

    over_limit = [named[key] for key in by_reads if fits(key, estimates, settings) is False]

    return {
        "queried_tables": [named[key] for key in by_reads[:LIST_LIMIT]],
        "custom_tables_queried": len(queries_per_table) - len(named),
        "store_enabled": bool(frappe.db.get_single_value("Insights Settings", "enable_data_store")),
        "row_limit": limit,
        "tables_over_limit": over_limit[:LIST_LIMIT],
        **chart_fit(estimates, settings, operations_by_query),
    }


def all_query_operations() -> dict:
    """Every query's operations, read once.

    The scan walks the whole site, and a walk that reads a query per hop reads
    the same rows again for every query above them.
    """
    return {
        query.name: query.operations for query in frappe.get_all(QUERY_DOCTYPE, fields=["name", "operations"])
    }


def tables_queries_read(operations_by_query: dict | None = None) -> dict:
    """Every (data source, table) a query reads, with how many queries read it.

    Through the queries a query reads, so a wrapper counts the tables under it.
    `source_tables` names each table once per query, so a query reaching one
    table twice counts once.

    Read from operations, never from `Insights Query Reference`: the edge table
    only holds a query saved since it shipped, so it answers for a fraction of
    an older site.
    """
    if operations_by_query is None:
        operations_by_query = all_query_operations()

    reads = Counter()
    for name, operations in operations_by_query.items():
        for ref in source_tables(name, operations, operations_by_query):
            reads[(ref["data_source"], ref["table_name"])] += 1
    return reads


def standard_doctypes(keys) -> dict:
    """The keys that name a standard doctype, mapped to that doctype's name.

    A name leaves the site only for a doctype a Frappe-published app ships. The
    scan counts, and never names, a table on any other source, a Custom DocType,
    and a third-party app's doctype.
    """
    site_db = frappe.get_all(DATA_SOURCE_DOCTYPE, filters={"is_site_db": 1}, pluck="name")
    candidates = {
        key: strip_schema_prefix(key[1]).removeprefix("tab")
        for key in keys
        if key[0] in site_db and strip_schema_prefix(key[1]).startswith("tab")
    }
    if not candidates:
        return {}

    doctypes = {
        row.name: row.module
        for row in frappe.get_all(
            "DocType",
            filters={"name": ["in", list(set(candidates.values()))], "custom": 0},
            fields=["name", "module"],
        )
    }
    standard = {app for app in frappe.get_installed_apps() if is_standard_app(app)}
    apps = {
        row.name: row.app_name
        for row in frappe.get_all(
            "Module Def", filters={"name": ["in", list(set(doctypes.values()))]}, fields=["name", "app_name"]
        )
    }
    return {
        key: doctype
        for key, doctype in candidates.items()
        if doctype in doctypes and apps.get(doctypes[doctype]) in standard
    }


def table_settings(keys) -> dict:
    sources = {key[0] for key in keys}
    if not sources:
        return {}
    rows = frappe.get_all(
        TABLE_DOCTYPE,
        filters={"data_source": ["in", list(sources)]},
        fields=["data_source", "table", "row_limit", "stored", "sync_mode"],
    )
    return {(row.data_source, row.table): row for row in rows}


def fits(key, estimates: dict, settings: dict):
    """Whether the table would sit on the data store. `None` when nobody knows."""
    setting = settings.get(key)
    if setting and (setting.stored or setting.sync_mode == "Incremental"):
        return True
    estimate = estimates.get(key)
    if estimate is None:
        return None
    return estimate < row_limit(setting and setting.row_limit)


def chart_fit(estimates: dict, settings: dict, operations_by_query: dict) -> dict:
    """How many charts the data store would hold.

    A chart reading one table nobody estimated is `charts_unknown`, and in
    neither of the other two counts. A source that did not answer is not a table
    that is too big.

    `charts_total` is the charts that read a table, unknown ones included, so
    the rate is `charts_fit / (charts_total - charts_unknown)`. A chart with no
    query, or whose query reads no table, is judged by nothing and has its own
    count.
    """
    charts = frappe.get_all(CHART_DOCTYPE, fields=["name", "query"])
    on_store = set(frappe.get_all(QUERY_DOCTYPE, filters={"use_live_connection": 0}, pluck="name"))

    fitting = 0
    unknown = 0
    without_tables = 0
    read_by = {}
    for chart in charts:
        if chart.query and chart.query not in read_by:
            read_by[chart.query] = {
                (ref["data_source"], ref["table_name"])
                for ref in source_tables(chart.query, operations_by_name=operations_by_query)
            }
        verdicts = [fits(key, estimates, settings) for key in read_by.get(chart.query, ())]
        if not verdicts:
            without_tables += 1
            continue
        if None in verdicts:
            unknown += 1
        elif all(verdicts):
            fitting += 1

    return {
        "charts_total": len(charts) - without_tables,
        "charts_fit": fitting,
        "charts_unknown": unknown,
        "charts_without_tables": without_tables,
        "charts_on_store": sum(1 for chart in charts if chart.query in on_store),
    }


def row_estimates(keys) -> dict:
    """Catalog row counts for the tables queries read, written to the table rows.

    The scan is the only writer of `estimated_row_count` and `estimated_on`. The
    scan logs a source that will not answer and leaves it out. A chart reading
    its tables then counts as neither fitting nor over the limit.
    """
    from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections

    by_source = defaultdict(set)
    for data_source, table_name in keys:
        by_source[data_source].add(table_name)

    estimates = {}
    with db_connections():
        for data_source, tables in by_source.items():
            try:
                counts = read_catalog(data_source, tables)
            except Exception:
                frappe.log_error(
                    title=f"Insights site scan: row estimates for {data_source}",
                    message=frappe.get_traceback(),
                )
                continue
            for table_name, rows in counts.items():
                estimates[(data_source, table_name)] = rows
                store_estimate(data_source, table_name, rows)
    return estimates


def read_catalog(data_source: str, tables: set) -> dict:
    """Row counts the source already keeps, never a count query.

    A REST source has no catalog. The scan asks it nothing.

    A reader answers for the whole database, and this function picks out the
    tables a query reads. A table name a user typed never reaches the SQL.

    Both sides match on `table_identity`, the way the table list sync matches. A
    stored name is a spelling, and on postgres two schemas may spell one table
    the same.
    """
    from insights.utils import InsightsDataSourcev3

    doc = InsightsDataSourcev3.get_doc(data_source)
    backend = doc._get_ibis_backend()
    reader = CATALOG_READERS.get(backend.name)
    if not reader:
        return {}

    stored = {doc.table_identity(table): table for table in tables}
    counts = reader(backend)
    return {stored[identity]: rows for identity, rows in counts.items() if identity in stored}


def read_mariadb_catalog(backend) -> dict:
    """Keyed by table name: a MariaDB source reads one database, and that is the identity."""
    rows = fetch(
        backend,
        "select TABLE_NAME, TABLE_ROWS from information_schema.TABLES where TABLE_SCHEMA = DATABASE()",
    )
    return {name: int(count or 0) for name, count in rows}


def read_postgres_catalog(backend) -> dict:
    """Keyed by `<schema>.<table>`: a source may read several schemas, and two of
    them may hold a table of the same name."""
    rows = fetch(
        backend,
        "select n.nspname, c.relname, c.reltuples from pg_class c"
        " join pg_namespace n on n.oid = c.relnamespace"
        " where n.nspname = any(current_schemas(false)) and c.relkind in ('r', 'p', 'm')",
    )
    return {f"{schema}.{name}": max(int(count or 0), 0) for schema, name, count in rows}


def read_clickhouse_catalog(backend) -> dict:
    """Keyed by table name: a ClickHouse source reads one database, and that is the identity."""
    rows = fetch(
        backend,
        "select name, total_rows from system.tables where database = currentDatabase()",
    )
    return {name: int(count or 0) for name, count in rows}


def read_duckdb_catalog(backend) -> dict:
    """Keyed by table name: a DuckDB source lists the tables of one schema."""
    rows = fetch(
        backend,
        "select table_name, estimated_size from duckdb_tables()"
        " where database_name = current_database() and schema_name = current_schema()",
    )
    return {name: int(count or 0) for name, count in rows}


CATALOG_READERS = {
    "mysql": read_mariadb_catalog,
    "postgres": read_postgres_catalog,
    "clickhouse": read_clickhouse_catalog,
    "duckdb": read_duckdb_catalog,
}


def fetch(backend, sql: str):
    result = backend.raw_sql(sql)
    # a DBAPI cursor for the SQL backends, a query result for ClickHouse
    return result.fetchall() if hasattr(result, "fetchall") else result.result_rows


def store_estimate(data_source: str, table_name: str, rows: int):
    name = frappe.db.get_value(TABLE_DOCTYPE, {"data_source": data_source, "table": table_name})
    if not name:
        return
    frappe.db.set_value(
        TABLE_DOCTYPE,
        name,
        {"estimated_row_count": rows, "estimated_on": now_datetime()},
        update_modified=False,
    )
