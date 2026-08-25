import frappe
import frappe.share
from frappe.permissions import update_permission_property

from insights.api.user import USER_FIELDS, get_users, user_lookup_allowed
from insights.api.workbooks import get_share_permissions, update_share_permissions
from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.insights.doctype.insights_team.insights_team import clear_cache as clear_team_cache
from insights.permissions import PERMISSION_DOCTYPES
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
)
from insights.tests.permissions_utils import (
    ADMIN,
    NON_INSIGHTS_USER,
    TEST_DS,
    TEST_TABLE1,
    USER_1,
    USER_2,
    USER_3,
    cleanup_test_fixtures,
    create_test_data_sources,
    create_test_tables,
    create_test_team,
    create_test_teams,
    create_test_users,
    share_chart,
    unshare_chart,
    update_dashboard_access,
)


@insights_whitelist()
def protected_insights_call():
    return True


class TestInsightsPermissions(InsightsIntegrationTestCase):
    SAVEPOINT = "test_insights_permissions"

    @classmethod
    def before_class(cls):
        cls.original_enable_permissions = frappe.db.get_single_value(DT.SETTINGS, "enable_permissions")
        cleanup_test_fixtures()
        create_test_users()
        clear_team_cache()

    @classmethod
    def after_class(cls):
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", cls.original_enable_permissions)
        clear_team_cache()
        cleanup_test_fixtures()

    def before_test(self):
        clear_team_cache()

    def after_test(self):
        clear_team_cache()

    def assert_no_access_to(self, user, doctype, name):
        """Both consumers of the permission query must refuse the user."""
        self.assert_not_visible_to(user, doctype, name)
        with self.as_user(user):
            for ptype in ("read", "write"):
                self.assertFalse(
                    frappe.has_permission(doctype, ptype=ptype, doc=name),
                    f"{user} should not hold {ptype} on {doctype} {name}",
                )

    def grant_every_resource_type_to_a_team(self):
        """Build one team holding a grant of each type, and one holding none."""
        create_test_data_sources()
        create_test_tables()
        workbook = create_test_workbook(ADMIN)
        query = create_test_query(ADMIN, workbook.name)
        chart = create_test_chart(ADMIN, workbook.name, query.name)
        dashboard = create_test_dashboard(ADMIN, workbook.name, chart.name)

        granted = {
            DT.DATA_SOURCE: TEST_DS,
            DT.TABLE: TEST_TABLE1,
            DT.CHART: chart.name,
            DT.DASHBOARD: dashboard.name,
        }
        create_test_team("team1", [USER_1], list(granted.items()))
        create_test_team("team2", [USER_3])
        return granted

    def test_permissions_for_non_insights_user(self):
        with self.as_user(NON_INSIGHTS_USER):
            for doctype in PERMISSION_DOCTYPES:
                self.assertFalse(
                    frappe.has_permission(doctype, ptype="read"),
                    f"{doctype} should not be readable without an Insights role",
                )

            with self.assertRaises(frappe.PermissionError):
                protected_insights_call()

    def test_permissions_on_team_based_doctype_with_team_permissions_disabled(self):
        create_test_data_sources()
        create_test_tables()
        create_test_teams()
        self.set_team_permissions(False)

        self.assert_visible_to(USER_2, DT.DATA_SOURCE, TEST_DS)
        self.assert_visible_to(USER_2, DT.TABLE, TEST_TABLE1)

    def test_permission_on_team_based_doctype_with_team_permissions_enabled(self):
        create_test_data_sources()
        create_test_tables()
        team = create_test_teams()
        self.set_team_permissions(True)

        self.assert_not_visible_to(USER_2, DT.DATA_SOURCE, TEST_DS)
        self.assert_not_visible_to(USER_2, DT.TABLE, TEST_TABLE1)

        with self.as_user("Administrator"):
            team.append(
                "team_permissions",
                {"resource_type": DT.DATA_SOURCE, "resource_name": TEST_DS},
            )
            team.append(
                "team_permissions",
                {
                    "resource_type": DT.TABLE,
                    "resource_name": TEST_TABLE1,
                },
            )
            team.save(ignore_permissions=True)
            clear_team_cache()

        self.assert_visible_to(USER_1, DT.DATA_SOURCE, TEST_DS)
        self.assert_visible_to(USER_1, DT.TABLE, TEST_TABLE1)

    def test_resource_grant_reaches_the_granted_team_only(self):
        """A grant is held by a team, so only that team's members may use it.

        The two users without access differ, and both matter. USER_2 is in no
        team, USER_3 is in a team that holds no grant. An empty set of teams and
        an empty set of grants have to land on the same empty result.
        """
        granted = self.grant_every_resource_type_to_a_team()
        self.set_team_permissions(True)

        for doctype, name in granted.items():
            self.assert_visible_to(USER_1, doctype, name)

        for user in (USER_2, USER_3):
            for doctype, name in granted.items():
                self.assert_no_access_to(user, doctype, name)

    def test_resource_grant_is_inert_while_team_permissions_are_off(self):
        """Team membership is not read while the setting is off, so no grant applies.

        Data sources and tables stay open to every Insights user - that is what
        the setting turns off. Charts and dashboards fall back to workbook
        access, which the grant holder does not have either.
        """
        granted = self.grant_every_resource_type_to_a_team()
        self.set_team_permissions(False)

        for user in (USER_1, USER_2, USER_3):
            self.assert_visible_to(user, DT.DATA_SOURCE, granted[DT.DATA_SOURCE])
            self.assert_visible_to(user, DT.TABLE, granted[DT.TABLE])
            self.assert_no_access_to(user, DT.CHART, granted[DT.CHART])
            self.assert_no_access_to(user, DT.DASHBOARD, granted[DT.DASHBOARD])

    def test_permission_for_admin_on_team_based_doctype_with_team_permissions_enabled(
        self,
    ):
        create_test_data_sources()
        create_test_tables()
        self.set_team_permissions(True)

        self.assert_visible_to(ADMIN, DT.DATA_SOURCE, TEST_DS)
        self.assert_visible_to(ADMIN, DT.TABLE, TEST_TABLE1)

    def test_permission_for_workbook(self):
        workbook = create_test_workbook(USER_1)

        self.assert_visible_to(USER_1, DT.WORKBOOK, workbook.name)
        self.assert_not_visible_to(USER_2, DT.WORKBOOK, workbook.name)

        with self.as_user(USER_1):
            update_share_permissions(
                workbook.name,
                [{"user": USER_2, "read": 1, "write": 0}],
            )
            share_permissions = get_share_permissions(workbook.name)
        self.assertIn(
            USER_2,
            [permission["user"] for permission in share_permissions["user_permissions"]],
        )

        self.assert_visible_to(USER_2, DT.WORKBOOK, workbook.name)

        with self.as_user(USER_1):
            update_share_permissions(workbook.name, [])

        self.assert_not_visible_to(USER_2, DT.WORKBOOK, workbook.name)

    def test_workbook_owner_can_look_up_users_to_share_with(self):
        # the share picker reads this roster, so an owner without an admin role
        # must find the other Insights users in it - with or without team permissions
        for team_permissions in (False, True):
            with self.subTest(team_permissions=team_permissions):
                self.set_team_permissions(team_permissions)
                with self.as_user(USER_1):
                    emails = [user["email"] for user in get_users()]

                self.assertIn(USER_2, emails)
                self.assertIn(ADMIN, emails)
                self.assertNotIn(NON_INSIGHTS_USER, emails)

    def test_roster_carries_nothing_but_directory_fields(self):
        # the api is the only way into `User`, so its field list is the whole
        # exposure - no phone number or api key may ride along
        with self.as_user(USER_1):
            users = get_users()

        self.assertTrue(users)
        for user in users:
            self.assertEqual(set(user.keys()), set(USER_FIELDS) | {"type"})

    def test_users_are_found_by_name_or_by_email(self):
        # the two are alternatives: matching a name must not also require the
        # address to match
        with self.as_user(USER_1):
            by_email = [user["email"] for user in get_users("user1")]
            by_name = [user["email"] for user in get_users("Insights User")]

        self.assertIn(USER_1, by_email)
        self.assertNotIn(USER_2, by_email)
        self.assertIn(USER_1, by_name)
        self.assertIn(USER_2, by_name)

    def test_user_lookup_is_on_for_a_site_that_never_set_it(self):
        # a Check stays out of `tabSingles` until the doc is first saved, and
        # `get_single_value` casts the missing value to 0. A setting named for
        # permission would therefore read as "off" on every existing site, so
        # the setting has to name the exception instead.
        frappe.db.sql(
            "delete from `tabSingles` where doctype = %s and field = %s",
            (DT.SETTINGS, "disable_user_lookup"),
        )
        frappe.db.value_cache.pop(DT.SETTINGS, None)

        self.assertTrue(user_lookup_allowed())
        with self.as_user(USER_1):
            self.assertIn(USER_2, [user["email"] for user in get_users()])

    def test_user_lookup_can_be_turned_off(self):
        # an open-signup site turns the roster off; sharing then works by naming
        # an address rather than picking one, so the roster may hold only the caller
        frappe.db.set_single_value(DT.SETTINGS, "disable_user_lookup", 1)
        self.addCleanup(frappe.db.set_single_value, DT.SETTINGS, "disable_user_lookup", 0)

        with self.as_user(USER_1):
            self.assertEqual([user["email"] for user in get_users()], [USER_1])

        # an admin still manages users, so the roster stays whole for them
        with self.as_user(ADMIN):
            self.assertIn(USER_2, [user["email"] for user in get_users()])

    def test_workbook_owned_by_administrator_can_still_be_shared(self):
        # a template import leaves Administrator owning the workbook, and the
        # owner rides along on every share update the dialog sends back
        workbook = create_test_workbook("Administrator")

        update_share_permissions(
            workbook.name,
            [
                {"user": "Administrator", "read": 1, "write": 1},
                {"user": USER_1, "read": 1, "write": 0},
            ],
        )

        self.assert_visible_to(USER_1, DT.WORKBOOK, workbook.name)

    def test_workbook_cannot_be_shared_with_a_non_insights_user(self):
        workbook = create_test_workbook(USER_1)

        with self.as_user(USER_1):
            with self.assertRaisesRegex(frappe.ValidationError, "not an Insights user"):
                update_share_permissions(
                    workbook.name,
                    [{"user": NON_INSIGHTS_USER, "read": 1, "write": 0}],
                )

    def test_team_membership_is_listed_for_admins_only(self):
        self.set_team_permissions(True)

        with self.as_user(USER_1):
            self.assertNotIn("teams", get_users()[0])

        with self.as_user(ADMIN):
            self.assertIn("teams", get_users()[0])

    def test_permission_for_dashboard(self):
        workbook = create_test_workbook(USER_1)
        dashboard = create_test_dashboard(USER_1, workbook.name)

        self.assert_visible_to(USER_1, DT.DASHBOARD, dashboard.name)
        self.assert_not_visible_to(USER_2, DT.DASHBOARD, dashboard.name)

        with self.as_user(USER_1):
            update_dashboard_access(dashboard.name, [USER_2])
        self.assert_visible_to(USER_2, DT.DASHBOARD, dashboard.name)

        with self.as_user(USER_1):
            update_dashboard_access(dashboard.name, [])
        self.assert_not_visible_to(USER_2, DT.DASHBOARD, dashboard.name)

        with self.as_user(USER_1):
            update_share_permissions(
                workbook.name,
                [{"user": USER_2, "read": 1, "write": 0}],
            )

        self.assert_visible_to(USER_2, DT.DASHBOARD, dashboard.name)
        with self.as_user(USER_2):
            self.assertFalse(frappe.has_permission(DT.DASHBOARD, ptype="write", doc=dashboard.name))
            with self.assertRaises(frappe.PermissionError):
                create_test_dashboard(
                    USER_2,
                    workbook.name,
                    title="Permissions Test Dashboard Read Only",
                )

    def test_permission_for_chart(self):
        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name)
        chart = create_test_chart(USER_1, workbook.name, query.name)

        self.assert_visible_to(USER_1, DT.CHART, chart.name)
        self.assert_not_visible_to(USER_2, DT.CHART, chart.name)

        with self.as_user(USER_1):
            share_chart(chart.name, USER_2)
        self.assert_visible_to(USER_2, DT.CHART, chart.name)

        with self.as_user(USER_1):
            unshare_chart(chart.name, USER_2)
        self.assert_not_visible_to(USER_2, DT.CHART, chart.name)

        with self.as_user(USER_1):
            update_share_permissions(
                workbook.name,
                [{"user": USER_2, "read": 1, "write": 0}],
            )

        self.assert_visible_to(USER_2, DT.CHART, chart.name)
        with self.as_user(USER_2):
            self.assertFalse(frappe.has_permission(DT.CHART, ptype="write", doc=chart.name))
            with self.assertRaises(frappe.PermissionError):
                create_test_chart(
                    USER_2,
                    workbook.name,
                    query.name,
                    title="Permissions Test Chart Read Only",
                )

        with self.as_user(USER_1):
            update_share_permissions(workbook.name, [])
        self.assert_not_visible_to(USER_2, DT.CHART, chart.name)

        dashboard = create_test_dashboard(
            USER_1,
            workbook.name,
            chart.name,
            title="Permissions Test Dashboard For Chart",
        )
        with self.as_user(USER_1):
            update_dashboard_access(dashboard.name, [USER_2])
        self.assert_visible_to(USER_2, DT.CHART, chart.name)

    def test_permission_for_query(self):
        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name)

        self.assert_visible_to(USER_1, DT.QUERY, query.name)
        self.assert_not_visible_to(USER_2, DT.QUERY, query.name)

        with self.as_user(USER_1):
            update_share_permissions(
                workbook.name,
                [{"user": USER_2, "read": 1, "write": 0}],
            )

        self.assert_visible_to(USER_2, DT.QUERY, query.name)
        with self.as_user(USER_2):
            with self.assertRaises(frappe.PermissionError):
                create_test_query(
                    USER_2,
                    workbook.name,
                    title="Permissions Test Query Read Only",
                )

        with self.as_user(USER_1):
            update_share_permissions(workbook.name, [])
        self.assert_not_visible_to(USER_2, DT.QUERY, query.name)

        chart = create_test_chart(
            USER_1,
            workbook.name,
            query.name,
            title="Permissions Test Chart For Query",
        )
        chart = frappe.get_doc(DT.CHART, chart.name)

        self.assert_not_visible_to(USER_2, DT.QUERY, query.name)
        self.assert_not_visible_to(USER_2, DT.QUERY, chart.data_query)

        with self.as_user(USER_1):
            share_chart(chart.name, USER_2)

        self.assert_visible_to(USER_2, DT.QUERY, query.name)
        self.assert_visible_to(USER_2, DT.QUERY, chart.data_query)

        with self.as_user(USER_1):
            unshare_chart(chart.name, USER_2)

        self.assert_not_visible_to(USER_2, DT.QUERY, query.name)
        self.assert_not_visible_to(USER_2, DT.QUERY, chart.data_query)

        dashboard = create_test_dashboard(
            USER_1,
            workbook.name,
            chart.name,
            title="Permissions Test Dashboard For Query",
        )
        with self.as_user(USER_1):
            update_dashboard_access(dashboard.name, [USER_2])

        self.assert_visible_to(USER_2, DT.QUERY, query.name)
        self.assert_visible_to(USER_2, DT.QUERY, chart.data_query)

        with self.as_user(NON_INSIGHTS_USER):
            with self.assertRaises(frappe.PermissionError):
                create_test_query(
                    NON_INSIGHTS_USER,
                    workbook.name,
                    title="Permissions Test Query Non Insights",
                )

    def test_download_results_requires_export_permission(self):
        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name)
        self.set_team_permissions(False)
        frappe.db.set_single_value(DT.SETTINGS, "allow_download", 1)
        self.addCleanup(frappe.clear_cache, doctype=DT.QUERY)

        update_permission_property(DT.QUERY, "Insights User", 0, "export", 0)
        frappe.clear_cache(doctype=DT.QUERY)

        with self.as_user(USER_1):
            query_doc = frappe.get_doc(DT.QUERY, query.name)
            with self.assertRaisesRegex(frappe.PermissionError, "export permission"):
                query_doc.download_results(format="csv")

        update_permission_property(DT.QUERY, "Insights User", 0, "export", 1)
        frappe.clear_cache(doctype=DT.QUERY)

        with self.as_user(USER_1):
            query_doc = frappe.get_doc(DT.QUERY, query.name)
            with db_connections():
                csv_data = query_doc.download_results(format="csv")
            self.assertIsInstance(csv_data, str)

    def test_download_results_requires_document_access(self):
        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name)
        frappe.db.set_single_value(DT.SETTINGS, "allow_download", 1)
        self.set_team_permissions(True)

        # USER_2 has the role-level export permission, but no access to
        # USER_1's workbook or query, so the download must still be blocked
        with self.as_user(USER_2):
            self.assertTrue(frappe.has_permission(DT.QUERY, ptype="export"))
            query_doc = frappe.get_doc(DT.QUERY, query.name)
            with self.assertRaises(frappe.PermissionError):
                query_doc.download_results(format="csv")

        # the owner can still download their own query
        self.set_team_permissions(False)
        with self.as_user(USER_1):
            query_doc = frappe.get_doc(DT.QUERY, query.name)
            with db_connections():
                csv_data = query_doc.download_results(format="csv")
            self.assertIsInstance(csv_data, str)

    def test_download_results_allowed_with_read_only_share(self):
        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name)
        # keep team permissions disabled so the underlying table stays
        # accessible; the owner/share based document restriction on
        # workbooks & queries is enforced regardless of this setting
        self.set_team_permissions(False)
        frappe.db.set_single_value(DT.SETTINGS, "allow_download", 1)

        # USER_2 is given read-only access to USER_1's workbook
        with self.as_user(USER_1):
            update_share_permissions(
                workbook.name,
                [{"user": USER_2, "read": 1, "write": 0}],
            )

        # USER_2 has the role-level export permission and read access to the
        # shared query, so the download must succeed without write access
        with self.as_user(USER_2):
            self.assertTrue(frappe.has_permission(DT.QUERY, ptype="export"))
            self.assertFalse(frappe.has_permission(DT.QUERY, ptype="write", doc=query.name))
            query_doc = frappe.get_doc(DT.QUERY, query.name)
            with db_connections():
                csv_data = query_doc.download_results(format="csv")
            self.assertIsInstance(csv_data, str)

    def test_download_results_blocked_when_globally_disabled(self):
        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name)
        self.set_team_permissions(False)
        frappe.db.set_single_value(DT.SETTINGS, "allow_download", 0)

        # USER_1 has the export permission via the Insights User role,
        # but the global toggle must still block the download
        with self.as_user(USER_1):
            self.assertTrue(frappe.has_permission(DT.QUERY, ptype="export"))
            query_doc = frappe.get_doc(DT.QUERY, query.name)
            with self.assertRaisesRegex(frappe.PermissionError, "not allowed to download"):
                query_doc.download_results(format="csv")
