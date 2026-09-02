"""A query reached through a reference is read like any other query.

An operation may source, join or union another query, and a dashboard filter or a
chart may name one. Either way the reference resolves to the whole query - its
operations, its native SQL, and the tables it reads - and the compiled result
carries all of it back.

The reference is checked once, where it is written. Execution then trusts what was
saved, so a chain stays runnable by everyone who may read the query at its head.
A reference that arrives with the request was never written, and is checked then.
"""

import frappe
from frappe.utils import set_request

from insights.api import run_doc_method
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    db_connections,
)
from insights.insights.query_utils import sync_query_references
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    as_user,
    create_test_chart,
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
    """A query that stands on its own, so no table permission enters the picture."""
    with as_user(owner):
        return frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": title,
                "workbook": workbook,
                "use_live_connection": 0,
                "is_script_query": 1,
                "operations": [{"type": "code", "code": SOURCE_ROWS}],
            }
        ).insert()


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

    def test_the_owner_query_is_not_readable_by_the_other_user(self):
        """The baseline the refusals below are measured against."""
        with self.as_user(OTHER):
            self.assertFalse(frappe.has_permission(DT.QUERY, ptype="read", doc=self.owner_query))

    def test_a_saved_chain_resolves_for_its_owner(self):
        with self.as_user(OWNER), db_connections():
            result = frappe.get_doc(DT.QUERY, self.owner_reference).execute()
        self.assertEqual(result["rows"][0]["secret"], SECRET)

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

    def test_forged_operations_on_a_saved_query_are_refused(self):
        """What was saved is the row, not what the request says was saved."""
        with self.as_user(OTHER):
            doc = frappe.get_doc(DT.QUERY, self.other_query)
            doc.operations = reference_operations(self.owner_query)
            with self.assertRaises(frappe.PermissionError), db_connections():
                doc.execute()

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


class ASavedReferenceCarriesItsOwnAccess:
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
        delete_users(OWNER, VIEWER)

    def before_test(self):
        self.set_team_permissions(self.ENABLE_PERMISSIONS)

    def test_the_share_carries_the_chart_and_its_query_only(self):
        """The baseline: a shared chart does not carry the workbook behind it."""
        with self.as_user(VIEWER):
            self.assertTrue(frappe.has_permission(DT.CHART, ptype="read", doc=self.chart))
            self.assertTrue(frappe.has_permission(DT.QUERY, ptype="read", doc=self.consumer))
            self.assertFalse(frappe.has_permission(DT.QUERY, ptype="read", doc=self.base))

    def test_someone_with_the_chart_can_run_the_chain(self):
        """Running the query they may read is what the share is for."""
        with self.as_user(VIEWER), db_connections():
            result = frappe.get_doc(DT.QUERY, self.consumer).execute()
        self.assertEqual(result["rows"][0]["secret"], SECRET)

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

    def test_an_export_carries_its_references_before_the_index_is_built(self):
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

    def test_an_export_skips_a_reference_whose_query_is_gone(self):
        """`on_trash` drops the edge rows but not the operations that name the
        query, so the export list carries a name with no row behind it."""
        with self.as_user(OWNER):
            gone = create_source_query(OWNER, self.workbook, "Chain Doomed Base").name
            orphan = create_referencing_query(OWNER, self.workbook, gone, "Chain Orphan").name
            frappe.delete_doc(DT.QUERY, gone, force=True)

            exported = frappe.get_doc(DT.QUERY, orphan).export()

        self.assertEqual(exported["dependencies"]["queries"], {})

    def test_a_reference_cannot_be_saved_to_an_unreadable_query(self):
        """Where the check lives."""
        with self.as_user(VIEWER), self.assertRaises(frappe.PermissionError):
            create_referencing_query(VIEWER, self.viewer_workbook, self.base, "Chain Forged Consumer")

    def test_a_reference_added_on_update_is_checked_too(self):
        """An existing query is not a way around the check."""
        with self.as_user(VIEWER):
            query = create_source_query(VIEWER, self.viewer_workbook, "Chain Viewer Source")
            query.operations = reference_operations(self.base)
            with self.assertRaises(frappe.PermissionError):
                query.save()


class DashboardFilterReadsTheQuery:
    """A dashboard filter names its own query, and the caller never does.

    A filter links a column as `` `<query>`.`<column>` ``. The caller sends the
    filter's name and `filter_source` reads the link off the stored dashboard, so
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
                        "title": f"Filter Dashboard {len(items)}",
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

    def test_a_filter_offers_the_values_of_the_column_it_links(self):
        with self.as_user(OWNER):
            values = self.distinct_values(self.owner_dashboard, self.FILTER_NAME)
        self.assertEqual(values, [SECRET])

    def test_a_filter_the_dashboard_does_not_declare_is_refused(self):
        """A name is all the caller sends, so an unknown one reaches no query."""
        with self.as_user(OWNER), self.assertRaises(frappe.PermissionError):
            self.distinct_values(self.owner_dashboard, "Not A Filter")

    def test_a_link_to_a_chart_the_dashboard_does_not_hold_is_not_followed(self):
        """`links` alone cannot reach a query: the chart has to be on the page."""
        with self.as_user(OWNER), self.assertRaises(frappe.PermissionError):
            self.distinct_values(self.detached_dashboard, self.FILTER_NAME)


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
        """The client sends the chart it holds, so the body carries its fields."""
        chart = frappe.get_doc(DT.CHART, name)
        body = {
            "doctype": DT.CHART,
            "name": chart.name,
            "workbook": chart.workbook,
            "query": chart.query,
            "chart_type": chart.chart_type,
        }
        return run_doc_method("export", {**body, **claims})

    def test_a_chart_exports_the_query_its_owner_may_read(self):
        """The baseline: the export carries the linked query."""
        with self.as_user(OWNER):
            exported = self.export_chart(self.owner_chart)
        self.assertIn(self.owner_query, exported["dependencies"]["queries"])

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


class TestAReferenceInTheRequestIsChecked(AReferenceInTheRequestIsChecked, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 0


class TestAReferenceInTheRequestIsCheckedWithTeamPermissions(
    AReferenceInTheRequestIsChecked, InsightsIntegrationTestCase
):
    ENABLE_PERMISSIONS = 1


class TestASavedReferenceCarriesItsOwnAccess(ASavedReferenceCarriesItsOwnAccess, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 0


class TestASavedReferenceCarriesItsOwnAccessWithTeamPermissions(
    ASavedReferenceCarriesItsOwnAccess, InsightsIntegrationTestCase
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
