import frappe

from insights.permissions import (
    VISIBILITY_LEVELS,
    get_permission_query_conditions,
    has_doc_permission,
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
    delete_workbooks,
)

VISIBILITY_ROLE = "Insights Visibility Test Role"

OWNER = "visibility_owner@test.com"
# holds an Insights role, but the owner's content never names them
INSIGHTS_PEER = "visibility_peer@test.com"
# holds VISIBILITY_ROLE and nothing else - the desk-report persona
ROLE_HOLDER = "visibility_role_holder@test.com"
# holds no role at all - proves the viewing path never asks for `Insights User`
DESK_USER = "visibility_desk_user@test.com"
GUEST = "Guest"

WORKBOOK_TITLE = "Visibility Test Workbook"


def create_visibility_users():
    if not frappe.db.exists("Role", VISIBILITY_ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": VISIBILITY_ROLE}).insert(ignore_permissions=True)

    create_user(OWNER, first_name="Visibility", last_name="Owner", roles="Insights User")
    create_user(INSIGHTS_PEER, first_name="Visibility", last_name="Peer", roles="Insights User")
    create_user(ROLE_HOLDER, first_name="Visibility", last_name="Role Holder", roles=VISIBILITY_ROLE)
    create_user(DESK_USER, first_name="Visibility", last_name="Desk User")


def cleanup_visibility_fixtures():
    delete_workbooks(owners=[OWNER])
    delete_users(OWNER, INSIGHTS_PEER, ROLE_HOLDER, DESK_USER)
    if frappe.db.exists("Role", VISIBILITY_ROLE):
        frappe.delete_doc("Role", VISIBILITY_ROLE, force=True)


class TestVisibility(InsightsIntegrationTestCase):
    SAVEPOINT = "test_visibility"

    @classmethod
    def before_class(cls):
        cls.original_enable_permissions = frappe.db.get_single_value(DT.SETTINGS, "enable_permissions")
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 0)
        cleanup_visibility_fixtures()
        create_visibility_users()

    @classmethod
    def after_class(cls):
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", cls.original_enable_permissions)
        cleanup_visibility_fixtures()

    # fixtures

    def make_content(self, link_chart_to_dashboard=False):
        workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE)
        query = create_test_query(OWNER, workbook.name, title="Visibility Test Query")
        chart = create_test_chart(OWNER, workbook.name, query.name, title="Visibility Test Chart")
        dashboard = create_test_dashboard(
            OWNER,
            workbook.name,
            chart.name if link_chart_to_dashboard else None,
            title="Visibility Test Dashboard",
        )
        return chart, dashboard

    def declare(self, doc, visibility, roles=None):
        doc.visibility = visibility
        doc.set("visible_to_roles", [{"role": role} for role in roles or []])
        doc.save(ignore_permissions=True)
        return frappe.get_doc(doc.doctype, doc.name)

    # assertions
    #
    # The visibility levels are read through the controller, the same entry point
    # `frappe.has_permission` calls. A user with no Insights role does not clear
    # the doctype level role check, so the doctype must also grant `read` to
    # `All` and `Guest` for visibility to answer on the desk surface.

    def assert_can_read(self, user, doc):
        self.assertTrue(
            bool(has_doc_permission(doc, "read", user)),
            f"{doc.doctype} {doc.name} ({doc.visibility}) should be readable by {user}",
        )
        self.assertTrue(
            self.is_listed(user, doc.doctype, doc.name),
            f"{doc.doctype} {doc.name} ({doc.visibility}) should be listed for {user}",
        )

    def assert_cannot_read(self, user, doc):
        self.assertFalse(
            bool(has_doc_permission(doc, "read", user)),
            f"{doc.doctype} {doc.name} ({doc.visibility}) should not be readable by {user}",
        )
        self.assertFalse(
            self.is_listed(user, doc.doctype, doc.name),
            f"{doc.doctype} {doc.name} ({doc.visibility}) should not be listed for {user}",
        )

    def is_listed(self, user, doctype, name):
        """Whether the list conditions alone admit this document for this user.

        `is_visible` in `factories` goes through `get_list`, which also applies
        the doctype role check. A desk user here holds no Insights role, so the
        conditions have to be read on their own.
        """
        condition = get_permission_query_conditions(user, doctype)
        self.assertTrue(condition, f"{doctype} list access should stay narrowed for {user}")
        return bool(
            frappe.db.sql(
                f"select name from `tab{doctype}` where name = %s and {condition}",  # nosemgrep
                name,
            )
        )

    # the levels, one by one

    # @feature permissions.visibility
    def test_private_admits_the_owner_only(self):
        for doc in self.make_content():
            doc = self.declare(doc, "Private")
            self.assert_can_read(OWNER, doc)
            for user in (INSIGHTS_PEER, ROLE_HOLDER, DESK_USER, GUEST):
                self.assert_cannot_read(user, doc)

    # @feature permissions.visibility
    def test_private_still_admits_a_docshare(self):
        for doc in self.make_content():
            doc = self.declare(doc, "Private")
            self.assert_cannot_read(INSIGHTS_PEER, doc)

            frappe.share.add(doc.doctype, doc.name, user=INSIGHTS_PEER, read=1, notify=0)
            self.assert_can_read(INSIGHTS_PEER, doc)
            self.assert_cannot_read(DESK_USER, doc)

    # @feature permissions.visibility
    def test_an_org_wide_share_admits_nobody(self):
        """`Everyone` is the one mechanism, so a DocShare has to name a person."""
        for doc in self.make_content():
            doc = self.declare(doc, "Private")
            frappe.share.add(doc.doctype, doc.name, everyone=1, read=1, notify=0)
            for user in (INSIGHTS_PEER, ROLE_HOLDER, DESK_USER, GUEST):
                self.assert_cannot_read(user, doc)

    # @feature permissions.share-dashboard
    def test_saving_a_dashboard_share_writes_no_org_wide_row(self):
        _, dashboard = self.make_content()
        with self.as_user(OWNER):
            frappe.get_doc(DT.DASHBOARD, dashboard.name).update_access(
                {"people_with_access": [INSIGHTS_PEER]}
            )

        shares = frappe.get_all(
            "DocShare",
            filters={"share_doctype": DT.DASHBOARD, "share_name": dashboard.name},
            fields=["user", "everyone"],
        )
        self.assertEqual(shares, [{"user": INSIGHTS_PEER, "everyone": 0}])

    # @feature permissions.visibility
    def test_roles_admits_the_named_roles_only(self):
        for doc in self.make_content():
            doc = self.declare(doc, "Roles", roles=[VISIBILITY_ROLE])
            self.assert_can_read(ROLE_HOLDER, doc)
            for user in (INSIGHTS_PEER, DESK_USER, GUEST):
                self.assert_cannot_read(user, doc)

    # @feature permissions.visibility
    def test_everyone_admits_any_logged_in_user(self):
        for doc in self.make_content():
            doc = self.declare(doc, "Everyone")
            for user in (INSIGHTS_PEER, ROLE_HOLDER, DESK_USER):
                self.assert_can_read(user, doc)
            self.assert_cannot_read(GUEST, doc)

    # @feature permissions.visibility shared.dashboard-link shared.chart-link
    def test_public_admits_guests(self):
        for doc in self.make_content():
            doc = self.declare(doc, "Public")
            for user in (INSIGHTS_PEER, ROLE_HOLDER, DESK_USER, GUEST):
                self.assert_can_read(user, doc)

    # @feature permissions.visibility permissions.non-insights-user
    def test_no_level_consults_the_insights_user_role(self):
        # DESK_USER holds no role, so an `Everyone` read proves the viewing
        # path never asks for `Insights User`
        self.assertNotIn("Insights User", frappe.get_roles(DESK_USER))
        for doc in self.make_content():
            self.assert_can_read(DESK_USER, self.declare(doc, "Everyone"))

    # visibility is view only

    # @feature permissions.visibility
    def test_visibility_grants_read_and_nothing_else(self):
        for visibility in ("Roles", "Everyone", "Public"):
            for doc in self.make_content():
                doc = self.declare(doc, visibility, roles=[VISIBILITY_ROLE])
                for user in (ROLE_HOLDER, DESK_USER, GUEST):
                    for ptype in ("write", "share", "delete"):
                        self.assertFalse(
                            bool(has_doc_permission(doc, ptype, user)),
                            f"{visibility} should not grant {ptype} to {user}",
                        )

    # widening the visibility

    def make_writable_by_peer(self, doc):
        """A peer who may edit the document but was never given `share`."""
        doc = self.declare(doc, "Private")
        frappe.share.add(doc.doctype, doc.name, user=INSIGHTS_PEER, read=1, write=1, notify=0)
        return doc

    def set_visibility(self, user, doc, visibility):
        with self.as_user(user):
            writable = frappe.get_doc(doc.doctype, doc.name)
            writable.visibility = visibility
            writable.save()

    # @feature shared.publish-needs-share
    def test_widening_visibility_needs_share_access(self):
        """Write must not imply publish: `visibility` is an ordinary field."""
        for doc in self.make_content():
            doc = self.make_writable_by_peer(doc)
            self.assertTrue(has_doc_permission(doc, "write", INSIGHTS_PEER))

            with self.assertRaises(frappe.PermissionError):
                self.set_visibility(INSIGHTS_PEER, doc, "Public")

            self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "visibility"), "Private")

    # @feature shared.publish-needs-share
    def test_every_widening_step_needs_share_access(self):
        """The rule is the move up, not the widest level."""
        for doc in self.make_content():
            doc = self.make_writable_by_peer(doc)
            for visibility in ("Roles", "Everyone", "Public"):
                with self.assertRaises(frappe.PermissionError):
                    self.set_visibility(INSIGHTS_PEER, doc, visibility)

    # @feature shared.publish-needs-share
    def test_narrowing_visibility_is_a_plain_write(self):
        """Coming back down takes nothing away from anybody."""
        for doc in self.make_content():
            doc = self.declare(doc, "Public")
            frappe.share.add(doc.doctype, doc.name, user=INSIGHTS_PEER, read=1, write=1, notify=0)

            self.set_visibility(INSIGHTS_PEER, doc, "Private")
            self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "visibility"), "Private")

    # @feature shared.publish-needs-share
    def test_an_owner_publishes_their_own(self):
        """Ownership carries `share`, so the owner is not stopped."""
        for doc in self.make_content():
            doc = self.declare(doc, "Private")
            self.set_visibility(OWNER, doc, "Public")
            self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "visibility"), "Public")

    # a linked chart

    # @feature permissions.chart-access-follows
    def test_chart_inherits_the_dashboard_visibility_downward_only(self):
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        chart = self.declare(chart, "Private")
        dashboard = self.declare(dashboard, "Everyone")

        self.assert_can_read(DESK_USER, dashboard)
        self.assert_can_read(DESK_USER, chart)

        # a chart's own visibility never reaches up to the dashboard
        dashboard = self.declare(dashboard, "Private")
        chart = self.declare(chart, "Everyone")

        self.assert_can_read(DESK_USER, chart)
        self.assert_cannot_read(DESK_USER, dashboard)

    # @feature shared.chart-on-public-dashboard shared.revoke
    def test_a_public_dashboard_admits_a_guest_to_its_charts(self):
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.declare(chart, "Private")
        dashboard = self.declare(dashboard, "Public")

        self.assert_can_read(GUEST, dashboard)
        self.assert_can_read(GUEST, frappe.get_doc(chart.doctype, chart.name))

        dashboard = self.declare(dashboard, "Everyone")
        self.assert_cannot_read(GUEST, dashboard)
        self.assert_cannot_read(GUEST, frappe.get_doc(chart.doctype, chart.name))

    # the Public level means the owner's permissions

    # @feature shared.rows-are-the-owners
    def test_publishing_a_chart_unchecks_apply_user_permissions(self):
        chart, _ = self.make_content()
        self.assertTrue(chart.apply_user_permissions)

        chart = self.declare(chart, "Public")
        self.assertFalse(chart.apply_user_permissions)

        # narrowing leaves the box where publishing put it
        chart = self.declare(chart, "Private")
        self.assertFalse(chart.apply_user_permissions)

    # @feature shared.rows-are-the-owners
    def test_a_public_chart_cannot_apply_each_users_permissions(self):
        chart, _ = self.make_content()
        chart = self.declare(chart, "Public")

        chart.apply_user_permissions = 1
        with self.assertRaises(frappe.ValidationError):
            chart.save(ignore_permissions=True)

    # @feature shared.chart-on-public-dashboard
    def test_publishing_a_dashboard_unchecks_the_box_on_its_charts(self):
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.declare(chart, "Private")

        self.declare(dashboard, "Public")
        self.assertFalse(frappe.db.get_value(chart.doctype, chart.name, "apply_user_permissions"))

    # @feature shared.chart-on-public-dashboard
    def test_a_linked_chart_cannot_apply_each_users_permissions(self):
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.declare(dashboard, "Public")

        chart = frappe.get_doc(chart.doctype, chart.name)
        chart.apply_user_permissions = 1
        with self.assertRaises(frappe.ValidationError):
            chart.save(ignore_permissions=True)

    # the seam

    # @feature permissions.visibility
    def test_visibility_answers_through_frappe_has_permission(self):
        for doc in self.make_content():
            doc = self.declare(doc, "Private")
            with self.as_user(INSIGHTS_PEER):
                self.assertFalse(frappe.has_permission(doc.doctype, ptype="read", doc=doc.name))

            doc = self.declare(doc, "Everyone")
            with self.as_user(INSIGHTS_PEER):
                self.assertTrue(frappe.has_permission(doc.doctype, ptype="read", doc=doc.name))
                self.assertFalse(frappe.has_permission(doc.doctype, ptype="write", doc=doc.name))

    # @feature permissions.visibility
    def test_declared_levels_match_the_schema(self):
        for doctype in (DT.CHART, DT.DASHBOARD):
            options = frappe.get_meta(doctype).get_field("visibility").options.split("\n")
            self.assertEqual(options, VISIBILITY_LEVELS)
