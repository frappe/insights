"""Retiring the site-wide switch, and what the upgrade tells admins about it.

See `insights/patches/retire_site_apply_user_permissions.py` and
`report_site_data_follows_desk.py`, which `bench migrate` runs against the
Singles row a released site holds.
"""

import frappe

from insights.api.upgrade import get_upgrade_items
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
from insights.insights.doctype.insights_team.insights_team import clear_cache as clear_team_cache
from insights.patches.report_site_data_follows_desk import execute as report_site_data
from insights.patches.report_site_data_follows_desk import restriction_data, site_data_findings
from insights.patches.retire_site_apply_user_permissions import FIELD, SETTINGS
from insights.patches.retire_site_apply_user_permissions import execute as retire
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_query,
    create_test_workbook,
    create_user,
    delete_users,
)
from insights.upgrade import ITEM

OWNER = "Administrator"
PREFIX = "Retirement Test"


class TestSiteSwitchRetirement(InsightsIntegrationTestCase):
    SAVEPOINT = "test_apply_user_permissions_retirement"

    @classmethod
    def before_class(cls):
        cls.plain = cls.make_chart("Plain")
        cls.shipped = cls.make_chart("Shipped")
        frappe.db.set_value(
            DT.WORKBOOK, frappe.db.get_value(DT.CHART, cls.shipped, "workbook"), "is_standard", 1
        )

    @classmethod
    def after_class(cls):
        for name in frappe.get_all(DT.WORKBOOK, filters={"title": ("like", f"{PREFIX}%")}, pluck="name"):
            frappe.db.set_value(DT.WORKBOOK, name, "is_standard", 0)
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)

    @classmethod
    def make_chart(cls, title):
        workbook = create_test_workbook(OWNER, title=f"{PREFIX} {title}")
        query = create_test_query(OWNER, workbook.name, title=f"{PREFIX} {title} Query")
        return create_test_chart(OWNER, workbook.name, query.name, title=f"{PREFIX} {title}").name

    def switch_was(self, value):
        """The Singles row a released site holds: "0", "1", or none at all."""
        frappe.db.delete("Singles", {"doctype": SETTINGS, "field": FIELD})
        if value is None:
            return
        frappe.db.sql(
            "insert into `tabSingles` (doctype, field, value) values (%s, %s, %s)",
            (SETTINGS, FIELD, value),
        )

    # @feature permissions.chart-run-as-owner standard.runs-as-the-reader
    def test_the_retirement_writes_nothing_to_a_chart(self):
        """The switch held only the frappe gate, and the Check moves the team
        grants and Table Restrictions with it. So a chart keeps running as its
        reader, on a switch-off site and on one that never wrote the switch."""
        for was_on in ("0", "1", None):
            with self.subTest(was_on=was_on):
                self.switch_was(was_on)
                retire()
                self.assertFalse(frappe.db.get_value(DT.CHART, self.plain, "run_as_owner"))
                self.assertFalse(frappe.db.get_value(DT.CHART, self.shipped, "run_as_owner"))
                self.assertFalse(frappe.db.exists("Singles", {"doctype": SETTINGS, "field": FIELD}))


READER = "site-data-findings-reader@test.com"
OUTSIDER = "site-data-findings-outsider@test.com"
TEAM_NAME = "Site Data Findings Team"


