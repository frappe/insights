import ast

import frappe

from insights.insights.doctype.insights_data_source_v3.ibis.utils import (
    BACKEND_ATTRIBUTE_NAMES,
    RUN_ATTRIBUTE_NAMES,
    attributes_of,
)
from insights.upgrade import add_item

QUERY = "Insights Query v3"
CHART = "Insights Chart v3"
# The names Insights 3.50 refuses after an attribute that a table does not define,
# so on Insights before 3.50 `t2.source` read the column. The others are table methods.
COLUMN_READS = frozenset({"source", "con", "raw_sql", "release"})
# Insights before 3.50 refused `get_backend` too, so an expression naming it never ran
NEWLY_REFUSED = (BACKEND_ATTRIBUTE_NAMES | RUN_ATTRIBUTE_NAMES) - {"get_backend"}


def execute():
    """Read a column named like a backend attribute as `t['name']`.

    Insights 3.50 refuses `t2.source` in an expression, because `source` and the
    names beside it lead from a table to its connection. Insights before 3.50 read it as
    the column, as in CRM's Lead `source`. The item form reads the same column
    and is never refused. The rest of the text is left as the author wrote it.

    An expression that still names a refused attribute called a table method,
    which an expression may no longer do. The owner is told.
    """
    for doctype, field in ((QUERY, "operations"), (CHART, "config")):
        for doc in frappe.get_all(
            doctype, filters={field: ("like", "%expression%")}, fields=["name", "title", "owner", field]
        ):
            content = frappe.parse_json(doc[field])
            before = frappe.as_json(content)
            refused = rewrite_expressions(content)
            if refused:
                report(doctype, doc, refused)
            if frappe.as_json(content) != before:
                frappe.db.set_value(doctype, doc.name, field, frappe.as_json(content), update_modified=False)


def rewrite_expressions(node) -> set[str]:
    """Rewrite every expression in `node`, in place. Answers the refused names left."""
    refused = set()
    if isinstance(node, list):
        for value in node:
            refused |= rewrite_expressions(value)
    elif isinstance(node, dict):
        if node.get("type") == "expression" and isinstance(node.get("expression"), str):
            node["expression"] = as_item_reads(node["expression"])
            refused |= attributes_of(node["expression"]) & NEWLY_REFUSED
        for value in node.values():
            refused |= rewrite_expressions(value)
    return refused


def as_item_reads(expression: str) -> str:
    """`expression` with each `name.source` read as `name['source']`, or as it
    is when it does not parse."""
    try:
        tree = ast.parse(expression)
    except SyntaxError:
        return expression

    called = {id(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    reads = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr in COLUMN_READS
        and isinstance(node.value, ast.Name)
        and id(node) not in called
    ]
    if not reads:
        return expression

    # offsets count bytes within a line
    lines = expression.encode().splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    text = expression.encode()
    for node in sorted(reads, key=lambda node: (node.end_lineno, node.end_col_offset), reverse=True):
        start = starts[node.value.end_lineno - 1] + node.value.end_col_offset
        end = starts[node.end_lineno - 1] + node.end_col_offset
        text = text[:start] + f"['{node.attr}']".encode() + text[end:]
    return text.decode()


def report(doctype: str, doc, refused: set[str]) -> None:
    data = {
        "title": doc.title or doc.name,
        "names": sorted(refused),
        "kind": "query" if doctype == QUERY else "chart",
    }
    names = ", ".join(f"`{name}`" for name in data["names"])
    add_item(
        "Q5",
        f'{data["kind"].capitalize()} "{data["title"]}" calls {names}',
        reference=(doctype, doc.name),
        user=None if doc.owner == "Administrator" else doc.owner,
        data=data,
    )
