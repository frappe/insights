"""A query reached through a reference is read like any other query.

An operation may source, join or union another query, and a dashboard filter or a
chart may name one. Either way the reference resolves to the whole query - its
operations, its native SQL, and the tables it reads - and the compiled result
brings all of it back.

The reference is checked once, where it is written. Execution then trusts what was
saved, so a chain stays runnable by everyone who may read the query at its head.
A reference that arrives with the request was never written, and is checked then.
"""

import frappe
from frappe.utils import set_request

from insights.api import run_doc_method
from insights.api.workbooks import update_share_permissions
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    db_connections,
)
from insights.insights.query_utils import sync_query_references
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    as_user,
    create_test_chart,
    create_test_dashboard,
    create_test_workbook,
    delete_users,
)
from insights.tests.permissions_utils import (
    TEST_DS,
    USER_1,
    USER_2,
    USER_3,
    cleanup_test_fixtures,
    create_test_data_sources,
    create_test_tables,
    create_test_users,
    share_chart,
)

OWNER = USER_1
OTHER = USER_2
VIEWER = USER_3

SECRET = "referenced query secret"
SOURCE_ROWS = f"results = [{{'secret': '{SECRET}', 'amount': 1}}]"


def create_source_query(owner, workbook, title):
    """A script query, so no table permission applies.

    It is a script, so an admin inserts it (Q17). `owner` is only the recorded owner.
    """
    with as_user("Administrator"):
        query = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": title,
                "workbook": workbook,
                "use_live_connection": 0,
                "is_script_query": 1,
                "operations": [{"type": "code", "code": SOURCE_ROWS}],
            }
        ).insert()
    query.db_set("owner", owner, update_modified=False)
    return query


def reference_operations(query_name):
    return [{"type": "source", "table": {"type": "query", "query_name": query_name}}]


def create_referencing_query(owner, workbook, referenced, title):
    with as_user(owner):
        return frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": title,
                "workbook": workbook,
                "use_live_connection": 0,
                "is_builder_query": 1,
                "operations": reference_operations(referenced),
            }
        ).insert()


class AReferenceInTheRequestIsChecked:
    """The rules for a reference that was never saved.

    Operations arrive with the request, so a caller can name any query in them.
    Nothing authorised that, and it is checked as it resolves.
    """

    ENABLE_PERMISSIONS = 0

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.owner_workbook = create_test_workbook(OWNER, title="Reference Owner Workbook").name
        cls.owner_query = create_source_query(OWNER, cls.owner_workbook, "Reference Owner Source").name
        cls.owner_reference = create_referencing_query(
            OWNER, cls.owner_workbook, cls.owner_query, "Reference Owner Consumer"
        ).name

        cls.other_workbook = create_test_workbook(OTHER, title="Reference Other Workbook").name
        cls.other_query = create_source_query(OTHER, cls.other_workbook, "Reference Other Source").name

    @classmethod
    def after_class(cls):
        for name in (cls.owner_workbook, cls.other_workbook):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    def before_test(self):
        self.set_team_permissions(self.ENABLE_PERMISSIONS)

    # @feature permissions.query-reference-checked
    def test_the_owner_query_is_not_readable_by_the_other_user(self):
        """The baseline the refusals below are measured against."""
        with self.as_user(OTHER):
            self.assertFalse(frappe.has_permission(DT.QUERY, ptype="read", doc=self.owner_query))

    # @feature query.source-query
    def test_a_saved_chain_resolves_for_its_owner(self):
        with self.as_user(OWNER), db_connections():
            result = frappe.get_doc(DT.QUERY, self.owner_reference).execute()
        self.assertEqual(result["rows"][0]["secret"], SECRET)

    # @feature permissions.query-reference-checked
    def test_a_reference_sent_inline_is_refused(self):
        """The operations arrive in the request, so the reference need not be saved."""
        with self.as_user(OTHER):
            doc = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "name": "new-query-inline",
                    "workbook": self.other_workbook,
                    "use_live_connection": 0,
                    "is_builder_query": 1,
                    "__islocal": True,
                    "operations": reference_operations(self.owner_query),
                }
            )
            with self.assertRaises(frappe.PermissionError), db_connections():
                doc.execute()

    # @feature permissions.query-reference-checked
    def test_forged_operations_on_a_saved_query_are_refused(self):
        """What was saved is the row, not what the request says was saved."""
        with self.as_user(OTHER):
            doc = frappe.get_doc(DT.QUERY, self.other_query)
            doc.operations = reference_operations(self.owner_query)
            with self.assertRaises(frappe.PermissionError), db_connections():
                doc.execute()

    # @feature permissions.query-reference-checked
    def test_a_refused_reference_returns_no_sql(self):
        """The compiled SQL is the query's logic, so a refusal returns none of it."""
        with self.as_user(OTHER):
            doc = frappe.get_doc(DT.QUERY, self.other_query)
            doc.operations = reference_operations(self.owner_query)
            try:
                with db_connections():
                    result = doc.execute()
            except frappe.PermissionError:
                return
            self.fail(f"the reference resolved and returned {result.get('sql')}")


