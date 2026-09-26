import frappe

from insights.insights.doctype.insights_team.insights_team import clear_cache as clear_team_cache
from insights.resolver import (
    CHART,
    DASHBOARD,
    resolve,
    resolve_for_read,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
)
from insights.tests.permissions_utils import (
    USER_1,
    USER_2,
    cleanup_test_fixtures,
    create_test_users,
)


class TestInsightsResolver(InsightsIntegrationTestCase):
    SAVEPOINT = "test_insights_resolver"

    @classmethod
    def before_class(cls):
        cleanup_test_fixtures()
        create_test_users()
        clear_team_cache()

    @classmethod
    def after_class(cls):
        clear_team_cache()
        cleanup_test_fixtures()

    def make_dashboard(self, title="Resolver Test Dashboard", chart=None):
        workbook = create_test_workbook(USER_1)
        return create_test_dashboard(USER_1, workbook.name, chart=chart, title=title)

    def make_chart(self):
        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name)
        return create_test_chart(USER_1, workbook.name, query.name)

    # @feature shared.reference
    def test_dashboard_resolves_by_docname_and_route(self):
        dashboard = self.make_dashboard(title="Resolver Test Docname Form")

        self.assertEqual(resolve(DASHBOARD, dashboard.name), dashboard.name)
        self.assertEqual(resolve(DASHBOARD, "resolver-test-docname-form"), dashboard.name)

    # @feature shared.reference
    def test_chart_resolves_by_docname_only(self):
        chart = self.make_chart()

        self.assertEqual(resolve(CHART, chart.name), chart.name)
        self.assertIsNone(resolve(CHART, "resolver-test-chart"))

    # @feature shared.old-name-resolves
    def test_a_v2_name_resolves_to_the_document_that_keeps_it_as_its_old_name(self):
        dashboard = self.make_dashboard(title="Resolver Test Old Name")
        chart = self.make_chart()
        frappe.db.set_value(DT.DASHBOARD, dashboard.name, "old_name", "old-dashboard", update_modified=False)
        frappe.db.set_value(DT.CHART, chart.name, "old_name", "old-chart", update_modified=False)

        self.assertEqual(resolve(DASHBOARD, "old-dashboard"), dashboard.name)
        self.assertEqual(resolve(CHART, "old-chart"), chart.name)

    # @feature shared.reference
    def test_blank_reference_and_unsupported_doctype(self):
        self.assertIsNone(resolve(DASHBOARD, ""))
        self.assertIsNone(resolve(DASHBOARD, None))
        with self.assertRaises(ValueError):
            resolve(DT.QUERY, "anything")

    # @feature permissions.denied-is-not-found
    def test_unknown_reference_and_denied_read_give_the_same_answer(self):
        dashboard = self.make_dashboard(title="Resolver Test Denied Dashboard")

        with self.as_user(USER_2):
            self.assertFalse(frappe.has_permission(DT.DASHBOARD, ptype="read", doc=dashboard.name))

            errors = []
            for reference in (
                dashboard.name,  # exists, not readable by USER_2
                "resolver-test-denied-dashboard",  # same document, by its route
                "no-such-route",
                frappe.generate_hash(length=10),  # no such docname
            ):
                with self.assertRaises(frappe.DoesNotExistError) as raised:
                    resolve_for_read(DASHBOARD, reference)
                errors.append(raised.exception)

            self.assertEqual({type(error) for error in errors}, {frappe.DoesNotExistError})
            self.assertEqual(len({str(error) for error in errors}), 1)

        # Only resolve_for_read hides a denied document. Plain resolve still
        # returns the name, for server code that has already checked access.
        with self.as_user(USER_2):
            self.assertEqual(resolve(DASHBOARD, dashboard.name), dashboard.name)

    # @feature permissions.denied-is-not-found
    def test_denied_read_answers_not_found(self):
        dashboard = self.make_dashboard(title="Resolver Test Error Shape")

        with self.as_user(USER_2), self.assertRaises(frappe.DoesNotExistError):
            resolve_for_read(DASHBOARD, dashboard.name)

    # @feature permissions.denied-is-not-found
    def test_a_user_permission_narrows_the_view_too(self):
        """`get_doc`, `can_write` and the list query all apply User Permissions.
        The view must apply them too, or it shows what the rest of the site
        refuses."""
        dashboard = self.make_dashboard(title="Resolver Test User Permission")
        other = self.make_dashboard(title="Resolver Test User Permission Allowed")
        for doc in (dashboard, other):
            frappe.db.set_value(DT.DASHBOARD, doc.name, "visibility", "Everyone", update_modified=False)

        with self.as_user(USER_2):
            self.assertEqual(resolve_for_read(DASHBOARD, dashboard.name), dashboard.name)

        permission = frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": USER_2,
                "allow": DT.DASHBOARD,
                "for_value": other.name,
            }
        ).insert(ignore_permissions=True)
        self.addCleanup(
            frappe.delete_doc, "User Permission", permission.name, force=True, ignore_permissions=True
        )

        with self.as_user(USER_2):
            self.assertFalse(frappe.has_permission(DT.DASHBOARD, ptype="read", doc=dashboard.name))
            with self.assertRaises(frappe.DoesNotExistError):
                resolve_for_read(DASHBOARD, dashboard.name)
            self.assertEqual(resolve_for_read(DASHBOARD, other.name), other.name)

    # @feature shared.reference
    def test_permitted_read_returns_the_document_name(self):
        dashboard = self.make_dashboard(title="Resolver Test Permitted Read")

        with self.as_user(USER_1):
            self.assertEqual(resolve_for_read(DASHBOARD, dashboard.name), dashboard.name)
            self.assertEqual(resolve_for_read(DASHBOARD, "resolver-test-permitted-read"), dashboard.name)

    # @feature dashboard.route
    def test_route_is_generated_from_the_title(self):
        dashboard = self.make_dashboard(title="Resolver Test: Quarterly Sales!")
        self.assertEqual(dashboard.route, "resolver-test-quarterly-sales")

    # @feature dashboard.route
    def test_route_is_unique(self):
        first = self.make_dashboard(title="Resolver Test Same Title")
        second = self.make_dashboard(title="Resolver Test Same Title")

        self.assertEqual(first.route, "resolver-test-same-title")
        self.assertEqual(second.route, "resolver-test-same-title-1")
        self.assertEqual(resolve(DASHBOARD, second.route), second.name)

    # @feature dashboard.route
    def test_a_manual_route_survives_a_new_title(self):
        dashboard = self.make_dashboard(title="Resolver Test Renamed Dashboard")
        dashboard.route = "Sales Overview"
        dashboard.save(ignore_permissions=True)
        self.assertEqual(dashboard.route, "sales-overview")

        dashboard.title = "Resolver Test Dashboard With A New Title"
        dashboard.save(ignore_permissions=True)
        self.assertEqual(dashboard.route, "sales-overview")
        self.assertEqual(resolve(DASHBOARD, "sales-overview"), dashboard.name)

    # @feature dashboard.route
    def test_a_manual_route_stays_unique(self):
        taken = self.make_dashboard(title="Resolver Test Taken Route")
        other = self.make_dashboard(title="Resolver Test Other Dashboard")

        other.route = taken.route
        other.save(ignore_permissions=True)
        self.assertEqual(other.route, f"{taken.route}-1")
        self.assertEqual(resolve(DASHBOARD, taken.route), taken.name)

    # @feature dashboard.route
    def test_a_route_is_unique_against_docnames_too(self):
        """A standard workbook renames its members to readable slugs, so routes
        and docnames share one namespace. A reference resolves by docname first,
        so a new route equal to a docname opens the wrong dashboard."""
        shipped = self.make_dashboard(title="Resolver Test Shipped Board")
        frappe.rename_doc(DT.DASHBOARD, shipped.name, "resolver-test-site-board", force=True)

        site = self.make_dashboard(title="Resolver Test Site Board")

        self.assertNotEqual(site.route, "resolver-test-site-board")
        self.assertEqual(resolve(DASHBOARD, "resolver-test-site-board"), "resolver-test-site-board")
        self.assertEqual(resolve(DASHBOARD, site.route), site.name)

    # @feature dashboard.route
    def test_clearing_the_route_regenerates_it(self):
        dashboard = self.make_dashboard(title="Resolver Test Cleared Route")
        dashboard.route = ""
        dashboard.save(ignore_permissions=True)
        self.assertEqual(dashboard.route, "resolver-test-cleared-route")
