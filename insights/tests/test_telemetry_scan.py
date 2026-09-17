"""The daily scan reports what the site holds, without naming anything custom.

Three events carry the whole answer. Each has to stay inside Pulse's size cap,
even on a site with far more tables than a list may carry. The row estimates
behind the fit numbers come from a catalog read the scan owns. A source that
will not answer costs its own tables, never the send.
"""

from unittest.mock import MagicMock, patch

import frappe

from insights import telemetry_scan
from insights.telemetry import default_properties, is_standard_app
from insights.telemetry_scan import (
    LIST_LIMIT,
    PROPERTY_CAP,
    read_catalog,
    run_site_scan,
    serialized_size,
    site_profile,
    site_queries,
    site_tables,
    tables_queries_read,
    within_cap,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
    create_user,
    delete_users,
)

USER = "site_scan_user@test.com"
WORKBOOK_TITLE = "Site Scan Workbook"
CUSTOM_DOCTYPE = "Site Scan Custom Table"

OPERATIONS = [
    {"type": "source", "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"}},
    {
        "type": "filter",
        "column": {"type": "column", "column_name": "status"},
        "operator": "=",
        "value": "Open",
    },
    {"type": "filter", "expression": {"type": "expression", "expression": "in_(q.status, 'Open')"}},
    {
        "type": "join",
        "join_type": "left",
        "table": {"type": "table", "data_source": "Site DB", "table_name": "tabUser"},
        "select_columns": [],
        "join_condition": {
            "left_column": {"type": "column", "column_name": "owner"},
            "right_column": {"type": "column", "column_name": "name"},
        },
    },
    {
        "type": "mutate",
        "new_name": "age",
        "data_type": "Integer",
        "expression": {"type": "expression", "expression": "date_diff('day', q.creation, now())"},
    },
    {
        "type": "summarize",
        "measures": [
            {"measure_name": "count", "column_name": "name", "data_type": "Integer", "aggregation": "count"}
        ],
        "dimensions": [{"dimension_name": "status", "column_name": "status", "data_type": "String"}],
    },
    {"type": "limit", "limit": 100},
]