class ASavedReferenceKeepsItsOwnAccess:
    """The rules for a reference that was saved.

    A chart can be shared with someone who holds no access to the workbook behind
    it. They read the chart and the query it is built on. When that query is built
    on another query, the chain is the query, not a detour around it - so they have
    to be able to run it. The reference was checked when it was written, and that
    is what the run trusts.
    """

    ENABLE_PERMISSIONS = 0

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.workbook = create_test_workbook(OWNER, title="Chain Owner Workbook").name
        cls.base = create_source_query(OWNER, cls.workbook, "Chain Base").name
        cls.consumer = create_referencing_query(OWNER, cls.workbook, cls.base, "Chain Consumer").name
        cls.chart = create_test_chart(OWNER, cls.workbook, query=cls.consumer, title="Chain Chart").name
        share_chart(cls.chart, VIEWER)

        cls.viewer_workbook = create_test_workbook(VIEWER, title="Chain Viewer Workbook").name

    @classmethod
    def after_class(cls):
        for name in (cls.workbook, cls.viewer_workbook):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(OWNER, VIEWER, OTHER)

    def before_test(self):
        self.set_team_permissions(self.ENABLE_PERMISSIONS)

    # @feature permissions.chart-access-follows
    def test_the_share_grants_read_on_the_chart_and_the_pipeline_it_reads(self):
        """A shared chart gives read on every query its pipeline reads, and no more.

        The engine trusts a saved reference, so the chart's number uses all of
        them. Refusing one showed the number but refused a column's values. A
        sibling query the chart does not read stays unreadable."""
        with self.as_user(VIEWER):
            self.assertTrue(frappe.has_permission(DT.CHART, ptype="read", doc=self.chart))
            self.assertTrue(frappe.has_permission(DT.QUERY, ptype="read", doc=self.consumer))
            self.assertTrue(frappe.has_permission(DT.QUERY, ptype="read", doc=self.base))

        with self.as_user(OWNER):
            sibling = create_source_query(OWNER, self.workbook, "Chain Sibling").name

        with self.as_user(VIEWER):
            self.assertFalse(frappe.has_permission(DT.QUERY, ptype="read", doc=sibling))

    # @feature permissions.chart-access-follows
    def test_a_charts_grant_stops_at_its_own_workbook(self):
        """Write on a workbook is write on its charts, and a chart there may read
        a query from a workbook this user cannot open. The chart gives no write
        or delete on that query, and no access outside the chart's workbook."""
        far = create_test_workbook(OWNER, title="Chain Far Workbook").name
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, far, force=True, ignore_permissions=True)
        far_query = create_source_query(OWNER, far, "Chain Far Source").name

        near = create_test_workbook(OWNER, title="Chain Near Workbook").name
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, near, force=True, ignore_permissions=True)
        near_query = create_source_query(OWNER, near, "Chain Near Consumer").name
        source_from(near_query, far_query)
        create_test_chart(OWNER, near, query=near_query, title="Chain Near Chart")
        with self.as_user(OWNER):
            update_share_permissions(near, [{"user": OTHER, "read": 1, "write": 1}])

        with self.as_user(OTHER):
            self.assertTrue(frappe.has_permission(DT.QUERY, ptype="write", doc=near_query))
            for ptype in ("read", "write", "delete"):
                self.assertFalse(frappe.has_permission(DT.QUERY, ptype=ptype, doc=far_query), ptype)

    # @feature permissions.chart-access-follows permissions.visibility
    def test_a_visibility_level_alone_grants_no_read_on_the_query_behind_the_chart(self):
        """A reader who sees a chart through its visibility level gets the chart's
        result, not the queries behind it."""
        chart = create_test_chart(OWNER, self.workbook, query=self.consumer, title="Chain Open Chart")
        with self.as_user(OWNER):
            chart.visibility = "Everyone"
            chart.save()

        with self.as_user(OTHER):
            self.assertTrue(frappe.has_permission(DT.CHART, ptype="read", doc=chart.name))
            self.assertFalse(frappe.has_permission(DT.QUERY, ptype="read", doc=self.consumer))
            self.assertFalse(frappe.has_permission(DT.QUERY, ptype="read", doc=self.base))

    # @feature permissions.chart-access-follows
    def test_someone_with_the_chart_can_run_the_chain(self):
        """Running the query they may read is what the share is for."""
        with self.as_user(VIEWER), db_connections():
            result = frappe.get_doc(DT.QUERY, self.consumer).execute()
        self.assertEqual(result["rows"][0]["secret"], SECRET)

    # @feature query.source-query
    def test_the_chain_runs_before_the_reference_index_is_built(self):
        """`Insights Query Reference` is rebuilt by a background job after the save
        commits, so it lags. What was saved is what decides, and it cannot wait."""
        frappe.db.delete("Insights Query Reference", {"query": self.consumer})
        self.addCleanup(
            sync_query_references,
            self.consumer,
            frappe.db.get_value(DT.QUERY, self.consumer, "operations"),
        )

        with self.as_user(VIEWER), db_connections():
            result = frappe.get_doc(DT.QUERY, self.consumer).execute()
        self.assertEqual(result["rows"][0]["secret"], SECRET)

    # @feature query.copy-paste
    def test_an_export_includes_its_references_before_the_index_is_built(self):
        """An export packs the queries it is built on. Which those are comes from
        the query, not from the index that a background job rebuilds."""
        frappe.db.delete("Insights Query Reference", {"query": self.consumer})
        self.addCleanup(
            sync_query_references,
            self.consumer,
            frappe.db.get_value(DT.QUERY, self.consumer, "operations"),
        )

        with self.as_user(OWNER):
            exported = frappe.get_doc(DT.QUERY, self.consumer).export()
        self.assertIn(self.base, exported["dependencies"]["queries"])

    # @feature query.copy-paste
    def test_an_export_skips_a_reference_whose_query_is_gone(self):
        """`on_trash` drops the edge rows but not the operations that name the
        query, so the export list includes a name with no row behind it."""
        with self.as_user(OWNER):
            gone = create_source_query(OWNER, self.workbook, "Chain Doomed Base").name
            orphan = create_referencing_query(OWNER, self.workbook, gone, "Chain Orphan").name
            frappe.delete_doc(DT.QUERY, gone, force=True)

            exported = frappe.get_doc(DT.QUERY, orphan).export()

        self.assertEqual(exported["dependencies"]["queries"], {})

    # @feature permissions.query-reference-checked
    def test_a_reference_cannot_be_saved_to_an_unreadable_query(self):
        """Where the check lives. The source is a query this user may not read."""
        with self.as_user(OWNER):
            unreadable = create_source_query(OWNER, self.workbook, "Chain Unshared Base").name

        with self.as_user(VIEWER), self.assertRaises(frappe.PermissionError):
            create_referencing_query(VIEWER, self.viewer_workbook, unreadable, "Chain Forged Consumer")

    # @feature permissions.query-reference-checked
    def test_a_reference_added_on_update_is_checked_too(self):
        """An existing query is not a way around the check."""
        with self.as_user(OWNER):
            unreadable = create_source_query(OWNER, self.workbook, "Chain Unshared Update Base").name

        with self.as_user(VIEWER):
            query = create_source_query(VIEWER, self.viewer_workbook, "Chain Viewer Source")
            query.operations = reference_operations(unreadable)
            with self.assertRaises(frappe.PermissionError):
                query.save()


