from contextlib import contextmanager

import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections


class DT:
    DATA_SOURCE = "Insights Data Source v3"
    TABLE = "Insights Table v3"
    WORKBOOK = "Insights Workbook"
    QUERY = "Insights Query v3"
    CHART = "Insights Chart v3"
    DASHBOARD = "Insights Dashboard v3"
    TEAM = "Insights Team"
    SETTINGS = "Insights Settings"
    USER = "User"


USER_1 = "workbook_flow_user@test.com"
TEST_WORKBOOK_TITLE = "Workbook Flow Test Workbook"
TEST_QUERY_TITLE = "Workbook Flow Test Query"
TEST_CHART_TITLE = "Workbook Flow Test Chart"
TEST_DASHBOARD_TITLE = "Workbook Flow Test Dashboard"


@contextmanager
def as_user(user):
    original_user = frappe.session.user
    frappe.set_user(user)
    try:
        yield
    finally:
        frappe.set_user(original_user)


def create_user(
    email,
    first_name="Test",
    last_name="User",
    roles=None,
    user_type="System User",
    **kwargs,
):
    if frappe.db.exists(DT.USER, email):
        user = frappe.get_doc(DT.USER, email)
    else:
        user = frappe.get_doc(
            {
                "doctype": DT.USER,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "send_welcome_email": 0,
                "user_type": user_type,
                "enabled": 1,
                **kwargs,
            }
        ).insert(ignore_permissions=True)

    if roles and not isinstance(roles, list | tuple | set):
        roles = [roles]

    for role in roles or []:
        if not frappe.db.exists("Has Role", {"parent": email, "role": role}):
            user.add_roles(role)

    return frappe.get_doc(DT.USER, email)


def create_test_user(email=USER_1, role="Insights User"):
    return create_user(
        email,
        first_name="Workbook",
        last_name="Flow User",
        roles=role,
    )


def delete_users(*emails):
    for email in emails:
        frappe.delete_doc(DT.USER, email, force=True)


def delete_test_users():
    delete_users(USER_1)


def create_test_workbook(owner, title=TEST_WORKBOOK_TITLE):
    with as_user(owner):
        return frappe.get_doc({"doctype": DT.WORKBOOK, "title": title}).insert()


def create_test_query(owner, workbook, title=TEST_QUERY_TITLE, operations=None):
    with as_user(owner):
        return frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": title,
                "workbook": workbook,
                "use_live_connection": 1,
                "is_builder_query": 1,
                "operations": operations
                or [
                    {
                        "type": "source",
                        "table": {
                            "type": "table",
                            "data_source": "Site DB",
                            "table_name": "tabToDo",
                        },
                    }
                ],
            }
        ).insert()


def create_test_chart(owner, workbook, query=None, title=TEST_CHART_TITLE):
    with as_user(owner):
        chart = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": title,
                "workbook": workbook,
                "query": query,
                "chart_type": "Bar",
                "config": {},
            }
        ).insert()
    return frappe.get_doc(DT.CHART, chart.name)


