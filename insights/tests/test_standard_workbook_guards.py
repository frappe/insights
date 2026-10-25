"""Guards on a standard workbook.

`insights/standard.py` reads `is_standard` to let a chart past the site's team
grants and Table Restrictions. `module` decides whether the next migrate finds
the workbook's file. If it does not, migrate deletes the workbook as an orphan,
with every query, chart, dashboard and folder in it. `frappe.client.set_value`
can write both fields and ignores `read_only`, so the document refuses both.
"""

import frappe

from insights.insights.doctype.insights_workbook.insights_workbook import _rename_members
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_dashboard, create_test_workbook

OWNER = "Administrator"
PREFIX = "Standard Guard Test"
SITE_MODULE = f"{PREFIX} Module"


class TestStandardWorkbookGuards(InsightsIntegrationTestCase):
    SAVEPOINT = "test_standard_workbook_guards"

    @classmethod
    def before_class(cls):
        cls.developer_mode_was = frappe.conf.developer_mode
        cls.workbook = create_test_workbook(OWNER, title=PREFIX).name

        # a module the site made: a `Module Def` row that no app's `modules.txt`
        # lists
        if not frappe.db.exists("Module Def", SITE_MODULE):
            frappe.get_doc(
                {
                    "doctype": "Module Def",
                    "module_name": SITE_MODULE,
                    "app_name": "insights",
                    "custom": 1,
                }
            ).insert(ignore_permissions=True)

    @classmethod
    def after_class(cls):
        frappe.conf.developer_mode = cls.developer_mode_was
        frappe.db.set_value(DT.WORKBOOK, cls.workbook, "is_standard", 0)
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        frappe.delete_doc("Module Def", SITE_MODULE, force=True, ignore_permissions=True)

    # @feature standard.read-only
    def test_a_request_cannot_mark_a_workbook_shipped(self):
        """A standard workbook lets its charts read tables the site denies their
        author."""
        frappe.conf.developer_mode = 0

        with self.assertRaises(frappe.ValidationError):
            frappe.client.set_value(DT.WORKBOOK, self.workbook, {"is_standard": 1, "module": "Insights"})

        self.assertFalse(frappe.db.get_value(DT.WORKBOOK, self.workbook, "is_standard"))

    # @feature standard.mark
    def test_a_workbook_cannot_ship_in_a_module_no_app_ships(self):
        """Migrate never reads a file in such a module, so the next migrate
        deletes the workbook."""
        frappe.conf.developer_mode = 1

        workbook = frappe.get_doc(DT.WORKBOOK, self.workbook)
        workbook.is_standard = 1
        workbook.module = SITE_MODULE

        with self.assertRaises(frappe.ValidationError):
            workbook.save(ignore_permissions=True)

        self.assertFalse(frappe.db.get_value(DT.WORKBOOK, self.workbook, "is_standard"))

    # @feature standard.mark
    def test_a_member_never_takes_a_name_a_dashboard_route_answers_to(self):
        """`resolver.resolve` tries a docname before a route. If a shipped
        dashboard's name equals a site dashboard's route, it takes over every
        link to that route, such as a workspace sidebar item."""
        other = create_test_workbook(OWNER, title=f"{PREFIX} Other")
        mine = create_test_workbook(OWNER, title=f"{PREFIX} Mine")
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, other.name, force=True)
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, mine.name, force=True)

        taken = f"{mine.name}-sales"
        squatter = create_test_dashboard(OWNER, other.name, title=f"{PREFIX} Squatter")
        frappe.db.set_value(DT.DASHBOARD, squatter.name, "route", taken)

        create_test_dashboard(OWNER, mine.name, title="Sales")

        minted = {new for _, _, new in _rename_members(mine.name)}

        self.assertIn(f"{taken}-2", minted)
        self.assertNotIn(taken, minted)

    # @feature standard.resync
    def test_a_file_cannot_take_over_a_member_another_workbook_holds(self):
        """A member is named `<workbook>-<title slug>`. Only the bench that
        wrote the file checks the name is unique, so a site with two apps can
        hold a collision that neither bench saw. Reusing the row would move the
        other app's chart into this workbook without warning."""
        holder = create_test_workbook(OWNER, title=f"{PREFIX} Holder")
        taker = create_test_workbook(OWNER, title=f"{PREFIX} Taker")
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, holder.name, force=True)
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, taker.name, force=True)

        contested = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "name": "standard-guard-contested",
                "title": "Contested",
                "workbook": holder.name,
                "use_live_connection": 0,
                "is_script_query": 1,
                "operations": [{"type": "code", "code": "results = []"}],
            }
        ).insert(set_name="standard-guard-contested")

        file = {
            "queries": {
                contested.name: {
                    "title": "Contested",
                    "use_live_connection": 0,
                    "is_script_query": 1,
                    "operations": [{"type": "code", "code": "results = []"}],
                }
            }
        }

        with self.assertRaises(frappe.ValidationError):
            taker.restore_workbook_contents(
                frappe.as_json(file), taker.name, ignore_permissions=True, keep_names=True
            )

        self.assertEqual(frappe.db.get_value(DT.QUERY, contested.name, "workbook"), holder.name)

    # @feature standard.resync
    def test_a_file_cannot_take_the_address_a_site_dashboard_answers_to(self):
        """A dashboard is found by its docname or its route, and
        `resolver.resolve` tries the docname first. Only the receiving site can
        see a collision between the two, so the site must check for it."""
        holder = create_test_workbook(OWNER, title=f"{PREFIX} Route Holder")
        taker = create_test_workbook(OWNER, title=f"{PREFIX} Route Taker")
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, holder.name, force=True)
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, taker.name, force=True)

        answering = create_test_dashboard(OWNER, holder.name, title="Standard Guard Route")
        self.assertEqual(answering.route, "standard-guard-route")

        file = {"dashboards": {"standard-guard-route": {"title": "Standard Guard Route", "items": []}}}

        with self.assertRaises(frappe.ValidationError):
            taker.restore_workbook_contents(
                frappe.as_json(file), taker.name, ignore_permissions=True, keep_names=True
            )

        self.assertFalse(frappe.db.exists(DT.DASHBOARD, "standard-guard-route"))
        self.assertEqual(frappe.db.get_value(DT.DASHBOARD, answering.name, "route"), "standard-guard-route")
