"""What the agent search endpoints report, and to whom.

The endpoints search every workbook on the site and quote what they find, so the
rule that matters is the last one here: a caller who may not read a document gets
neither its name nor a line of its content.
"""

import frappe
from frappe.utils import add_days, now_datetime

from insights.api.ai.search import search_columns, search_content
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
)
from insights.tests.permissions_utils import (
    ADMIN,
    TEST_DS,
    TEST_TABLE1,
    USER_1,
    USER_2,
    cleanup_test_fixtures,
    create_test_data_sources,
    create_test_tables,
    create_test_team,
    create_test_users,
)

# one token, nowhere else on the site: a hit for it is a hit on these fixtures
TERM = "netrevenue"
OWNER = USER_1
OUTSIDER = USER_2

WORKBOOK_TITLE = "Agent Search Workbook"
TITLED_QUERY = f"Agent Search {TERM.title()} Monthly"
BODIED_QUERY = "Agent Search Plain Query"


def source_operations(column: str | None = None):
    operations = [
        {
            "type": "source",
            "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
        }
    ]
    if column:
        operations.append(
            {
                "type": "mutate",
                "new_name": column,
                "data_type": "Decimal",
                "mutation": {"type": "expression", "expression": f"q.amount / q.total  # {column}"},
            }
        )
    return operations


class TestAgentSearch(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cleanup_test_fixtures()
        create_test_users()
        create_test_data_sources()
        create_test_tables()

        cls.workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE).name
        # the term is in the title of one query and in the body of the other
        cls.titled_query = create_test_query(
            OWNER, cls.workbook, title=TITLED_QUERY, operations=source_operations()
        ).name
        cls.bodied_query = create_test_query(
            OWNER,
            cls.workbook,
            title=BODIED_QUERY,
            operations=source_operations(f"{TERM}_share"),
        ).name

        cls.chart = create_test_chart(
            OWNER, cls.workbook, query=cls.bodied_query, title="Agent Search Chart"
        ).name
        cls.dashboard = create_test_dashboard(
            OWNER, cls.workbook, chart=cls.chart, title="Agent Search Dashboard"
        ).name

        cls.recent_views = 2
        for days_ago in (1, 2, 40):
            cls.log_view(cls.dashboard, days_ago)

    @classmethod
    def after_class(cls):
        frappe.db.delete("View Log", {"reference_doctype": DT.DASHBOARD, "reference_name": cls.dashboard})
        cleanup_test_fixtures()

    @classmethod
    def log_view(cls, dashboard, days_ago):
        log = frappe.get_doc(
            {
                "doctype": "View Log",
                "reference_doctype": DT.DASHBOARD,
                "reference_name": dashboard,
                "viewed_by": OWNER,
            }
        ).insert(ignore_permissions=True)
        frappe.db.set_value(
            "View Log",
            log.name,
            "creation",
            add_days(now_datetime(), -days_ago),
            update_modified=False,
        )

    def before_test(self):
        self.set_team_permissions(0)

    def search(self, user, term=TERM, **kwargs):
        with self.as_user(user):
            return search_content(term, **kwargs)

    def hit_for(self, hits, name):
        return next((hit for hit in hits if hit["name"] == name), None)

    def test_a_title_match_is_returned(self):
        hit = self.hit_for(self.search(OWNER), self.titled_query)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["matched_field"], "title")
        self.assertEqual(hit["doctype"], DT.QUERY)
        self.assertEqual(hit["workbook"], self.workbook)
        self.assertEqual(hit["workbook_title"], WORKBOOK_TITLE)

    def test_a_body_match_is_returned(self):
        hit = self.hit_for(self.search(OWNER), self.bodied_query)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["matched_field"], "operations")

    def test_the_snippet_quotes_the_term(self):
        hit = self.hit_for(self.search(OWNER), self.bodied_query)
        # the match is marked where it sits, so the column reads as `**term**_share`
        self.assertIn(f"**{TERM}**_share", hit["snippet"].lower())
        # a snippet is an excerpt, not the field
        self.assertLess(len(hit["snippet"]), 300)

    def test_a_title_match_outranks_a_body_match(self):
        hits = self.search(OWNER)
        names = [hit["name"] for hit in hits]
        self.assertLess(names.index(self.titled_query), names.index(self.bodied_query))

    def test_usage_counts_a_query_behind_a_charted_dashboard(self):
        hit = self.hit_for(self.search(OWNER), self.bodied_query)
        self.assertEqual(hit["used_by_charts"], 1)
        self.assertEqual(hit["used_by_dashboards"], 1)
        self.assertEqual(hit["dashboard_views"], self.recent_views)

    def test_a_query_nothing_reads_carries_no_usage(self):
        hit = self.hit_for(self.search(OWNER), self.titled_query)
        self.assertEqual(hit["used_by_charts"], 0)
        self.assertEqual(hit["used_by_dashboards"], 0)
        self.assertEqual(hit["dashboard_views"], 0)

    def test_an_unreadable_workbook_yields_no_hit_and_no_snippet(self):
        """The rule the whole endpoint rests on."""
        self.assertEqual(self.search(OUTSIDER), [])

    def test_a_blank_term_searches_nothing(self):
        self.assertEqual(self.search(OWNER, term="   "), [])

    def test_search_columns_reads_the_stored_columns(self):
        frappe.db.set_value(
            DT.TABLE,
            TEST_TABLE1,
            "columns",
            frappe.as_json([{"name": f"{TERM}_amount", "type": "Decimal"}]),
            update_modified=False,
        )
        self.addCleanup(frappe.db.set_value, DT.TABLE, TEST_TABLE1, "columns", None, update_modified=False)

        with self.as_user(ADMIN):
            matches = search_columns(TERM)

        self.assertEqual(len(matches), 1)
        self.assertEqual(
            matches[0],
            {
                "data_source": TEST_DS,
                "table_name": "table1",
                "label": "table1",
                "column": f"{TERM}_amount",
                "type": "Decimal",
            },
        )

    def test_search_columns_skips_a_table_the_caller_may_not_read(self):
        frappe.db.set_value(
            DT.TABLE,
            TEST_TABLE1,
            "columns",
            frappe.as_json([{"name": f"{TERM}_amount", "type": "Decimal"}]),
            update_modified=False,
        )
        self.addCleanup(frappe.db.set_value, DT.TABLE, TEST_TABLE1, "columns", None, update_modified=False)
        create_test_team("team1", [OWNER])
        self.set_team_permissions(1)

        with self.as_user(OWNER):
            self.assertEqual(search_columns(TERM), [])
