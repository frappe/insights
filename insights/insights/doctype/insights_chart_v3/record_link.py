# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Which columns of a result name a desk document.

A cell holds a document when the column it sits in came from a site-DB table and
holds an id there: the table's own `name`, or one of its `Link` fields. So a
grid of quotations links the quotation and the customer, and leaves the
territory's label alone.

Where a column came from is traced, never guessed. Each step of the pipeline is
followed — a rename gives a column another name, a copy gives it a second one, a
join brings columns in from another table, a group-by keeps the ones it grouped
by — and a column an expression wrote carries nothing at all. What the trace
says is checked against the result columns, so a trace that goes wrong draws no
link rather than one that lands on the wrong record.

The same answer serves a drilled record list and a Table chart, because both
draw rows and neither can tell from a value that it names a document.
"""

import re

import frappe
from frappe.model import std_fields

from insights.insights.doctype.insights_data_source_v3.ibis_utils import sanitize_name

# `owner` and `modified_by` are on every table and in no doctype's field list,
# so the framework's own list of them is what says where they point
STANDARD_LINKS = {
    field["fieldname"]: field["options"]
    for field in std_fields
    if field["fieldtype"] == "Link" and field.get("options")
}

# a mutate whose expression is one bare word copies that column. A word that
# names no field of the table it would come from links to nothing anyway, so
# this needs no column list to be safe
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

DATA_SOURCE = "Insights Data Source v3"
QUERY = "Insights Query v3"

# a column of the result, as the trace holds it: the site table it came from and
# the field it is there. `None` for a column an expression made up.
Origin = tuple[str, str] | None
# what the pipeline pinned a field to, keyed by the field it pinned: the answer
# a `Dynamic Link` needs, and the only thing that makes one safe to follow
Pins = dict[tuple[str, str], str]


def record_links(operations: list[dict], columns: list[dict]) -> dict[str, str]:
    """The doctype each result column names, for the columns that name one.

    Keyed by result column name. Empty when the pipeline reads something this
    cannot follow — an external source, a union, raw SQL.
    """
    traced = _trace(operations, set())
    if not traced:
        return {}

    default_table, origins, pins = traced
    links = {}
    for column in columns:
        name = column["name"]
        origin = origins.get(name, (default_table, name) if default_table else None)
        doctype = _doctype_named_by(origin, pins)
        if doctype:
            links[name] = doctype

    return links


def _doctype_named_by(origin: Origin, pins: Pins) -> str | None:
    """The doctype the values of this column name, or nothing."""
    if not origin:
        return None

    table_name, field = origin
    doctype = table_name[len("tab") :] if table_name.startswith("tab") else None
    if not doctype or not frappe.db.exists("DocType", doctype):
        return None

    meta = frappe.get_meta(doctype)
    if field == "name":
        # a child row has no form of its own: the desk routes the parent, which
        # the row cannot name
        return None if meta.istable else doctype

    df = meta.get_field(field)
    if df and df.fieldtype == "Link" and df.options:
        return df.options

    # A `Dynamic Link` names its doctype in a second column, which the result
    # rarely draws. It is followed only where the pipeline pinned that column to
    # one value — `party_type = "Customer"` — because then every row of the
    # column is that doctype and no cell has to be read to know it.
    if df and df.fieldtype == "Dynamic Link" and df.options:
        pinned = pins.get((table_name, df.options))
        return pinned if pinned and frappe.db.exists("DocType", pinned) else None

    return STANDARD_LINKS.get(field)


def _trace(operations: list[dict], seen: set) -> tuple[str | None, dict[str, Origin], Pins] | None:
    """Where the columns of this pipeline come from.

    Returns the table every column comes from unless said otherwise, and what is
    said otherwise. The default falls away at the first group-by: after it, only
    the columns it kept exist, and each of them is named.

    Followed through the queries the pipeline is built on, because a chart's
    operations start at its source query and the rename that matters is often
    down there.
    """
    for operation in operations:
        if operation.get("type") in ("union", "sql", "code"):
            return None

    source = next((o for o in operations if o.get("type") == "source"), None)
    base = _table_of((source or {}).get("table") or {}, seen)
    if not base:
        return None

    return _follow(operations, base, seen)


def _table_of(table: dict, seen: set) -> tuple[str | None, dict[str, Origin], Pins] | None:
    """The same answer for a table a pipeline reads or joins to.

    A site-DB table names itself, and a query is traced the way any pipeline is.
    Anything else — another data source — names nothing, so its columns carry no
    link.
    """
    if table.get("type") == "table":
        if not frappe.db.get_value(DATA_SOURCE, table.get("data_source"), "is_site_db"):
            return None
        return (table.get("table_name"), {}, {})

    if table.get("type") != "query" or table.get("query_name") in seen:
        return None

    query = table["query_name"]
    seen.add(query)
    return _trace(frappe.parse_json(frappe.db.get_value(QUERY, query, "operations")) or [], seen)


def _follow(
    operations: list[dict],
    base: tuple[str | None, dict[str, Origin], Pins],
    seen: set,
) -> tuple[str | None, dict[str, Origin], Pins]:
    """What each step does to where the columns come from."""
    default, origins, pins = base
    origins = dict(origins)
    pins = dict(pins)

    def origin_of(column: str) -> Origin:
        return origins.get(column, (default, column) if default else None)

    for operation in operations:
        type = operation.get("type")

        if type == "rename":
            old_name = (operation.get("column") or {}).get("column_name")
            origins[sanitize_name(operation.get("new_name"))] = origin_of(old_name)

        elif type == "mutate":
            # a mutate that copies a column carries its origin into the new one.
            # Any other expression makes a value that belongs to no table
            new_name = sanitize_name(operation.get("new_name"))
            expression = ((operation.get("expression") or {}).get("expression") or "").strip()
            origins[new_name] = origin_of(expression) if _IDENTIFIER.match(expression) else None

        elif type == "join":
            # the right table's columns arrive under their own names, and the
            # duplicates ibis renames are left untraced rather than guessed at
            joined = _table_of(operation.get("table") or {}, seen)
            for column in operation.get("select_columns") or []:
                name = column.get("column_name")
                origins[name] = _joined_origin(joined, name)
            if joined:
                pins.update(joined[2])

            # a join to a table's `name` is the author saying outright that this
            # column holds that table's ids. It is the one place a foreign key is
            # written down, and it beats whatever the column looked like before
            condition = operation.get("join_condition") or {}
            left = (condition.get("left_column") or {}).get("column_name")
            if left and (condition.get("right_column") or {}).get("column_name") == "name":
                origins[left] = _joined_origin(joined, "name")

        elif type == "select":
            kept = set(operation.get("column_names") or [])
            origins = {name: origin for name, origin in origins.items() if name in kept}

        elif type == "remove":
            for name in operation.get("column_names") or []:
                origins.pop(name, None)

        elif type in ("filter", "filter_group"):
            # what the pipeline narrowed to one value, said about the field it
            # narrowed rather than the column name it used to say it
            for rule in [operation] if type == "filter" else operation.get("filters") or []:
                origin = origin_of((rule.get("column") or {}).get("column_name"))
                if origin and rule.get("operator") == "=" and isinstance(rule.get("value"), str):
                    pins[origin] = rule["value"]

        elif type in ("summarize", "pivot_wider"):
            # one row per group: only the columns it grouped by are still a
            # column of anything, under whatever the dimension calls them
            dimensions = operation.get("dimensions") if type == "summarize" else operation.get("rows")
            origins = {
                (d.get("dimension_name") or d["column_name"]): origin_of(d["column_name"])
                for d in dimensions or []
                if d.get("column_name")
            }
            default = None

    return (default, origins, pins)


def _joined_origin(joined: tuple[str | None, dict[str, Origin], Pins] | None, column: str) -> Origin:
    if not joined:
        return None
    default, origins, _ = joined
    return origins.get(column, (default, column) if default else None)
