"""The upgrade from Insights 3: who is welcomed, and what reaches whom.

See `insights/upgrade.py`. The patches that add items come later; these tests
add their own.
"""

import frappe

from insights.api import get_user_info
from insights.api.upgrade import (
    dismiss_upgrade_items,
    fix_upgrade_item,
    get_shipping_apps,
    get_upgrade_items,
    mark_upgrade_seen,
    reopen_upgrade_items,
)
from insights.patches import mark_v3_users as mark_v3_users_patch
from insights.patches.run_public_charts_as_owner import report as report_public_chart
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_chart, create_test_workbook, create_user, delete_users
from insights.upgrade import ITEM, SEEN_VERSION, add_item, mark_v3_users

ALICE = "upgrade_alice@test.com"
BOB = "upgrade_bob@test.com"
NEWCOMER = "upgrade_newcomer@test.com"
PREFIX = "Upgrade Items Test"


class TestUpgradeItems(InsightsIntegrationTestCase):
    SAVEPOINT = "test_upgrade_items"

    @classmethod
    def before_class(cls):
        create_user(ALICE, first_name="Alice", last_name="Moss", roles="Insights User")
        create_user(BOB, first_name="Bob", last_name="Lane", roles="Insights User")

    @classmethod
    def after_class(cls):
        for name in frappe.get_all(DT.WORKBOOK, filters={"title": ("like", f"{PREFIX}%")}, pluck="name"):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(ALICE, BOB, NEWCOMER)

    def before_test(self):
        frappe.db.delete(ITEM)

    def after_test(self):
        # the savepoint rolls back the defaults, not the cache of them
        for user in frappe.get_all("User", pluck="name"):
            frappe.client_cache.delete_value(f"defaults::{user}")

    def user_info(self, user):
        with self.as_user(user):
            return get_user_info()

    # @feature upgrade.v3-users-welcomed
    def test_a_user_of_insights_3_is_welcomed_once_and_a_newcomer_never(self):
        mark_v3_users()
        create_user(NEWCOMER, roles="Insights User")

        self.assertTrue(self.user_info(ALICE)["upgraded_from_v3"])
        self.assertTrue(self.user_info("Administrator")["upgraded_from_v3"])
        self.assertFalse(self.user_info(NEWCOMER)["upgraded_from_v3"])

        with self.as_user(ALICE):
            mark_upgrade_seen()
        self.assertFalse(self.user_info(ALICE)["upgraded_from_v3"])
        self.assertTrue(self.user_info(BOB)["upgraded_from_v3"])

    # @feature upgrade.v3-users-welcomed
    def test_only_a_site_upgrading_from_a_release_of_insights_3_welcomes_its_users(self):
        row = {"parent": "Installed Applications", "app_name": "insights"}
        for version, branch, welcomed in (
            ("3.14.2", "version-3", True),
            ("3.3.1", "develop", False),
            ("4.0.0-dev", "develop", False),
            ("4.0.0", "version-4", False),
        ):
            with self.subTest(version=version, branch=branch):
                frappe.db.set_value(
                    "Installed Application", row, {"app_version": version, "git_branch": branch}
                )
                frappe.defaults.clear_user_default(SEEN_VERSION, ALICE)
                self.after_test()

                mark_v3_users_patch.execute()

                self.assertEqual(self.user_info(ALICE)["upgraded_from_v3"], welcomed)

    # @feature upgrade.attention-items
    def test_an_admin_sees_every_open_item_and_a_user_only_their_own(self):
        add_item("Q13", "Set Fiscal Year Start to pin it.", action="open_settings")
        add_item("P20", "Only admins can edit this script now.", user=ALICE)
        add_item("P20", "Only admins can edit this script now.", user=BOB)

        with self.as_user(ALICE):
            self.assertEqual([(i.code, i.user) for i in get_upgrade_items()], [("P20", ALICE)])
        self.assertEqual(self.user_info(ALICE)["upgrade_item_count"], 1)
        self.assertEqual(len(get_upgrade_items()), 3)
        self.assertEqual(self.user_info("Administrator")["upgrade_item_count"], 3)

    # @feature upgrade.attention-items
    def test_an_item_names_its_people_by_first_name_and_a_moved_chart_names_both_owners(self):
        workbook = create_test_workbook(BOB, title=f"{PREFIX} Published")
        chart = create_test_chart(BOB, workbook.name, title=f"{PREFIX} Chart")
        report_public_chart(chart.name, BOB, ALICE, moved=True)
        add_item("P3", "A workbook is shared.", data={"workbook": "Sales", "users": [ALICE, "Nobody"]})
        data = {"chart": f"{PREFIX} Chart", "publisher": ALICE, "owner": BOB}
        people = {
            ALICE: {"full_name": "Alice Moss", "first_name": "Alice"},
            BOB: {"full_name": "Bob Lane", "first_name": "Bob"},
        }

        items = get_upgrade_items()

        self.assertEqual(
            [(i.code, i.user, i.data, i.people) for i in items],
            [
                ("P11", BOB, data, people),
                ("P11", ALICE, data, people),
                ("P3", None, {"workbook": "Sales", "users": [ALICE, "Nobody"]}, {ALICE: people[ALICE]}),
            ],
        )
        with self.as_user(ALICE):
            self.assertEqual([(i.data, i.people) for i in get_upgrade_items()], [(data, people)])

    # @feature upgrade.attention-items
    def test_an_item_without_data_has_none_to_show(self):
        add_item("Q13", "Set Fiscal Year Start to pin it.", action="open_settings")

        self.assertEqual([(i.data, i.people) for i in get_upgrade_items()], [({}, {})])

    # @feature upgrade.attention-items
    def test_a_system_manager_sees_every_open_item_as_desk_shows_them(self):
        add_item("P20", "Only admins can edit this script now.", user=ALICE)
        frappe.get_doc(DT.USER, BOB).add_roles("System Manager")

        with self.as_user(BOB):
            self.assertEqual([(i.code, i.user) for i in get_upgrade_items()], [("P20", ALICE)])
        # the wizard lays out its steps by the same rule
        self.assertTrue(self.user_info(BOB)["is_upgrade_admin"])
        self.assertFalse(self.user_info(ALICE)["is_upgrade_admin"])

    # @feature upgrade.attention-items
    def test_an_item_whose_doctype_is_gone_is_left_out(self):
        add_item("P20", "Only admins can edit this script now.", reference=("User", "Administrator"))
        frappe.db.set_value(ITEM, {"code": "P20"}, "reference_doctype", "Uninstalled Doctype")
        add_item("Q13", "Set Fiscal Year Start to pin it.", action="open_settings")

        self.assertEqual([i.code for i in get_upgrade_items()], ["Q13"])

    # @feature upgrade.attention-items
    def test_a_user_dismisses_their_own_item_and_no_one_elses(self):
        add_item("P20", "Only admins can edit this script now.", user=ALICE)
        add_item("P20", "Only admins can edit this script now.", user=BOB)
        alices = frappe.db.get_value(ITEM, {"user": ALICE})
        bobs = frappe.db.get_value(ITEM, {"user": BOB})

        with self.as_user(ALICE):
            self.assertEqual(dismiss_upgrade_items([alices, bobs]), [alices])
            self.assertEqual(get_upgrade_items(), [])
        self.assertEqual(frappe.db.get_value(ITEM, bobs, "status"), "Open")

    # @feature upgrade.attention-items
    def test_dismissing_an_item_closed_elsewhere_still_closes_the_rest(self):
        add_item("P11", "Moved to Bob.", user=ALICE)
        add_item("P11", "Moved to Bob.", user=BOB)
        names = frappe.get_all(ITEM, pluck="name")
        frappe.db.set_value(ITEM, names[0], "status", "Dismissed")

        self.assertEqual(dismiss_upgrade_items(names), names[1:])
        self.assertEqual(frappe.get_all(ITEM, filters={"status": "Open"}), [])

    # @feature upgrade.attention-items
    def test_a_user_reopens_their_own_closed_item_and_no_one_elses(self):
        add_item("P20", "Only admins can edit this script now.", user=ALICE)
        add_item("P20", "Only admins can edit this script now.", user=BOB)
        add_item("Q13", "Set Fiscal Year Start to pin it.", action="open_settings")
        alices = frappe.db.get_value(ITEM, {"user": ALICE})
        bobs = frappe.db.get_value(ITEM, {"user": BOB})
        open_one = frappe.db.get_value(ITEM, {"code": "Q13"})
        for name in (alices, bobs):
            frappe.db.set_value(ITEM, name, "status", "Dismissed")

        with self.as_user(ALICE):
            self.assertEqual(reopen_upgrade_items([alices, bobs]), [alices])
        self.assertEqual(frappe.db.get_value(ITEM, alices, "status"), "Open")
        self.assertEqual(frappe.db.get_value(ITEM, bobs, "status"), "Dismissed")
        # an admin reopens anyone's, and an open item has nothing to reopen
        self.assertEqual(reopen_upgrade_items([bobs, open_one]), [bobs])

    # @feature upgrade.attention-items
    def test_a_patch_that_runs_again_does_not_bring_back_a_dismissed_item(self):
        workbook = create_test_workbook("Administrator", title=f"{PREFIX} Copy")
        reference = (DT.WORKBOOK, workbook.name)
        add_item("W2", "This copy duplicates a standard workbook.", reference=reference)
        dismiss_upgrade_items([frappe.db.get_value(ITEM, {"code": "W2"})])

        add_item("W2", "This copy duplicates a standard workbook.", reference=reference)

        self.assertEqual(frappe.get_all(ITEM, filters={"code": "W2"}, pluck="status"), ["Dismissed"])

    # @feature upgrade.attention-fix
    def test_fix_needs_the_users_own_permission_on_what_it_names(self):
        workbook = create_test_workbook(BOB, title=f"{PREFIX} Bobs")
        add_item(
            "W2",
            "This copy duplicates a standard workbook.",
            reference=(DT.WORKBOOK, workbook.name),
            user=ALICE,
            action="delete_workbook",
        )
        item = frappe.db.get_value(ITEM, {"code": "W2"})

        with self.as_user(ALICE):
            self.assertFalse(get_upgrade_items()[0].can_fix)
            self.assertRaises(frappe.PermissionError, fix_upgrade_item, item)
        self.assertTrue(frappe.db.exists(DT.WORKBOOK, workbook.name))
        self.assertEqual(frappe.db.get_value(ITEM, item, "status"), "Open")

    # @feature upgrade.attention-fix
    def test_fix_deletes_a_template_copy(self):
        workbook = create_test_workbook("Administrator", title=f"{PREFIX} Template Copy")
        add_item(
            "W2",
            "This copy duplicates a standard workbook.",
            reference=(DT.WORKBOOK, workbook.name),
            action="delete_workbook",
        )

        fix_upgrade_item(frappe.db.get_value(ITEM, {"code": "W2"}))

        self.assertFalse(frappe.db.exists(DT.WORKBOOK, workbook.name))

    # @feature upgrade.wizard
    def test_the_apps_that_ship_workbooks_come_with_their_title_and_logo(self):
        from insights import standard

        workbooks = frappe.get_all(DT.WORKBOOK, filters={"is_standard": 1}, pluck="name")
        shipping = set(standard.shipping_apps(workbooks).values())
        with self.as_user(ALICE):
            apps = get_shipping_apps()

        self.assertTrue(apps)
        self.assertEqual({app["app"] for app in apps}, shipping)
        for app in apps:
            self.assertEqual(app["title"], standard.app_title(app["app"]))
            self.assertEqual(app["logo"], standard.app_logo_url(app["app"]))

    # @feature upgrade.wizard
    def test_the_session_says_what_the_welcome_shows_only_to_those_who_can_do_it(self):
        standard = bool(frappe.db.exists(DT.DASHBOARD, {"is_standard": 1}))
        self.assertEqual(self.user_info("Administrator")["reads_standard_dashboards"], standard)
        self.assertTrue(self.user_info("Administrator")["can_show_in_desk"])
        self.assertFalse(self.user_info(ALICE)["reads_standard_dashboards"])
        self.assertFalse(self.user_info(ALICE)["can_show_in_desk"])

    # @feature upgrade.wizard
    def test_the_session_says_whether_the_user_owns_a_workbook(self):
        self.assertFalse(self.user_info(BOB)["owns_workbooks"])
        create_test_workbook(BOB, title=f"{PREFIX} Owned")
        self.assertTrue(self.user_info(BOB)["owns_workbooks"])
