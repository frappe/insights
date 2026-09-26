from unittest.mock import patch

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
# has an Insights role, but no grant on the owner's content
INSIGHTS_PEER = "visibility_peer@test.com"
# has only VISIBILITY_ROLE, like a desk user who reads reports
ROLE_HOLDER = "visibility_role_holder@test.com"
# has no role, to prove that reading never needs `Insights User`
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

    # These call the controller's `has_doc_permission`, as `frappe.has_permission`
    # does. A user with no Insights role fails the doctype's role check, so the
    # doctype also grants `read` to `All` and `Guest`. Without it, visibility has
    # no effect on desk.

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
        """Whether the list query conditions alone include this document.

        `factories.is_visible` uses `get_list`, which also applies the doctype
        role check. A desk user here has no Insights role, so this reads the
        conditions directly.
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
    def test_private_allows_the_owner_only(self):
        for doc in self.make_content():
            doc = self.declare(doc, "Private")
            self.assert_can_read(OWNER, doc)
            for user in (INSIGHTS_PEER, ROLE_HOLDER, DESK_USER, GUEST):
                self.assert_cannot_read(user, doc)

    # @feature permissions.visibility
    def test_private_still_allows_a_docshare(self):
        for doc in self.make_content():
            doc = self.declare(doc, "Private")
            self.assert_cannot_read(INSIGHTS_PEER, doc)

            frappe.share.add(doc.doctype, doc.name, user=INSIGHTS_PEER, read=1, notify=0)
            self.assert_can_read(INSIGHTS_PEER, doc)
            self.assert_cannot_read(DESK_USER, doc)

    # @feature permissions.visibility
    def test_an_org_wide_share_allows_nobody(self):
        """`Everyone` is the only way to allow every user, so a DocShare must
        name a person. `frappe.share.add` refuses an org-wide share, and the
        permission check ignores an older one."""
        for doc in self.make_content():
            doc = self.declare(doc, "Private")
            with self.assertRaises(frappe.ValidationError):
                frappe.share.add(doc.doctype, doc.name, everyone=1, read=1, notify=0)
            frappe.get_doc(
                {
                    "doctype": "DocShare",
                    "share_doctype": doc.doctype,
                    "share_name": doc.name,
                    "everyone": 1,
                    "read": 1,
                }
            ).db_insert()
            for user in (INSIGHTS_PEER, ROLE_HOLDER, DESK_USER, GUEST):
                self.assert_cannot_read(user, doc)

    # @feature permissions.share-workbook-org
    def test_a_workbook_open_to_the_organization_allows_no_guest(self):
        """An org-wide share allows every signed-in user, and a guest is not signed in."""
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.declare(chart, "Private")
        self.declare(dashboard, "Private")

        frappe.share.add(DT.WORKBOOK, chart.workbook, everyone=1, read=1, notify=0)

        for doc in (chart, dashboard):
            stored = frappe.get_doc(doc.doctype, doc.name)
            self.assert_can_read(INSIGHTS_PEER, stored)
            self.assert_cannot_read(GUEST, stored)

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

    # @feature permissions.share-dashboard
    def test_a_dashboard_is_shared_with_insights_users_only(self):
        """A dashboard's DocShare also lets the user read its charts, their rows
        and their files. So a dashboard share checks for an Insights user, as a
        workbook share does."""
        _, dashboard = self.make_content()

        with self.as_user(OWNER), self.assertRaises(frappe.ValidationError):
            frappe.get_doc(DT.DASHBOARD, dashboard.name).update_access({"people_with_access": [DESK_USER]})

    # @feature permissions.share-dashboard
    def test_a_share_the_dashboard_already_holds_is_kept_when_sent_back(self):
        """`DashboardShareDialog` loads its list from `get_people_with_access` and
        sends the whole list back on Done. So an older share, or one with a user
        who has since left Insights, comes back each time. Keeping it gives
        nobody new access."""
        _, dashboard = self.make_content()
        frappe.share.add(DT.DASHBOARD, dashboard.name, user=DESK_USER, read=1, notify=0)

        with self.as_user(OWNER):
            board = frappe.get_doc(DT.DASHBOARD, dashboard.name)
            echoed = [person.email for person in board.get_people_with_access()]
            board.update_access({"people_with_access": [*echoed, INSIGHTS_PEER]})

        shared = frappe.get_all(
            "DocShare",
            filters={"share_doctype": DT.DASHBOARD, "share_name": dashboard.name},
            pluck="user",
        )
        self.assertEqual(sorted(shared), sorted([DESK_USER, INSIGHTS_PEER]))

    # @feature permissions.visibility
    def test_roles_allows_the_named_roles_only(self):
        for doc in self.make_content():
            doc = self.declare(doc, "Roles", roles=[VISIBILITY_ROLE])
            self.assert_can_read(ROLE_HOLDER, doc)
            for user in (INSIGHTS_PEER, DESK_USER, GUEST):
                self.assert_cannot_read(user, doc)

    # @feature permissions.visibility
    def test_everyone_allows_any_logged_in_user(self):
        for doc in self.make_content():
            doc = self.declare(doc, "Everyone")
            for user in (INSIGHTS_PEER, ROLE_HOLDER, DESK_USER):
                self.assert_can_read(user, doc)
            self.assert_cannot_read(GUEST, doc)

    # @feature permissions.visibility shared.dashboard-link shared.chart-link
    def test_public_allows_guests(self):
        for doc in self.make_content():
            doc = self.declare(doc, "Public")
            for user in (INSIGHTS_PEER, ROLE_HOLDER, DESK_USER, GUEST):
                self.assert_can_read(user, doc)

    # @feature permissions.visibility permissions.non-insights-user
    def test_no_visibility_level_consults_the_insights_user_role(self):
        self.assertNotIn("Insights User", frappe.get_roles(DESK_USER))
        for doc in self.make_content():
            self.assert_can_read(DESK_USER, self.declare(doc, "Everyone"))

    # visibility grants read only

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

    def reads_through_workbook(self, doc):
        doc = self.declare(doc, "Private")
        frappe.share.add(DT.WORKBOOK, doc.workbook, user=INSIGHTS_PEER, read=1, notify=0)
        return doc

    def edits_through_workbook(self, doc):
        """A member gets write and share only from its workbook."""
        frappe.share.add(DT.WORKBOOK, doc.workbook, user=INSIGHTS_PEER, read=1, write=1, notify=0)

    def set_visibility(self, user, doc, visibility):
        with self.as_user(user):
            writable = frappe.get_doc(doc.doctype, doc.name)
            writable.visibility = visibility
            writable.save()

    # @feature shared.publish-needs-share
    def test_an_editor_of_the_workbook_widens_who_may_read(self):
        """`validate_visibility` checks share, and a member gets share from write
        on its workbook. So any editor of the workbook can publish, not only its
        owner."""
        for doc in self.make_content():
            doc = self.declare(doc, "Private")
            self.edits_through_workbook(doc)
            self.assertTrue(has_doc_permission(doc, "share", INSIGHTS_PEER))

            self.set_visibility(INSIGHTS_PEER, doc, "Everyone")
            self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "visibility"), "Everyone")

    # @feature shared.publish-needs-share
    def test_every_widening_step_needs_write_on_the_workbook(self):
        """The check applies to every widening, not only to the widest level.
        `Roles` with no role allows nobody, so the test names a role."""
        for doc in self.make_content():
            doc = self.reads_through_workbook(doc)
            self.assertFalse(has_doc_permission(doc, "share", INSIGHTS_PEER))
            for visibility in ("Roles", "Everyone", "Public"):
                with self.as_user(INSIGHTS_PEER), self.assertRaises(frappe.PermissionError):
                    writable = frappe.get_doc(doc.doctype, doc.name)
                    writable.visibility = visibility
                    writable.set("visible_to_roles", [{"role": VISIBILITY_ROLE}])
                    writable.save()

            self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "visibility"), "Private")

    # @feature shared.publish-needs-share
    def test_naming_another_role_needs_write_on_the_workbook(self):
        """Adding a role widens reach as a level does, so it needs the same check."""
        for doc in self.make_content():
            doc = self.reads_through_workbook(doc)
            doc = self.declare(doc, "Roles", roles=[VISIBILITY_ROLE])
            with self.as_user(INSIGHTS_PEER), self.assertRaises(frappe.PermissionError):
                writable = frappe.get_doc(doc.doctype, doc.name)
                writable.append("visible_to_roles", {"role": "Insights User"})
                writable.save()

            self.assertEqual(
                [row.role for row in frappe.get_doc(doc.doctype, doc.name).get("visible_to_roles")],
                [VISIBILITY_ROLE],
            )

    # @feature permissions.visibility
    def test_a_role_every_user_holds_cannot_be_named(self):
        """The roles `All` and `Guest` would repeat the Everyone and Public
        levels without the checks on those levels."""
        for doc in self.make_content():
            with self.assertRaises(frappe.ValidationError):
                self.declare(doc, "Roles", roles=["All"])

    # @feature permissions.visibility
    def test_a_collaborator_duplicates_a_chart_that_is_not_private(self):
        """A copy widens nobody's reach, so it must not need share access. It
        starts at `Private`, as a new chart does."""
        chart, _ = self.make_content()
        chart = self.declare(chart, "Everyone")
        # a workbook collaborator: write on the workbook, no share flag
        frappe.share.add(DT.WORKBOOK, chart.workbook, user=INSIGHTS_PEER, read=1, write=1, notify=0)

        with self.as_user(INSIGHTS_PEER):
            copy = frappe.get_doc(chart.doctype, chart.name).duplicate()

        self.assertEqual(frappe.db.get_value(chart.doctype, copy, "visibility"), "Private")

    # @feature shared.publish-needs-share
    def test_narrowing_visibility_is_a_plain_write(self):
        """Narrowing allows nobody new, so it needs only write."""
        for doc in self.make_content():
            doc = self.declare(doc, "Public")
            self.edits_through_workbook(doc)

            self.set_visibility(INSIGHTS_PEER, doc, "Private")
            self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "visibility"), "Private")

    # @feature shared.publish-needs-share
    def test_an_owner_publishes_their_own(self):
        """The workbook's owner can write every member, so the check passes."""
        for doc in self.make_content():
            doc = self.declare(doc, "Private")
            self.set_visibility(OWNER, doc, "Public")
            self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "visibility"), "Public")

    # a chart on a dashboard

    # @feature permissions.chart-access-follows
    def test_chart_inherits_the_dashboard_visibility_downward_only(self):
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        chart = self.declare(chart, "Private")
        dashboard = self.declare(dashboard, "Everyone")

        self.assert_can_read(DESK_USER, dashboard)
        self.assert_can_read(DESK_USER, chart)

        # a chart's visibility never lets a user read its dashboard
        dashboard = self.declare(dashboard, "Private")
        chart = self.declare(chart, "Everyone")

        self.assert_can_read(DESK_USER, chart)
        self.assert_cannot_read(DESK_USER, dashboard)

    # @feature permissions.chart-access-follows
    def test_a_dashboard_hands_its_charts_read_and_nothing_more(self):
        """`frappe.client.delete`, the write check in `authoring.chart_to_run` and
        a query's read check all call `has_doc_permission`. A user the dashboard
        is shared with can read its charts. They cannot change, delete or share
        them, or read their queries."""
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        query = frappe.get_doc(DT.QUERY, chart.query)

        frappe.share.add(dashboard.doctype, dashboard.name, user=INSIGHTS_PEER, read=1, notify=0)
        stored = frappe.get_doc(chart.doctype, chart.name)

        self.assertTrue(has_doc_permission(stored, "read", INSIGHTS_PEER))
        for ptype in ("write", "delete", "share"):
            self.assertFalse(has_doc_permission(stored, ptype, INSIGHTS_PEER), ptype)
        self.assertFalse(has_doc_permission(query, "read", INSIGHTS_PEER))

    # @feature workbook.remove-item
    def test_a_charts_delete_leaves_the_rest_of_the_dashboards_grid(self):
        """Deleting a chart saves every dashboard that shows it. That save adds no
        chart, so the deleter needs no access to the other charts on the
        dashboard."""
        theirs, dashboard = self.make_content(link_chart_to_dashboard=True)
        frappe.share.add(DT.WORKBOOK, theirs.workbook, user=INSIGHTS_PEER, read=1, write=1, notify=0)
        mine = create_test_chart(OWNER, theirs.workbook, theirs.query, title="Visibility Test Chart, kept")
        dashboard = frappe.get_doc(dashboard.doctype, dashboard.name)
        dashboard.items = [
            *frappe.parse_json(dashboard.items),
            {"id": "chart-2", "type": "chart", "chart": mine.name},
        ]
        dashboard.save(ignore_permissions=True)

        with self.as_user(INSIGHTS_PEER):
            frappe.delete_doc(theirs.doctype, theirs.name)

        self.assertEqual(
            [row.chart for row in frappe.get_doc(dashboard.doctype, dashboard.name).linked_charts],
            [mine.name],
        )

    # @feature workbook.remove-item
    def test_a_dashboard_saved_from_a_stale_tab_drops_a_deleted_charts_cell(self):
        """A browser tab loaded the dashboard before the chart was deleted, so its
        save still sends the chart's cell."""
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        stale_items = frappe.parse_json(dashboard.items)
        frappe.delete_doc(chart.doctype, chart.name, ignore_permissions=True)

        with self.as_user(OWNER):
            stale = frappe.get_doc(dashboard.doctype, dashboard.name)
            stale.items = [*stale_items, {"id": "text-1", "type": "text", "text": "kept"}]
            stale.save()

        saved = frappe.get_doc(dashboard.doctype, dashboard.name)
        self.assertEqual([item["type"] for item in frappe.parse_json(saved.items)], ["text"])
        self.assertEqual(saved.linked_charts, [])

    # @feature shared.chart-on-public-dashboard shared.revoke
    def test_a_public_dashboard_lets_a_guest_read_its_charts(self):
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.declare(chart, "Private")
        self.runs_as_its_owner(chart)
        dashboard = self.declare(dashboard, "Public")

        self.assert_can_read(GUEST, dashboard)
        self.assert_can_read(GUEST, frappe.get_doc(chart.doctype, chart.name))

        dashboard = self.declare(dashboard, "Everyone")
        self.assert_cannot_read(GUEST, dashboard)
        self.assert_cannot_read(GUEST, frappe.get_doc(chart.doctype, chart.name))

    # Public runs a chart as its owner

    # @feature shared.rows-are-the-owners
    def test_publishing_a_chart_runs_it_as_its_owner(self):
        chart, _ = self.make_content()
        self.assertFalse(chart.run_as_owner)

        chart = self.declare(chart, "Public")
        self.assertTrue(chart.run_as_owner)

        # narrowing leaves Run as owner on
        chart = self.declare(chart, "Private")
        self.assertTrue(chart.run_as_owner)

    # @feature shared.rows-are-the-owners
    def test_a_public_chart_cannot_run_as_its_reader(self):
        chart, _ = self.make_content()
        chart = self.declare(chart, "Public")

        chart.run_as_owner = 0
        with self.assertRaises(frappe.ValidationError):
            chart.save(ignore_permissions=True)

    # @feature shared.chart-on-public-dashboard
    def test_a_dashboard_is_not_public_while_a_chart_on_it_runs_as_its_reader(self):
        """Run as owner belongs to the chart, so publishing the dashboard never
        sets it. The save is refused, naming the chart, until its owner ticks
        Run as owner."""
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)

        with self.assertRaisesRegex(frappe.ValidationError, chart.title):
            self.declare(dashboard, "Public")
        self.assertFalse(frappe.db.get_value(chart.doctype, chart.name, "run_as_owner"))
        self.assertEqual(frappe.db.get_value(dashboard.doctype, dashboard.name, "visibility"), "Private")

        self.runs_as_its_owner(chart)
        self.declare(frappe.get_doc(dashboard.doctype, dashboard.name), "Public")
        self.assertEqual(frappe.db.get_value(dashboard.doctype, dashboard.name, "visibility"), "Public")

    # @feature shared.chart-on-public-dashboard
    def test_a_chart_is_not_added_to_a_public_dashboard_while_it_runs_as_its_reader(self):
        """Adding a chart saves only the dashboard, so the dashboard must check
        its charts on every save."""
        chart, dashboard = self.make_content()
        self.declare(dashboard, "Public")

        dashboard = frappe.get_doc(dashboard.doctype, dashboard.name)
        dashboard.items = [{"type": "chart", "chart": chart.name}]
        with self.assertRaisesRegex(frappe.ValidationError, chart.title):
            dashboard.save(ignore_permissions=True)

        self.assertFalse(frappe.db.get_value(chart.doctype, chart.name, "run_as_owner"))

    # @feature shared.chart-on-public-dashboard standard.runs-as-the-reader
    def test_publishing_a_dashboard_leaves_a_shipped_charts_box_alone(self):
        """A standard chart must run as its reader, because its owner is
        Administrator on every site. Publishing it shares nobody's rows, so
        there is nothing to check."""
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        frappe.db.set_value(chart.doctype, chart.name, "is_standard", 1)
        self.addCleanup(frappe.db.set_value, chart.doctype, chart.name, "is_standard", 0)

        self.declare(dashboard, "Public")

        self.assertEqual(frappe.db.get_value(dashboard.doctype, dashboard.name, "visibility"), "Public")
        self.assertFalse(frappe.db.get_value(chart.doctype, chart.name, "run_as_owner"))

    # @feature permissions.chart-run-as-owner
    def test_only_the_owner_can_make_a_chart_run_with_the_owners_permissions(self):
        """Write on a chart does not let a user share the owner's rows."""
        chart, _ = self.make_content()
        self.edits_through_workbook(chart)

        with self.as_user(INSIGHTS_PEER), self.assertRaises(frappe.PermissionError):
            writable = frappe.get_doc(chart.doctype, chart.name)
            writable.run_as_owner = 1
            writable.save()

        self.assertFalse(frappe.db.get_value(chart.doctype, chart.name, "run_as_owner"))

    # @feature shared.publish-needs-share
    def test_a_member_says_whether_its_caller_may_share_it(self):
        """`ChartBuilderActions` and `DashboardEditActions` show Share by
        `can_share`. A dashboard returns `people_with_access` only when
        `can_share` is set. Outside developer mode, nobody can share standard
        content."""
        chart, dashboard = self.make_content()
        frappe.share.add(DT.WORKBOOK, chart.workbook, user=INSIGHTS_PEER, read=1, notify=0)

        def can_share(user, doc):
            with self.as_user(user):
                d = frappe.get_doc(doc.doctype, doc.name).as_dict()
            if doc.doctype == DT.DASHBOARD:
                self.assertEqual("people_with_access" in d, d.can_share, (user, doc.doctype))
            return d.can_share

        for doc in (chart, dashboard):
            self.assertTrue(can_share(OWNER, doc), doc.doctype)
            self.assertFalse(can_share(INSIGHTS_PEER, doc), doc.doctype)

        self.edits_through_workbook(chart)
        for doc in (chart, dashboard):
            self.assertTrue(can_share(INSIGHTS_PEER, doc), doc.doctype)

        frappe.db.set_value(DT.WORKBOOK, chart.workbook, "is_standard", 1)
        with patch.dict(frappe.conf, {"developer_mode": 0}):
            for doc in (chart, dashboard):
                self.assertFalse(can_share(OWNER, doc), doc.doctype)

    # @feature permissions.chart-run-as-owner permissions.run-as-owner-lapses
    def test_a_chart_says_who_may_move_its_box(self):
        """`ChartShareDialog` enables its Run as owner toggle by this.
        `validate_run_as_owner` treats a System Manager as an admin without
        `Insights Admin`. Only the owner may tick it. Unticking only narrows, so
        any editor may."""
        chart, _ = self.make_content()
        self.edits_through_workbook(chart)
        system_manager = create_user("visibility_system_manager@test.com", roles="System Manager")
        self.assertNotIn("Insights Admin", frappe.get_roles(system_manager.name))

        def may_move(user):
            with self.as_user(user):
                return frappe.get_doc(chart.doctype, chart.name).as_dict()["can_move_run_as_owner"]

        for user, may in ((OWNER, True), (system_manager.name, True), (INSIGHTS_PEER, False)):
            self.assertEqual(may_move(user), may, user)

        self.runs_as_its_owner(chart)
        self.assertTrue(may_move(INSIGHTS_PEER))

    # @feature permissions.run-as-owner-lapses
    def test_any_editor_makes_a_chart_run_as_its_reader_again(self):
        """Unticking shares nobody's rows. It is how an editor stops a chart from
        running as an owner who has lost access to the workbook."""
        chart, _ = self.make_content()
        self.runs_as_its_owner(chart)
        self.edits_through_workbook(chart)

        with self.as_user(INSIGHTS_PEER):
            writable = frappe.get_doc(chart.doctype, chart.name)
            writable.run_as_owner = 0
            writable.save()

        self.assertFalse(frappe.db.get_value(chart.doctype, chart.name, "run_as_owner"))

        # a user who can only read the chart may not untick it
        self.runs_as_its_owner(chart)
        frappe.share.remove(DT.WORKBOOK, chart.workbook, INSIGHTS_PEER)
        frappe.share.add(DT.WORKBOOK, chart.workbook, user=INSIGHTS_PEER, read=1, notify=0)
        with self.as_user(INSIGHTS_PEER), self.assertRaises(frappe.PermissionError):
            writable = frappe.get_doc(chart.doctype, chart.name)
            writable.run_as_owner = 0
            writable.save()

    # @feature shared.chart-on-public-dashboard
    def test_publishing_a_dashboard_never_checks_somebody_elses_chart(self):
        """Otherwise the publisher would share the chart owner's rows."""
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.edits_through_workbook(dashboard)
        frappe.share.add(chart.doctype, chart.name, user=INSIGHTS_PEER, read=1, notify=0)

        with self.as_user(INSIGHTS_PEER), self.assertRaises(frappe.ValidationError):
            writable = frappe.get_doc(dashboard.doctype, dashboard.name)
            writable.visibility = "Public"
            writable.save()

        self.assertEqual(frappe.db.get_value(dashboard.doctype, dashboard.name, "visibility"), "Private")
        self.assertFalse(frappe.db.get_value(chart.doctype, chart.name, "run_as_owner"))

    # @feature shared.chart-on-public-dashboard
    def test_a_chart_on_a_public_dashboard_cannot_run_as_its_reader(self):
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.runs_as_its_owner(chart)
        self.declare(dashboard, "Public")

        chart = frappe.get_doc(chart.doctype, chart.name)
        chart.run_as_owner = 0
        with self.assertRaises(frappe.ValidationError):
            chart.save(ignore_permissions=True)

    # a chart that already runs as its owner

    def runs_as_its_owner(self, chart):
        """The state a publish leaves a chart in. The `run_public_charts_as_owner` patch writes it too."""
        frappe.db.set_value(chart.doctype, chart.name, "run_as_owner", 1)

    # @feature permissions.chart-run-as-owner
    def test_a_sharer_cannot_publish_a_chart_that_runs_as_its_owner(self):
        """Share permission passes on the user's own access, never the owner's rows."""
        chart, _ = self.make_content()
        self.runs_as_its_owner(chart)
        self.edits_through_workbook(chart)

        with self.as_user(INSIGHTS_PEER), self.assertRaises(frappe.PermissionError):
            writable = frappe.get_doc(chart.doctype, chart.name)
            writable.visibility = "Everyone"
            writable.save()

        self.assertEqual(frappe.db.get_value(chart.doctype, chart.name, "visibility"), "Private")

    # @feature shared.chart-on-public-dashboard
    def test_publishing_a_dashboard_cannot_include_a_chart_that_runs_as_somebody_else(self):
        """Unlike `test_publishing_a_dashboard_never_checks_somebody_elses_chart`,
        Run as owner is already on here. Nothing is left to tick, but a guest
        would still read the owner's rows."""
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.runs_as_its_owner(chart)
        self.edits_through_workbook(dashboard)
        frappe.share.add(chart.doctype, chart.name, user=INSIGHTS_PEER, read=1, notify=0)

        # `Roles` too: a role allows users that nobody named one by one, and
        # share permission cannot grant that for another user's rows
        for level in ("Public", "Everyone", "Roles"):
            with self.as_user(INSIGHTS_PEER), self.assertRaises(frappe.PermissionError):
                writable = frappe.get_doc(dashboard.doctype, dashboard.name)
                writable.visibility = level
                if level == "Roles":
                    writable.append("visible_to_roles", {"role": VISIBILITY_ROLE})
                writable.save()

            self.assertEqual(frappe.db.get_value(dashboard.doctype, dashboard.name, "visibility"), "Private")

    # @feature permissions.chart-run-as-owner
    def test_a_sharer_cannot_publish_somebody_elses_chart_to_a_role(self):
        """A role allows a group of users. They get the owner's rows, as they do
        at `Everyone` and `Public`."""
        chart, _ = self.make_content()
        self.runs_as_its_owner(chart)
        self.edits_through_workbook(chart)

        with self.as_user(INSIGHTS_PEER), self.assertRaises(frappe.PermissionError):
            writable = frappe.get_doc(chart.doctype, chart.name)
            writable.visibility = "Roles"
            writable.append("visible_to_roles", {"role": VISIBILITY_ROLE})
            writable.save()

        self.assertEqual(frappe.db.get_value(chart.doctype, chart.name, "visibility"), "Private")

    # @feature permissions.chart-run-as-owner
    def test_a_sharer_cannot_name_another_role_on_an_already_published_chart(self):
        """The level stays `Roles`, but adding a role still widens reach. Its
        users would get the owner's rows without the owner's consent."""
        chart, _ = self.make_content()
        chart = self.declare(chart, "Roles", roles=[VISIBILITY_ROLE])
        self.runs_as_its_owner(chart)
        self.edits_through_workbook(chart)

        with self.as_user(INSIGHTS_PEER), self.assertRaises(frappe.PermissionError):
            writable = frappe.get_doc(chart.doctype, chart.name)
            writable.append("visible_to_roles", {"role": "Insights User"})
            writable.save()

    # @feature shared.publish-needs-share
    def test_narrowing_a_published_dashboard_to_a_role_is_not_a_publish(self):
        """`frappe.client.save` gives the controller the stored row as
        `get_doc_before_save`. A move from `Everyone` to a role removes readers,
        so it publishes no chart, whoever owns it."""
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.runs_as_its_owner(chart)
        dashboard = self.declare(dashboard, "Everyone")
        self.edits_through_workbook(dashboard)

        with self.as_user(INSIGHTS_PEER):
            writable = frappe.get_doc(dashboard.doctype, dashboard.name)
            writable.visibility = "Roles"
            writable.append("visible_to_roles", {"role": VISIBILITY_ROLE})
            writable.save()

        self.assertEqual(frappe.db.get_value(dashboard.doctype, dashboard.name, "visibility"), "Roles")

    # @feature shared.publish-needs-share permissions.chart-run-as-owner
    def test_narrowing_a_chart_to_a_role_is_a_plain_write(self):
        """A collaborator who may write the chart but not share it moves it from
        `Everyone` to a role. Nobody new can read it, so the save needs neither
        share permission nor the owner."""
        chart, _ = self.make_content()
        chart = self.declare(chart, "Everyone")
        self.runs_as_its_owner(chart)
        self.edits_through_workbook(chart)

        with self.as_user(INSIGHTS_PEER):
            writable = frappe.get_doc(chart.doctype, chart.name)
            writable.visibility = "Roles"
            writable.append("visible_to_roles", {"role": VISIBILITY_ROLE})
            writable.save()

        self.assertEqual(frappe.db.get_value(chart.doctype, chart.name, "visibility"), "Roles")

    # @feature permissions.visibility permissions.chart-run-as-owner
    def test_roles_with_no_role_allows_nobody(self):
        """`Roles` with no role allows nobody, as `Private` does. So the move is
        not a publish, and `published_reach` tells `ChartShareDialog` so."""
        chart, _ = self.make_content()
        self.runs_as_its_owner(chart)
        self.edits_through_workbook(chart)

        with self.as_user(INSIGHTS_PEER):
            writable = frappe.get_doc(chart.doctype, chart.name)
            writable.visibility = "Roles"
            writable.save()

        chart = frappe.get_doc(chart.doctype, chart.name)
        self.assertEqual(chart.visibility, "Roles")
        self.assertFalse(chart.published_reach()["published"])
        self.assert_cannot_read(ROLE_HOLDER, chart)

    # @feature shared.chart-on-public-dashboard
    def test_a_chart_left_unchecked_under_a_public_dashboard_stays_saveable(self):
        """The `run_public_charts_as_owner` patch leaves Run as owner off when the
        dashboard's publisher did not own the chart. The chart then refuses to
        run instead of showing another user's rows. The save checks only what
        changed. Otherwise every later save of the chart would fail: a retitle,
        a folder move, or an edit by its owner."""
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.runs_as_its_owner(chart)
        self.declare(dashboard, "Public")
        frappe.db.set_value(chart.doctype, chart.name, "run_as_owner", 0)

        saved = frappe.get_doc(chart.doctype, chart.name)
        saved.title = "Visibility Test Chart, retitled"
        saved.save(ignore_permissions=True)

        self.assertFalse(frappe.db.get_value(chart.doctype, chart.name, "run_as_owner"))

    # @feature shared.chart-on-public-dashboard
    def test_a_chart_reports_the_reach_a_dashboard_gives_it(self):
        """The share dialog's confirm and its Run as owner toggle depend on this.
        A chart's own level is only half the answer, because a public dashboard
        also publishes its charts. A chart that the patch left on a public
        dashboard starts in this state."""
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.declare(chart, "Private")

        self.assertEqual(
            frappe.get_doc(chart.doctype, chart.name).published_reach(),
            {"published": False, "published_by_dashboard": None, "on_public_dashboard": False},
        )

        self.runs_as_its_owner(chart)
        self.declare(dashboard, "Public")

        self.assertEqual(
            frappe.get_doc(chart.doctype, chart.name).published_reach(),
            {"published": False, "published_by_dashboard": dashboard.title, "on_public_dashboard": True},
        )

    # @feature shared.chart-on-public-dashboard
    def test_a_chart_reports_only_the_dashboards_its_caller_may_read(self):
        """Any reader of a chart can open `ChartShareDialog`, and it calls
        `published_reach`. A dashboard's title reveals the dashboard, so only
        its readers get it."""
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.declare(dashboard, "Roles", roles=[VISIBILITY_ROLE])
        frappe.share.add(chart.doctype, chart.name, user=INSIGHTS_PEER, read=1, notify=0)

        with self.as_user(INSIGHTS_PEER):
            self.assertIsNone(
                frappe.get_doc(chart.doctype, chart.name).published_reach()["published_by_dashboard"]
            )
        with self.as_user(OWNER):
            self.assertEqual(
                frappe.get_doc(chart.doctype, chart.name).published_reach()["published_by_dashboard"],
                dashboard.title,
            )

    # @feature shared.chart-on-public-dashboard
    def test_saving_a_published_dashboard_publishes_nothing_new(self):
        """A save that changes neither the level nor the grid is not a publish.

        The `run_public_charts_as_owner` patch leaves Run as owner off on a chart
        of a public dashboard when it cannot tell whose rows the chart showed.
        An unrelated save must not tick it."""
        chart, dashboard = self.make_content(link_chart_to_dashboard=True)
        self.runs_as_its_owner(chart)
        dashboard = self.declare(dashboard, "Public")
        frappe.db.set_value(chart.doctype, chart.name, "run_as_owner", 0)

        dashboard.title = "Visibility Test Dashboard, retitled"
        dashboard.save(ignore_permissions=True)

        self.assertFalse(frappe.db.get_value(chart.doctype, chart.name, "run_as_owner"))

    # through frappe.has_permission

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
    def test_declared_visibility_levels_match_the_schema(self):
        for doctype in (DT.CHART, DT.DASHBOARD):
            options = frappe.get_meta(doctype).get_field("visibility").options.split("\n")
            self.assertEqual(options, VISIBILITY_LEVELS)


