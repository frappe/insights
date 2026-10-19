"""What the upgrade from Insights 3 leaves for an admin or an author to do.

See `insights/patches/report_upgrade_items.py`. Each test sets up the state
Insights 3 left and the earlier patches made, runs one report, and reads the
items it wrote.
"""

from unittest.mock import patch

import frappe

from insights.insights.doctype.insights_data_source_v3.sandbox import refused_names
from insights.insights.doctype.insights_team.insights_team import clear_cache as clear_team_cache
from insights.patches import report_upgrade_items as report
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
    create_user,
    delete_users,
)
from insights.upgrade import ITEM

OWNER = "Administrator"
AUTHOR = "upgrade_report_author@test.com"
MEMBER = "upgrade_report_member@test.com"
PREFIX = "Upgrade Report Test"
TEAM_NAME = "Upgrade Report Team"


def items(code):
    return frappe.get_all(
        ITEM,
        filters={"code": code},
        fields=["reference_doctype", "reference_name", "user", "action", "message"],
    )


class TestUpgradeReport(InsightsIntegrationTestCase):
    SAVEPOINT = "test_upgrade_report"

    @classmethod
    def before_class(cls):
        create_user(AUTHOR, roles="Insights User")
        create_user(MEMBER, roles="Insights User")
        workbook = create_test_workbook(OWNER, title=PREFIX)
        cls.workbook = workbook.name
        cls.query = create_test_query(OWNER, workbook.name, title=f"{PREFIX} Query").name
        cls.chart = create_test_chart(OWNER, workbook.name, cls.query, title=f"{PREFIX} Chart").name
        cls.dashboard = create_test_dashboard(
            OWNER, workbook.name, cls.chart, title=f"{PREFIX} Dashboard"
        ).name

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        delete_users(AUTHOR, MEMBER)
        clear_team_cache()

    def before_test(self):
        frappe.db.delete(ITEM)

    def after_test(self):
        clear_team_cache()

    # @feature upgrade.left-to-do-reported
    def test_a_team_member_who_edited_a_dashboard_through_the_team_is_reported(self):
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 1)
        team = frappe.get_doc({"doctype": DT.TEAM, "team_name": TEAM_NAME})
        team.append("team_members", {"user": MEMBER})
        team.append("team_members", {"user": AUTHOR})
        team.append("team_permissions", {"resource_type": DT.DASHBOARD, "resource_name": self.dashboard})
        team.insert(ignore_permissions=True)
        frappe.share.add_docshare(
            DT.WORKBOOK, self.workbook, AUTHOR, write=1, flags={"ignore_share_permission": 1}
        )

        report.report_team_grants_that_lost_write()

        [item] = items("P4")
        self.assertEqual((item.reference_doctype, item.reference_name), (DT.WORKBOOK, self.workbook))
        self.assertIn(f"let {MEMBER} edit", item.message)
        self.assertNotIn(AUTHOR, item.message)

    # @feature upgrade.left-to-do-reported
    def test_a_chart_whose_owner_may_no_longer_run_it_is_reported(self):
        frappe.db.set_value(DT.CHART, self.chart, {"owner": AUTHOR, "run_as_owner": 1}, update_modified=False)
        frappe.db.set_value(DT.USER, AUTHOR, "enabled", 0)

        report.report_charts_that_cannot_run_as_owner()

        [item] = items("P12")
        self.assertEqual(item.reference_name, self.chart)
        self.assertIn("whose account is disabled", item.message)

    # @feature upgrade.left-to-do-reported
    def test_a_chart_whose_owner_still_runs_it_is_not_reported(self):
        frappe.db.set_value(DT.CHART, self.chart, "run_as_owner", 1, update_modified=False)

        report.report_charts_that_cannot_run_as_owner()

        self.assertEqual(items("P12"), [])

    # @feature upgrade.left-to-do-reported
    def test_an_author_who_may_no_longer_change_their_script_is_told(self):
        script = [{"type": "code", "code": "result = [{'a': 1}]\nresult"}]
        frappe.db.set_value(
            DT.QUERY,
            self.query,
            {"operations": frappe.as_json(script), "owner": AUTHOR, "is_script_query": 1},
            update_modified=False,
        )

        report.report_trusted_code_of_authors()

        [item] = items("P20")
        self.assertEqual((item.reference_name, item.user), (self.query, AUTHOR))

    # @feature upgrade.left-to-do-reported
    def test_a_script_that_uses_a_name_the_sandbox_refuses_is_reported_to_its_author(self):
        script = [
            {"type": "code", "code": "frappe.db.set_value('ToDo', 'x', 'status', 'Closed')\nresult = []"}
        ]
        frappe.db.set_value(
            DT.QUERY,
            self.query,
            {"operations": frappe.as_json(script), "owner": AUTHOR, "is_script_query": 1},
            update_modified=False,
        )

        report.report_scripts_with_refused_names()

        [item] = items("Q1")
        self.assertEqual((item.reference_name, item.user), (self.query, AUTHOR))
        self.assertIn("`frappe.db.set_value`", item.message)

    # @feature upgrade.left-to-do-reported
    def test_an_import_job_whose_script_will_fail_is_reported(self):
        job = frappe.get_doc(
            {
                "doctype": report.IMPORT_JOB,
                "title": f"{PREFIX} Job",
                "data_source": "Site DB",
                "table_name": "upgrade_report_rows",
                "script": "rows = client.get('/x')\nfrappe.enqueue('x')\ntable.insert(rows)",
            }
        )
        job.db_insert()

        report.report_scripts_with_refused_names()

        [item] = items("J4")
        self.assertEqual(item.reference_name, job.name)
        self.assertIn("`frappe.enqueue`", item.message)
        self.assertNotIn("client", item.message)

    # @feature upgrade.left-to-do-reported
    def test_a_template_copy_nobody_changed_can_be_deleted_and_a_changed_one_cannot(self):
        copy = frappe._dict(
            name=self.workbook, title=PREFIX, from_template="insights/sales", imported_checksum="x"
        )
        with patch.object(report, "template_copies", return_value=[copy]):
            report.report_template_copies()
        if not items("W2"):
            self.skipTest("no installed app ships the Selling workbook")
        [untouched] = items("W2")

        frappe.db.delete(ITEM)
        frappe.db.set_value(
            DT.CHART,
            self.chart,
            "modified",
            frappe.utils.add_days(frappe.utils.now(), 1),
            update_modified=False,
        )
        with patch.object(report, "template_copies", return_value=[copy]):
            report.report_template_copies()
        [changed] = items("W2")

        self.assertEqual(untouched.action, "delete_workbook")
        self.assertIn('"Selling"', untouched.message)
        self.assertFalse(changed.action)

    # @feature upgrade.left-to-do-reported
    def test_a_blank_fiscal_year_start_is_reported_with_the_settings_to_set_it(self):
        frappe.db.set_single_value(DT.SETTINGS, "fiscal_year_start", None)

        report.report_blank_fiscal_year_start()

        [item] = items("Q13")
        self.assertEqual(item.action, "open_settings")

        frappe.db.delete(ITEM)
        frappe.db.set_single_value(DT.SETTINGS, "fiscal_year_start", "2026-04-01")
        report.report_blank_fiscal_year_start()
        self.assertEqual(items("Q13"), [])

    # @feature upgrade.left-to-do-reported
    def test_a_site_that_was_not_on_insights_3_gets_no_report(self):
        frappe.db.set_single_value(DT.SETTINGS, "fiscal_year_start", None)

        with patch.object(report, "was_on_v3", return_value=False):
            report.execute()

        self.assertEqual(frappe.get_all(ITEM), [])