class DashboardFilterReadsTheQuery:
    """A dashboard filter names its own query, and the caller never does.

    A filter links a column as `` `<query>`.`<column>` ``. The caller sends the
    filter's name and `lookup_filter` reads the link off the stored dashboard, so
    the query a lookup runs against is the dashboard's word and not the request's.

    A link is followed only through a chart the dashboard actually holds, which is
    what keeps `links` from reaching a query on its own: putting the chart there
    was already checked.
    """

    ENABLE_PERMISSIONS = 0
    FILTER_NAME = "Secret"

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.owner_workbook = create_test_workbook(OWNER, title="Filter Owner Workbook").name
        cls.owner_query = create_source_query(OWNER, cls.owner_workbook, "Filter Owner Source").name
        cls.owner_chart = create_test_chart(
            OWNER, cls.owner_workbook, query=cls.owner_query, title="Filter Owner Chart"
        ).name

        cls.other_workbook = create_test_workbook(OTHER, title="Filter Other Workbook").name

        cls.owner_dashboard = cls.create_dashboard(OWNER, cls.owner_workbook, cls.owner_chart)
        # the same link, on a dashboard that does not hold the chart it names
        cls.detached_dashboard = cls.create_dashboard(
            OWNER, cls.owner_workbook, cls.owner_chart, hold_the_chart=False
        )

    @classmethod
    def create_dashboard(cls, owner, workbook, chart, hold_the_chart=True):
        link = {chart: f"`{cls.owner_query}`.`secret`"}
        items = [{"id": "filter-1", "type": "filter", "filter_name": cls.FILTER_NAME, "links": link}]
        if hold_the_chart:
            items.insert(0, {"id": "chart-1", "type": "chart", "chart": chart})

        with as_user(owner):
            return (
                frappe.get_doc(
                    {
                        "doctype": DT.DASHBOARD,
                        "title": f"Filter Dashboard {workbook} {len(items)}",
                        "workbook": workbook,
                        "items": items,
                    }
                )
                .insert()
                .name
            )

    @classmethod
    def after_class(cls):
        for name in (cls.owner_workbook, cls.other_workbook):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    def before_test(self):
        self.set_team_permissions(self.ENABLE_PERMISSIONS)

    def distinct_values(self, dashboard, filter_name):
        with db_connections():
            return frappe.get_doc(DT.DASHBOARD, dashboard).get_distinct_column_values(filter_name)

    # @feature dashboard.filter-values
    def test_a_filter_lists_the_values_of_the_column_it_links(self):
        with self.as_user(OWNER):
            values = self.distinct_values(self.owner_dashboard, self.FILTER_NAME)
        self.assertEqual(values, [SECRET])

    # @feature dashboard.filter-values
    def test_a_filter_the_dashboard_does_not_declare_is_refused(self):
        """A name is all the caller sends, so an unknown one reaches no query."""
        with self.as_user(OWNER), self.assertRaises(frappe.PermissionError):
            self.distinct_values(self.owner_dashboard, "Not A Filter")

    # @feature dashboard.filter-values
    def test_a_link_to_a_chart_the_dashboard_does_not_hold_is_not_followed(self):
        """`links` alone cannot reach a query: the chart has to be on the page."""
        with self.as_user(OWNER), self.assertRaises(frappe.PermissionError):
            self.distinct_values(self.detached_dashboard, self.FILTER_NAME)

    # @feature permissions.query-reference-checked permissions.not-permitted-chart
    def test_a_filter_cannot_read_a_query_its_caller_may_not(self):
        """The read on the dashboard is settled upstream of this method, so the
        caller's read on the query behind the filter is checked here too. It
        returns an empty list, not an error, because the caller may read the
        dashboard. See `insights/not_permitted.py`."""
        with self.as_user(OTHER):
            self.assertEqual(self.distinct_values(self.owner_dashboard, self.FILTER_NAME), [])

    # @feature permissions.request-body-not-trusted
    def test_items_sent_with_the_request_do_not_decide_the_column(self):
        """A method runs on the body the client sends, so the link is read off
        the row and not off the `items` that arrive with the call."""
        forged = frappe.get_doc(
            {
                "doctype": DT.DASHBOARD,
                "name": self.owner_dashboard,
                "items": [
                    {"id": "chart-1", "type": "chart", "chart": self.owner_chart},
                    {
                        "id": "filter-1",
                        "type": "filter",
                        "filter_name": self.FILTER_NAME,
                        "links": {self.owner_chart: f"`{self.owner_query}`.`amount`"},
                    },
                ],
            }
        )
        with self.as_user(OWNER), db_connections():
            self.assertEqual(forged.get_distinct_column_values(self.FILTER_NAME), [SECRET])


