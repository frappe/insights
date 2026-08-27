"""A table's stats answer for one table, and name the queries the caller may read.

`Insights Table v3.get_stats` reports which queries reference the table. Reading
the table is what gets you the stats. Which queries are named is the queries' own
question, and their workbooks answer it.

The table the stats answer for is the one the name identifies. `autoname` builds
that name from the data source and the table, so the two cannot disagree.
"""

import frappe
from frappe.utils import set_request

from insights.api import run_doc_method
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_test_workbook
from insights.tests.permissions_utils import (
    TEST_DS,
    USER_1,
    USER_2,
    cleanup_test_fixtures,
    create_test_data_sources,
    create_test_tables,
    create_test_team,
    create_test_users,
)

OWNER = USER_1
OTHER = USER_2

TABLE = "table1"
OTHER_TABLE = "table2"
SECRET_TITLE = "Owner Query With A Telling Title"


def create_query_over_the_table(owner, workbook, title, table=TABLE):
    with as_user(owner):
        return frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": title,
                "workbook": workbook,
                "use_live_connection": 1,
                "is_builder_query": 1,
                "operations": [
                    {
                        "type": "source",
                        "table": {
                            "type": "table",
                            "data_source": TEST_DS,
                            "table_name": table,
                        },
                    }
                ],
            }
        ).insert()


class StatsNameReadableQueriesOnly:
    """The rules. Both `enable_permissions` settings run them.

    Off, every table is readable. On, a team grant is what reaches the table, and
    the rule still has to hold past that point.
    """

    ENABLE_PERMISSIONS = 0

    @classmethod
    def before_class(cls):
        cleanup_test_fixtures()
        create_test_users()
        create_test_data_sources()
        create_test_tables()
        cls.table = get_table_name(TEST_DS, TABLE)

        cls.owner_workbook = create_test_workbook(OWNER, title="Stats Owner Workbook").name
        cls.owner_query = create_query_over_the_table(OWNER, cls.owner_workbook, SECRET_TITLE).name

        cls.other_workbook = create_test_workbook(OTHER, title="Stats Other Workbook").name
        cls.other_query = create_query_over_the_table(OTHER, cls.other_workbook, "Other Query").name

        cls.other_table = get_table_name(TEST_DS, OTHER_TABLE)
        cls.query_on_other_table = create_query_over_the_table(
            OTHER, cls.other_workbook, "Other Table Query", table=OTHER_TABLE
        ).name

        create_test_team("team1", [OWNER, OTHER], grants=[("Insights Table v3", cls.table)])

    @classmethod
    def after_class(cls):
        cleanup_test_fixtures()

    def before_test(self):
        self.set_team_permissions(self.ENABLE_PERMISSIONS)
        set_request(method="POST", path="/api/method/insights.api.run_doc_method")

    def referencing_queries(self, user):
        with self.as_user(user):
            stats = frappe.get_doc(DT.TABLE, self.table).get_stats()
        return [q["name"] for q in stats["referencing_queries"]]

    def test_a_query_in_another_workbook_is_not_readable(self):
        """The baseline the rule below is measured against."""
        with self.as_user(OTHER):
            self.assertFalse(frappe.has_permission(DT.QUERY, ptype="read", doc=self.owner_query))

    def test_the_stats_name_your_own_query(self):
        self.assertIn(self.other_query, self.referencing_queries(OTHER))

    def test_the_stats_do_not_name_a_query_you_cannot_read(self):
        self.assertNotIn(self.owner_query, self.referencing_queries(OTHER))

    def test_a_pair_that_disagrees_with_the_name_is_refused(self):
        """The name is built from the pair, so the two naming different tables is
        not a request that can be answered."""
        with self.as_user(OTHER), self.assertRaises(frappe.ValidationError):
            run_doc_method(
                "get_stats",
                docs={
                    "doctype": DT.TABLE,
                    "name": self.table,
                    "data_source": TEST_DS,
                    "table": OTHER_TABLE,
                },
            )

    def test_a_body_that_omits_the_pair_is_refused(self):
        """`get_table_name` concatenates the two, so a missing one has to be
        refused before it is read, not raise `TypeError` inside the hash."""
        with self.as_user(OTHER), self.assertRaises(frappe.ValidationError):
            run_doc_method("get_stats", docs={"doctype": DT.TABLE, "name": self.table})

    def test_the_stats_answer_when_the_pair_agrees(self):
        """The path the client actually takes."""
        with self.as_user(OTHER):
            stats = run_doc_method(
                "get_stats",
                docs={
                    "doctype": DT.TABLE,
                    "name": self.table,
                    "data_source": TEST_DS,
                    "table": TABLE,
                },
            )

        names = [q["name"] for q in stats["referencing_queries"]]
        self.assertIn(self.other_query, names)
        self.assertNotIn(self.query_on_other_table, names)

    def test_an_administrator_still_sees_every_query(self):
        """Narrowing is per caller, not a smaller report for everyone."""
        names = self.referencing_queries("Administrator")
        self.assertIn(self.owner_query, names)
        self.assertIn(self.other_query, names)


class TestStatsNameReadableQueriesOnly(StatsNameReadableQueriesOnly, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 0


class TestStatsNameReadableQueriesOnlyWithTeamPermissions(
    StatsNameReadableQueriesOnly, InsightsIntegrationTestCase
):
    ENABLE_PERMISSIONS = 1
