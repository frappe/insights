import frappe
import frappe.share
from frappe.permissions import update_permission_property

from insights.api.alerts import get_alerts
from insights.api.user import USER_FIELDS, get_users, user_lookup_allowed
from insights.api.workbooks import get_share_permissions, update_share_permissions
from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
from insights.insights.doctype.insights_team.insights_team import clear_cache as clear_team_cache
from insights.permissions import PERMISSION_DOCTYPES
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
    execute_test_query,
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

    # @feature permissions.non-insights-user
    def test_permissions_for_non_insights_user(self):
        # Charts and dashboards give doctype-level read to everyone. Visibility
        # limits access per document, so viewing needs no Insights role (see
        # test_visibility).
        visibility_gated = ["Insights Chart v3", "Insights Dashboard v3"]
        with self.as_user(NON_INSIGHTS_USER):
            for doctype in PERMISSION_DOCTYPES:
                if doctype in visibility_gated:
                    continue
                self.assertFalse(
                    frappe.has_permission(doctype, ptype="read"),
                    f"{doctype} should not be readable without an Insights role",
                )

            with self.assertRaises(frappe.PermissionError):
                protected_insights_call()

    # @feature permissions.team-off-open settings.permissions-toggle
    def test_permissions_on_team_based_doctype_with_team_permissions_disabled(self):
        create_test_data_sources()
        create_test_tables()
        create_test_teams()
        self.set_team_permissions(False)

        self.assert_visible_to(USER_2, DT.DATA_SOURCE, TEST_DS)
        self.assert_visible_to(USER_2, DT.TABLE, TEST_TABLE1)

    # @feature permissions.team-grant settings.permissions-toggle
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

    # @feature permissions.team-grant
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

    # @feature permissions.team-off-open permissions.non-insights-user
    def test_team_permissions_off_open_every_source_to_insights_users_only(self):
        """A chart can run as a guest on a Public chart, or as a user with no
        Insights role on an `Everyone` chart. With team permissions off, neither
        may read a table. The Not Permitted check uses the same
        `check_table_permission`."""
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import InsightsTablev3
        from insights.insights.doctype.insights_team.insights_team import check_table_permission
        from insights.not_permitted import NotPermitted
        from insights.permission_user import permission_user

        create_test_data_sources()
        create_test_tables()
        self.set_team_permissions(False)

        for user, allowed in ((USER_1, True), (ADMIN, True), (NON_INSIGHTS_USER, False), ("Guest", False)):
            with self.subTest(user=user):
                self.assertIs(
                    check_table_permission(TEST_DS, "table1", user=user, raise_error=False), allowed
                )
                if not allowed:
                    with permission_user(user), self.assertRaisesRegex(NotPermitted, "access this table"):
                        InsightsTablev3.get_ibis_table(TEST_DS, "table1", use_live_connection=True)

    # @feature permissions.team-off-open
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

    # @feature permissions.admin-bypass
    def test_permission_for_admin_on_team_based_doctype_with_team_permissions_enabled(
        self,
    ):
        create_test_data_sources()
        create_test_tables()
        self.set_team_permissions(True)

        self.assert_visible_to(ADMIN, DT.DATA_SOURCE, TEST_DS)
        self.assert_visible_to(ADMIN, DT.TABLE, TEST_TABLE1)

    # @feature permissions.viewer-sees-granted
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

    # @feature permissions.share-user-lookup
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

    # @feature permissions.share-user-lookup
    def test_roster_includes_nothing_but_directory_fields(self):
        # the api is the only way into `User`, so its field list is the whole
        # exposure - no phone number or api key may ride along
        with self.as_user(USER_1):
            users = get_users()

        self.assertTrue(users)
        for user in users:
            self.assertEqual(set(user.keys()), set(USER_FIELDS) | {"type"})

    # @feature permissions.share-user-lookup settings.users-list
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

    # @feature permissions.share-user-lookup
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

    # @feature permissions.share-user-lookup
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

    # @feature permissions.share-workbook-user
    def test_workbook_owned_by_administrator_can_still_be_shared(self):
        # an import leaves Administrator owning the workbook, and the
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

    # @feature permissions.share-workbook-user
    def test_workbook_cannot_be_shared_with_a_non_insights_user(self):
        workbook = create_test_workbook(USER_1)

        with self.as_user(USER_1):
            with self.assertRaisesRegex(frappe.ValidationError, "not an Insights user"):
                update_share_permissions(
                    workbook.name,
                    [{"user": NON_INSIGHTS_USER, "read": 1, "write": 0}],
                )

    # @feature permissions.share-workbook-user
    def test_a_share_the_workbook_already_holds_is_kept_when_sent_back(self):
        """`WorkbookShareDialog` sends the whole share list back on every save.
        So an old share, or a share to someone who left Insights, comes back each
        time. Keeping or narrowing it is allowed. Widening it to edit is checked."""
        workbook = create_test_workbook(USER_1)
        frappe.share.add(DT.WORKBOOK, workbook.name, user=NON_INSIGHTS_USER, read=1, notify=0)

        def echoed(**access):
            shown = get_share_permissions(workbook.name)["user_permissions"]
            return [{**permission, **access.get(permission["user"], {})} for permission in shown]

        with self.as_user(USER_1):
            update_share_permissions(workbook.name, [*echoed(), {"user": USER_2, "read": 1, "write": 0}])
            self.assert_visible_to(USER_2, DT.WORKBOOK, workbook.name)

            with self.assertRaisesRegex(frappe.ValidationError, "not an Insights user"):
                update_share_permissions(
                    workbook.name, echoed(**{NON_INSIGHTS_USER: {"read": 0, "write": 1}})
                )

            update_share_permissions(workbook.name, echoed(**{USER_2: {"read": 0, "write": 1}}))
            update_share_permissions(workbook.name, echoed(**{USER_2: {"read": 1, "write": 0}}))

        shared = frappe.get_all(
            "DocShare",
            filters={"share_doctype": DT.WORKBOOK, "share_name": workbook.name, "everyone": 0},
            fields=["user", "write"],
        )
        self.assertEqual(
            {share.user: share.write for share in shared},
            {USER_1: 1, USER_2: 0, NON_INSIGHTS_USER: 0},
        )

    # @feature permissions.share-workbook-user
    def test_a_removed_share_given_back_is_checked_again(self):
        """`WorkbookShareDialog` removes a person by sending them with no access.
        Their share row stays at read 0 and write 0. Giving access back widens
        it, so `update_share_permissions` checks the user again."""
        workbook = create_test_workbook(USER_1)
        frappe.share.add(DT.WORKBOOK, workbook.name, user=NON_INSIGHTS_USER, read=1, notify=0)

        with self.as_user(USER_1):
            update_share_permissions(workbook.name, [{"user": NON_INSIGHTS_USER, "read": 0, "write": 0}])
            with self.assertRaisesRegex(frappe.ValidationError, "not an Insights user"):
                update_share_permissions(workbook.name, [{"user": NON_INSIGHTS_USER, "read": 1, "write": 0}])

    # @feature permissions.viewer-cannot-edit
    def test_a_folder_is_read_and_changed_on_its_workbook_grant(self):
        """`frappe.client` and `frappe.get_list` reach a folder without the
        folder endpoints, so the folder's own permission must follow its workbook."""
        workbook = create_test_workbook(USER_1)
        folder = frappe.get_doc(
            {"doctype": "Insights Folder", "workbook": workbook.name, "title": "Payroll", "type": "query"}
        ).insert(ignore_permissions=True)

        def grants(user):
            with self.as_user(user):
                listed = folder.name in frappe.get_list(
                    "Insights Folder", filters={"workbook": workbook.name}, pluck="name"
                )
                return {
                    "list": listed,
                    **{
                        ptype: bool(frappe.has_permission("Insights Folder", ptype=ptype, doc=folder.name))
                        for ptype in ("read", "write", "delete")
                    },
                }

        none = {"list": False, "read": False, "write": False, "delete": False}
        self.assertEqual(grants(USER_2), none)

        frappe.db.set_value("Insights Folder", folder.name, "owner", USER_2)
        self.assertEqual(grants(USER_2), none)

        frappe.share.add(DT.WORKBOOK, workbook.name, user=USER_2, read=1, notify=0)
        self.assertEqual(grants(USER_2), {"list": True, "read": True, "write": False, "delete": False})

        frappe.share.add(DT.WORKBOOK, workbook.name, user=USER_2, read=1, write=1, notify=0)
        self.assertEqual(grants(USER_2), {"list": True, "read": True, "write": True, "delete": True})

    # @feature permissions.member-stays-in-its-workbook
    def test_a_member_never_moves_to_another_workbook(self):
        """Every grant on a member comes from its workbook. A move would give
        the member to the target workbook's editors, so it is refused, even for
        an editor of both workbooks and for an admin."""
        source = create_test_workbook(USER_1)
        target = create_test_workbook(USER_1, title="Permissions Test Target Workbook")
        query = create_test_query(USER_1, source.name)
        target_query = create_test_query(USER_1, target.name)
        chart = create_test_chart(USER_1, source.name, query.name)
        dashboard = create_test_dashboard(USER_1, source.name)
        folder = frappe.get_doc(
            {"doctype": "Insights Folder", "workbook": source.name, "title": "Payroll", "type": "query"}
        ).insert(ignore_permissions=True)
        alert = frappe.get_doc(
            {
                "doctype": "Insights Alert",
                "title": "Moved alert",
                "channel": "Email",
                "query": query.name,
                "frequency": "Daily",
                "custom_condition": 1,
                "condition": "True",
                "message": "hello",
                "recipients": "someone@external.example.org",
                "disabled": 1,
            }
        ).insert(ignore_permissions=True)

        moves = [
            (DT.QUERY, query.name, "workbook", target.name),
            (DT.CHART, chart.name, "workbook", target.name),
            (DT.DASHBOARD, dashboard.name, "workbook", target.name),
            ("Insights Folder", folder.name, "workbook", target.name),
            # an alert belongs to its query's workbook
            ("Insights Alert", alert.name, "query", target_query.name),
        ]
        for user in (USER_1, ADMIN):
            for doctype, name, field, value in moves:
                before = frappe.db.get_value(doctype, name, field)
                with self.as_user(user), self.assertRaises(frappe.CannotChangeConstantError):
                    frappe.client.set_value(doctype, name, field, value)
                self.assertEqual(frappe.db.get_value(doctype, name, field), before, (user, doctype))

    # @feature permissions.member-write-follows-workbook
    def test_write_on_a_member_comes_only_from_write_on_its_workbook(self):
        """Owning a member grants nothing, and a team grant on a chart or a
        dashboard gives read only. So a person removed from the workbook loses
        what they made there. An edit share on the workbook gives write and
        share on every member."""
        self.set_team_permissions(True)
        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name)
        chart = create_test_chart(USER_1, workbook.name, query.name)
        dashboard = create_test_dashboard(USER_1, workbook.name, chart.name)
        alert = frappe.get_doc(
            {
                "doctype": "Insights Alert",
                "title": "Owned alert",
                "channel": "Email",
                "query": query.name,
                "frequency": "Daily",
                "custom_condition": 1,
                "condition": "True",
                "message": "hello",
                "recipients": "someone@external.example.org",
                "disabled": 1,
            }
        ).insert(ignore_permissions=True)
        folder = frappe.get_doc(
            {"doctype": "Insights Folder", "workbook": workbook.name, "title": "Owned", "type": "query"}
        ).insert(ignore_permissions=True)
        members = [
            (DT.QUERY, query.name),
            (DT.CHART, chart.name),
            (DT.DASHBOARD, dashboard.name),
            ("Insights Alert", alert.name),
            ("Insights Folder", folder.name),
        ]

        def grants(user, doctype, name):
            with self.as_user(user):
                return {
                    ptype: bool(frappe.has_permission(doctype, ptype=ptype, doc=name))
                    for ptype in ("read", "write", "delete", "share")
                }

        nothing = {"read": False, "write": False, "delete": False, "share": False}
        read_only = {"read": True, "write": False, "delete": False, "share": False}
        edit = {"read": True, "write": True, "delete": True, "share": True}

        # USER_2 owns every member; USER_3's team is granted the chart and the dashboard
        for doctype, name in members:
            frappe.db.set_value(doctype, name, "owner", USER_2)
        create_test_team("team1", [USER_3], [(DT.CHART, chart.name), (DT.DASHBOARD, dashboard.name)])

        for doctype, name in members:
            self.assertEqual(grants(USER_2, doctype, name), nothing, (USER_2, doctype))
            self.assert_not_visible_to(USER_2, doctype, name)
            self.assertEqual(grants(USER_1, doctype, name), edit, (USER_1, doctype))
        for doctype, name in ((DT.CHART, chart.name), (DT.DASHBOARD, dashboard.name)):
            self.assertEqual(grants(USER_3, doctype, name), read_only, (USER_3, doctype))
        # the team reads the query behind the chart, never an alert on that query
        self.assertTrue(grants(USER_3, DT.QUERY, query.name)["read"])
        self.assertEqual(grants(USER_3, "Insights Alert", alert.name), nothing)
        self.assert_not_visible_to(USER_3, "Insights Alert", alert.name)

        # a new alert is a new member of its query's workbook
        def new_alert():
            return frappe.copy_doc(alert).insert()

        with self.as_user(USER_1):
            update_share_permissions(workbook.name, [{"user": USER_2, "read": 1, "write": 0}])
        for doctype, name in members:
            self.assertEqual(grants(USER_2, doctype, name), read_only, ("viewer", doctype))
        with self.as_user(USER_2), self.assertRaises(frappe.PermissionError):
            new_alert()

        with self.as_user(USER_1):
            update_share_permissions(
                workbook.name,
                [{"user": USER_2, "read": 1, "write": 1}, {"user": USER_3, "read": 1, "write": 1}],
            )
        for user in (USER_2, USER_3):
            for doctype, name in members:
                self.assertEqual(grants(user, doctype, name), edit, (user, doctype))
        with self.as_user(USER_2):
            new_alert()

        with self.as_user(USER_1):
            update_share_permissions(workbook.name, [])
        for doctype, name in members:
            self.assertEqual(grants(USER_2, doctype, name), nothing, ("removed", doctype))
            self.assert_not_visible_to(USER_2, doctype, name)

        # Desk can set share on the workbook's DocShare. It gives share on no member.
        with self.as_user(USER_1):
            frappe.share.add(DT.WORKBOOK, workbook.name, user=USER_2, read=1, share=1, notify=0)
        for doctype, name in members:
            self.assertFalse(grants(USER_2, doctype, name)["share"], ("workbook share", doctype))

    # @feature permissions.member-row-saved-with-member
    def test_a_row_of_a_member_is_saved_with_it_and_never_on_its_own(self):
        """`frappe.client.save` and `/api/resource` can save or delete a child
        row on its own. The member's checks (linked charts, visibility, the
        standard guard) run only when the member saves, so a row saved on its own
        skips them."""
        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name)
        chart = create_test_chart(USER_1, workbook.name, query.name)
        dashboard = create_test_dashboard(USER_1, workbook.name, chart.name)
        others = create_test_workbook(USER_2)
        private_chart = create_test_chart(USER_2, others.name, create_test_query(USER_2, others.name).name)

        with self.as_user(USER_1):
            forged = [
                {"parent": dashboard.name, "parentfield": "linked_charts", "chart": private_chart.name},
                {"parent": dashboard.name, "parentfield": "visible_to_roles", "role": "All"},
                {"parent": chart.name, "parentfield": "visible_to_roles", "role": "All"},
                {"parent": query.name, "parentfield": "variables", "variable_name": "key"},
            ]
            for row in forged:
                parenttype = dashboard.doctype if row["parent"] == dashboard.name else None
                parenttype = parenttype or (chart.doctype if row["parent"] == chart.name else query.doctype)
                child = frappe.get_meta(parenttype).get_field(row["parentfield"]).options
                with self.assertRaisesRegex(frappe.ValidationError, "not on its own", msg=row):
                    frappe.client.save({"doctype": child, "parenttype": parenttype, **row})
            self.assertFalse(frappe.has_permission(DT.CHART, ptype="read", doc=private_chart.name))

            # a stored row, changed or deleted on its own
            linked = frappe.get_doc(dashboard.doctype, dashboard.name).linked_charts[0]
            with self.assertRaisesRegex(frappe.ValidationError, "not on its own"):
                frappe.client.save({**linked.as_dict(), "chart": private_chart.name})
            with self.assertRaisesRegex(frappe.ValidationError, "not on its own"):
                frappe.delete_doc(linked.doctype, linked.name)
            self.assertEqual(
                [row.chart for row in frappe.get_doc(dashboard.doctype, dashboard.name).linked_charts],
                [chart.name],
            )

            # the same rows save through the member
            writable = frappe.get_doc(chart.doctype, chart.name)
            writable.visibility = "Roles"
            writable.append("visible_to_roles", {"role": "Insights User"})
            writable.save()

        # every table of every member, whoever saves the row
        for doctype in PERMISSION_DOCTYPES:
            meta = frappe.get_meta(doctype)
            if not meta.has_field("workbook") and doctype != "Insights Alert":
                continue
            for field in meta.get_table_fields():
                with self.assertRaisesRegex(
                    frappe.ValidationError, "not on its own", msg=(doctype, field.fieldname)
                ):
                    frappe.get_doc(
                        {
                            "doctype": field.options,
                            "parenttype": doctype,
                            "parentfield": field.fieldname,
                            "parent": "anything",
                        }
                    ).insert(ignore_permissions=True, ignore_mandatory=True)

        # frappe handles a row of any other doctype
        role = frappe.get_doc({"doctype": "Role", "role_name": "Member Row Test"}).insert()
        frappe.get_doc(
            {
                "doctype": "Has Role",
                "parenttype": "User",
                "parentfield": "roles",
                "parent": USER_3,
                "role": role.name,
            }
        ).insert(ignore_permissions=True)
        self.assertTrue(frappe.db.exists("Has Role", {"parent": USER_3, "role": role.name}))

    # @feature permissions.member-row-saved-with-member
    def test_a_row_of_a_member_is_refused_on_its_own_under_any_spelling_of_its_parent(self):
        """`frappe.client.save` finds the parent doctype case-insensitively, but
        stores the `parenttype` string as sent, and SQL matches that string. So
        every spelling that frappe resolves to a member must be refused."""
        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name)
        chart = create_test_chart(USER_1, workbook.name, query.name)
        dashboard = create_test_dashboard(USER_1, workbook.name, chart.name)
        others = create_test_workbook(USER_2)
        private_chart = create_test_chart(USER_2, others.name, create_test_query(USER_2, others.name).name)

        rows = [
            (dashboard, {"parentfield": "linked_charts", "chart": private_chart.name}),
            (dashboard, {"parentfield": "visible_to_roles", "role": "All"}),
            (chart, {"parentfield": "visible_to_roles", "role": "Insights User"}),
            (query, {"parentfield": "variables", "variable_name": "key"}),
        ]
        with self.as_user(USER_1):
            for member, row in rows:
                child = member.meta.get_field(row["parentfield"]).options
                for spelling in (member.doctype.lower(), member.doctype.upper(), member.doctype + " "):
                    with self.assertRaisesRegex(frappe.ValidationError, "not on its own", msg=spelling):
                        frappe.client.save(
                            {"doctype": child, "parenttype": spelling, "parent": member.name, **row}
                        )
            self.assertFalse(frappe.has_permission(DT.CHART, ptype="read", doc=private_chart.name))

            # a stored row with another spelling
            linked = frappe.get_doc(dashboard.doctype, dashboard.name).linked_charts[0]
            with self.assertRaisesRegex(frappe.ValidationError, "not on its own"):
                frappe.client.save(
                    {**linked.as_dict(), "parenttype": dashboard.doctype.lower(), "chart": private_chart.name}
                )
        self.assertFalse(
            frappe.db.exists(
                "Insights Dashboard Chart v3", {"parent": dashboard.name, "chart": private_chart.name}
            )
        )

        # frappe handles a row of any other doctype, under any spelling
        role = frappe.get_doc({"doctype": "Role", "role_name": "Member Row Spelling Test"}).insert()
        frappe.get_doc(
            {
                "doctype": "Has Role",
                "parenttype": "user",
                "parentfield": "roles",
                "parent": USER_3,
                "role": role.name,
            }
        ).insert(ignore_permissions=True)
        self.assertTrue(frappe.db.exists("Has Role", {"parent": USER_3, "role": role.name}))

    # @feature permissions.member-share-names-a-reader
    def test_a_share_on_a_member_is_a_named_read_share_on_a_dashboard_or_chart(self):
        """`frappe.has_permission` reads any DocShare after the controller
        refuses, so a DocShare on a member must be a read share to one user.
        Other shares are refused when written, and `bench migrate` fixes or
        removes old ones. Workbook shares are not member shares and keep every
        flag."""
        from insights.patches.reshape_member_shares import execute as reshape_member_shares

        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name)
        chart = create_test_chart(USER_1, workbook.name, query.name)
        dashboard = create_test_dashboard(USER_1, workbook.name, chart.name)
        folder = frappe.get_doc(
            {"doctype": "Insights Folder", "workbook": workbook.name, "title": "Payroll", "type": "query"}
        ).insert(ignore_permissions=True)
        alert = frappe.get_doc(
            {
                "doctype": "Insights Alert",
                "title": "Shared alert",
                "channel": "Email",
                "query": query.name,
                "frequency": "Daily",
                "custom_condition": 1,
                "condition": "True",
                "message": "hello",
                "recipients": "someone@external.example.org",
                "disabled": 1,
            }
        ).insert(ignore_permissions=True)
        members = [
            (DT.QUERY, query.name),
            (DT.CHART, chart.name),
            (DT.DASHBOARD, dashboard.name),
            ("Insights Folder", folder.name),
            ("Insights Alert", alert.name),
        ]

        shareable = {DT.CHART, DT.DASHBOARD}

        def grants(user, doctype, name):
            with self.as_user(user):
                return {
                    ptype: bool(frappe.has_permission(doctype, ptype=ptype, doc=name))
                    for ptype in ("read", "write", "share")
                }

        nothing = {"read": False, "write": False, "share": False}
        read_only = {"read": True, "write": False, "share": False}

        refused_shapes = [
            {"user": USER_2, "read": 1, "write": 1},
            {"user": USER_2, "read": 1, "share": 1},
            {"everyone": 1, "read": 1},
        ]
        for doctype, name in members:
            shapes = refused_shapes if doctype in shareable else [{"user": USER_2, "read": 1}]
            for shape in shapes:
                with self.as_user(USER_1), self.assertRaises(frappe.ValidationError, msg=(doctype, shape)):
                    frappe.share.add(doctype, name, notify=0, **shape)
            self.assertEqual(grants(USER_2, doctype, name), nothing, doctype)

        for doctype in shareable:
            name = dict(members)[doctype]
            with self.as_user(USER_1):
                frappe.share.add(doctype, name, user=USER_2, read=1, notify=0)
            self.assertEqual(grants(USER_2, doctype, name), read_only, doctype)
        with self.as_user(USER_1):
            update_dashboard_access(dashboard.name, [USER_2, USER_3])
        self.assertEqual(grants(USER_3, DT.DASHBOARD, dashboard.name), read_only)

        # old rows: USER_3 has every flag on every member, and everyone reads the chart
        frappe.db.delete("DocShare", {"share_doctype": ("in", [d for d, _ in members])})
        for doctype, name in members:
            frappe.get_doc(
                {
                    "doctype": "DocShare",
                    "share_doctype": doctype,
                    "share_name": name,
                    "user": USER_3,
                    "read": 1,
                    "write": 1,
                    "share": 1,
                }
            ).db_insert()
        frappe.get_doc(
            {
                "doctype": "DocShare",
                "share_doctype": DT.CHART,
                "share_name": chart.name,
                "everyone": 1,
                "read": 1,
            }
        ).db_insert()
        self.assertTrue(all(grants(USER_3, doctype, name)["write"] for doctype, name in members))

        reshape_member_shares()
        self.assertEqual(
            frappe.get_all(
                "DocShare",
                filters={"share_doctype": ("in", [doctype for doctype, _ in members])},
                fields=["share_doctype", "user", "everyone", "read", "write", "share"],
                order_by="share_doctype",
            ),
            [
                {"share_doctype": doctype, "user": USER_3, "everyone": 0, "read": 1, "write": 0, "share": 0}
                for doctype in sorted(shareable)
            ],
        )
        # USER_3 reads the query through the chart. Only the workbook gives read on an alert.
        for doctype, name in members:
            expected = nothing if doctype in ("Insights Folder", "Insights Alert") else read_only
            self.assertEqual(grants(USER_3, doctype, name), expected, doctype)
            self.assertEqual(grants(USER_2, doctype, name), nothing, doctype)
        with self.as_user(USER_3):
            self.assertEqual(get_alerts(query.name), [])

        with self.as_user(USER_1):
            frappe.share.add(DT.WORKBOOK, workbook.name, user=USER_2, read=1, write=1, share=1, notify=0)
        for doctype, name in members:
            self.assertEqual(
                grants(USER_2, doctype, name), {"read": True, "write": True, "share": True}, doctype
            )
        with self.as_user(USER_2):
            self.assertEqual([row.name for row in get_alerts(query.name)], [alert.name])

    # @feature permissions.share-user-lookup
    def test_team_membership_is_listed_for_admins_only(self):
        self.set_team_permissions(True)

        with self.as_user(USER_1):
            self.assertNotIn("teams", get_users()[0])

        with self.as_user(ADMIN):
            self.assertIn("teams", get_users()[0])

    # @feature permissions.share-dashboard
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

    # @feature permissions.chart-access-follows
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

    # @feature permissions.chart-access-follows
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

        with self.as_user(USER_1):
            share_chart(chart.name, USER_2)

        self.assert_visible_to(USER_2, DT.QUERY, query.name)

        with self.as_user(USER_1):
            unshare_chart(chart.name, USER_2)

        self.assert_not_visible_to(USER_2, DT.QUERY, query.name)

        dashboard = create_test_dashboard(
            USER_1,
            workbook.name,
            chart.name,
            title="Permissions Test Dashboard For Query",
        )
        with self.as_user(USER_1):
            update_dashboard_access(dashboard.name, [USER_2])

        # a dashboard shares the chart's result, not the query behind it
        self.assert_not_visible_to(USER_2, DT.QUERY, query.name)

        with self.as_user(NON_INSIGHTS_USER):
            with self.assertRaises(frappe.PermissionError):
                create_test_query(
                    NON_INSIGHTS_USER,
                    workbook.name,
                    title="Permissions Test Query Non Insights",
                )

    # @feature permissions.download-gated
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
            with self.assertRaisesRegex(frappe.PermissionError, "not allowed to download"):
                query_doc.download_results(format="csv")

        update_permission_property(DT.QUERY, "Insights User", 0, "export", 1)
        frappe.clear_cache(doctype=DT.QUERY)

        with self.as_user(USER_1):
            query_doc = frappe.get_doc(DT.QUERY, query.name)
            with db_connections():
                csv_data = query_doc.download_results(format="csv")
            self.assertIsInstance(csv_data, str)

    # @feature permissions.download-gated
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

    # @feature permissions.download-gated permissions.request-body-not-trusted
    def test_download_results_decides_against_the_stored_query(self):
        """`run_doc_method` builds the document from the request body. So the
        caller can send any `owner`, and the check must read the stored query."""
        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name)
        frappe.db.set_single_value(DT.SETTINGS, "allow_download", 1)
        self.set_team_permissions(True)

        with self.as_user(USER_2):
            self.assertTrue(frappe.has_permission(DT.QUERY, ptype="export"))
            forged = frappe.get_doc({**frappe.get_doc(DT.QUERY, query.name).as_dict(), "owner": USER_2})
            with self.assertRaisesRegex(frappe.PermissionError, "not allowed to download"):
                forged.download_results(format="csv")

    # @feature permissions.download-gated
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

    # @feature permissions.download-gated settings.allow-download
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


