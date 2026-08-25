"""A table's stats name the queries the caller may read.

`Insights Table v3.get_stats` reports which queries reference the table. Reading
the table is what gets you the stats. Which queries are named is the queries' own
question, and their workbooks answer it.
"""

import frappe

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
SECRET_TITLE = "Owner Query With A Telling Title"


def create_query_over_the_table(owner, workbook, title):
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
                            "table_name": TABLE,
                        },
                    }
                ],
            }
        ).insert()


class StatsNameReadableQueriesOnly:
    """The rules. Both `enable_permissions` settings run them.

    With the setting off every table is readable, which is the shipped default and
    the wider case. With it on, a team grant is what gets the caller to the table,
    and the rule still has to hold past that point.
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

        create_test_team("team1", [OWNER, OTHER], grants=[("Insights Table v3", cls.table)])

    @classmethod
    def after_class(cls):
        cleanup_test_fixtures()

    def before_test(self):
        self.set_team_permissions(self.ENABLE_PERMISSIONS)

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