class TestOrgShareMigration(InsightsIntegrationTestCase):
    """The patch that turns an org-wide DocShare into the `Everyone` level.

    See `insights/patches/set_visibility_from_org_shares.py`. The permission
    query ignores org-wide rows on content, so a row the patch leaves behind
    grants nothing.
    """

    SAVEPOINT = "test_org_share_migration"

    @classmethod
    def before_class(cls):
        cleanup_visibility_fixtures()
        create_visibility_users()

    @classmethod
    def after_class(cls):
        cleanup_visibility_fixtures()

    def shared_with_the_org(self, **flags):
        workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE)
        query = create_test_query(OWNER, workbook.name, title="Org Share Test Query")
        chart = create_test_chart(OWNER, workbook.name, query.name, title="Org Share Test Chart")
        dashboard = create_test_dashboard(OWNER, workbook.name, title="Org Share Test Dashboard")

        # inserted raw, as an old site holds them: a share with write on a
        # member can no longer be saved
        for doc in (chart, dashboard):
            frappe.get_doc(
                {
                    "doctype": "DocShare",
                    "share_doctype": doc.doctype,
                    "share_name": doc.name,
                    "everyone": 1,
                    **flags,
                }
            ).db_insert()
        return chart, dashboard

    def migrate(self):
        from insights.patches.set_visibility_from_org_shares import execute

        execute()

    # @feature permissions.visibility
    def test_an_org_share_that_granted_only_read_becomes_the_everyone_level(self):
        for doc in self.shared_with_the_org(read=1):
            self.migrate()
            self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "visibility"), "Everyone")
            self.assertFalse(
                frappe.db.exists("DocShare", {"share_doctype": doc.doctype, "share_name": doc.name})
            )

    # @feature permissions.visibility
    def test_an_org_share_that_granted_write_still_becomes_the_everyone_level(self):
        """A share with write also granted read, and a row left behind would grant nothing."""
        for doc in self.shared_with_the_org(read=1, write=1):
            self.migrate()
            self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "visibility"), "Everyone")
            self.assertFalse(
                frappe.db.exists("DocShare", {"share_doctype": doc.doctype, "share_name": doc.name})
            )