class TestTableRowRestriction(InsightsIntegrationTestCase):
    """A team's grant can have an expression that limits the rows the grant gives.

    The restriction rides `Insights Resource Permission.table_restrictions` and is
    applied where every table read funnels through, so it reaches a query, a
    preview and a chart alike. An admin is not restricted.
    """

    SITE_DB = "Site DB"
    TABLE = "tabToDo"
    PREFIX = "Row Restriction Test"

    @classmethod
    def before_class(cls):
        cleanup_test_fixtures()
        create_test_users()
        cls.settings_was = {
            "enable_permissions": frappe.db.get_single_value(DT.SETTINGS, "enable_permissions"),
        }
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 1)

        cls.table_row = get_table_name(cls.SITE_DB, cls.TABLE)
        if not frappe.db.exists(DT.TABLE, cls.table_row):
            frappe.get_doc(
                {
                    "doctype": DT.TABLE,
                    "table": cls.TABLE,
                    "label": cls.TABLE,
                    "data_source": cls.SITE_DB,
                    "sync_mode": "Full",
                }
            ).insert(ignore_permissions=True)

        cls.todos = [
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": f"{cls.PREFIX} {status} {i}",
                    "status": status,
                    # Each reader gets their own todos, which desk permissions
                    # allow in full. So only the team's row filter limits the rest.
                    "allocated_to": user,
                    "assigned_by": "Administrator",
                }
            )
            .insert(ignore_permissions=True)
            .name
            for user in (USER_1, ADMIN)
            for status, i in (("Open", 1), ("Open", 2), ("Closed", 3))
        ]

        create_test_team(
            "team1",
            [USER_1],
            grants=[(DT.DATA_SOURCE, cls.SITE_DB)],
        )
        team = frappe.get_doc(DT.TEAM, "team1")
        team.append(
            "team_permissions",
            {
                "resource_type": DT.TABLE,
                "resource_name": cls.table_row,
                "table_restrictions": "status == 'Open'",
            },
        )
        team.save(ignore_permissions=True)
        clear_team_cache()

    @classmethod
    def after_class(cls):
        for name in cls.todos:
            frappe.delete_doc("ToDo", name, force=True, ignore_permissions=True)
        for key, value in cls.settings_was.items():
            frappe.db.set_single_value(DT.SETTINGS, key, value)
        clear_team_cache()
        cleanup_test_fixtures()

    def before_test(self):
        clear_team_cache()

    def after_test(self):
        clear_team_cache()

    def statuses_read_by(self, user):
        """The statuses this suite's own todos come back with, for `user`."""
        workbook = create_test_workbook(user, title=f"Row Restriction Workbook {user}")
        query = create_test_query(
            user,
            workbook.name,
            title=f"Row Restriction Query {user}",
            operations=[
                {
                    "type": "source",
                    "table": {
                        "type": "table",
                        "data_source": self.SITE_DB,
                        "table_name": self.TABLE,
                    },
                },
                {
                    "type": "filter",
                    "column": {"type": "column", "column_name": "description"},
                    "operator": "contains",
                    "value": self.PREFIX,
                },
            ],
        )
        with self.as_user(user):
            rows = execute_test_query(query.name)["rows"]
        return sorted(row["status"] for row in rows)

    # @feature permissions.table-row-restriction
    def test_a_teams_row_restriction_cuts_only_the_rows_its_grant_adds(self):
        """Desk permissions allow the reader's own todos, closed ones included.
        The grant adds the other reader's open todos, never their closed one."""
        self.assertEqual(self.statuses_read_by(USER_1), ["Closed", "Open", "Open", "Open", "Open"])
        self.assertEqual(self.statuses_read_by(ADMIN), ["Closed", "Open", "Open"])

    # @feature permissions.table-row-restriction
    def test_one_teams_grant_never_narrows_anothers(self):
        """The reader is in two teams that both grant the table. Each grant
        lets the reader read the rows its own restriction allows. A grant with no restriction
        allows the whole table."""
        team = self.second_team("status == 'Closed'")
        # only the second team allows the other reader's closed todo
        self.assertEqual(self.statuses_read_by(USER_1), ["Closed", "Closed", "Open", "Open", "Open", "Open"])

        team.team_permissions[-1].table_restrictions = "status == 'Nothing'"
        team.save(ignore_permissions=True)
        clear_team_cache()
        self.assertEqual(self.statuses_read_by(USER_1), ["Closed", "Open", "Open", "Open", "Open"])

        team.team_permissions[-1].table_restrictions = None
        team.save(ignore_permissions=True)
        clear_team_cache()
        self.assertEqual(self.statuses_read_by(USER_1), ["Closed", "Closed", "Open", "Open", "Open", "Open"])

    def second_team(self, restriction):
        team = create_test_team("team2", [USER_1], grants=[(DT.DATA_SOURCE, self.SITE_DB)])
        self.addCleanup(frappe.delete_doc, DT.TEAM, team.name, force=True, ignore_permissions=True)
        team.append(
            "team_permissions",
            {"resource_type": DT.TABLE, "resource_name": self.table_row, "table_restrictions": restriction},
        )
        team.save(ignore_permissions=True)
        clear_team_cache()
        return team