class ChartExportReadsTheQuery:
    """The same rule where a chart names the query it is built on.

    `Insights Chart v3.export` exports the linked query in full. The chart is
    checked, and until now the query it named was not. A chart may only be saved
    over a query its author can read, but a document method runs on the body the
    client sends, so the link the method reads need never have been saved.
    """

    ENABLE_PERMISSIONS = 0

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.owner_workbook = create_test_workbook(OWNER, title="Chart Export Owner Workbook").name
        cls.owner_query = create_source_query(OWNER, cls.owner_workbook, "Chart Export Owner Source").name
        cls.owner_chart = create_test_chart(
            OWNER, cls.owner_workbook, query=cls.owner_query, title="Chart Export Owner Chart"
        ).name

        cls.other_workbook = create_test_workbook(OTHER, title="Chart Export Other Workbook").name
        cls.other_query = create_source_query(OTHER, cls.other_workbook, "Chart Export Other Source").name
        cls.other_chart = create_test_chart(
            OTHER, cls.other_workbook, query=cls.other_query, title="Chart Export Other Chart"
        ).name

    @classmethod
    def after_class(cls):
        for name in (cls.owner_workbook, cls.other_workbook):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    def before_test(self):
        self.set_team_permissions(self.ENABLE_PERMISSIONS)
        set_request(method="POST", path="/api/method/insights.api.run_doc_method")

    def export_chart(self, name, **claims):
        """The client sends the chart it holds, so the body includes its fields."""
        chart = frappe.get_doc(DT.CHART, name)
        body = {
            "doctype": DT.CHART,
            "name": chart.name,
            "workbook": chart.workbook,
            "query": chart.query,
            "chart_type": chart.chart_type,
        }
        return run_doc_method("export", {**body, **claims})

    # @feature charts.copy-paste
    def test_a_chart_exports_the_query_its_owner_may_read(self):
        """The baseline: the export includes the linked query."""
        with self.as_user(OWNER):
            exported = self.export_chart(self.owner_chart)
        self.assertIn(self.owner_query, exported["dependencies"]["queries"])

    # @feature permissions.request-body-not-trusted
    def test_a_chart_cannot_export_a_query_its_caller_may_not_read(self):
        """The link is sent with the request, so the stored chart says nothing
        about which query the export reads."""
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            self.export_chart(self.other_chart, query=self.owner_query)


