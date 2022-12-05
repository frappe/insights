# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe

"""
	utitilies to help convert filters to expressions
"""

BINARY_OPERATORS = {
    "equals": "=",
    "not equals": "!=",
    "smaller than": "<",
    "greater than": ">",
    "smaller than equal to": "<=",
    "greater than equal to": ">=",
}

FUNCTION_OPERATORS = [
    "is",
    "in",
    "not_in",
    "between",
    "timespan",
    "starts_with",
    "ends_with",
    "contains",
    "not_contains",
]


def convert_to_expression(table, column, filter_operator, filter_value, value_type):
    if filter_operator in BINARY_OPERATORS:
        return make_binary_expression(
            table, column, filter_operator, filter_value, value_type
        )
    if filter_operator in FUNCTION_OPERATORS:
        return make_call_expression(
            table, column, filter_operator, filter_value, value_type
        )


def make_binary_expression(table, column, filter_operator, filter_value, value_type):
    return {
        "type": "BinaryExpression",
        "operator": BINARY_OPERATORS[filter_operator],
        "left": {
            "type": "Column",
            "value": {
                "column": column,
                "table": table,
            },
        },
        "right": {
            "type": "Number" if value_type in ("Integer", "Decimal") else "String",
            "value": filter_value,
        },
    }


def make_call_expression(table, column, filter_operator, filter_value, value_type):
    operator_function = filter_operator
    if filter_operator == "is":
        operator_function = "is_set" if filter_value == "set" else "is_not_set"

    return {
        "type": "CallExpression",
        "function": operator_function,
        "arguments": [
            {
                "type": "Column",
                "value": {
                    "column": column,
                    "table": table,
                },
            },
            *make_args_for_call_expression(operator_function, filter_value, value_type),
        ],
    }


def make_args_for_call_expression(operator_function, filter_value, value_type):
    if operator_function == "is":
        return []

    if operator_function == "between":
        values = [v.strip() for v in filter_value.split(",")]
        return [
            {
                "type": "Number" if value_type == "Number" else "String",
                "value": v,
            }
            for v in values
        ]

    if operator_function in ["in", "not_in"]:
        return [{"type": "String", "value": v} for v in filter_value]

    return [
        {
            "type": "Number" if value_type == "Number" else "String",
            "value": filter_value,
        }
    ]


"""
utitilies to set proper layout for dashboard items
"""


def get_item_size(item):
    item = frappe._dict(item)
    if item.item_type == "Text":
        return {"w": 20, "h": 3, "x": 0, "y": 0}
    if item.item_type == "Filter":
        return {"w": 4, "h": 3, "x": 0, "y": 0}
    if item.item_type == "Chart":
        chart_type = frappe.db.get_value("Insights Query Chart", item.chart, "type")
        if chart_type == "Number":
            return {"w": 4, "h": 4, "x": 0, "y": 0}
        if chart_type == "Progress":
            return {"w": 6, "h": 5, "x": 0, "y": 0}
        return {"w": 12, "h": 9, "x": 0, "y": 0}
    return {"w": 6, "h": 6, "x": 0, "y": 0}


def get_item_position(item, existing_layouts):
    new_layout = frappe.parse_json(item.get("layout")) or get_item_size(item)
    # find the first available position
    for y in range(0, 100_000):
        for x in range(0, 20):
            new_layout["x"] = x
            new_layout["y"] = y
            if not any(
                [
                    layout_overlap(new_layout, existing_layout)
                    for existing_layout in existing_layouts
                ]
            ):
                return new_layout


def layout_overlap(new_layout, existing_layout):
    return (
        new_layout.get("x") < existing_layout.get("x") + existing_layout.get("w")
        and new_layout.get("x") + new_layout.get("w") > existing_layout.get("x")
        and new_layout.get("y") < existing_layout.get("y") + existing_layout.get("h")
        and new_layout.get("y") + new_layout.get("h") > existing_layout.get("y")
    )
