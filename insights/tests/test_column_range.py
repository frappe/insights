"""What a number filter offers to pick from, for a column of whole numbers.

`column_range` reads the smallest and largest a column goes and hands them to
the filter picker. It reads them off a pandas frame, which answers in the
column's own scalar type — and the type an integer column answers in is not one
the response can serialize. A float column's is, so the failure is invisible
until somebody filters a quantity, a count or a year.
"""

import json

import frappe
from frappe.utils.response import json_handler

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

AUTHOR = "column_range_author@test.com"

WORKBOOK_TITLE = "Column Range Test Workbook"
TODO_PREFIX = "Column Range Test"
# descriptions of three lengths, so a measure derived from the length has a
# range with a known low and a known high
TODOS = [f"{TODO_PREFIX} {'x' * extra}" for extra in (0, 5, 20)]
LENGTHS = sorted(len(description) for description in TODOS)


def weighted_operations():
    """A query over `tabToDo` with a whole number per row.

    `tabToDo` carries no number of its own, so the column under test is derived
    from something the fixtures differ on.
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


class TestColumnRange(InsightsIntegrationTestCase):
    SAVEPOINT = "test_column_range"

    @classmethod
    def before_class(cls):
        cls.original_enable_permissions = frappe.db.get_single_value(DT.SETTINGS, "enable_permissions")
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 0)
        cls.cleanup()

        create_user(AUTHOR, first_name="Range", last_name="Author", roles="Insights User")
        for description in TODOS:
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": description,
                    "status": "Open",
                    "allocated_to": AUTHOR,
                    "assigned_by": "Administrator",
                }
            ).insert(ignore_permissions=True)

        with as_user(AUTHOR):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            cls.query = (
                frappe.get_doc(
                    {
                        "doctype": DT.QUERY,
                        "title": "Column Range Test Query",
                        "workbook": workbook.name,
                        "use_live_connection": 1,
                        "is_builder_query": 1,
                        "operations": weighted_operations(),
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

    def column_range(self, column_name):
        with as_user(AUTHOR), db_connections():
            return frappe.get_doc(DT.QUERY, self.query).column_range(column_name)

    # @feature query.filter-number-range
    def test_a_whole_number_column_reports_its_smallest_and_largest(self):
        self.assertEqual(self.column_range("weight"), [LENGTHS[0], LENGTHS[-1]])

    # @feature query.filter-number-range
    def test_a_whole_number_range_can_be_sent_to_the_browser(self):
        """The picker's presets are built from this, and the client swallows the
        error, so a range that cannot be serialized reads as a column with no
        presets."""
        low, high = self.column_range("weight")
        self.assertEqual(json.dumps([low, high], default=json_handler), f"[{LENGTHS[0]}, {LENGTHS[-1]}]")