def create_query_over_a_table(owner, workbook, title):
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
                        "table": {"type": "table", "data_source": TEST_DS, "table_name": "table1"},
                    }
                ],
            }
        ).insert()


class TestSourceTablesComeFromTheQuery(InsightsIntegrationTestCase):
    """Which tables a query reads is a forward question, so the row answers it.

    `refresh_stored_tables` runs right after a save, and the edge table is rebuilt
    by a background job that runs after the save commits.
    """

    @classmethod
    def before_class(cls):
        create_test_users()
        create_test_data_sources()
        create_test_tables()
        cls.workbook = create_test_workbook(OWNER, title="Source Tables Workbook").name
        cls.query = create_query_over_a_table(OWNER, cls.workbook, "Source Tables Query").name

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        cleanup_test_fixtures()
        delete_users(OWNER)

    # @feature query.source-query
    def test_the_tables_are_found_before_the_index_is_built(self):
        frappe.db.delete("Insights Query Reference", {"query": self.query})
        self.addCleanup(
            sync_query_references,
            self.query,
            frappe.db.get_value(DT.QUERY, self.query, "operations"),
        )

        with self.as_user(OWNER):
            tables = frappe.get_doc(DT.QUERY, self.query).get_source_tables()

        self.assertEqual(tables, [{"data_source": TEST_DS, "table_name": "table1"}])


class TestTheLineageGraph(InsightsIntegrationTestCase):
    """The graph the lineage dialog renders is built from the reference rows."""

    @classmethod
    def before_class(cls):
        create_test_users()
        create_test_data_sources()
        create_test_tables()
        cls.workbook = create_test_workbook(OWNER, title="Lineage Workbook").name
        cls.source_query = create_query_over_a_table(OWNER, cls.workbook, "Lineage Source Query").name
        with as_user(OWNER):
            cls.derived_query = (
                frappe.get_doc(
                    {
                        "doctype": DT.QUERY,
                        "title": "Lineage Derived Query",
                        "workbook": cls.workbook,
                        "use_live_connection": 1,
                        "is_builder_query": 1,
                        "operations": reference_operations(cls.source_query),
                    }
                )
                .insert()
                .name
            )

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        cleanup_test_fixtures()
        delete_users(OWNER)

    # @feature workbook.lineage
    def test_the_lineage_graph_shows_an_edge_from_a_query_to_the_query_it_reads(self):
        graph = frappe.get_doc(DT.WORKBOOK, self.workbook).get_lineage_graph()

        table_id = f"table::{TEST_DS}::table1"
        source_id = f"query::{self.source_query}"
        derived_id = f"query::{self.derived_query}"

        self.assertEqual(
            {node["id"]: node["node_type"] for node in graph["nodes"]},
            {table_id: "table", source_id: "query", derived_id: "query"},
        )
        self.assertEqual(
            {(edge["source"], edge["target"]) for edge in graph["edges"]},
            {(table_id, source_id), (source_id, derived_id)},
        )
        self.assertEqual(
            {node["id"]: node["label"] for node in graph["nodes"]},
            {
                table_id: "table1",
                source_id: "Lineage Source Query",
                derived_id: "Lineage Derived Query",
            },
        )


