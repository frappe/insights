"""A summarize carries a money measure's currency code beside the measure. The value
is in every row, read by name. The column is listed nowhere and exported nowhere.
"""

import copy

import frappe

from insights.insights.doctype.insights_data_source_v3.ibis_utils import is_hidden_column
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_test_query, create_test_workbook, delete_users
from insights.tests.permissions_utils import ADMIN, create_test_users

SITE_DB = {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"}

# filters out the site's other ToDos
TOKEN = "insights-hidden-columns"

# a ToDo's priority is a short code, so it stands in for a currency column
OPERATIONS = [
    {"type": "source", "table": SITE_DB},
    {
        "type": "filter_group",
        "logical_operator": "And",
        "filters": [
            {
                "column": {"type": "column", "column_name": "description"},
                "operator": "=",
                "value": TOKEN,
            }
        ],
    },
    {
        "type": "summarize",
        "measures": [
            {
                "measure_name": "todos",
                "column_name": "name",
                "data_type": "Integer",
                "aggregation": "count",
                "format": "currency",
                "currency_column": "priority",
            }
        ],
        "dimensions": [{"dimension_name": "status", "column_name": "status", "data_type": "String"}],
    },
]


def make_todo(status, priority):
    todo = frappe.get_doc(
        {
            "doctype": "ToDo",
            "description": TOKEN,
            "status": status,
            "priority": priority,
        }
    ).insert()
    if priority is None:
        # priority has a default, so empty it after insert
        frappe.db.set_value("ToDo", todo.name, "priority", None)
    return todo.name


class TestHiddenColumns(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_test_users()
        cls.workbook = create_test_workbook(ADMIN, title="Hidden Columns Workbook").name
        cls.query = create_test_query(ADMIN, cls.workbook, title="Hidden Columns", operations=OPERATIONS).name
        with as_user(ADMIN):
            cls.todos = [
                make_todo("Open", "High"),
                make_todo("Closed", "Medium"),
                make_todo("Closed", None),
            ]
        # the query reads over its own connection, so commit
        frappe.db.commit()

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        for todo in cls.todos:
            frappe.delete_doc("ToDo", todo, force=True, ignore_permissions=True)
        frappe.db.commit()
        delete_users(ADMIN)

    def carried(self):
        with as_user(ADMIN):
            result = frappe.get_doc(DT.QUERY, self.query).execute(force=True)
        return result, {row["status"]: row["todos__currency"] for row in result["rows"]}

    def test_the_name_says_what_is_carried(self):
        # the client reads the code off the row by this name
        self.assertTrue(is_hidden_column("todos__currency"))
        self.assertFalse(is_hidden_column("todos"))

    def test_a_query_built_on_this_one_hides_the_carried_column_too(self):
        operations = [
            {
                "type": "source",
                "table": {"type": "query", "workbook": self.workbook, "query_name": self.query},
            }
        ]
        reader = create_test_query(ADMIN, self.workbook, title="Reads Hidden Columns", operations=operations)
        with as_user(ADMIN):
            result = reader.execute(force=True)
            offered = reader.get_columns_for_selection()
        by_name = {c["name"]: c for c in result["columns"]}
        self.assertTrue(by_name["todos__currency"].get("hidden"))
        self.assertNotIn("todos__currency", [c["name"] for c in offered])

    def test_a_carried_column_is_marked_and_its_value_still_rides_in_the_row(self):
        result, by_status = self.carried()
        by_name = {c["name"]: c for c in result["columns"]}
        self.assertTrue(by_name["todos__currency"].get("hidden"))
        self.assertNotIn("hidden", by_name["todos"])
        self.assertEqual(by_status["Open"], "High")
        self.assertEqual(result["currency_symbols"]["High"]["symbol"], "High")
        self.assertNotIn(None, result["currency_symbols"])

    def test_a_group_holding_a_row_without_a_code_carries_none(self):
        # min and max skip nulls, so a null row must void the group on its own
        _, by_status = self.carried()
        self.assertIsNone(by_status["Closed"])

    def test_a_carried_column_is_not_offered_to_the_author(self):
        with as_user(ADMIN):
            offered = frappe.get_doc(DT.QUERY, self.query).get_columns_for_selection()
        names = [c["name"] for c in offered]
        self.assertIn("todos", names)
        self.assertNotIn("todos__currency", names)

    def test_a_currency_column_that_is_gone_carries_none_rather_than_failing(self):
        # a missing column must not fail the query, and it carries null, not the site currency
        operations = copy.deepcopy(OPERATIONS)
        operations[-1]["measures"][0]["currency_column"] = "no_such_column"
        query = create_test_query(ADMIN, self.workbook, title="Missing Currency", operations=operations)
        with as_user(ADMIN):
            result = query.execute(force=True)
        self.assertTrue(all(row["todos__currency"] is None for row in result["rows"]))

    def test_a_carried_column_does_not_leave_in_an_export(self):
        frappe.db.set_single_value("Insights Settings", "allow_download", 1)
        with as_user(ADMIN):
            csv = frappe.get_doc(DT.QUERY, self.query).download_results(format="csv")
        header = csv.splitlines()[0].split(",")
        self.assertIn("todos", header)
        self.assertNotIn("todos__currency", header)
