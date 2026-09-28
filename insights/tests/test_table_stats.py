"""A table's stats answer for one table, and name the queries the caller may read.

`Insights Table v3.get_stats` reports which queries reference the table. Reading
the table is what gets you the stats. Which queries are named is the queries' own
question, and their workbooks answer it.

The table the stats answer for is the one the name identifies. `autoname` builds
that name from the data source and the table, so the two cannot disagree.

The import stats read `Insights Table Import Log`. A finished import writes the
status "Completed", so that is the value the last-import filter has to name.
"""

import frappe
from frappe.utils import add_days, now_datetime, set_request

from insights.api import run_doc_method
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    get_table_name,
    get_table_stats,
)
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


IMPORT_DS = "Site DB"
IMPORT_TABLE = "tabImportStatsTable"


class TestStatsReportTheLastImport(InsightsIntegrationTestCase):
    """The last-import stats come from the newest log the import finished.

    The status a finished import writes is "Completed". A filter on any other
    value matches nothing, and the panel reports an empty last import.
    """

    @classmethod
    def before_class(cls):
        cls.table = get_table_name(IMPORT_DS, IMPORT_TABLE)
        if frappe.db.exists(DT.TABLE, cls.table):
            frappe.delete_doc(DT.TABLE, cls.table, force=True)

        doc = frappe.get_doc(
            {
                "doctype": DT.TABLE,
                "data_source": IMPORT_DS,
                "table": IMPORT_TABLE,
                "label": IMPORT_TABLE,
                "stored": 1,
                "last_synced_on": now_datetime(),
            }
        )
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)

    @classmethod
    def after_class(cls):
        frappe.db.delete("Insights Table Import Log", {"table_name": IMPORT_TABLE})
        frappe.delete_doc(DT.TABLE, cls.table, force=True)

    def before_test(self):
        frappe.db.delete("Insights Table Import Log", {"table_name": IMPORT_TABLE})

    def log_import(self, status, rows=0, seconds=0, days_ago=0):
        log = frappe.get_doc(
            {
                "doctype": "Insights Table Import Log",
                "data_source": IMPORT_DS,
                "table_name": IMPORT_TABLE,
                "status": status,
                "rows_imported": rows,
                "time_taken": seconds,
            }
        )
        log.flags.ignore_links = True
        log.insert(ignore_permissions=True)
        if days_ago:
            frappe.db.set_value(
                "Insights Table Import Log",
                log.name,
                "creation",
                add_days(now_datetime(), -days_ago),
                update_modified=False,
            )
        return log

    def stats(self):
        return get_table_stats(IMPORT_DS, IMPORT_TABLE)

    def test_a_completed_log_reports_its_rows_and_duration(self):
        self.log_import("Completed", rows=1500, seconds=42)

        stats = self.stats()
        self.assertEqual(stats["last_import_rows"], 1500)
        self.assertEqual(stats["last_import_duration"], 42)

    def test_the_newest_completed_log_wins(self):
        self.log_import("Completed", rows=100, seconds=5, days_ago=3)
        self.log_import("Completed", rows=900, seconds=11)

        stats = self.stats()
        self.assertEqual(stats["last_import_rows"], 900)
        self.assertEqual(stats["last_import_duration"], 11)

    def test_a_later_failure_does_not_replace_the_last_import(self):
        """The last import is the last one that finished, not the last attempt."""
        self.log_import("Completed", rows=700, seconds=9, days_ago=1)
        self.log_import("Failed", rows=0, seconds=2)

        stats = self.stats()
        self.assertEqual(stats["last_import_rows"], 700)
        self.assertEqual(stats["last_import_duration"], 9)

    def test_the_stats_count_every_attempt_and_the_failures(self):
        self.log_import("Completed", rows=700, seconds=9, days_ago=1)
        self.log_import("Failed", rows=0, seconds=2)

        stats = self.stats()
        self.assertEqual(stats["total_syncs"], 2)
        self.assertEqual(stats["total_sync_time"], 11)
        self.assertEqual(stats["failed_syncs"], 1)

    def test_no_log_reports_an_empty_last_import(self):
        stats = self.stats()
        self.assertEqual(stats["last_import_rows"], 0)
        self.assertEqual(stats["last_import_duration"], 0)
        self.assertEqual(stats["total_syncs"], 0)