def source_from(query_name, source):
    """Set the source without a save, because a save refuses a source from another workbook."""
    frappe.db.set_value(
        DT.QUERY,
        query_name,
        "operations",
        frappe.as_json(reference_operations(source)),
        update_modified=False,
    )


class TestCrossWorkbookSourcesAreCopied(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_test_users()

    @classmethod
    def after_class(cls):
        delete_users(OWNER)

    def make_workbook(self, title):
        name = create_test_workbook(OWNER, title=title).name
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, name, force=True, ignore_permissions=True)
        return name

    def sources_of(self, query_name):
        operations = frappe.parse_json(frappe.db.get_value(DT.QUERY, query_name, "operations"))
        return [
            op["table"]["query_name"] for op in operations if (op.get("table") or {}).get("type") == "query"
        ]

    # @feature query.source-query
    def test_a_workbook_gets_its_own_copy_of_a_chain_it_sources_from_another(self):
        from insights.patches.copy_cross_workbook_query_sources import execute

        far = self.make_workbook("Copy Far Workbook")
        base = create_source_query(OWNER, far, "Copy Base").name
        middle = create_referencing_query(OWNER, far, base, "Copy Middle").name
        far_operations = {q: frappe.db.get_value(DT.QUERY, q, "operations") for q in (base, middle)}

        near = self.make_workbook("Copy Near Workbook")
        first = create_source_query(OWNER, near, "Copy First Reader").name
        second = create_source_query(OWNER, near, "Copy Second Reader").name
        source_from(first, middle)
        source_from(second, middle)

        execute()

        (copy,) = set(self.sources_of(first)) | set(self.sources_of(second))
        self.assertNotEqual(copy, middle)
        self.assertEqual(frappe.db.get_value(DT.QUERY, copy, ["workbook", "title"]), (near, "Copy Middle"))
        (base_copy,) = self.sources_of(copy)
        self.assertEqual(frappe.db.get_value(DT.QUERY, base_copy, ["workbook", "title"]), (near, "Copy Base"))

        # the originals are unchanged
        for query, operations in far_operations.items():
            self.assertEqual(
                frappe.db.get_value(DT.QUERY, query, ["workbook", "operations"]), (far, operations)
            )

        with self.as_user(OWNER), db_connections():
            result = frappe.get_doc(DT.QUERY, first).execute()
        self.assertEqual(result["rows"][0]["secret"], SECRET)

        # a second run finds nothing left to copy
        count = frappe.db.count(DT.QUERY)
        execute()
        self.assertEqual(frappe.db.count(DT.QUERY), count)

    # @feature query.source-query dashboard.filter-links
    def test_a_filter_linked_to_the_source_is_linked_to_the_copy(self):
        """`route_filters` follows a link only to a query the card reads. After
        the patch the card reads the copy, so the link must point at the copy."""
        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import chart_reads
        from insights.patches.copy_cross_workbook_query_sources import execute

        far = self.make_workbook("Copy Link Far Workbook")
        source = create_source_query(OWNER, far, "Copy Link Source").name

        near = self.make_workbook("Copy Link Near Workbook")
        reader = create_source_query(OWNER, near, "Copy Link Reader").name
        source_from(reader, source)
        chart = create_test_chart(OWNER, near, query=reader, title="Copy Link Chart").name
        dashboard = create_test_dashboard(OWNER, near, chart, title="Copy Link Dashboard").name
        items = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard, "items"))
        items.append({"type": "filter", "filter_name": "secret", "links": {chart: f"`{source}`.`secret`"}})
        frappe.db.set_value(DT.DASHBOARD, dashboard, "items", frappe.as_json(items), update_modified=False)

        execute()

        (copy,) = self.sources_of(reader)
        (filter_item,) = [
            item
            for item in frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard, "items"))
            if item["type"] == "filter"
        ]
        self.assertEqual(filter_item["links"], {chart: f"`{copy}`.`secret`"})
        self.assertTrue(chart_reads(chart, copy))

    # @feature query.source-query dashboard.filter-links
    def test_a_filter_linked_past_the_first_hop_is_linked_to_the_copy_whatever_the_order(self):
        """The chain spans three workbooks: a reader, its source in a second
        workbook, and that source's source in a third. The patch handles readers
        in row order, so the second workbook's reader may already point at its
        own copy when the first workbook copies it."""
        from unittest.mock import patch

        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import chart_reads
        from insights.patches import copy_cross_workbook_query_sources as module

        third = self.make_workbook("Copy Hop Third Workbook")
        far_source = create_source_query(OWNER, third, "Copy Hop Source").name
        second = self.make_workbook("Copy Hop Second Workbook")
        middle = create_source_query(OWNER, second, "Copy Hop Middle").name
        source_from(middle, far_source)
        near = self.make_workbook("Copy Hop Near Workbook")
        reader = create_source_query(OWNER, near, "Copy Hop Reader").name
        source_from(reader, middle)
        chart = create_test_chart(OWNER, near, query=reader, title="Copy Hop Chart").name
        dashboard = create_test_dashboard(OWNER, near, chart, title="Copy Hop Dashboard").name
        items = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard, "items"))
        items.append(
            {"type": "filter", "filter_name": "secret", "links": {chart: f"`{far_source}`.`secret`"}}
        )
        frappe.db.set_value(DT.DASHBOARD, dashboard, "items", frappe.as_json(items), update_modified=False)

        stored = module.foreign_sources
        for first in (reader, middle):
            with self.subTest(first=first):
                frappe.db.savepoint("copy_hop")
                in_order = lambda workbook_of, first=first: sorted(
                    stored(workbook_of), key=lambda row: row[0] != first
                )
                with patch.object(module, "foreign_sources", in_order):
                    module.execute()

                (middle_copy,) = self.sources_of(reader)
                (source_copy,) = self.sources_of(middle_copy)
                self.assertEqual(frappe.db.get_value(DT.QUERY, source_copy, "workbook"), near)
                (filter_item,) = [
                    item
                    for item in frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard, "items"))
                    if item["type"] == "filter"
                ]
                self.assertEqual(filter_item["links"], {chart: f"`{source_copy}`.`secret`"})
                self.assertTrue(chart_reads(chart, source_copy))
                frappe.db.rollback(save_point="copy_hop")

    # @feature query.source-query
    def test_a_copy_keeps_a_sources_variables_without_their_values(self):
        """A variable holds a script's credential, and editors of the reading
        workbook can edit the copy. So the copy gets no values, and the patch
        lists the copies that need a value entered."""
        import contextlib
        import io

        from insights.patches.copy_cross_workbook_query_sources import execute

        far = self.make_workbook("Copy Secret Far Workbook")
        source = frappe.get_doc(DT.QUERY, create_source_query(OWNER, far, "Copy Secret Source").name)
        source.append("variables", {"variable_name": "LOG_PASSWORD", "variable_value": "hunter2"})
        source.save(ignore_permissions=True)

        near = self.make_workbook("Copy Secret Near Workbook")
        reader = create_source_query(OWNER, near, "Copy Secret Reader").name
        source_from(reader, source.name)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            execute()

        (copy,) = self.sources_of(reader)
        (variable,) = frappe.get_doc(DT.QUERY, copy).variables
        self.assertEqual(variable.variable_name, "LOG_PASSWORD")
        self.assertIsNone(variable.get_password("variable_value", raise_exception=False))
        self.assertIn(copy, output.getvalue())
        self.assertEqual(
            frappe.get_doc(DT.QUERY, source.name).variables[0].get_password("variable_value"), "hunter2"
        )


