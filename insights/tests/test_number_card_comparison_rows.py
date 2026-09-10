"""Which row a number card's reading is measured against.

A card fetches one stretch per distinct comparison and gets one row each,
oldest first. Two readings asking different questions therefore read different
rows, and a stretch with no data comes back not at all — neither of which
counting back from the end can say. The server names the rows, and what is
proven here is that it names them right.
"""

import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
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


def card_config(comparisons, anchor=ANCHOR):
    """A card counting the todos of the month so far, one reading per entry.

    An entry of `None` is a reading nothing compares.
    """
    return {
        "sparkline": False,
        "number_columns": [_count(f"count_{index}") for index in range(len(comparisons))],
        "number_column_options": [
            {"comparison": {"source": source}} if source else {} for source in comparisons
        ],
        "date_column": {"column_name": "date", "dimension_name": "date", "data_type": "Date"},
        "window": {"span": "month to date", "anchor": anchor},
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

    def fetch(self, comparisons, anchor=ANCHOR):
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
                "config": card_config(comparisons, anchor),
            }
        ).insert()

        with db_connections():
            return frappe.get_doc(DT.CHART, chart.name).get_data(force=True)

    def test_two_readings_asking_different_questions_read_different_rows(self):
        """The one case counting back from the end cannot answer: both readings
        would have read the row before the last, and the card comparing with a
        year back would print the month before under that caption."""
        result = self.fetch(["previous", "last year"])

        self.assertEqual([row["count_0"] for row in result["rows"]], [1, 2, 3])
        self.assertEqual(result["comparison_rows"], {"previous": 1, "last year": 0})

    def test_one_question_asked_twice_reads_one_row(self):
        result = self.fetch(["previous", "previous"])

        self.assertEqual([row["count_0"] for row in result["rows"]], [2, 3])
        self.assertEqual(result["comparison_rows"], {"previous": 0})

    def test_a_question_that_came_back_empty_is_named_with_nothing(self):
        """A stretch with no data returns no row, which is not the same as a
        question this period cannot be asked: the card still prints what it
        would have compared against, with no figure in front of it."""
        result = self.fetch(["previous", "last year"], anchor="2026-07-10")

        self.assertEqual([row["count_0"] for row in result["rows"]], [2])
        self.assertEqual(result["comparison_rows"], {"previous": None, "last year": None})

    def test_a_card_nothing_compares_names_no_rows(self):
        self.assertNotIn("comparison_rows", self.fetch([None]))
