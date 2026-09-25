"""The lists the home, dashboard and data store pages read.

Each endpoint answers one question: which rows the caller may see, which of them
a search term keeps, and which lens — owned, shared, favourite, recent — narrows
it further. The pages only render what comes back.

The site has rows these suites did not make, so a list is read through the
fixtures' own titles. A lens is still checked whole: the rows it must keep and the
rows it must drop are both named.
"""

import frappe
from frappe.desk.like import toggle_like
from frappe.desk.search import search_link

from insights.api.dashboards import get_dashboards
from insights.api.data_store import get_data_store_tables
from insights.api.workbooks import get_workbooks, update_share_permissions
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    as_user,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
    delete_users,
)
from insights.tests.permissions_utils import (
    ADMIN,
    TEST_DS,
    USER_1,
    USER_2,
    create_test_data_sources,
    create_test_users,
    delete_test_data_sources,
    update_dashboard_access,
)

OWNER = USER_1
OTHER = USER_2

TITLE_PREFIX = "List Test"
TABLE_PREFIX = "list_test_table"


def ours(rows, key="title"):
    """The rows this suite made, in the order they came back."""
    return [row[key] for row in rows if str(row[key]).startswith(TITLE_PREFIX)]


class TestWorkbookList(InsightsIntegrationTestCase):
    OWN = f"{TITLE_PREFIX} Workbook Mine"
    OTHERS = f"{TITLE_PREFIX} Workbook Theirs"

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.own = create_test_workbook(OWNER, title=cls.OWN).name
        cls.others = create_test_workbook(OTHER, title=cls.OTHERS).name
        cls.query = create_test_query(OWNER, cls.own, title=f"{TITLE_PREFIX} ESOP Grants").name
        cls.chart = create_test_chart(OWNER, cls.own, query=cls.query, title=f"{TITLE_PREFIX} Grants").name
        cls.dashboard = create_test_dashboard(OWNER, cls.own, title=f"{TITLE_PREFIX} Board").name
        with as_user(OTHER):
            update_share_permissions(cls.others, [{"user": OWNER, "read": 1, "write": 0}])

    @classmethod
    def after_class(cls):
        for name in (cls.own, cls.others):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER, ADMIN)

    # @feature workbook.list
    def test_the_workbook_list_narrows_by_title_and_the_shared_lens_keeps_only_other_peoples_workbooks(
        self,
    ):
        with self.as_user(OWNER):
            everything = ours(get_workbooks())
            searched = ours(get_workbooks(search_term="Workbook Theirs"))
            owned = ours(get_workbooks(sources=["created"]))
            shared = ours(get_workbooks(sources=["shared"]))
            capped = get_workbooks(limit=1)

        self.assertEqual(sorted(everything), [self.OWN, self.OTHERS])
        self.assertEqual(searched, [self.OTHERS])
        self.assertEqual(owned, [self.OWN])
        self.assertEqual(shared, [self.OTHERS])
        self.assertEqual(len(capped), 1)

    # @feature workbook.home-recent
    def test_the_list_puts_the_workbook_modified_last_first(self):
        frappe.get_doc(DT.WORKBOOK, self.others).save(ignore_permissions=True)
        with self.as_user(OWNER):
            listed = ours(get_workbooks(limit=20))

        self.assertEqual(listed, [self.OTHERS, self.OWN])

        frappe.get_doc(DT.WORKBOOK, self.own).save(ignore_permissions=True)
        with self.as_user(OWNER):
            after_a_save = ours(get_workbooks(limit=20))

        self.assertEqual(after_a_save, [self.OWN, self.OTHERS])

    # @feature workbook.list-everyone
    def test_an_admin_lists_only_what_was_given_to_them_until_they_ask_for_everyones(self):
        with self.as_user(ADMIN):
            everything = ours(get_workbooks())
            everyones = ours(get_workbooks(sources=["created", "shared", "others"]))
            others = ours(get_workbooks(sources=["others"]))
        with self.as_user(OWNER):
            not_created = ours(get_workbooks(sources=["shared", "others"]))

        self.assertEqual(everything, [])
        self.assertEqual(sorted(everyones), [self.OWN, self.OTHERS])
        self.assertEqual(sorted(others), [self.OWN, self.OTHERS])
        self.assertEqual(not_created, [self.OTHERS])

    # @feature workbook.list-filter
    def test_the_list_filters_on_what_a_workbook_contains(self):
        def listed(*filters):
            with self.as_user(OWNER):
                return sorted(ours(get_workbooks(filters=list(filters))))

        self.assertEqual(listed(["query", "LIKE", "%esop%"]), [self.OWN])
        self.assertEqual(listed(["query", "=", self.query]), [self.OWN])
        self.assertEqual(listed(["chart", "in", [self.chart]]), [self.OWN])
        self.assertEqual(listed(["dashboard", "=", self.dashboard]), [self.OWN])
        self.assertEqual(listed(["name", "=", self.others]), [self.OTHERS])
        self.assertEqual(listed(["name", "LIKE", "%Theirs%"]), [self.OTHERS])
        self.assertEqual(listed(["data_source", "=", "Site DB"]), [self.OWN])
        self.assertEqual(listed(["data_source", "in", ["Site DB", TEST_DS]]), [self.OWN])
        self.assertEqual(listed(["table_name", "LIKE", "%ToDo%"]), [self.OWN])
        todo = frappe.db.get_value(DT.TABLE, {"data_source": "Site DB", "table": "tabToDo"})
        if not todo:
            todo = (
                frappe.get_doc(
                    {"doctype": DT.TABLE, "data_source": "Site DB", "table": "tabToDo", "label": "ToDo"}
                )
                .insert(ignore_permissions=True)
                .name
            )
        self.assertEqual(listed(["table_name", "=", todo]), [self.OWN])
        self.assertEqual(listed(["data_source", "!=", "Site DB"]), [self.OTHERS])
        self.assertEqual(listed(["query", "is", "not set"]), [self.OTHERS])
        self.assertEqual(listed(["title", "LIKE", "%Theirs%"]), [self.OTHERS])

    # @feature workbook.list-filter
    def test_a_query_option_names_its_workbook(self):
        with self.as_user(OWNER):
            options = search_link(DT.QUERY, "ESOP Grants")

        self.assertIn(
            {
                "value": self.query,
                "label": f"{TITLE_PREFIX} ESOP Grants",
                "description": f"{self.query}, {self.OWN}",
            },
            options,
        )