class TestASourceIsAQueryOfItsOwnWorkbook(InsightsIntegrationTestCase):
    """A query's sources are queries of its own workbook. Reuse across workbooks
    comes through datasets, not through a reference."""

    @classmethod
    def before_class(cls):
        create_test_users()

    @classmethod
    def after_class(cls):
        delete_users(OWNER)

    def setUp(self):
        self.near = create_test_workbook(OWNER, title="Own Near Workbook").name
        self.far = create_test_workbook(OWNER, title="Own Far Workbook").name
        for name in (self.near, self.far):
            self.addCleanup(frappe.delete_doc, DT.WORKBOOK, name, force=True, ignore_permissions=True)
        self.far_query = create_source_query(OWNER, self.far, "Own Far Source").name

    # @feature query.source-query
    def test_saving_a_source_from_another_workbook_is_refused(self):
        """The builder saves through `frappe.client.save`, which runs `validate`."""
        with self.assertRaises(frappe.ValidationError):
            create_referencing_query(OWNER, self.near, self.far_query, "Own Near Reader")

    # @feature query.copy-paste
    def test_pasting_a_source_from_another_workbook_is_refused(self):
        """Paste sends the copied query to `import_query`. A source missing from
        the copy stays a reference to the query on this site, in another workbook."""
        with self.as_user(OWNER):
            reader = create_source_query(OWNER, self.far, "Own Far Reader")
            source_from(reader.name, self.far_query)
            exported = frappe.get_doc(DT.QUERY, reader.name).export()
            exported["dependencies"]["queries"] = {}

            with self.assertRaises(frappe.ValidationError):
                frappe.get_doc(DT.WORKBOOK, self.near).import_query(exported)

    # @feature query.source-query
    def test_running_a_stored_source_from_another_workbook_is_refused(self):
        """A source stored before the rule is refused when the query runs."""
        reader = create_source_query(OWNER, self.near, "Own Near Stored Reader").name
        source_from(reader, self.far_query)

        with self.as_user(OWNER), db_connections(), self.assertRaises(frappe.ValidationError):
            frappe.get_doc(DT.QUERY, reader).execute()