class TestSiteDataFindings(InsightsIntegrationTestCase):
    """What the upgrade tells admins about site data now following desk alone.

    The reader's team grants `tabDeleted Document`, which desk lets only a
    System Manager read, and `tabToDo` with a Table Restriction. The outsider
    is in no team. A saved query reads both tables.
    """

    SAVEPOINT = "test_site_data_findings"

    @classmethod
    def before_class(cls):
        delete_users(READER, OUTSIDER)
        create_user(READER, roles="Insights User")
        create_user(OUTSIDER, roles="Insights User")
        workbook = create_test_workbook(OWNER, title=f"{PREFIX} Findings")
        for table in ("tabDeleted Document", "tabToDo"):
            create_test_query(
                OWNER,
                workbook.name,
                title=f"{PREFIX} {table}",
                operations=[
                    {
                        "type": "source",
                        "table": {"type": "table", "data_source": "Site DB", "table_name": table},
                    }
                ],
            )
            if not frappe.db.exists(DT.TABLE, get_table_name("Site DB", table)):
                frappe.get_doc(
                    {"doctype": DT.TABLE, "table": table, "label": table, "data_source": "Site DB"}
                ).insert(ignore_permissions=True)

        team = frappe.get_doc({"doctype": DT.TEAM, "team_name": TEAM_NAME})
        team.append("team_members", {"user": READER})
        team.append(
            "team_permissions",
            {"resource_type": DT.TABLE, "resource_name": get_table_name("Site DB", "tabDeleted Document")},
        )
        team.append(
            "team_permissions",
            {
                "resource_type": DT.TABLE,
                "resource_name": get_table_name("Site DB", "tabToDo"),
                "table_restrictions": "status == 'Open'",
            },
        )
        team.insert(ignore_permissions=True)
        cls.team = team.name

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.TEAM, cls.team, force=True, ignore_permissions=True)
        for name in frappe.get_all(DT.WORKBOOK, filters={"title": ("like", f"{PREFIX}%")}, pluck="name"):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(READER, OUTSIDER)
        clear_team_cache()

    def before_test(self):
        frappe.db.delete(ITEM, {"code": "P17"})

    def after_test(self):
        clear_team_cache()

    def findings(self, team_permissions, switch):
        self.set_team_permissions(team_permissions)
        TestSiteSwitchRetirement.switch_was(self, switch)
        found = site_data_findings()
        users = {user.user: user for user in found.users if user.user in (READER, OUTSIDER)}
        teams = [team for team in found.restrictions if team.team == self.team]
        return users, teams

    # @feature upgrade.site-data-follows-desk
    def test_a_team_member_desk_denies_and_a_restriction_that_stopped_are_listed(self):
        users, teams = self.findings(team_permissions=1, switch="1")

        self.assertEqual(list(users), [READER])
        self.assertEqual(users[READER].unreadable, ["Deleted Document"])
        self.assertEqual(users[READER].narrowed, [])
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0].users, [READER])
        self.assertEqual(
            [(r.doctype, r.restriction) for r in teams[0].restrictions], [("ToDo", "status == 'Open'")]
        )

    # @feature upgrade.site-data-follows-desk
    def test_with_team_permissions_off_every_insights_user_was_let_in(self):
        """Insights v3 let every Insights user into every table, and applied no
        Table Restriction."""
        users, teams = self.findings(team_permissions=0, switch="1")

        self.assertIn("Deleted Document", users[READER].unreadable)
        self.assertIn("Deleted Document", users[OUTSIDER].unreadable)
        self.assertEqual(teams, [])

    # @feature upgrade.site-data-follows-desk
    def test_with_apply_user_permissions_off_desk_now_narrows_what_was_whole(self):
        """Desk lets an Insights User read only the ToDos they are assigned, so
        a reader who read every ToDo now reads fewer."""
        users, _ = self.findings(team_permissions=1, switch="0")

        self.assertEqual(users[READER].unreadable, ["Deleted Document"])
        self.assertEqual(users[READER].narrowed, ["ToDo"])

    # @feature upgrade.site-data-follows-desk
    def test_a_site_that_never_wrote_apply_user_permissions_had_it_off(self):
        """Insights v3 read the missing row as 0, so desk narrows here too."""
        users, _ = self.findings(team_permissions=1, switch=None)

        self.assertEqual(users[READER].narrowed, ["ToDo"])

    # @feature upgrade.site-data-follows-desk
    def test_a_restriction_names_its_field_and_value_only_when_it_compares_one_field_to_text(self):
        self.assertEqual(
            restriction_data("ToDo", 'status == "Open"'),
            {"doctype": "ToDo", "condition": 'status == "Open"', "field": "status", "value": "Open"},
        )
        self.assertEqual(
            restriction_data("ToDo", "status == 'Open' and priority == 'High'"),
            {"doctype": "ToDo", "condition": "status == 'Open' and priority == 'High'"},
        )
        self.assertEqual(
            restriction_data("ToDo", "status != 'Open'"), {"doctype": "ToDo", "condition": "status != 'Open'"}
        )

    # @feature upgrade.site-data-follows-desk upgrade.attention-items
    def test_the_patch_tells_the_admins_who_lost_rows_and_what_fixes_it(self):
        self.set_team_permissions(1)
        TestSiteSwitchRetirement.switch_was(self, "1")
        report_site_data()
        report_site_data()

        items = frappe.get_all(
            ITEM,
            filters={"code": "P17", "reference_name": ("in", [READER, OUTSIDER, self.team])},
            fields=["reference_doctype", "reference_name", "user", "message", "data"],
            order_by="reference_doctype asc",
        )
        self.assertEqual(
            [(item.reference_doctype, item.reference_name, item.user) for item in items],
            [(DT.TEAM, self.team, None), ("User", READER, None)],
        )
        team_item, user_item = items
        self.assertIn("status == 'Open'", team_item.message)
        self.assertIn("Deleted Document", user_item.message)
        self.assertIn("Not Permitted", user_item.message)
        self.assertEqual(
            frappe.parse_json(team_item.data),
            {
                "team": self.team,
                "members": [READER],
                "restrictions": [
                    {"doctype": "ToDo", "condition": "status == 'Open'", "field": "status", "value": "Open"}
                ],
            },
        )
        self.assertEqual(
            frappe.parse_json(user_item.data),
            {"user": READER, "doctypes": ["Deleted Document"], "narrowed": []},
        )

        # the app has no page for a user or a team, so Open goes to the desk form
        listed = {item.reference_name: item for item in get_upgrade_items()}
        self.assertIn("/desk/user/", listed[READER].form_url)
        self.assertIn("/desk/insights-team/", listed[self.team].form_url)