class TestDashboardList(InsightsIntegrationTestCase):
    OWN = f"{TITLE_PREFIX} Dashboard Mine"
    OTHERS = f"{TITLE_PREFIX} Dashboard Theirs"

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.own_workbook = create_test_workbook(OWNER, title=f"{TITLE_PREFIX} Dash Workbook Mine").name
        cls.other_workbook = create_test_workbook(OTHER, title=f"{TITLE_PREFIX} Dash Workbook Theirs").name
        cls.own = create_test_dashboard(OWNER, cls.own_workbook, title=cls.OWN).name
        cls.others = create_test_dashboard(OTHER, cls.other_workbook, title=cls.OTHERS).name
        with as_user(OTHER):
            update_dashboard_access(cls.others, [OWNER])

    @classmethod
    def after_class(cls):
        for name in (cls.own_workbook, cls.other_workbook):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    # @feature dashboard.list
    def test_the_dashboard_list_narrows_by_title_and_the_lenses_keep_their_own(self):
        with self.as_user(OWNER):
            everything = ours(get_dashboards())
            searched = ours(get_dashboards(filters=[["name", "LIKE", "%Dashboard Theirs%"]]))
            owned = ours(get_dashboards(sources=["created"]))
            shared = ours(get_dashboards(sources=["shared"]))
        with self.as_user(ADMIN):
            admins = ours(get_dashboards())
            everyones = ours(get_dashboards(sources=["created", "shared", "others"]))

        self.assertEqual(sorted(everything), [self.OWN, self.OTHERS])
        self.assertEqual(searched, [self.OTHERS])
        self.assertEqual(owned, [self.OWN])
        self.assertEqual(shared, [self.OTHERS])
        self.assertEqual(admins, [])
        self.assertEqual(sorted(everyones), [self.OWN, self.OTHERS])

    # @feature dashboard.list
    def test_the_list_puts_the_dashboard_opened_last_first(self):
        with self.as_user(OWNER):
            frappe.get_doc(DT.DASHBOARD, self.others).track_view()
            frappe.get_doc(DT.DASHBOARD, self.own).track_view()
            listed = ours(get_dashboards())

        self.assertEqual(listed, [self.OWN, self.OTHERS])

    # @feature dashboard.favorite
    def test_a_favorited_dashboard_is_marked_and_listed_first(self):
        with self.as_user(OWNER):
            frappe.get_doc(DT.DASHBOARD, self.others).track_view()
            toggle_like(DT.DASHBOARD, self.own, add="Yes")
            self.addCleanup(self.unlike)

            listed = ours(get_dashboards())
            marked = {row["title"]: bool(row.get("is_favourite")) for row in get_dashboards()}

        self.assertTrue(marked[self.OWN])
        self.assertFalse(marked[self.OTHERS])
        self.assertEqual(listed, [self.OWN, self.OTHERS])

    def unlike(self):
        with self.as_user(OWNER):
            toggle_like(DT.DASHBOARD, self.own, add="No")

    # @feature dashboard.list
    def test_only_a_writer_refreshes_a_dashboards_preview(self):
        """`update_dashboard_preview`, which `DashboardList.vue`'s "Refresh
        Preview" and `DashboardCard`'s "Load Preview" call, and the `can_write`
        each row of `get_dashboards` includes for them. The preview is rendered with
        the rows of whoever refreshes it, and every reader of the list sees it."""
        from unittest.mock import patch

        from insights.api.dashboards import update_dashboard_preview
        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
            InsightsDashboardv3,
        )

        with patch.object(
            InsightsDashboardv3, "generate_dashboard_preview", return_value="/preview.png"
        ) as rendered:
            for user, dashboard, writes in ((OWNER, self.others, False), (OWNER, self.own, True)):
                with self.subTest(user=user, dashboard=dashboard), self.as_user(user):
                    row = next(row for row in get_dashboards() if row["name"] == dashboard)
                    self.assertIs(row["can_write"], writes)
                    if writes:
                        self.assertEqual(update_dashboard_preview(dashboard), "/preview.png")
                    else:
                        with self.assertRaises(frappe.PermissionError):
                            update_dashboard_preview(dashboard)
        self.assertEqual(rendered.call_count, 1)

    def probed_dashboard(self):
        """A dashboard of OTHER's, shared with OWNER by name, over a chart of a
        query that reads Site DB."""
        query = create_test_query(OTHER, self.other_workbook, title=f"{TITLE_PREFIX} Probed Query")
        chart = create_test_chart(
            OTHER, self.other_workbook, query=query.name, title=f"{TITLE_PREFIX} Hidden"
        )
        probed = create_test_dashboard(
            OTHER, self.other_workbook, chart=chart.name, title=f"{TITLE_PREFIX} Dashboard Probed"
        ).name
        for doctype, name in ((DT.DASHBOARD, probed), (DT.CHART, chart.name), (DT.QUERY, query.name)):
            self.addCleanup(frappe.delete_doc, doctype, name, force=True, ignore_permissions=True)
        with as_user(OTHER):
            update_dashboard_access(probed, [OWNER])

        def listed(user, *filters):
            with self.as_user(user):
                return probed in [row["name"] for row in get_dashboards(filters=list(filters))]

        return chart.name, listed

    # @feature dashboard.list workbook.list-filter
    def test_a_chart_filter_matches_only_the_charts_the_reader_may_read(self):
        """`get_dashboards`, which `DashboardList.vue`'s Chart filter calls. A
        guess at a chart title a User Permission hides from the reader must not
        list its dashboard. Its owner still filters by it."""
        chart, listed = self.probed_dashboard()

        own_chart = create_test_chart(OWNER, self.own_workbook, title=f"{TITLE_PREFIX} Allowed").name
        self.addCleanup(frappe.delete_doc, DT.CHART, own_chart, force=True, ignore_permissions=True)
        restriction = frappe.get_doc(
            {"doctype": "User Permission", "user": OWNER, "allow": DT.CHART, "for_value": own_chart}
        ).insert(ignore_permissions=True)
        self.addCleanup(frappe.delete_doc, "User Permission", restriction.name, force=True)
        self.assertTrue(listed(OWNER))
        for probe in (["chart", "=", chart], ["chart", "like", "%Hidden%"]):
            with self.subTest(probe=probe):
                self.assertFalse(listed(OWNER, probe))
                self.assertTrue(listed(OTHER, probe))

    # @feature dashboard.list
    def test_the_data_source_filter_matches_a_picked_name_over_the_charts_the_reader_reads(self):
        """`get_dashboards`, which `DashboardList.vue`'s Data Source filter calls
        (Q26). A reader of the dashboard's chart who reads no query filters by
        the data source the chart reads, as its owner does. A pattern matches
        nothing, so no guess runs over a query's pipeline."""
        _chart, listed = self.probed_dashboard()

        answers = (
            (["data_source", "=", "Site DB"], True),
            (["data_source", "in", ["Site DB", TEST_DS]], True),
            (["data_source", "is", "set"], True),
            (["data_source", "=", "Site DB "], False),
            (["data_source", "=", "site db"], False),
            (["data_source", "=", TEST_DS], False),
            (["data_source", "!=", "Site DB"], False),
            (["data_source", "is", "not set"], False),
            (["data_source", "like", "Site%"], False),
            (["data_source", "like", "%Site DB%"], False),
            (["data_source", "not like", "%Nothing%"], False),
        )
        for probe, expected in answers:
            for user in (OWNER, OTHER):
                with self.subTest(probe=probe, user=user):
                    self.assertIs(listed(user, probe), expected)


