"""Which row a number card's reading is measured against.

A card fetches one stretch per distinct comparison and gets one row each,
oldest first. Two readings asking different questions therefore read different
rows, and a stretch with no data comes back not at all — neither of which
counting back from the end can say. The server names the rows, and what is
proven here is that it names them right.
"""

import frappe

from insights.api.authoring import get_chart_data as get_authoring_chart_data
from insights.api.view import get_chart_data, get_drill_data
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.insights.query_builders.sql_functions import read_on
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, delete_workbooks

WORKBOOK_TITLE = "Comparison Rows Test Workbook"
TODO_PREFIX = "Comparison Rows Test"

# the day the card is read on, so the stretches it covers never move
ANCHOR = "2026-08-10"

# one row in the stretch a year back, two in the one before this month, three
# in the month so far — so a reading that read the wrong row reads a different
# number
TODOS = {
    f"{TODO_PREFIX} a year back": "2025-08-05",
    f"{TODO_PREFIX} last month one": "2026-07-05",
    f"{TODO_PREFIX} last month two": "2026-07-06",
    f"{TODO_PREFIX} this month one": "2026-08-03",
    f"{TODO_PREFIX} this month two": "2026-08-04",
    f"{TODO_PREFIX} this month three": "2026-08-09",
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


def _count(name):
    return {
        "measure_name": name,
        "column_name": "name",
        "aggregation": "count",
        "data_type": "Integer",
    }


def card_config(comparisons, window):
    """A card counting the todos of its period, one reading per entry.

    An entry of `None` is a reading nothing compares.
    """
    return {
        "sparkline": False,
        "number_columns": [_count(f"count_{index}") for index in range(len(comparisons))],
        "number_column_options": [
            {"comparison": {"source": source}} if source else {} for source in comparisons
        ],
        "date_column": {"column_name": "date", "dimension_name": "date", "data_type": "Date"},
        "window": window,
    }


class TestNumberCardComparisonRows(InsightsIntegrationTestCase):
    SAVEPOINT = "test_number_card_comparison_rows"

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

    def fetch(self, comparisons, anchor=ANCHOR, window=None):
        chart = self.make_chart(comparisons, window or {"span": "month to date", "anchor": anchor})

        with db_connections():
            return frappe.get_doc(DT.CHART, chart.name).fetch(force=True)

    def make_chart(self, comparisons, window):
        workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
        query = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": "Comparison Rows Test Query",
                "workbook": workbook.name,
                "use_live_connection": 1,
                "is_builder_query": 1,
                "operations": todo_operations(),
            }
        ).insert()
        chart = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": "Comparison Rows Test Chart",
                "workbook": workbook.name,
                "query": query.name,
                "chart_type": "Number",
                "config": card_config(comparisons, window),
            }
        ).insert()
        self.dashboard = frappe.get_doc(
            {
                "doctype": DT.DASHBOARD,
                "title": "Comparison Rows Test Dashboard",
                "workbook": workbook.name,
                "items": [
                    {
                        "type": "chart",
                        "chart": chart.name,
                        "layout": {"i": "1", "x": 0, "y": 1, "w": 4, "h": 4},
                    },
                    {
                        "type": "filter",
                        "filter_name": "Date",
                        "filter_type": "Date",
                        "links": {chart.name: f"`{query.name}`.`date`"},
                        "layout": {"i": "2", "x": 0, "y": 0, "w": 4, "h": 1},
                    },
                    {
                        "type": "filter",
                        "filter_name": "Range",
                        "filter_type": "Date",
                        "links": {chart.name: f"`{query.name}`.`date`"},
                        "layout": {"i": "3", "x": 4, "y": 0, "w": 4, "h": 1},
                    },
                ],
            }
        ).insert()
        return chart

    def on_dashboard(self, comparisons, operator, value, window=None, range=None):
        """The card as a dashboard filtered on its date column shows it, read on `ANCHOR`."""
        chart = self.make_chart(comparisons, window)
        filters = {"Date": {"operator": operator, "value": value}}
        if range:
            filters["Range"] = {"operator": "between", "value": range}

        with read_on(ANCHOR), db_connections():
            result = get_chart_data(chart.name, self.dashboard.name, filters=filters, force=True)
        return chart, filters, result

    # @feature charts.number-comparison
    def test_two_readings_asking_different_questions_read_different_rows(self):
        """The one case counting back from the end cannot answer: both readings
        would have read the row before the last, and the card comparing with a
        year back would print the month before under that caption."""
        result = self.fetch(["previous", "last year"])

        self.assertEqual([row["count_0"] for row in result["rows"]], [1, 2, 3])
        self.assertEqual(result["comparison_rows"], {"previous": 1, "last year": 0})

    # @feature charts.number-comparison
    def test_one_question_asked_twice_reads_one_row(self):
        result = self.fetch(["previous", "previous"])

        self.assertEqual([row["count_0"] for row in result["rows"]], [2, 3])
        self.assertEqual(result["comparison_rows"], {"previous": 0})

    # @feature charts.number-comparison
    def test_a_stretch_with_no_data_is_still_a_row_of_its_own(self):
        """Every stretch the card asked for comes back, empty or not, because
        the card reads its rows by position. So the comparison still names a
        row, and the figure in front of it is the stretch's own emptiness."""
        result = self.fetch(["previous", "last year"], anchor="2026-07-10")

        self.assertEqual([row["count_0"] for row in result["rows"]], [0, 0, 2])
        self.assertEqual(result["comparison_rows"], {"previous": 1, "last year": 0})

    # @feature charts.number-comparison
    def test_a_card_nothing_compares_names_no_rows(self):
        self.assertNotIn("comparison_rows", self.fetch([None]))

    # @feature charts.number-comparison
    def test_a_grain_card_reads_the_period_before_its_own(self):
        result = self.fetch(["previous"], window={"grain": "month"})

        self.assertEqual([row["count_0"] for row in result["rows"]], [1, 2, 3])
        self.assertEqual(result["comparison_rows"], {"previous": 1})

    # @feature charts.number-comparison
    def test_a_grain_card_whose_previous_period_has_no_data_names_no_row(self):
        """The day before the newest one has no todos, so the row before the
        last is some earlier day, and reading it would print that day's figure
        as the previous day's."""
        result = self.fetch(["previous"], window={"grain": "day"})

        self.assertEqual(str(result["rows"][-1]["date"])[:10], "2026-08-09")
        self.assertEqual(result["comparison_rows"], {"previous": None})

    # @feature charts.number-period-from-dashboard
    def test_a_card_with_no_period_compares_the_dashboards_span_with_the_one_before(self):
        """Read as a row filter, the span left the card one number and nothing
        to step back from, so `previous` printed nothing."""
        _, _, result = self.on_dashboard(["previous", "last year"], "within", "month to date")

        self.assertEqual([row["count_0"] for row in result["rows"]], [1, 2, 3])
        self.assertEqual(result["comparison_rows"], {"previous": 1, "last year": 0})
        # the card labels its rows and words its comparison by the Period it read
        self.assertEqual(result["chart"]["config"]["window"], {"span": "month to date"})

    # @feature charts.number-period-from-dashboard
    def test_a_date_range_on_the_dashboard_narrows_a_card_with_no_period_to_one_number(self):
        _, _, result = self.on_dashboard(["previous"], "between", ["2026-07-01", "2026-08-10"])

        self.assertEqual([row["count_0"] for row in result["rows"]], [5])
        # asked, with no span to step back from
        self.assertEqual(result["comparison_rows"], {"previous": None})
        self.assertIsNone(result["chart"]["config"]["window"])

    # @feature charts.number-period-from-dashboard
    def test_a_second_filter_on_the_date_column_keeps_the_span_a_row_filter(self):
        """Lent beside a range, the span's comparison stretch would be cut by
        the range: half of July read as "previous month"."""
        _, _, result = self.on_dashboard(
            ["previous"], "within", "month to date", range=["2026-07-15", "2026-08-31"]
        )

        self.assertEqual([row["count_0"] for row in result["rows"]], [3])
        self.assertEqual(result["comparison_rows"], {"previous": None})
        self.assertIsNone(result["chart"]["config"]["window"])

    # @feature charts.number-period-from-dashboard
    def test_a_card_that_states_its_own_period_keeps_it_under_the_dashboards_span(self):
        """The dashboard's span still narrows the rows, so this month reads empty
        and the month before reads July's first ten days."""
        _, _, result = self.on_dashboard(
            ["previous"], "within", "last month", window={"span": "month to date", "anchor": ANCHOR}
        )

        self.assertEqual([row["count_0"] for row in result["rows"]], [2, 0])
        self.assertEqual(result["comparison_rows"], {"previous": 0})
        self.assertEqual(result["chart"]["config"]["window"], {"span": "month to date", "anchor": ANCHOR})

    # @feature charts.number-period-from-dashboard charts.drill-number-card
    def test_a_card_reading_the_dashboards_span_drills_into_that_span_alone(self):
        chart, filters, _ = self.on_dashboard(["previous"], "within", "month to date")

        with db_connections():
            result = get_drill_data(
                chart.name,
                self.dashboard.name,
                filters=filters,
                drill_stack=[
                    {
                        "segment_filters": [{"column": "date", "operator": "=", "value": "2026-08-01"}],
                        "action": {"rows": True, "measure": "count_0"},
                        "read_on": ANCHOR,
                    }
                ],
            )

        self.assertEqual(
            sorted(row["description"] for row in result["rows"]),
            sorted(description for description, date in TODOS.items() if date.startswith("2026-08")),
        )

    # @feature charts.number-period-from-dashboard charts.preview
    def test_the_builders_dashboard_grid_reads_the_card_as_its_reader_does(self):
        """The builder renders the config it is editing, so it gets the lent
        Period beside the rows rather than inside a config."""
        chart, filters, _ = self.on_dashboard(["previous"], "within", "month to date")

        with read_on(ANCHOR), db_connections():
            result = get_authoring_chart_data(
                chart.chart_type,
                chart.query,
                frappe.parse_json(chart.config),
                chart_name=chart.name,
                dashboard_items=frappe.parse_json(self.dashboard.items),
                filters=filters,
                force=True,
            )

        self.assertEqual([row["count_0"] for row in result["rows"]], [2, 3])
        self.assertEqual(result["comparison_rows"], {"previous": 0})
        self.assertEqual(result["period"], {"span": "month to date"})
