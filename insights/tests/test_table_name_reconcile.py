"""Guards against regressing frappe/insights#1371.

A table list sync used to match the remote tables against the stored spellings, so a
re-spelled table read as one never seen. See `InsightsDataSourcev3.table_identity`.
"""

from unittest.mock import patch

import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    InsightsDataSourcev3,
)
from insights.insights.doctype.insights_table_v3 import table_rename
from insights.insights.doctype.insights_table_v3.insights_table_v3 import InsightsTablev3, get_table_name
from insights.insights.doctype.insights_team.insights_team import (
    get_allowed_resources_for_user,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_query, create_test_workbook, create_user

TITLE = "Table Reconcile Test PG"


class TestTableNameReconcile(InsightsIntegrationTestCase):
    def before_test(self):
        # import logs outlive the data source they name — `on_trash` does not reach them
        frappe.db.delete("Insights Table Import Log", {"data_source": frappe.scrub(TITLE)})
        self.data_source = self.create_data_source()
        # the Data Store is not what these tests are about; a rename always lands
        self.renamed = []
        self.dropped = []
        self.warehouse_moves = True
        self.patch(table_rename, "rename_warehouse_table", self.fake_rename)
        self.patch(table_rename, "drop_warehouse_table", self.fake_drop)

    # helpers

    def patch(self, target, attribute, replacement):
        patcher = patch.object(target, attribute, replacement)
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_rename(self, data_source, old_table, new_table):
        self.renamed.append((old_table, new_table))
        return self.warehouse_moves

    def fake_drop(self, data_source, table):
        self.dropped.append(table)

    def create_data_source(self, schema=None):
        name = frappe.scrub(TITLE)
        if frappe.db.exists("Insights Data Source v3", name):
            frappe.delete_doc("Insights Data Source v3", name, force=True)

        doc = frappe.get_doc(
            {
                "doctype": "Insights Data Source v3",
                "title": TITLE,
                "database_type": "PostgreSQL",
                "database_name": "reconcile_test",
                "schema": schema,
                "host": "localhost",
                "port": 5432,
                "username": "test",
                "password": "test",
            }
        )
        # `on_update` reaches the remote database, which these tests do not have
        with patch.object(InsightsDataSourcev3, "on_update", lambda self: None):
            doc.insert()
        return doc

    def create_table(self, table, stored=0, **kwargs):
        doc = frappe.get_doc(
            {
                "doctype": "Insights Table v3",
                "data_source": self.data_source.name,
                "table": table,
                "label": table,
                "stored": stored,
                **kwargs,
            }
        )
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        return doc

    def create_team_with_grant(self, resource_name, restrictions=None, members=None):
        team = frappe.get_doc(
            {
                "doctype": "Insights Team",
                "team_name": "Reconcile Test Team",
                "team_members": [{"user": member} for member in members or []],
            }
        )
        team.flags.ignore_links = True
        team.insert(ignore_permissions=True)
        self.addCleanup(frappe.delete_doc, "Insights Team", team.name, force=True)
        self.grant(team.name, resource_name, restrictions)
        return team.name

    def grant(self, team, resource_name, restrictions=None):
        parent = frappe.get_doc("Insights Team", team)
        parent.append(
            "team_permissions",
            {
                "resource_type": "Insights Table v3",
                "resource_name": resource_name,
                "table_restrictions": restrictions,
            },
        )
        parent.flags.ignore_links = True
        parent.save(ignore_permissions=True)

    def sync(self, remote_tables):
        with patch.object(InsightsDataSourcev3, "get_table_list", return_value=remote_tables):
            self.data_source.update_table_list()

    def stored_tables(self):
        return sorted(
            frappe.get_all("Insights Table v3", {"data_source": self.data_source.name}, pluck="table")
        )

    # tests

    def test_a_re_spelled_table_is_renamed_not_duplicated(self):
        self.create_table("public.orders", stored=1)

        self.sync(["orders"])

        self.assertEqual(self.stored_tables(), ["orders"])
        self.assertEqual(self.renamed, [("public.orders", "orders")])
        # the record keeps its identity as the name derived from the new table
        self.assertTrue(
            frappe.db.exists("Insights Table v3", get_table_name(self.data_source.name, "orders"))
        )

    def test_a_re_spelled_table_keeps_its_import(self):
        self.create_table("public.orders", stored=1, sync_mode="Full", row_limit=500)

        self.sync(["orders"])

        record = frappe.db.get_value(
            "Insights Table v3",
            get_table_name(self.data_source.name, "orders"),
            ["stored", "row_limit"],
            as_dict=True,
        )
        self.assertEqual(record.stored, 1)
        self.assertEqual(record.row_limit, 500)

    def test_a_re_spelled_table_that_cannot_move_its_data_re_imports(self):
        self.create_table("public.orders", stored=1)
        self.warehouse_moves = False

        self.sync(["orders"])

        stored = frappe.db.get_value(
            "Insights Table v3", get_table_name(self.data_source.name, "orders"), "stored"
        )
        self.assertEqual(stored, 0)

    def test_an_existing_duplicate_pair_is_merged(self):
        self.create_table("public.orders", stored=1, row_limit=900)
        self.create_table("orders", stored=0)

        self.sync(["orders"])

        self.assertEqual(self.stored_tables(), ["orders"])
        survivor = frappe.db.get_value(
            "Insights Table v3",
            get_table_name(self.data_source.name, "orders"),
            ["stored", "row_limit"],
            as_dict=True,
        )
        # the survivor had no copy of its own, so it inherits the one that was importing
        self.assertEqual(survivor.stored, 1)
        self.assertEqual(survivor.row_limit, 900)

    def test_a_merge_keeps_the_survivors_own_import(self):
        self.create_table("public.orders", stored=1, row_limit=900)
        self.create_table("orders", stored=1, row_limit=100)

        self.sync(["orders"])

        self.assertEqual(self.stored_tables(), ["orders"])
        survivor = frappe.db.get_value(
            "Insights Table v3",
            get_table_name(self.data_source.name, "orders"),
            ["stored", "row_limit"],
            as_dict=True,
        )
        self.assertEqual(survivor.row_limit, 100)
        # one remote table, one Data Store copy; the loser's is dropped
        self.assertEqual(self.dropped, ["public.orders"])

    def test_a_rename_follows_the_queries_that_name_the_table(self):
        self.create_table("public.orders")
        workbook = create_test_workbook("Administrator", "Reconcile Test Workbook")
        query = create_test_query(
            "Administrator",
            workbook.name,
            title="Reconcile Test Query",
            operations=[
                {
                    "type": "source",
                    "table": {
                        "type": "table",
                        "data_source": self.data_source.name,
                        "table_name": "public.orders",
                    },
                }
            ],
        )

        self.sync(["orders"])

        operations = frappe.parse_json(frappe.db.get_value("Insights Query v3", query.name, "operations"))
        self.assertEqual(operations[0]["table"]["table_name"], "orders")

    def test_a_new_table_is_still_created(self):
        self.create_table("orders")

        self.sync(["orders", "invoices"])

        self.assertEqual(self.stored_tables(), ["invoices", "orders"])
        self.assertEqual(self.renamed, [])

    def test_a_table_gaining_a_prefix_is_renamed_too(self):
        self.data_source.db_set("schema", "public, sales")
        self.data_source.reload()
        self.create_table("orders", stored=1)

        self.sync(["public.orders", "sales.leads"])

        self.assertEqual(self.stored_tables(), ["public.orders", "sales.leads"])
        self.assertEqual(self.renamed, [("orders", "public.orders")])

    def test_a_table_name_holding_a_dot_is_not_read_as_a_schema(self):
        self.create_table("v1.2 metrics")

        self.sync(["v1.2 metrics"])

        self.assertEqual(self.stored_tables(), ["v1.2 metrics"])
        self.assertEqual(self.renamed, [])

    def test_a_merge_keeps_the_import_settings_when_the_data_cannot_move(self):
        self.create_table("public.orders", stored=1, sync_mode="Incremental", sync_cursor_column="modified")
        self.create_table("orders", stored=0)
        self.warehouse_moves = False

        self.sync(["orders"])

        survivor = frappe.db.get_value(
            "Insights Table v3",
            get_table_name(self.data_source.name, "orders"),
            ["stored", "sync_mode", "sync_cursor_column"],
            as_dict=True,
        )
        # only the copy was at risk — the cursor column is the user's, and unrecoverable
        self.assertEqual(survivor.stored, 0)
        self.assertEqual(survivor.sync_mode, "Incremental")
        self.assertEqual(survivor.sync_cursor_column, "modified")

    def test_a_merge_keeps_the_teams_that_read_the_table(self):
        loser = self.create_table("public.orders", stored=1)
        self.create_table("orders")
        team = self.create_team_with_grant(loser.name, restrictions='[{"column": "region"}]')

        self.sync(["orders"])

        survivor_name = get_table_name(self.data_source.name, "orders")
        grants = frappe.get_all(
            "Insights Resource Permission",
            filters={"parent": team, "resource_type": "Insights Table v3"},
            fields=["resource_name", "table_restrictions"],
        )
        self.assertEqual([g.resource_name for g in grants], [survivor_name])
        self.assertEqual(grants[0].table_restrictions, '[{"column": "region"}]')

    def test_a_merge_does_not_grant_a_team_the_same_table_twice(self):
        loser = self.create_table("public.orders", stored=1)
        survivor = self.create_table("orders")
        team = self.create_team_with_grant(loser.name)
        self.grant(team, survivor.name)

        self.sync(["orders"])

        grants = frappe.get_all(
            "Insights Resource Permission",
            filters={"parent": team, "resource_type": "Insights Table v3"},
            pluck="resource_name",
        )
        self.assertEqual(grants, [get_table_name(self.data_source.name, "orders")])

    def test_a_rename_follows_the_sync_history(self):
        self.create_table("public.orders", stored=1)
        frappe.get_doc(
            {
                "doctype": "Insights Table Import Log",
                "data_source": self.data_source.name,
                "table_name": "public.orders",
                "status": "Completed",
                "rows_imported": 10,
                "time_taken": 2,
            }
        ).insert(ignore_permissions=True)

        self.sync(["orders"])

        logs = frappe.get_all(
            "Insights Table Import Log",
            filters={"data_source": self.data_source.name},
            pluck="table_name",
        )
        self.assertEqual(logs, ["orders"])

    def test_a_merge_keeps_settings_the_user_typed_on_the_survivor(self):
        self.create_table("public.orders", stored=1, sync_mode="Full")
        # the user found the duplicate the sync made and set it up — no import has run yet
        self.create_table("orders", stored=0, sync_mode="Incremental", sync_cursor_column="modified")

        self.sync(["orders"])

        survivor = frappe.db.get_value(
            "Insights Table v3",
            get_table_name(self.data_source.name, "orders"),
            ["sync_mode", "sync_cursor_column"],
            as_dict=True,
        )
        self.assertEqual(survivor.sync_mode, "Incremental")
        self.assertEqual(survivor.sync_cursor_column, "modified")
        # the copy belongs to settings the survivor does not share
        self.assertEqual(self.dropped, ["public.orders"])

    def test_a_merge_keeps_a_label_the_user_wrote(self):
        loser = self.create_table("public.orders")
        frappe.db.set_value("Insights Table v3", loser.name, "label", "Orders 2026")
        self.create_table("orders")

        self.sync(["orders"])

        label = frappe.db.get_value(
            "Insights Table v3", get_table_name(self.data_source.name, "orders"), "label"
        )
        self.assertEqual(label, "Orders 2026")

    def test_a_rename_clears_the_cached_team_grants(self):
        loser = self.create_table("public.orders", stored=1)
        self.create_table("orders")
        user = create_user("reconcile_test_user@test.com", roles="Insights User")
        self.addCleanup(frappe.delete_doc, DT.USER, user.name, force=True)
        self.create_team_with_grant(loser.name, members=[user.name])
        self.set_team_permissions(True)

        # read once, so the allowed list is cached under the old record name
        self.assertEqual(get_allowed_resources_for_user("Insights Table v3", user.name), [loser.name])

        self.sync(["orders"])

        survivor_name = get_table_name(self.data_source.name, "orders")
        self.assertEqual(get_allowed_resources_for_user("Insights Table v3", user.name), [survivor_name])

    def test_a_rename_follows_a_link_on_either_side(self):
        self.create_table("public.orders")
        self.create_table("public.customers")
        frappe.get_doc(
            {
                "doctype": "Insights Table Link v3",
                "data_source": self.data_source.name,
                "left_table": "public.customers",
                "left_column": "name",
                "right_table": "public.orders",
                "right_column": "customer",
            }
        ).insert(ignore_permissions=True)

        self.sync(["orders", "customers"])

        link = frappe.get_all(
            "Insights Table Link v3",
            filters={"data_source": self.data_source.name},
            fields=["left_table", "right_table"],
        )[0]
        self.assertEqual(link.left_table, "customers")
        self.assertEqual(link.right_table, "orders")

    def test_a_rename_leaves_the_other_side_of_a_link_alone(self):
        self.create_table("public.orders")
        self.create_table("regions")
        frappe.get_doc(
            {
                "doctype": "Insights Table Link v3",
                "data_source": self.data_source.name,
                "left_table": "regions",
                "left_column": "name",
                "right_table": "public.orders",
                "right_column": "region",
            }
        ).insert(ignore_permissions=True)

        self.sync(["orders", "regions"])

        link = frappe.get_all(
            "Insights Table Link v3",
            filters={"data_source": self.data_source.name},
            fields=["left_table", "right_table"],
        )[0]
        self.assertEqual(link.left_table, "regions")
        self.assertEqual(link.right_table, "orders")

    def test_a_merge_inherits_when_the_survivor_came_from_a_bulk_insert(self):
        self.create_table("public.orders", stored=1, sync_cursor_column="modified")
        # the sync writes records through `bulk_insert`, which names no sync field
        InsightsTablev3.bulk_create(self.data_source.name, ["orders"])

        self.sync(["orders"])

        survivor = frappe.db.get_value(
            "Insights Table v3",
            get_table_name(self.data_source.name, "orders"),
            ["stored", "sync_cursor_column"],
            as_dict=True,
        )
        self.assertEqual(survivor.stored, 1)
        self.assertEqual(survivor.sync_cursor_column, "modified")