class TestRefusedNames(InsightsIntegrationTestCase):
    SAVEPOINT = "test_refused_names"

    # @feature upgrade.left-to-do-reported
    def test_names_the_sandbox_refuses_are_listed(self):
        self.assertEqual(refused_names("frappe.db.set_value('ToDo', 'x', 'a', 1)"), ["frappe.db.set_value"])
        self.assertEqual(refused_names("frappe.qb.from_('ToDo').run()"), ["frappe.qb"])
        self.assertEqual(refused_names("pandas.read_csv('rows.csv')"), ["pandas.read_csv"])
        self.assertEqual(refused_names("df = pandas.DataFrame([])\ndf.to_csv('/tmp/x')"), [".to_csv"])

    # @feature upgrade.left-to-do-reported
    def test_names_the_sandbox_gives_a_script_are_not_listed(self):
        self.assertEqual(
            refused_names(
                "rows = frappe.get_all('ToDo')\n"
                "doc = frappe.get_doc('ToDo', rows[0].name)\n"
                "start = doc.from_date\n"
                "result = pandas.DataFrame(rows).to_dict('records')\n"
                "frappe.utils.getdate(start)"
            ),
            [],
        )
        self.assertEqual(refused_names("frappe = 1\nfrappe.qb"), [])
        self.assertEqual(refused_names("not python ("), [])
