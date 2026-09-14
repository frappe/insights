"""The lists the home, dashboard and data store pages read.

Each endpoint answers one question: which rows the caller may see, which of them
a search term keeps, and which lens — owned, shared, favourite, recent — narrows
it further. The pages only render what comes back.

The site carries rows these suites did not make, so a list is read through the
fixtures' own titles. A lens is still checked whole: the rows it must keep and the
rows it must drop are both named.
"""

import frappe
from frappe.desk.like import toggle_like

from insights.api.dashboards import get_dashboards, get_recent_dashboards
from insights.api.data_store import get_data_store_tables
from insights.api.workbooks import get_workbooks, update_share_permissions
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    as_user,
    create_test_dashboard,
    create_test_workbook,
    delete_users,
)
from insights.tests.permissions_utils import (
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
        with as_user(OTHER):
            update_share_permissions(cls.others, [{"user": OWNER, "read": 1, "write": 0}])

    @classmethod
    def after_class(cls):
        for name in (cls.own, cls.others):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    # @feature workbook.list
    def test_the_workbook_list_narrows_by_title_and_the_shared_lens_keeps_only_other_peoples_workbooks(
        self,
    ):
        with self.as_user(OWNER):
            everything = ours(get_workbooks())
            searched = ours(get_workbooks(search_term="Workbook Theirs"))
            owned = ours(get_workbooks(scope="owned"))
            shared = ours(get_workbooks(scope="shared"))
            capped = get_workbooks(limit=1)

        self.assertEqual(sorted(everything), [self.OWN, self.OTHERS])
        self.assertEqual(searched, [self.OTHERS])
        self.assertEqual(owned, [self.OWN])
        self.assertEqual(shared, [self.OTHERS])
        self.assertEqual(len(capped), 1)

    # @feature workbook.home-recent
    def test_the_home_list_puts_the_workbook_created_last_first(self):
        """Recent means newest, not last touched.

        The list carries the order `Insights Workbook` sorts in, which is
        `creation desc`. Saving an older workbook again does not move it up, so
        a home page that wants last-touched order cannot get it from here.
        """
        with self.as_user(OWNER):
            listed = ours(get_workbooks(limit=20))

        self.assertEqual(listed, [self.OTHERS, self.OWN])

        frappe.get_doc(DT.WORKBOOK, self.own).save(ignore_permissions=True)

        with self.as_user(OWNER):
            after_a_save = ours(get_workbooks(limit=20))

        self.assertEqual(after_a_save, [self.OTHERS, self.OWN])


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
            searched = ours(get_dashboards(search_term="Dashboard Theirs"))
            owned = ours(get_dashboards(scope="owned"))
            shared = ours(get_dashboards(scope="shared"))

        self.assertEqual(sorted(everything), [self.OWN, self.OTHERS])
        self.assertEqual(searched, [self.OTHERS])
        self.assertEqual(owned, [self.OWN])
        self.assertEqual(shared, [self.OTHERS])

    # @feature dashboard.list
    def test_the_recent_list_puts_the_dashboard_opened_last_first(self):
        with self.as_user(OWNER):
            frappe.get_doc(DT.DASHBOARD, self.others).track_view()
            frappe.get_doc(DT.DASHBOARD, self.own).track_view()
            recent = ours(get_recent_dashboards())

        self.assertEqual(recent, [self.OWN, self.OTHERS])

    # @feature dashboard.favorite
    def test_a_favorited_dashboard_is_marked_and_listed_under_favorites(self):
        with self.as_user(OWNER):
            toggle_like(DT.DASHBOARD, self.own, add="Yes")
            self.addCleanup(self.unlike)

            marked = {row["title"]: bool(row.get("is_favourite")) for row in get_dashboards()}
            favorites = ours(get_dashboards(get_favorites=True))

        self.assertTrue(marked[self.OWN])
        self.assertFalse(marked[self.OTHERS])
        self.assertEqual(favorites, [self.OWN])

    def unlike(self):
        with self.as_user(OWNER):
            toggle_like(DT.DASHBOARD, self.own, add="No")


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