class TestStoredTableList(InsightsIntegrationTestCase):
    """Only a stored table is in the data store, and it is found by either name."""

    ALPHA = f"{TABLE_PREFIX}_alpha"
    BETA = f"{TABLE_PREFIX}_beta"
    UNSTORED = f"{TABLE_PREFIX}_unstored"

    @classmethod
    def before_class(cls):
        create_test_users()
        create_test_data_sources()
        for table_name, label, stored in (
            (cls.ALPHA, f"{TITLE_PREFIX} Alpha", 1),
            (cls.BETA, f"{TITLE_PREFIX} Beta", 1),
            (cls.UNSTORED, f"{TITLE_PREFIX} Unstored", 0),
        ):
            frappe.get_doc(
                {
                    "doctype": DT.TABLE,
                    "table": table_name,
                    "label": label,
                    "data_source": TEST_DS,
                    "sync_mode": "Full",
                    "stored": stored,
                }
            ).insert()

    @classmethod
    def after_class(cls):
        for name in frappe.get_all(DT.TABLE, filters={"table": ["like", f"{TABLE_PREFIX}%"]}, pluck="name"):
            frappe.delete_doc(DT.TABLE, name, force=True)
        delete_test_data_sources()
        delete_users(OWNER, OTHER)

    def listed(self, **kwargs):
        rows = get_data_store_tables(data_source=TEST_DS, **kwargs)
        return sorted(row["table_name"] for row in rows)

    # @feature data-store.list
    def test_the_stored_table_list_holds_only_stored_tables_and_narrows_by_label_or_name(self):
        self.assertEqual(self.listed(), [self.ALPHA, self.BETA])
        self.assertEqual(self.listed(search_term="Alpha"), [self.ALPHA])
        self.assertEqual(self.listed(search_term="_beta"), [self.BETA])
        self.assertEqual(self.listed(search_term="Unstored"), [])
        self.assertEqual(self.listed(search_term="nothing here"), [])