def chart_derivation_fixtures():
    """Chart configs paired with the operations they must derive into.

    One case per chart type, plus the branches within a type that produce a
    different shape — a funnel counting measures instead of grouping, a table
    that pivots, a chart whose config sorts by its own measure. The list is what
    says a type derives at all, so a new chart type belongs here on the day it
    lands.

    The shapes were the browser's while the browser derived them, and the
    shipped workbooks carried its output chart by chart. That output is written
    out here instead: read once off the derivations that were checked against
    it, and from here on an expectation this codebase owns.

    `query` is the source query's name, which the derivation does not resolve.
    """
    revenue = {
        "aggregation": "sum",
        "column_name": "base_net_total",
        "data_type": "Decimal",
        "measure_name": "Revenue",
    }
    territory = {
        "column_name": "territory",
        "data_type": "String",
        "dimension_name": "territory",
    }

    return [
        {
            "title": "Revenue by Territory",
            "chart_type": "Map",
            "query": "sales-invoices",
            "config": {
                "filters": {"filters": [], "logical_operator": "And"},
                "limit": 100,
                "order_by": [],
                "map_type": "world",
                "location_column": territory,
                "value_column": revenue,
            },
            "operations": [
                _source_operation("sales-invoices"),
                {"type": "summarize", "measures": [revenue], "dimensions": [territory]},
            ],
        },
        {
            "title": "Customer Value vs Volume",
            "chart_type": "Bubble",
            "query": "sales-invoices",
            "config": {
                "filters": {"filters": [], "logical_operator": "And"},
                "limit": 100,
                "order_by": [],
                "xAxis": revenue,
                "yAxis": {
                    "aggregation": "count",
                    "column_name": "name",
                    "data_type": "Integer",
                    "measure_name": "Invoices",
                },
                "size_column": {
                    "aggregation": "avg",
                    "column_name": "base_net_total",
                    "data_type": "Decimal",
                    "measure_name": "Avg Invoice Value",
                },
                "dimension": {
                    "column_name": "customer",
                    "data_type": "String",
                    "dimension_name": "customer",
                },
                "quadrant_column": territory,
                "show_quadrants": True,
            },
            "operations": [
                _source_operation("sales-invoices"),
                {
                    "type": "summarize",
                    "measures": [
                        revenue,
                        {
                            "aggregation": "count",
                            "column_name": "name",
                            "data_type": "Integer",
                            "measure_name": "Invoices",
                        },
                        {
                            "aggregation": "avg",
                            "column_name": "base_net_total",
                            "data_type": "Decimal",
                            "measure_name": "Avg Invoice Value",
                        },
                    ],
                    "dimensions": [
                        {
                            "column_name": "customer",
                            "data_type": "String",
                            "dimension_name": "customer",
                        },
                        territory,
                    ],
                },
            ],
        },
        {
            # measures mode: no group-by at all, one row carrying every stage
            "title": "Sales Pipeline",
            "chart_type": "Funnel",
            "query": "quotations",
            "config": {
                "filters": {"filters": [], "logical_operator": "And"},
                "limit": 100,
                "order_by": [],
                "show_percentage": True,
                "measures": [
                    {
                        "aggregation": "count",
                        "column_name": "name",
                        "data_type": "Integer",
                        "measure_name": "Quotations",
                    },
                    {
                        "data_type": "Integer",
                        "expression": {
                            "type": "expression",
                            "expression": "count_if(status == 'Ordered')",
                        },
                        "measure_name": "Ordered",
                    },
                ],
            },
            "operations": [
                _source_operation("quotations"),
                {
                    "type": "summarize",
                    "measures": [
                        {
                            "aggregation": "count",
                            "column_name": "name",
                            "data_type": "Integer",
                            "measure_name": "Quotations",
                        },
                        {
                            "data_type": "Integer",
                            "expression": {
                                "type": "expression",
                                "expression": "count_if(status == 'Ordered')",
                            },
                            "measure_name": "Ordered",
                        },
                    ],
                    "dimensions": [],
                },
            ],
        },
        {
            # a table with columns pivots instead of summarizing
            "title": "Revenue by Item Group and Month",
            "chart_type": "Table",
            "query": "sales-invoice-items",
            "config": {
                "filters": {
                    "filters": [
                        {
                            "column": {"type": "column", "column_name": "base_net_amount"},
                            "operator": ">",
                            "value": 0,
                        }
                    ],
                    "logical_operator": "And",
                },
                "limit": 50,
                "max_column_values": 6,
                "order_by": [{"column": {"type": "column", "column_name": "Item Group"}, "direction": "asc"}],
                "rows": [
                    {
                        "column_name": "item_group",
                        "data_type": "String",
                        "dimension_name": "Item Group",
                    }
                ],
                "columns": [
                    {
                        "column_name": "posting_date",
                        "data_type": "Date",
                        "dimension_name": "Month",
                        "granularity": "month",
                    }
                ],
                "values": [
                    {
                        "aggregation": "sum",
                        "column_name": "base_net_amount",
                        "data_type": "Decimal",
                        "measure_name": "Revenue",
                    }
                ],
            },
            "operations": [
                _source_operation("sales-invoice-items"),
                {
                    "type": "filter_group",
                    "logical_operator": "And",
                    "filters": [
                        {
                            "column": {"type": "column", "column_name": "base_net_amount"},
                            "operator": ">",
                            "value": 0,
                        }
                    ],
                },
                {
                    "type": "pivot_wider",
                    "rows": [
                        {
                            "column_name": "item_group",
                            "data_type": "String",
                            "dimension_name": "Item Group",
                        }
                    ],
                    "columns": [
                        {
                            "column_name": "posting_date",
                            "data_type": "Date",
                            "dimension_name": "Month",
                            "granularity": "month",
                        }
                    ],
                    "values": [
                        {
                            "aggregation": "sum",
                            "column_name": "base_net_amount",
                            "data_type": "Decimal",
                            "measure_name": "Revenue",
                        }
                    ],
                    "max_column_values": 6,
                },
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "Item Group"},
                    "direction": "asc",
                },
            ],
        },
        {
            # the chart sorts by its own measure, and the config sorts by it the
            # other way: one order-by survives, the config's
            "title": "Smallest Item Groups",
            "chart_type": "Donut",
            "query": "sales-invoice-items",
            "config": {
                "filters": {"filters": [], "logical_operator": "And"},
                "limit": 100,
                "legend_position": "bottom",
                "order_by": [{"column": {"type": "column", "column_name": "Revenue"}, "direction": "asc"}],
                "label_column": {
                    "column_name": "item_group",
                    "data_type": "String",
                    "dimension_name": "item_group",
                },
                "value_column": {
                    "aggregation": "sum",
                    "column_name": "base_net_amount",
                    "data_type": "Decimal",
                    "measure_name": "Revenue",
                },
            },
            "operations": [
                _source_operation("sales-invoice-items"),
                {
                    "type": "summarize",
                    "measures": [
                        {
                            "aggregation": "sum",
                            "column_name": "base_net_amount",
                            "data_type": "Decimal",
                            "measure_name": "Revenue",
                        }
                    ],
                    "dimensions": [
                        {
                            "column_name": "item_group",
                            "data_type": "String",
                            "dimension_name": "item_group",
                        }
                    ],
                },
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "Revenue"},
                    "direction": "asc",
                },
            ],
        },
        {
            # no measure on the y-axis: the chart counts rows
            "title": "Invoices by Status",
            "chart_type": "Bar",
            "query": "sales-invoices",
            "config": {
                "filters": {"filters": [], "logical_operator": "And"},
                "limit": 100,
                "order_by": [],
                "x_axis": {
                    "dimension": {
                        "column_name": "status",
                        "data_type": "String",
                        "dimension_name": "status",
                    }
                },
                "y_axis": {"series": []},
            },
            "operations": [
                _source_operation("sales-invoices"),
                {
                    "type": "summarize",
                    "measures": [
                        {
                            "column_name": "count",
                            "data_type": "Integer",
                            "aggregation": "count",
                            "measure_name": "count_of_rows",
                        }
                    ],
                    "dimensions": [
                        {
                            "column_name": "status",
                            "data_type": "String",
                            "dimension_name": "status",
                        }
                    ],
                },
            ],
        },
        {
            # one number over the whole result: measures, no dimension
            "title": "Total AP",
            "chart_type": "Number",
            "query": "ap-open-invoices",
            "config": {
                "comparison": False,
                "shorten_numbers": True,
                "sparkline": False,
                "number_columns": [
                    {
                        "aggregation": "sum",
                        "column_name": "outstanding",
                        "data_type": "Decimal",
                        "measure_name": "Total AP",
                    }
                ],
            },
            "operations": [
                _source_operation("ap-open-invoices"),
                {
                    "type": "summarize",
                    "measures": [
                        {
                            "aggregation": "sum",
                            "column_name": "outstanding",
                            "data_type": "Decimal",
                            "measure_name": "Total AP",
                        }
                    ],
                    "dimensions": [],
                },
            ],
        },
        {
            # a date dimension carries its granularity into the summarize
            "title": "Spend Trend",
            "chart_type": "Line",
            "query": "purchase-invoices",
            "config": {
                "filters": {"filters": [], "logical_operator": "And"},
                "limit": 100,
                "order_by": [
                    {"column": {"type": "column", "column_name": "posting_date"}, "direction": "asc"}
                ],
                "x_axis": {
                    "dimension": {
                        "column_name": "posting_date",
                        "data_type": "Date",
                        "dimension_name": "posting_date",
                        "granularity": "month",
                    }
                },
                "y_axis": {
                    "series": [
                        {
                            "measure": {
                                "aggregation": "sum",
                                "column_name": "base_net_total",
                                "data_type": "Decimal",
                                "measure_name": "Spend",
                            }
                        }
                    ],
                    "show_data_labels": False,
                },
            },
            "operations": [
                _source_operation("purchase-invoices"),
                {
                    "type": "summarize",
                    "measures": [
                        {
                            "aggregation": "sum",
                            "column_name": "base_net_total",
                            "data_type": "Decimal",
                            "measure_name": "Spend",
                        }
                    ],
                    "dimensions": [
                        {
                            "column_name": "posting_date",
                            "data_type": "Date",
                            "dimension_name": "posting_date",
                            "granularity": "month",
                        }
                    ],
                },
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "posting_date"},
                    "direction": "asc",
                },
            ],
        },
        {
            # a top-N list: sorted by the measure the summarize just wrote
            "title": "Top 10 Suppliers",
            "chart_type": "Row",
            "query": "purchase-invoices",
            "config": {
                "filters": {"filters": [], "logical_operator": "And"},
                "limit": 10,
                "order_by": [{"column": {"type": "column", "column_name": "Spend"}, "direction": "desc"}],
                "x_axis": {
                    "dimension": {
                        "column_name": "supplier",
                        "data_type": "String",
                        "dimension_name": "supplier",
                    }
                },
                "y_axis": {
                    "series": [
                        {
                            "measure": {
                                "aggregation": "sum",
                                "column_name": "base_net_total",
                                "data_type": "Decimal",
                                "measure_name": "Spend",
                            }
                        }
                    ]
                },
            },
            "operations": [
                _source_operation("purchase-invoices"),
                {
                    "type": "summarize",
                    "measures": [
                        {
                            "aggregation": "sum",
                            "column_name": "base_net_total",
                            "data_type": "Decimal",
                            "measure_name": "Spend",
                        }
                    ],
                    "dimensions": [
                        {
                            "column_name": "supplier",
                            "data_type": "String",
                            "dimension_name": "supplier",
                        }
                    ],
                },
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "Spend"},
                    "direction": "desc",
                },
            ],
        },
        {
            # the value is aggregated per source-and-target pair, which is the
            # one row a Sankey link is
            "title": "Territory to Item Group",
            "chart_type": "Sankey",
            "query": "sales-invoice-items",
            "config": {
                "filters": {"filters": [], "logical_operator": "And"},
                "limit": 100,
                "order_by": [],
                "orient": "horizontal",
                "node_align": "justify",
                "source_column": {
                    "column_name": "territory",
                    "data_type": "String",
                    "dimension_name": "territory",
                },
                "target_column": {
                    "column_name": "item_group",
                    "data_type": "String",
                    "dimension_name": "item_group",
                },
                "value_column": {
                    "aggregation": "sum",
                    "column_name": "base_net_amount",
                    "data_type": "Decimal",
                    "measure_name": "Revenue",
                },
            },
            "operations": [
                _source_operation("sales-invoice-items"),
                {
                    "type": "summarize",
                    "measures": [
                        {
                            "aggregation": "sum",
                            "column_name": "base_net_amount",
                            "data_type": "Decimal",
                            "measure_name": "Revenue",
                        }
                    ],
                    "dimensions": [
                        {
                            "column_name": "territory",
                            "data_type": "String",
                            "dimension_name": "territory",
                        },
                        {
                            "column_name": "item_group",
                            "data_type": "String",
                            "dimension_name": "item_group",
                        },
                    ],
                },
            ],
        },
    ]


