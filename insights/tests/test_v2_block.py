import contextlib
import io
import json
from unittest.mock import patch

import frappe

from insights.patches import check_legacy_v2_data_before_upgrade as v2_block
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import create_test_dashboard, create_test_workbook

# v3.50 ships no v2 doctypes, so the test makes the tables a site upgraded from
# v3.15 still holds, with only the columns the check reads
V2_TABLES = {
    v2_block.V2_QUERY: "name varchar(140) primary key",
    v2_block.V2_DASHBOARD: "name varchar(140) primary key",
    v2_block.V2_DASHBOARD_ITEM: "name varchar(140) primary key, parent varchar(140), "
    "parenttype varchar(140), options longtext",
}
HIDDEN_V3_DASHBOARD = "tab_hidden_insights_dashboard_v3"


class V2BlockTestCase(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cls.made_tables = [table for table in V2_TABLES if not frappe.db.table_exists(table)]
        for table in cls.made_tables:
            frappe.db.sql_ddl(f"create table `tab{table}` ({V2_TABLES[table]})")

    @classmethod
    def after_class(cls):
        for table in cls.made_tables:
            frappe.db.sql_ddl(f"drop table `tab{table}`")

    def seed(self):
        # a dashboard that reads one query, and a query no dashboard reads; both ran last week
        for query in ("v2-sales", "v2-alone"):
            frappe.db.sql(f"insert into `tab{v2_block.V2_QUERY}` (name) values (%s)", query)
            log = frappe.get_doc(
                {
                    "doctype": "Insights Query Execution Log",
                    "query": query,
                    "data_source": "Site DB",
                    "sql": "select 1",
                }
            ).insert(ignore_permissions=True)
            # a MyISAM table, which the test's rollback does not reach
            self.addCleanup(frappe.db.delete, "Insights Query Execution Log", log.name)
        frappe.db.sql(f"insert into `tab{v2_block.V2_DASHBOARD}` (name) values ('v2-board')")
        frappe.db.sql(
            f"insert into `tab{v2_block.V2_DASHBOARD_ITEM}` (name, parent, parenttype, options) values (%s, %s, %s, %s)",
            ("v2-item", "v2-board", v2_block.V2_DASHBOARD, json.dumps({"query": "v2-sales"})),
        )

    def run_block(self) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            v2_block.execute()
        return out.getvalue()

    def assert_blocked(self):
        self.seed()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            v2_block.execute()

        self.assertEqual(v2_block.unmigrated_v2_dashboards(), ["v2-board"])
        self.assertIn("not migrated yet: 1.", out.getvalue())


class TestV2Block(V2BlockTestCase):
    SAVEPOINT = "test_v2_block"

    # @feature upgrade.v2-block
    def test_a_site_that_used_v2_and_migrated_nothing_is_blocked(self):
        self.assert_blocked()

    # @feature upgrade.v2-block
    def test_a_site_that_migrated_its_dashboards_updates_with_a_query_outside_them(self):
        self.seed()
        workbook = create_test_workbook("Administrator")
        dashboard = create_test_dashboard("Administrator", workbook.name)
        frappe.db.set_value("Insights Dashboard v3", dashboard.name, "old_name", "v2-board")

        self.assertEqual(self.run_block(), "")

    # @feature upgrade.v2-block
    def test_the_site_config_lets_a_site_update_without_migrating(self):
        self.seed()
        with patch.dict(frappe.conf, {"insights_allow_legacy_v2_upgrade": 1}):
            self.assertEqual(self.run_block(), "")


class TestV2BlockFromV2(V2BlockTestCase):
    """A site that updates straight from v2: the check runs before model sync, so
    no v3 table exists yet."""

    SAVEPOINT = "test_v2_block_from_v2"

    @classmethod
    def before_class(cls):
        super().before_class()
        # DDL commits, so it runs here, outside the tests' savepoint
        frappe.db.sql_ddl(f"rename table `tab{v2_block.V3_DASHBOARD}` to `{HIDDEN_V3_DASHBOARD}`")
        frappe.client_cache.delete_value("db_tables")

    @classmethod
    def after_class(cls):
        frappe.db.sql_ddl(f"rename table `{HIDDEN_V3_DASHBOARD}` to `tab{v2_block.V3_DASHBOARD}`")
        frappe.client_cache.delete_value("db_tables")
        super().after_class()

    # @feature upgrade.v2-block
    def test_a_site_updating_straight_from_v2_is_blocked_before_v3_tables_exist(self):
        self.assertFalse(frappe.db.table_exists(v2_block.V3_DASHBOARD))
        self.assert_blocked()
