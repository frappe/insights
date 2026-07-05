import frappe
from frappe.permissions import update_permission_property

from insights.api.workbooks import get_share_permissions, update_share_permissions
from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
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
    cleanup_test_fixtures,
    clear_team_cache,
    create_test_data_sources,
    create_test_tables,
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

    def toggle_team_permissions(self, enable):
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", enable)
        clear_team_cache()

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
        self.toggle_team_permissions(False)

        self.assert_visible_to(USER_2, DT.DATA_SOURCE, TEST_DS)
        self.assert_visible_to(USER_2, DT.TABLE, TEST_TABLE1)

    def test_permission_on_team_based_doctype_with_team_permissions_enabled(self):
        create_test_data_sources()
        create_test_tables()
        team = create_test_teams()
        self.toggle_team_permissions(True)

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

    def test_permission_for_admin_on_team_based_doctype_with_team_permissions_enabled(
        self,
    ):
        create_test_data_sources()
        create_test_tables()
        self.toggle_team_permissions(True)

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
        self.toggle_team_permissions(False)
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
        self.toggle_team_permissions(True)

        # USER_2 has the role-level export permission, but no access to
        # USER_1's workbook or query, so the download must still be blocked
        with self.as_user(USER_2):
            self.assertTrue(frappe.has_permission(DT.QUERY, ptype="export"))
            query_doc = frappe.get_doc(DT.QUERY, query.name)
            with self.assertRaises(frappe.PermissionError):
                query_doc.download_results(format="csv")

        # the owner can still download their own query
        self.toggle_team_permissions(False)
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
        self.toggle_team_permissions(False)
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
        self.toggle_team_permissions(False)
        frappe.db.set_single_value(DT.SETTINGS, "allow_download", 0)

        # USER_1 has the export permission via the Insights User role,
        # but the global toggle must still block the download
        with self.as_user(USER_1):
            self.assertTrue(frappe.has_permission(DT.QUERY, ptype="export"))
            query_doc = frappe.get_doc(DT.QUERY, query.name)
            with self.assertRaisesRegex(frappe.PermissionError, "not allowed to download"):
                query_doc.download_results(format="csv")
