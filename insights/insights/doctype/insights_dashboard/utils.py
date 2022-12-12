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


def is_string_or_number(arg):
    return arg.get("type") == "String" or arg.get("type") == "Number"


def is_simple_filter(condition):
    return (
        condition.get("type") == "BinaryExpression"
        and condition.get("left").get("type") == "Column"
        and is_string_or_number(condition.get("right"))
    ) or (
        condition.get("type") == "CallExpression"
        and condition.get("arguments")[0].get("type") == "Column"
        and all(is_string_or_number(arg) for arg in condition.get("arguments")[1:])
    )


def convert_into_simple_filter(expression):
    if not expression:
        return

    if not is_simple_filter(expression):
        print("Not a simple filter")
        return
    if is_binary_operator(expression.get("operator")):
        column = expression.get("left").get("value")
        operator = expression.get("operator")
        value = expression.get("right").get("value")
        return {"column": column, "operator": operator, "value": value}

    if is_call_function(expression.get("function")):
        column = expression.get("arguments")[0].get("value")
        operator = get_operator_from_call_function(expression.get("function"))
        label, value = make_value_from_call_function(expression)
        return {"column": column, "operator": operator, "value": value}


FILTER_FUNCTIONS = {
    "is": "is",
    "in": "one of",
    "not_in": "not one of",
    "between": "between",
    "timespan": "within",
    "starts_with": "starts with",
    "ends_with": "ends with",
    "contains": "contains",
    "not_contains": "not contains",
}


def get_operator_from_call_function(function_name):
    if FILTER_FUNCTIONS.get(function_name):
        return function_name
    if "set" in function_name:
        return "is"
    return None


def is_binary_operator(operator):
    if not operator:
        return False
    return operator in BINARY_OPERATORS.values()


def is_call_function(function_name):
    if not function_name:
        return False
    return bool(FILTER_FUNCTIONS.get(get_operator_from_call_function(function_name)))


def make_value_from_call_function(expression):
    if expression.get("function") == "is_set":
        return ["Set", "Set"]
    if expression.get("function") == "is_not_set":
        return ["Not Set", "Not Set"]
    if expression.get("function") == "between":
        value = (
            expression.get("arguments")[1].get("value")
            + ", "
            + expression.get("arguments")[2].get("value")
        )
        return [value, value]
    if expression.get("function") in ["in", "not_in"]:
        values = [a.get("value") for a in expression.get("arguments")[1:]]
        label = str(len(values)) + " values" if len(values) > 1 else values[0]
        return [label, values]
    value = expression.get("arguments")[1].get("value")
    return [value, value]


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
