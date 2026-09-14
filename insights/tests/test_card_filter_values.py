"""What a reader's own filter on a card offers, and what it may ask about.

A card filter names a column of the picture. So the values it lists come from
the card's own query — narrowed the way the card is narrowed, because a list
offering rows the card does not show reaches past what the chart published.

Which columns may be asked about is the card's operations, not two slots of its
config: a measure and a column a pivot made are drawn and hold no source
column, so they offer no values rather than refusing a reader mid-action.
"""

import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

AUTHOR = "card_filter_author@test.com"

WORKBOOK_TITLE = "Card Filter Test Workbook"
TODO_PREFIX = "Card Filter Test"

OPEN_ONE = f"{TODO_PREFIX} open one"
OPEN_TWO = f"{TODO_PREFIX} open two longer"
CLOSED = f"{TODO_PREFIX} closed and very much the longest of them all"
TODOS = {OPEN_ONE: "Open", OPEN_TWO: "Open", CLOSED: "Closed"}
OPEN_TODOS = sorted(d for d, status in TODOS.items() if status == "Open")
OPEN_LENGTHS = sorted(len(d) for d in OPEN_TODOS)


def todo_operations():
    """A query over `tabToDo`, narrowed to this module's fixtures, with a number.

    `tabToDo` carries no number of its own, and a range has nothing to report
    without one.
    """
    return [
        {
            "type": "source",
            "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
        },
        {
            "type": "filter",
            "column": {"type": "column", "column_name": "description"},
            "operator": "contains",
            "value": TODO_PREFIX,
        },
        {
            "type": "mutate",
            "new_name": "weight",
            "data_type": "Integer",
            "expression": {"type": "expression", "expression": "description.length()"},
        },
    ]


def dimension(column_name, data_type="String"):
    return {"column_name": column_name, "dimension_name": column_name, "data_type": data_type}


def count(measure_name="Todos"):
    return {
        "measure_name": measure_name,
        "column_name": "name",
        "aggregation": "count",
        "data_type": "Integer",
    }


def open_only():
    """The card's own filter: it draws the open todos and nothing else."""
    return {
        "logical_operator": "And",
        "filters": [
            {
                "type": "filter",
                "column": {"type": "column", "column_name": "status"},
                "operator": "=",
                "value": "Open",
            }
        ],
    }


class TestCardFilterValues(InsightsIntegrationTestCase):
    SAVEPOINT = "test_card_filter_values"

    @classmethod
    def before_class(cls):
        cls.original_enable_permissions = frappe.db.get_single_value(DT.SETTINGS, "enable_permissions")
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 0)
        cls.cleanup()

        create_user(AUTHOR, first_name="Card", last_name="Author", roles="Insights User")
        for description, status in TODOS.items():
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": description,
                    "status": status,
                    "allocated_to": AUTHOR,
                    "assigned_by": "Administrator",
                }
            ).insert(ignore_permissions=True)

        with as_user(AUTHOR):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            cls.workbook = workbook.name
            cls.query = (
                frappe.get_doc(
                    {
                        "doctype": DT.QUERY,
                        "title": "Card Filter Test Query",
                        "workbook": cls.workbook,
                        "use_live_connection": 1,
                        "is_builder_query": 1,
                        "operations": todo_operations(),
                    }
                )
                .insert()
                .name
            )
            cls.table = cls.make_chart(
                "Table",
                {
                    "filters": open_only(),
                    "order_by": [],
                    "rows": [dimension("description"), dimension("weight", "Integer")],
                    "columns": [],
                    "values": [count()],
                },
            )
            cls.pivot = cls.make_chart(
                "Table",
                {
                    "filters": open_only(),
                    "order_by": [],
                    "rows": [dimension("description")],
                    "columns": [dimension("status")],
                    "values": [count()],
                },
            )
            cls.bar = cls.make_chart(
                "Bar",
                {
                    "filters": open_only(),
                    "order_by": [],
                    "x_axis": {"dimension": dimension("description")},
                    "y_axis": {"series": []},
                },
            )
            cls.dashboard = (
                frappe.get_doc(
                    {
                        "doctype": DT.DASHBOARD,
                        "title": "Card Filter Test Dashboard",
                        "workbook": cls.workbook,
                        "items": [
                            {
                                "type": "chart",
                                "chart": chart,
                                "layout": {"i": chart, "x": 0, "y": index, "w": 10, "h": 8},
                            }
                            for index, chart in enumerate([cls.table, cls.pivot, cls.bar])
                        ],
                    }
                )
                .insert()
                .name
            )

    @classmethod
    def make_chart(cls, chart_type, config):
        return (
            frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": f"Card Filter {chart_type} {len(config.get('columns') or [])}",
                    "workbook": cls.workbook,
                    "query": cls.query,
                    "chart_type": chart_type,
                    "config": config,
                }
            )
            .insert()
            .name
        )

    @classmethod
    def after_class(cls):
        cls.cleanup()
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", cls.original_enable_permissions)

    @classmethod
    def cleanup(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        for todo in frappe.get_all(
            "ToDo", filters={"description": ["like", f"%{TODO_PREFIX}%"]}, pluck="name"
        ):
            frappe.delete_doc("ToDo", todo, force=True, ignore_permissions=True)
        delete_users(AUTHOR)

    def values(self, chart, column):
        with as_user(AUTHOR), db_connections():
            return frappe.get_doc(DT.DASHBOARD, self.dashboard).get_card_column_values(chart, column)

    def column_range(self, chart, column):
        with as_user(AUTHOR), db_connections():
            return frappe.get_doc(DT.DASHBOARD, self.dashboard).get_card_column_range(chart, column)

    # @feature dashboard.card-filter
    def test_a_card_filter_offers_only_what_the_card_draws(self):
        """The card draws the open todos, so the closed one is not a value its
        filter may offer."""
        self.assertEqual(sorted(self.values(self.table, "description")), OPEN_TODOS)

    # @feature dashboard.card-filter
    def test_a_card_filter_s_range_covers_only_what_the_card_draws(self):
        """A range read off more rows than the card draws is the same overreach
        as a value list read off them."""
        self.assertEqual(self.column_range(self.table, "weight"), [OPEN_LENGTHS[0], OPEN_LENGTHS[-1]])

    # @feature dashboard.card-filter
    def test_an_axis_chart_s_own_dimension_can_be_filtered(self):
        """The x-axis is a column the card draws, the same as a table's rows."""
        self.assertEqual(sorted(self.values(self.bar, "description")), OPEN_TODOS)

    # @feature dashboard.card-filter
    def test_a_measure_the_card_draws_offers_no_values(self):
        """A measure is computed over the result and holds no source column. The
        picker asks anyway, so this is a normal reader action and not a refusal."""
        self.assertEqual(self.values(self.table, "Todos"), [])
        self.assertIsNone(self.column_range(self.table, "Todos"))

    # @feature dashboard.card-filter
    def test_a_column_a_pivot_made_offers_no_values(self):
        """A pivot names its columns after the values its data holds, so the
        config cannot say which ones the card draws."""
        self.assertEqual(self.values(self.pivot, "Open"), [])

    # @feature dashboard.card-filter
    def test_a_column_the_card_does_not_draw_is_refused(self):
        with self.assertRaises(frappe.PermissionError):
            self.values(self.bar, "status")
