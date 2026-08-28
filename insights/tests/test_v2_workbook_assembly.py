"""A v2 dashboard becomes a v3 workbook: its closure, in order, written once.

Two halves, tested apart. The plan is pure - closure, order, cycle, and the
report - so it is a unit test over dicts. The write is an integration test: it
builds a small v2 dashboard in the v2 tables, migrates it, and reads the v3 rows
back.

The fixture goes in with SQL, the way the migrator reads. Removing the v2 code
takes the v2 doctype rows with it and leaves the tables and their rows standing,
which is the state the migrator is built for, so the fixture has to stand in it
too - with or without the v2 meta this site happens to carry.
"""

import json

import frappe
from frappe.tests import UnitTestCase

from insights.migrator.v2_workbooks import (
    CircularQueryReference,
    DashboardPlan,
    candidate_roots,
    closure,
    dashboard_roots,
    format_report,
    load_v2_dashboard,
    load_v2_queries,
    migrate_dashboard,
    plan_dashboard,
    resolve_v3_data_source,
    result_columns,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT

V2_SOURCE_TITLE = "V2 Migration Test"
V2_SOURCE_V3_NAME = "v2_migration_test"


def insert_row(doctype, row):
    """Put a row in a v2 table without asking the meta whether the doctype exists."""
    row = {
        "creation": frappe.utils.now(),
        "modified": frappe.utils.now(),
        "modified_by": "Administrator",
        "owner": "Administrator",
        "docstatus": 0,
        **row,
    }
    columns = ", ".join(f"`{key}`" for key in row)
    placeholders = ", ".join(["%s"] * len(row))
    frappe.db.sql(f"insert into `tab{doctype}` ({columns}) values ({placeholders})", tuple(row.values()))


def v2_query(name, table, columns=None, data_source=V2_SOURCE_TITLE, **overrides):
    spec = {
        "table": {"table": table, "label": table},
        "joins": [],
        "columns": columns or [],
        "calculations": [],
        "filters": [],
        "measures": [],
        "dimensions": [],
        "orders": [],
        "limit": None,
    }
    query = {
        "name": name,
        "title": name,
        "data_source": data_source,
        "json": json.dumps(spec),
        "sql": "SELECT 1",
        "script": None,
        "is_native_query": 0,
        "is_assisted_query": 1,
        "is_script_query": 0,
        "transforms": [],
    }
    query.update(overrides)
    return query


def group_by(column, label, data_type="String"):
    return {
        "aggregation": "group by",
        "alias": label,
        "label": label,
        "column": column,
        "table": "tabIssue",
        "type": data_type,
        "expression": {},
        "granularity": "",
        "order": None,
    }


def count_column(label="Count of records"):
    return {
        "aggregation": "count",
        "alias": label,
        "label": label,
        "column": "*",
        "table": "tabIssue",
        "type": "Integer",
        "expression": {},
        "granularity": "",
        "order": None,
    }


class TestV2Planning(UnitTestCase):
    def test_closure_puts_a_reference_before_the_query_that_reads_it(self):
        queries = {
            "QRY-1": v2_query("QRY-1", "tabIssue"),
            "QRY-2": v2_query("QRY-2", "QRY-1", data_source="Query Store"),
            "QRY-3": v2_query("QRY-3", "QRY-2", data_source="Query Store"),
        }
        ordered = closure(["QRY-3"], queries)
        self.assertEqual(ordered, ["QRY-1", "QRY-2", "QRY-3"])

    def test_closure_reaches_a_query_only_a_join_names(self):
        joined = v2_query("QRY-2", "tabIssue")
        spec = json.loads(joined["json"])
        spec["joins"] = [
            {
                "left_table": {"table": "tabIssue"},
                "right_table": {"table": "QRY-1"},
                "left_column": {"column": "name"},
                "right_column": {"column": "name"},
            }
        ]
        joined["json"] = json.dumps(spec)
        queries = {"QRY-1": v2_query("QRY-1", "tabIssue"), "QRY-2": joined}

        self.assertEqual(closure(["QRY-2"], queries), ["QRY-1", "QRY-2"])

    def test_a_cycle_is_caught_before_anything_is_written(self):
        queries = {
            "QRY-1": v2_query("QRY-1", "QRY-2", data_source="Query Store"),
            "QRY-2": v2_query("QRY-2", "QRY-1", data_source="Query Store"),
        }
        with self.assertRaises(CircularQueryReference):
            closure(["QRY-1"], queries)

    def test_a_cycle_stops_the_plan_and_is_reported(self):
        queries = {
            "QRY-1": v2_query("QRY-1", "QRY-2", data_source="Query Store"),
            "QRY-2": v2_query("QRY-2", "QRY-1", data_source="Query Store"),
        }
        items = [{"name": 1, "item_type": "Bar", "options": json.dumps({"query": "QRY-1"})}]
        plan = plan_dashboard({"name": "DSH-1", "title": "Cyclic"}, items, queries)

        self.assertEqual(plan.queries, [])
        self.assertIn("circular_query_reference", [gap.kind for gap in plan.gaps])

    def test_a_root_lives_in_options_as_often_as_in_the_column(self):
        """The `query` column survives on an old site and is empty on a new one."""
        queries = {"QRY-1": v2_query("QRY-1", "tabIssue")}
        items = [
            {"name": 1, "item_type": "Bar", "query": "QRY-1", "options": "{}"},
            {"name": 2, "item_type": "Bar", "options": json.dumps({"query": "QRY-1"})},
            {"name": 3, "item_type": "Text", "options": json.dumps({"markdown": "hi"})},
            {"name": 4, "item_type": "Filter", "options": "{}"},
        ]
        roots, orphans = dashboard_roots(items, queries)

        self.assertEqual(roots, ["QRY-1"])
        self.assertEqual(orphans, [])

    def test_an_item_naming_a_query_that_is_gone_is_reported_as_dropped(self):
        items = [{"name": 1, "item_type": "Bar", "options": json.dumps({"query": "QRY-9"})}]
        plan = plan_dashboard({"name": "DSH-1", "title": "Orphan"}, items, {})

        dropped = [gap for gap in plan.gaps if gap.dropped]
        self.assertEqual([gap.kind for gap in dropped], ["item_without_query"])
        self.assertFalse(plan.converts_cleanly)

    def test_result_columns_come_off_the_stored_spec(self):
        query = v2_query("QRY-1", "tabIssue", [group_by("status", "Status"), count_column()])
        self.assertEqual(
            result_columns(query),
            [
                {"name": "Status", "type": "String"},
                {"name": "Count of records", "type": "Integer"},
            ],
        )

    def test_a_public_v2_dashboard_does_not_become_a_public_v3_one(self):
        plan = plan_dashboard({"name": "DSH-1", "title": "Public", "is_public": 1}, [], {})
        self.assertIn("public_not_carried", [gap.kind for gap in plan.gaps])

    def test_query_store_is_not_reported_as_a_missing_data_source(self):
        queries = {
            "QRY-1": v2_query("QRY-1", "tabIssue", [group_by("status", "Status")]),
            "QRY-2": v2_query("QRY-2", "QRY-1", [group_by("Status", "Status")], data_source="Query Store"),
        }
        items = [{"name": 1, "item_type": "Bar", "options": json.dumps({"query": "QRY-2"})}]
        plan = plan_dashboard(
            {"name": "DSH-1", "title": "Stored"},
            items,
            queries,
            resolve_data_source=lambda name: {V2_SOURCE_TITLE: V2_SOURCE_V3_NAME}.get(name),
        )

        self.assertEqual(plan.unresolved_data_sources, [])
        self.assertEqual(plan.data_source_map, {V2_SOURCE_TITLE: V2_SOURCE_V3_NAME})

    def test_a_data_source_with_no_v3_counterpart_is_reported(self):
        queries = {"QRY-1": v2_query("QRY-1", "tabIssue", [group_by("status", "Status")])}
        items = [{"name": 1, "item_type": "Bar", "options": json.dumps({"query": "QRY-1"})}]
        plan = plan_dashboard(
            {"name": "DSH-1", "title": "Sourceless"}, items, queries, resolve_data_source=lambda name: None
        )

        self.assertEqual(plan.unresolved_data_sources, [V2_SOURCE_TITLE])
        self.assertIn("unresolved_data_source", [gap.kind for gap in plan.blocking_gaps])

    def test_the_report_names_every_gap_and_where_it_came_from(self):
        queries = {"QRY-1": v2_query("QRY-1", "tabIssue", [group_by("status", "Status")], is_native_query=1)}
        items = [{"name": 1, "item_type": "Bar", "options": json.dumps({"query": "QRY-1"})}]
        report = format_report(plan_dashboard({"name": "DSH-1", "title": "One"}, items, queries))

        self.assertIn("DSH-1 - One", report)
        self.assertIn("sql 1", report)
        self.assertIn("[query QRY-1] sql_floor", report)

    def test_an_empty_plan_reports_no_gaps(self):
        plan = DashboardPlan(source="DSH-1", title="Empty")
        self.assertIn("no gaps", format_report(plan))


class TestV2WorkbookAssembly(InsightsIntegrationTestCase):
    """The write path, against real rows."""

    DASHBOARD = "DSH-MIGTEST"
    BASE = "QRY-MIGTEST-1"
    STORED = "QRY-MIGTEST-2"

    @classmethod
    def before_class(cls):
        cls.create_v3_data_source()
        cls.create_v2_dashboard()

    @classmethod
    def after_class(cls):
        cls.delete_v3_output()
        cls.delete_v2_fixture()
        frappe.db.delete(DT.DATA_SOURCE, {"name": V2_SOURCE_V3_NAME})

    # -- fixtures ----------------------------------------------------------

    @classmethod
    def create_v3_data_source(cls):
        """Written with `db_insert` on purpose.

        `on_update` tests the connection and imports the table list, and this
        source points at nothing. The migrator only ever looks the name up.
        """
        if frappe.db.exists(DT.DATA_SOURCE, V2_SOURCE_V3_NAME):
            return
        source = frappe.get_doc(
            {
                "doctype": DT.DATA_SOURCE,
                "name": V2_SOURCE_V3_NAME,
                "title": V2_SOURCE_TITLE,
                "status": "Inactive",
                "database_type": "DuckDB",
                "database_name": "v2_migration_test",
            }
        )
        source.db_insert()

    @classmethod
    def create_v2_dashboard(cls):
        """One v2 dashboard: two queries, one of them a Query Store reference."""
        cls.delete_v2_fixture()

        base = v2_query(cls.BASE, "tabIssue", [group_by("status", "Status"), count_column()])
        stored = v2_query(
            cls.STORED,
            cls.BASE,
            [group_by("Status", "Status"), count_column("Count of records")],
            data_source="Query Store",
        )
        for row in (base, stored):
            insert_row("Insights Query", {k: v for k, v in row.items() if k != "transforms"})

        insert_row("Insights Dashboard", {"name": cls.DASHBOARD, "title": "Migration Test", "is_public": 1})

        items = [
            {
                "name": 900001,
                "item_type": "Bar",
                "item_id": "900001",
                "layout": json.dumps({"i": 900001, "x": 0, "y": 0, "w": 10, "h": 8}),
                "options": json.dumps(
                    {
                        "query": cls.STORED,
                        "title": "Issues by Status",
                        "xAxis": "Status",
                        "yAxis": ["Count of records"],
                    }
                ),
            },
            {
                "name": 900002,
                "item_type": "Filter",
                "item_id": "900002",
                "layout": json.dumps({"i": 900002, "x": 10, "y": 0, "w": 4, "h": 2}),
                "options": json.dumps(
                    {
                        "label": "Status",
                        "column": {"column": "status", "label": "Status", "type": "String"},
                        "links": {"900001": {"column": "status", "label": "Status"}},
                    }
                ),
            },
            {
                "name": 900003,
                "item_type": "Text",
                "item_id": "900003",
                "layout": json.dumps({"i": 900003, "x": 0, "y": 8, "w": 20, "h": 2}),
                "options": json.dumps({"markdown": "<b>notes</b>"}),
            },
        ]
        for idx, item in enumerate(items, start=1):
            insert_row(
                "Insights Dashboard Item",
                {
                    "parent": cls.DASHBOARD,
                    "parenttype": "Insights Dashboard",
                    "parentfield": "items",
                    "idx": idx,
                    **item,
                },
            )

    @classmethod
    def delete_v2_fixture(cls):
        frappe.db.sql("delete from `tabInsights Dashboard Item` where parent = %s", (cls.DASHBOARD,))
        frappe.db.sql("delete from `tabInsights Dashboard` where name = %s", (cls.DASHBOARD,))
        frappe.db.sql(
            "delete from `tabInsights Query` where name in %(names)s", {"names": (cls.BASE, cls.STORED)}
        )

    @classmethod
    def delete_v3_output(cls):
        for workbook in frappe.get_all(DT.WORKBOOK, filters={"title": "Migration Test"}, pluck="name"):
            frappe.delete_doc(DT.WORKBOOK, workbook, force=True, ignore_permissions=True)

    # -- the migration -----------------------------------------------------

    def setUp(self):
        super().setUp()
        self.delete_v3_output()
        self.result = migrate_dashboard(self.DASHBOARD)

    def test_the_closure_is_migrated_not_just_the_charted_query(self):
        self.assertEqual([plan.source for plan in self.result.plan.queries], [self.BASE, self.STORED])
        self.assertEqual(len(self.result.query_names), 2)

    def test_every_v3_document_carries_its_v2_name(self):
        self.assertEqual(frappe.db.get_value(DT.DASHBOARD, self.result.dashboard, "old_name"), self.DASHBOARD)
        self.assertEqual(
            {frappe.db.get_value(DT.QUERY, name, "old_name") for name in self.result.query_names.values()},
            {self.BASE, self.STORED},
        )
        chart = next(iter(self.result.chart_names.values()))
        self.assertEqual(str(frappe.db.get_value(DT.CHART, chart, "old_name")), "900001")

    def test_the_reference_points_at_the_v3_copy(self):
        stored = frappe.get_doc(DT.QUERY, self.result.query_names[self.STORED])
        source = frappe.parse_json(stored.operations)[0]

        self.assertEqual(source["table"]["type"], "query")
        self.assertEqual(source["table"]["query_name"], self.result.query_names[self.BASE])
        self.assertEqual(source["table"]["workbook"], self.result.workbook)

    def test_a_table_reference_names_the_v3_data_source(self):
        base = frappe.get_doc(DT.QUERY, self.result.query_names[self.BASE])
        source = frappe.parse_json(base.operations)[0]

        self.assertEqual(source["table"]["data_source"], V2_SOURCE_V3_NAME)
        self.assertEqual(self.result.plan.unresolved_data_sources, [])

    def test_every_query_reads_the_live_source_as_v2_did(self):
        for name in self.result.query_names.values():
            self.assertTrue(frappe.db.get_value(DT.QUERY, name, "use_live_connection"))
            self.assertTrue(frappe.db.get_value(DT.QUERY, name, "is_builder_query"))

    def test_the_doctype_makes_the_charts_data_query_not_the_migrator(self):
        chart = frappe.get_doc(DT.CHART, next(iter(self.result.chart_names.values())))

        self.assertTrue(chart.data_query)
        self.assertNotIn(chart.data_query, self.result.query_names.values())
        self.assertEqual(chart.query, self.result.query_names[self.STORED])
        self.assertEqual(chart.chart_type, "Bar")

    def test_every_item_lands_on_the_v3_dashboard(self):
        items = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, self.result.dashboard, "items"))

        self.assertEqual([item["type"] for item in items], ["chart", "filter", "text"])
        self.assertEqual(self.result.plan.dropped_items, 0)
        self.assertEqual(items[0]["chart"], next(iter(self.result.chart_names.values())))

    def test_a_filter_links_to_the_v3_chart_and_the_v3_query(self):
        items = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, self.result.dashboard, "items"))
        links = items[1]["links"]

        chart = next(iter(self.result.chart_names.values()))
        self.assertEqual(links, {chart: f"`{self.result.query_names[self.STORED]}`.`Status`"})

    def test_a_public_v2_dashboard_lands_private(self):
        self.assertFalse(frappe.db.get_value(DT.DASHBOARD, self.result.dashboard, "is_public"))
        self.assertFalse(frappe.db.get_value(DT.DASHBOARD, self.result.dashboard, "permission_user"))
        self.assertIn("public_not_carried", [gap.kind for gap in self.result.plan.gaps])

    def test_running_it_twice_makes_one_workbook(self):
        again = migrate_dashboard(self.DASHBOARD)

        self.assertTrue(again.skipped)
        self.assertEqual(again.dashboard, self.result.dashboard)
        self.assertEqual(again.workbook, self.result.workbook)
        self.assertEqual(frappe.db.count(DT.DASHBOARD, {"old_name": self.DASHBOARD}), 1)

    def test_the_v2_dashboard_is_untouched(self):
        self.assertTrue(frappe.db.get_value("Insights Dashboard", self.DASHBOARD, "is_public"))
        self.assertEqual(frappe.db.count("Insights Dashboard Item", {"parent": self.DASHBOARD}), 3)
        self.assertEqual(frappe.db.count("Insights Query", {"name": ["in", [self.BASE, self.STORED]]}), 2)

    def test_a_failed_migration_leaves_no_workbook(self):
        self.delete_v3_output()

        original = frappe.new_doc

        def explode(doctype, *args, **kwargs):
            if doctype == DT.DASHBOARD:
                raise ValueError("boom")
            return original(doctype, *args, **kwargs)

        frappe.new_doc = explode
        try:
            with self.assertRaises(ValueError):
                migrate_dashboard(self.DASHBOARD)
        finally:
            frappe.new_doc = original

        self.assertEqual(frappe.db.count(DT.WORKBOOK, {"title": "Migration Test"}), 0)
        self.assertEqual(frappe.db.count(DT.QUERY, {"old_name": self.BASE}), 0)

    def test_v2_is_read_without_asking_the_meta(self):
        """Passes whether or not this site still carries the v2 doctype rows."""
        dashboard, items = load_v2_dashboard(self.DASHBOARD)
        queries = load_v2_queries(candidate_roots(items))

        self.assertEqual(dashboard["title"], "Migration Test")
        self.assertEqual(len(items), 3)
        # only QRY-2 is on the dashboard; QRY-1 is reached by reference
        self.assertEqual(candidate_roots(items), [self.STORED])
        self.assertEqual(set(queries), {self.BASE, self.STORED})

    def test_the_v3_data_source_is_found_by_its_scrubbed_name(self):
        self.assertEqual(resolve_v3_data_source(V2_SOURCE_TITLE), V2_SOURCE_V3_NAME)
        self.assertIsNone(resolve_v3_data_source("no such source"))
