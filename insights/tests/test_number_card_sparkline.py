"""A windowed number card's sparkline, from the config to the rows.

The card and its trend are two executions of one fetch. What is proven here is
what derivation cannot say on its own: that the second execution runs, that it
runs under the same filters as the first, and that a card asking for no trend
runs nothing extra.
"""

import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, delete_workbooks

WORKBOOK_TITLE = "Sparkline Test Workbook"
TODO_PREFIX = "Sparkline Test"

# the day the card is read on, so the window it covers never moves
ANCHOR = "2026-08-10"
IN_WINDOW = f"{TODO_PREFIX} third"

# two on one day and one on another, plus a row on either side of the window
TODOS = {
    f"{TODO_PREFIX} first": "2026-08-03",
    f"{TODO_PREFIX} second": "2026-08-03",
    IN_WINDOW: "2026-08-09",
    f"{TODO_PREFIX} before the window": "2026-07-20",
    f"{TODO_PREFIX} after the anchor": "2026-08-20",
}


def todo_operations():
    """A query over `tabToDo`, narrowed to this module's fixtures."""
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
    ]


def card_config(sparkline=True, window=True):
    """A card counting the todos of the month so far."""
    config = {
        "sparkline": sparkline,
        "number_columns": [
            {
                "measure_name": "count",
                "column_name": "name",
                "aggregation": "count",
                "data_type": "Integer",
            }
        ],
        "date_column": {"column_name": "date", "dimension_name": "date", "data_type": "Date"},
        "number_column_options": [{}],
    }
    if window:
        config["window"] = {"span": "month to date", "anchor": ANCHOR}
    return config


class TestNumberCardSparkline(InsightsIntegrationTestCase):
    SAVEPOINT = "test_number_card_sparkline"

    @classmethod
    def before_class(cls):
        cls.cleanup()
        for description, date in TODOS.items():
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": description,
                    "date": date,
                    "assigned_by": "Administrator",
                }
            ).insert(ignore_permissions=True)

    @classmethod
    def after_class(cls):
        cls.cleanup()

    @classmethod
    def cleanup(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        for todo in frappe.get_all(
            "ToDo", filters={"description": ["like", f"%{TODO_PREFIX}%"]}, pluck="name"
        ):
            frappe.delete_doc("ToDo", todo, force=True, ignore_permissions=True)

    def make_card(self, **kwargs):
        workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
        query = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": "Sparkline Test Query",
                "workbook": workbook.name,
                "use_live_connection": 1,
                "is_builder_query": 1,
                "operations": todo_operations(),
            }
        ).insert()
        chart = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": "Sparkline Test Chart",
                "workbook": workbook.name,
                "query": query.name,
                "chart_type": "Number",
                "config": card_config(**kwargs),
            }
        ).insert()

        return query, frappe.get_doc(DT.CHART, chart.name)

    def fetch(self, chart, query=None, description=None):
        """The card's rows, narrowed by a dashboard filter when one is named.

        The filter state goes over unrouted, the way a surface sends it: the grid
        it sits on and the link that says which column it lands on.
        """
        kwargs = {}
        if description:
            kwargs = {
                "chart_name": chart.name,
                "dashboard_items": [
                    {"type": "chart", "chart": chart.name},
                    {
                        "type": "filter",
                        "filter_name": "Description",
                        "links": {chart.name: f"`{query.name}`.`description`"},
                    },
                ],
                "filters": {"Description": {"operator": "=", "value": description}},
            }
        with db_connections():
            return chart.get_data(force=True, **kwargs)

    def days(self, result):
        return [(str(row["date"])[:10], row["count"]) for row in result["sparkline"]["rows"]]

    def test_the_series_splits_the_cards_own_window_by_day(self):
        _, chart = self.make_card()

        result = self.fetch(chart)

        # one row per window is what the number is read off
        self.assertEqual([row["count"] for row in result["rows"]], [3])
        self.assertEqual(self.days(result), [("2026-08-03", 2), ("2026-08-09", 1)])

    def test_one_filter_reaches_the_number_and_the_series(self):
        """A filter that moves the number and leaves the series behind draws a
        trend of a number nobody is reading."""
        query, chart = self.make_card()

        result = self.fetch(chart, query, IN_WINDOW)

        self.assertEqual([row["count"] for row in result["rows"]], [1])
        self.assertEqual(self.days(result), [("2026-08-09", 1)])

    def test_nothing_but_a_windowed_sparkline_runs_a_second_query(self):
        for case, kwargs in [
            ("the sparkline is off", {"sparkline": False}),
            ("the card has no window", {"window": False}),
        ]:
            with self.subTest(case=case):
                _, chart = self.make_card(**kwargs)
                self.assertNotIn("sparkline", self.fetch(chart))

    def test_the_number_reads_the_same_whether_the_trend_is_drawn_or_not(self):
        """The trend is asked beside the number, never instead of it."""
        _, drawn = self.make_card()
        _, plain = self.make_card(sparkline=False)

        self.assertEqual(self.fetch(drawn)["rows"], self.fetch(plain)["rows"])