class TestRemovingAQuery(InsightsIntegrationTestCase):
    """Deleting a query deletes its alerts and reference edges. A query that a
    chart reads cannot be deleted."""

    def setUp(self):
        self.workbook = create_test_workbook("Administrator", title="Remove Query Workbook").name
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, self.workbook, force=True, ignore_permissions=True)
        self.base = create_source_query("Administrator", self.workbook, "Remove Query Base").name
        self.consumer = create_referencing_query(
            "Administrator", self.workbook, self.base, "Remove Query Consumer"
        ).name
        self.alert = (
            frappe.get_doc(
                {
                    "doctype": "Insights Alert",
                    "title": "Remove Query Alert",
                    "channel": "Email",
                    "query": self.base,
                    "frequency": "Daily",
                    "custom_condition": 1,
                    "condition": "amount > 0",
                    "message": "hello",
                    "recipients": "someone@external.example.org",
                }
            )
            .insert()
            .name
        )

    def kept(self):
        return (
            frappe.db.exists("Insights Alert", self.alert),
            frappe.db.exists("Insights Query Reference", {"ref_query": self.base}),
        )

    # @feature workbook.remove-item
    def test_a_query_a_chart_reads_is_refused_before_it_takes_anything(self):
        """frappe checks links after `on_trash`. A script that caught the error
        and committed would keep the query but lose its alerts and edges."""
        create_test_chart("Administrator", self.workbook, self.base, title="Remove Query Chart")

        with self.assertRaises(frappe.LinkExistsError):
            frappe.delete_doc(DT.QUERY, self.base)

        self.assertTrue(all(self.kept()))

    # @feature workbook.remove-item
    def test_a_query_no_chart_reads_goes_with_its_alerts_and_edges(self):
        frappe.delete_doc(DT.QUERY, self.base)

        self.assertFalse(frappe.db.exists(DT.QUERY, self.base))
        self.assertFalse(any(self.kept()))


class TestAReferenceInTheRequestIsChecked(AReferenceInTheRequestIsChecked, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 0


class TestAReferenceInTheRequestIsCheckedWithTeamPermissions(
    AReferenceInTheRequestIsChecked, InsightsIntegrationTestCase
):
    ENABLE_PERMISSIONS = 1


class TestASavedReferenceKeepsItsOwnAccess(ASavedReferenceKeepsItsOwnAccess, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 0


class TestASavedReferenceKeepsItsOwnAccessWithTeamPermissions(
    ASavedReferenceKeepsItsOwnAccess, InsightsIntegrationTestCase
):
    ENABLE_PERMISSIONS = 1


class TestDashboardFilterReadsTheQuery(DashboardFilterReadsTheQuery, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 0


class TestDashboardFilterReadsTheQueryWithTeamPermissions(
    DashboardFilterReadsTheQuery, InsightsIntegrationTestCase
):
    ENABLE_PERMISSIONS = 1


class TestChartExportReadsTheQuery(ChartExportReadsTheQuery, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 0


class TestChartExportReadsTheQueryWithTeamPermissions(ChartExportReadsTheQuery, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 1