class TestSiteScan(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_user(USER, first_name="Site", last_name="Scan", roles="Insights User")
        cls.workbook = create_test_workbook(USER, title=WORKBOOK_TITLE).name
        cls.query = create_test_query(USER, cls.workbook, title="Site Scan Query", operations=OPERATIONS).name
        cls.chart = create_test_chart(USER, cls.workbook, query=cls.query, title="Site Scan Chart").name
        create_test_dashboard(USER, cls.workbook, chart=cls.chart, title="Site Scan Dashboard")

        if not frappe.db.exists("DocType", CUSTOM_DOCTYPE):
            frappe.get_doc(
                {
                    "doctype": "DocType",
                    "name": CUSTOM_DOCTYPE,
                    "module": "Insights",
                    "custom": 1,
                    "fields": [{"fieldname": "title", "fieldtype": "Data", "label": "Title"}],
                    "permissions": [{"role": "System Manager", "read": 1}],
                }
            ).insert()

        cls.tables = frappe.get_all(
            "DocType", filters={"custom": 0, "issingle": 0}, pluck="name", order_by="name asc", limit=60
        )
        for table in [*cls.tables, CUSTOM_DOCTYPE]:
            create_test_query(
                USER,
                cls.workbook,
                title=f"Site Scan Reads {table}",
                operations=[
                    {
                        "type": "source",
                        "table": {"type": "table", "data_source": "Site DB", "table_name": f"tab{table}"},
                    }
                ],
            )

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        frappe.delete_doc("DocType", CUSTOM_DOCTYPE, force=True, ignore_permissions=True)
        delete_users(USER)

    def scanned(self):
        """The events the scan sent, by name."""
        with (
            patch.object(telemetry_scan, "is_pulse_enabled", return_value=True),
            patch.object(telemetry_scan, "capture") as sender,
        ):
            run_site_scan()
        return {call.args[0]: call.kwargs for call in sender.call_args_list}

    # @feature telemetry.site-scan
    def test_the_daily_scan_sends_a_profile_a_query_shape_and_a_table_fit(self):
        sent = self.scanned()
        self.assertEqual(set(sent), {"site_profile", "site_queries", "site_tables"})
        for event, kwargs in sent.items():
            # the daily job is the gate. An interval would drop a tick that runs early
            self.assertNotIn("interval", kwargs, event)
            self.assertTrue(kwargs, f"{event} carries no properties")

    # @feature telemetry.site-scan
    def test_a_site_with_telemetry_off_is_asked_nothing(self):
        with (
            patch.object(telemetry_scan, "is_pulse_enabled", return_value=False),
            patch.object(telemetry_scan, "read_catalog") as catalog,
            patch.object(telemetry_scan, "capture") as sender,
        ):
            run_site_scan()
        catalog.assert_not_called()
        sender.assert_not_called()

    # @feature telemetry.site-scan
    def test_a_site_with_more_tables_than_a_list_holds_still_fits_the_size_cap(self):
        for build in (site_profile, site_queries, site_tables):
            props = within_cap(build())
            # the cap is on what Pulse receives, which is these plus the defaults
            sent = {**default_properties(), **props}
            self.assertLess(serialized_size(sent), PROPERTY_CAP, build.__name__)
            for key, value in props.items():
                if isinstance(value, list):
                    self.assertLessEqual(len(value), LIST_LIMIT, f"{build.__name__}.{key}")
        self.assertEqual(len(within_cap(site_tables())["queried_tables"]), LIST_LIMIT)

    # @feature telemetry.standard-names-only
    def test_an_app_is_named_only_when_frappe_publishes_it(self):
        self.assertTrue(is_standard_app("insights"))
        self.assertTrue(is_standard_app("frappe"))
        self.assertFalse(is_standard_app("an_app_nobody_installed"))

        props = site_profile()
        self.assertIn("insights", props["apps"])
        self.assertEqual(props["custom_apps"], len(frappe.get_installed_apps()) - len(props["apps"]))

    # @feature telemetry.standard-names-only
    def test_a_custom_doctype_is_counted_and_never_named(self):
        props = site_tables()
        self.assertGreaterEqual(props["custom_tables_queried"], 1)
        self.assertNotIn(CUSTOM_DOCTYPE, props["queried_tables"])
        self.assertNotIn(CUSTOM_DOCTYPE, frappe.as_json(props))

    # @feature telemetry.site-scan
    def test_a_query_shape_counts_the_operations_and_the_functions_its_expressions_call(self):
        props = site_queries()
        self.assertGreaterEqual(props["operations_filter"], 2)
        self.assertGreaterEqual(props["queries_with_summarize"], 1)
        self.assertGreaterEqual(props["join_left"], 1)
        self.assertGreaterEqual(props["agg_count"], 1)
        self.assertGreaterEqual(props["filter_eq"], 1)
        self.assertGreaterEqual(props["filter_expression"], 1)
        self.assertIn("now", props["expression_functions"])
        self.assertNotIn("q.status", frappe.as_json(props))

    # @feature telemetry.standard-names-only
    def test_a_value_the_engine_does_not_know_is_counted_as_other_and_never_named(self):
        before = site_queries()
        query = create_test_query(
            USER,
            self.workbook,
            title="Site Scan Unknown Values",
            operations=[
                OPERATIONS[0],
                {
                    "type": "filter",
                    "column": {"type": "column", "column_name": "status"},
                    "operator": "teleports_to",
                    "value": "Open",
                },
                {
                    "type": "join",
                    "join_type": "sideways",
                    "table": {"type": "table", "data_source": "Site DB", "table_name": "tabUser"},
                    "select_columns": [],
                    "join_condition": {
                        "left_column": {"type": "column", "column_name": "owner"},
                        "right_column": {"type": "column", "column_name": "name"},
                    },
                },
                {
                    "type": "summarize",
                    "measures": [
                        {"measure_name": "total", "column_name": "name", "aggregation": "median_of"}
                    ],
                    "dimensions": [],
                },
                {
                    "type": "mutate",
                    "new_name": "secret",
                    "expression": {"type": "expression", "expression": "our_own_function(q.status)"},
                },
            ],
        )
        self.addCleanup(frappe.delete_doc, DT.QUERY, query.name, force=True)

        props = site_queries()
        self.assertEqual(props["filter_other"], before.get("filter_other", 0) + 1)
        self.assertEqual(props["join_other"], before.get("join_other", 0) + 1)
        self.assertEqual(props["agg_other"], before.get("agg_other", 0) + 1)
        self.assertNotIn("our_own_function", props["expression_functions"])
        for word in ("teleports_to", "sideways", "median_of", "our_own_function"):
            self.assertNotIn(word, frappe.as_json(props))

    # @feature telemetry.row-estimate
    def test_a_source_that_will_not_answer_costs_its_estimates_and_not_the_send(self):
        with patch.object(telemetry_scan, "read_catalog", side_effect=Exception("source is down")):
            sent = self.scanned()
        self.assertEqual(set(sent), {"site_profile", "site_queries", "site_tables"})
        self.assertGreaterEqual(sent["site_tables"]["charts_total"], 1)
        self.assertGreaterEqual(sent["site_tables"]["charts_unknown"], 1)
        self.assertLess(sent["site_tables"]["charts_fit"], sent["site_tables"]["charts_total"])
        self.assertEqual(sent["site_tables"]["tables_over_limit"], [])

    # @feature telemetry.standard-names-only
    def test_a_chart_type_the_backend_does_not_know_is_counted_as_other(self):
        chart = create_test_chart(USER, self.workbook, query=self.query, title="Site Scan Odd Chart")
        self.addCleanup(frappe.delete_doc, DT.CHART, chart.name, force=True)
        # chart_type is a Data field, so a client may write any word into it
        frappe.db.set_value(DT.CHART, chart.name, "chart_type", "Secret Widget")

        props = site_profile()
        self.assertEqual(props["charts_other"], 1)
        self.assertNotIn("secret", frappe.as_json(props).lower())

    # @feature telemetry.site-scan
    def test_a_query_that_reads_another_query_counts_the_tables_under_it(self):
        before = tables_queries_read()
        base = create_test_query(USER, self.workbook, title="Site Scan Base Query")
        self.addCleanup(frappe.delete_doc, DT.QUERY, base.name, force=True)
        wrapper = create_test_query(
            USER,
            self.workbook,
            title="Site Scan Wrapper Query",
            operations=[{"type": "source", "table": {"type": "query", "query_name": base.name}}],
        )
        self.addCleanup(frappe.delete_doc, DT.QUERY, wrapper.name, force=True)

        after = tables_queries_read()
        key = ("Site DB", "tabToDo")
        self.assertEqual(after[key], before[key] + 2)

    # @feature telemetry.site-scan
    def test_the_scan_reads_every_query_s_operations_in_one_go(self):
        with patch.object(frappe.db, "get_value", wraps=frappe.db.get_value) as reader:
            site_tables()

        per_query_reads = [
            call
            for call in reader.call_args_list
            if call.args[:1] == (DT.QUERY,) and "operations" in call.args
        ]
        self.assertEqual(per_query_reads, [])

    # @feature telemetry.site-scan
    def test_a_chart_with_no_query_is_counted_apart_from_the_ones_the_fit_judged(self):
        before = site_tables()
        chart = create_test_chart(USER, self.workbook, title="Site Scan Chart Without A Query")
        self.addCleanup(frappe.delete_doc, DT.CHART, chart.name, force=True)

        after = site_tables()
        self.assertEqual(after["charts_total"], before["charts_total"])
        self.assertEqual(after["charts_without_tables"], before["charts_without_tables"] + 1)

    # @feature telemetry.row-estimate
    def test_the_catalog_answers_with_a_row_estimate_for_a_table_a_query_reads(self):
        estimates = read_catalog("Site DB", {"tabUser"})
        self.assertIsInstance(estimates["tabUser"], int)

    # @feature telemetry.row-estimate
    def test_two_postgres_schemas_holding_a_table_of_one_name_each_get_an_estimate(self):
        source = frappe.get_doc(
            {"doctype": DT.DATA_SOURCE, "database_type": "PostgreSQL", "schema": "public,sales"}
        )
        backend = MagicMock()
        backend.name = "postgres"
        backend.raw_sql.return_value.fetchall.return_value = [
            ("public", "orders", 12),
            ("sales", "orders", 3400),
        ]
        source._get_ibis_backend = lambda: backend

        with patch("insights.utils.InsightsDataSourcev3.get_doc", return_value=source):
            estimates = read_catalog("pg", {"public.orders", "sales.orders"})

        self.assertEqual(estimates, {"public.orders": 12, "sales.orders": 3400})
