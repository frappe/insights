import frappe

from insights.insights.doctype.insights_team.insights_team import clear_cache as clear_team_cache
from insights.resolver import (
    CHART,
    DASHBOARD,
    ContentNotAvailableError,
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

SHIPPED_ID = "resolver_test_app/monthly_sales"


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

    def ship(self, doctype, name, logical_id=SHIPPED_ID, is_standard=1):
        doc = frappe.get_doc(doctype, name)
        doc.db_set("logical_id", logical_id, update_modified=False)
        doc.db_set("is_standard", is_standard, update_modified=False)
        return doc

    def test_dashboard_resolves_by_docname_slug_and_logical_id(self):
        dashboard = self.make_dashboard(title="Resolver Test Docname Form")
        self.ship(DT.DASHBOARD, dashboard.name)

        self.assertEqual(resolve(DASHBOARD, dashboard.name), dashboard.name)
        self.assertEqual(resolve(DASHBOARD, "resolver-test-docname-form"), dashboard.name)
        self.assertEqual(resolve(DASHBOARD, SHIPPED_ID), dashboard.name)

    def test_chart_resolves_by_docname_and_logical_id_only(self):
        chart = self.make_chart()
        self.ship(DT.CHART, chart.name)

        self.assertEqual(resolve(CHART, chart.name), chart.name)
        self.assertEqual(resolve(CHART, SHIPPED_ID), chart.name)
        # charts carry no slug, so a slug-shaped reference resolves to nothing
        self.assertIsNone(resolve(CHART, "resolver-test-chart"))

    def test_blank_reference_and_unsupported_doctype(self):
        self.assertIsNone(resolve(DASHBOARD, ""))
        self.assertIsNone(resolve(DASHBOARD, None))
        with self.assertRaises(ValueError):
            resolve(DT.QUERY, "anything")

    def test_unknown_reference_and_denied_read_give_the_same_answer(self):
        dashboard = self.make_dashboard(title="Resolver Test Denied Dashboard")
        self.ship(DT.DASHBOARD, dashboard.name)

        with self.as_user(USER_2):
            self.assertFalse(frappe.has_permission(DT.DASHBOARD, ptype="read", doc=dashboard.name))

            errors = []
            for reference in (
                dashboard.name,  # exists, not readable by USER_2
                SHIPPED_ID,  # same document, by its logical id
                "resolver-test-denied-dashboard",  # same document, by its slug
                "resolver_test_app/no_such_thing",  # no such logical id
                "no-such-slug",  # no such slug
                frappe.generate_hash(length=10),  # no such docname
            ):
                with self.assertRaises(ContentNotAvailableError) as raised:
                    resolve_for_read(DASHBOARD, reference)
                errors.append(raised.exception)

            self.assertEqual({type(error) for error in errors}, {ContentNotAvailableError})
            self.assertEqual(len({str(error) for error in errors}), 1)

        # the collapse is the read helper's job — a plain resolve still answers,
        # so server-side callers that already hold access are not blinded
        with self.as_user(USER_2):
            self.assertEqual(resolve(DASHBOARD, dashboard.name), dashboard.name)

    def test_denied_read_is_a_permission_error(self):
        dashboard = self.make_dashboard(title="Resolver Test Error Shape")

        with self.as_user(USER_2), self.assertRaises(frappe.PermissionError):
            resolve_for_read(DASHBOARD, dashboard.name)

    def test_permitted_read_returns_the_document_name(self):
        dashboard = self.make_dashboard(title="Resolver Test Permitted Read")

        with self.as_user(USER_1):
            self.assertEqual(resolve_for_read(DASHBOARD, dashboard.name), dashboard.name)
            self.assertEqual(resolve_for_read(DASHBOARD, "resolver-test-permitted-read"), dashboard.name)

    def test_user_copy_is_never_returned_for_a_shipped_id(self):
        shipped = self.make_dashboard(title="Resolver Test Shipped Dashboard")
        self.ship(DT.DASHBOARD, shipped.name)

        copy = self.make_dashboard(title="Resolver Test Copy Of Shipped")
        self.ship(DT.DASHBOARD, copy.name, is_standard=0)

        self.assertEqual(resolve(DASHBOARD, SHIPPED_ID), shipped.name)
        # the copy keeps its own identity
        self.assertEqual(resolve(DASHBOARD, copy.name), copy.name)

        # with the standard document gone, the id resolves to nothing at all
        frappe.delete_doc(DT.DASHBOARD, shipped.name, force=True, ignore_permissions=True)
        self.assertIsNone(resolve(DASHBOARD, SHIPPED_ID))

    def test_slug_is_generated_from_the_title(self):
        dashboard = self.make_dashboard(title="Resolver Test: Quarterly Sales!")
        self.assertEqual(dashboard.slug, "resolver-test-quarterly-sales")

    def test_slug_is_unique(self):
        first = self.make_dashboard(title="Resolver Test Same Title")
        second = self.make_dashboard(title="Resolver Test Same Title")

        self.assertEqual(first.slug, "resolver-test-same-title")
        self.assertEqual(second.slug, "resolver-test-same-title-1")
        self.assertEqual(resolve(DASHBOARD, second.slug), second.name)

    def test_manual_slug_survives_a_rename(self):
        dashboard = self.make_dashboard(title="Resolver Test Renamed Dashboard")
        dashboard.slug = "Sales Overview"
        dashboard.save(ignore_permissions=True)
        self.assertEqual(dashboard.slug, "sales-overview")

        dashboard.title = "Resolver Test Dashboard With A New Title"
        dashboard.save(ignore_permissions=True)
        self.assertEqual(dashboard.slug, "sales-overview")
        self.assertEqual(resolve(DASHBOARD, "sales-overview"), dashboard.name)

    def test_manual_slug_stays_unique(self):
        taken = self.make_dashboard(title="Resolver Test Taken Slug")
        other = self.make_dashboard(title="Resolver Test Other Dashboard")

        other.slug = taken.slug
        other.save(ignore_permissions=True)
        self.assertEqual(other.slug, f"{taken.slug}-1")
        self.assertEqual(resolve(DASHBOARD, taken.slug), taken.name)

    def test_clearing_the_slug_regenerates_it(self):
        dashboard = self.make_dashboard(title="Resolver Test Cleared Slug")
        dashboard.slug = ""
        dashboard.save(ignore_permissions=True)
        self.assertEqual(dashboard.slug, "resolver-test-cleared-slug")
