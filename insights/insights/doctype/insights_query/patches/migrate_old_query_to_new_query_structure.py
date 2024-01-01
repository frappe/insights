import frappe

from insights.insights.doctype.insights_query.insights_legacy_query_utils import (
    convert_into_simple_filter,
    is_simple_filter,
)


def execute():
    old_queries = frappe.get_all(
        "Insights Query",
        filters={
            "is_assisted_query": 0,
            "is_native_query": 0,
            "is_script_query": 0,
            "sql": ("is", "set"),
        },
    )
    for old_query in old_queries:
        doc = frappe.get_doc("Insights Query", old_query.name)
        doc.db_set("json", convert_classic_to_assisted(doc), update_modified=False)
        doc.db_set("is_assisted_query", 1, update_modified=False)


def convert_classic_to_assisted(old_query):
    if not old_query.sql or not old_query.tables or not old_query.tables[0].table:
        return "{}"
    return frappe.as_json(
        {
            "table": get_table(old_query),
            "joins": get_joins(old_query),
            "filters": get_filters(old_query),
            "columns": get_columns(old_query),
            "calculations": [],
            "measures": [],
            "dimensions": [],
            "orders": [],
            "limit": old_query.limit,
        }
    )


def get_table(old_query):
    table = {}
    table["table"] = old_query.tables[0].table
    table["label"] = old_query.tables[0].label
    return table


def get_joins(old_query):
    joins = []
    for table in old_query.tables:
        if not table.get("join"):
            continue
        join_data = frappe.parse_json(table.get("join"))
        right_table = join_data.get("with") or {}
        condition = join_data.get("condition") or {}
        left_column = condition.get("left")
        right_column = condition.get("right")
        if not right_table or not condition or not left_column or not right_column:
            continue
        joins.append(
            {
                "join_type": join_data.get("type"),
                "left_table": {
                    "table": table.get("table"),
                    "label": table.get("label"),
                },
                "left_column": {
                    "table": table.get("table"),
                    "column": left_column.get("value"),
                    "label": left_column.get("label"),
                },
                "right_table": {
                    "table": right_table.get("value"),
                    "label": right_table.get("label"),
                },
                "right_column": {
                    "table": right_table.get("value"),
                    "column": right_column.get("value"),
                    "label": right_column.get("label"),
                },
            }
        )
    return joins


def get_filters(old_query):
    filters = []
    old_filters = frappe.parse_json(old_query.get("filters"))
    for condition in old_filters.get("conditions"):
        if condition.get("is_expression"):
            filters.append(
                {
                    "expression": {
                        "raw": condition.get("raw"),
                        "ast": condition,
                    }
                }
            )
        elif is_simple_filter(condition):
            simple_filter = convert_into_simple_filter(condition)
            filters.append(
                {
                    "column": {
                        "table": simple_filter.get("column").get("table"),
                        "column": simple_filter.get("column").get("column"),
                    },
                    "operator": {
                        "label": OPERATOR_MAP.get(simple_filter.get("operator")),
                        "value": simple_filter.get("operator"),
                    },
                    "value": {
                        "label": simple_filter.get("value"),
                        "value": simple_filter.get("value"),
                    },
                    "expression": {},
                }
            )
    return filters


def get_columns(old_query):
    columns = []
    for column in old_query.get("columns"):
        columns.append(
            {
                "table": column.get("table"),
                "table_label": column.get("table_label"),
                "column": column.get("column"),
                "label": column.get("label"),
                "alias": column.get("label"),
                "type": column.get("type"),
                "aggregation": (column.get("aggregation") or "").lower(),
                "order": column.get("order_by"),
                "expression": frappe.parse_json(column.get("expression"))
                if column.get("is_expression")
                else {},
                "granularity": frappe.parse_json(column.get("format_option")).get("date_format")
                if frappe.parse_json(column.get("format_option"))
                else "",
            }
        )
    return columns


OPERATOR_MAP = {
    "=": "equals",
    "!=": "not equals",
    "is": "is",
    "contains": "contains",
    "not_contains": "not contains",
    "starts_with": "starts with",
    "ends_with": "ends with",
    "in": "one of",
    "not_in": "not one of",
    ">": "greater than",
    "<": "smaller than",
    ">=": "greater than equal to",
    "<=": "smaller than equal to",
    "between": "between",
    "timespan": "within",
}