def derivation_case(chart_type: str) -> dict:
    """The fixture for one chart type, for a check that is about that type."""
    return next(case for case in chart_derivation_fixtures() if case["chart_type"] == chart_type)


def _source_operation(query):
    return {"type": "source", "table": {"type": "query", "workbook": 0, "query_name": query}}


def create_test_dashboard(owner, workbook, chart=None, title=TEST_DASHBOARD_TITLE):
    with as_user(owner):
        items = []
        if chart:
            items.append({"id": "chart-1", "type": "chart", "chart": chart})

        dashboard = frappe.get_doc(
            {
                "doctype": DT.DASHBOARD,
                "title": title,
                "workbook": workbook,
                "items": items,
            }
        ).insert()
    return frappe.get_doc(DT.DASHBOARD, dashboard.name)


def execute_test_query(query_name):
    query = frappe.get_doc(DT.QUERY, query_name)
    with db_connections():
        return query.execute()


def is_visible(doctype, name):
    return bool(frappe.get_list(doctype, filters={"name": name}, pluck="name", limit=1))


def delete_workbooks(title_prefix=None, owners=None):
    if not title_prefix and not owners:
        raise ValueError("delete_workbooks requires a title_prefix or owners")

    filters = {}
    if title_prefix:
        filters["title"] = ["like", f"{title_prefix}%"]
    if owners:
        filters["owner"] = ["in", list(owners)]

    workbooks = frappe.get_all(DT.WORKBOOK, filters=filters, pluck="name")
    for workbook in workbooks:
        frappe.delete_doc(DT.WORKBOOK, workbook, force=True)


def delete_test_workbooks():
    delete_workbooks(title_prefix=TEST_WORKBOOK_TITLE)


def cleanup_workbook_flow_fixtures():
    delete_test_workbooks()
    delete_test_users()
