"""The guards on a workbook that claims to be shipped.

Two ordinary columns decide a lot. `is_standard` is what `insights/standard.py`
reads to let a chart past the site's team grants and its Table Restrictions, and
`module` decides whether the next migrate finds the workbook's file at all - or
deletes it as an orphan, taking every query, chart, dashboard and folder in it.
`frappe.client.set_value` reaches both and enforces no `read_only`, so both are
refused on the document.
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

        # a module the site made for itself: a `Module Def` row, and in no app's
        # `modules.txt`
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
        """Marking it is what lets every chart in it read the tables the site
        denies its author."""
        frappe.conf.developer_mode = 0

        with self.assertRaises(frappe.ValidationError):
            frappe.client.set_value(DT.WORKBOOK, self.workbook, {"is_standard": 1, "module": "Insights"})

        self.assertFalse(frappe.db.get_value(DT.WORKBOOK, self.workbook, "is_standard"))

    # @feature standard.mark
    def test_a_workbook_cannot_ship_in_a_module_no_app_ships(self):
        """The file would land where a migrate never looks, and
        the next migrate deletes the workbook it belongs to."""
        frappe.conf.developer_mode = 1

        workbook = frappe.get_doc(DT.WORKBOOK, self.workbook)
        workbook.is_standard = 1
        workbook.module = SITE_MODULE

        with self.assertRaises(frappe.ValidationError):
            workbook.save(ignore_permissions=True)

        self.assertFalse(frappe.db.get_value(DT.WORKBOOK, self.workbook, "is_standard"))

    # @feature standard.mark
    def test_a_member_never_takes_a_name_a_dashboard_route_answers_to(self):
        """`resolver.resolve` tries a docname before a route, so a shipped
        dashboard named onto a site dashboard's route takes over every link that
        used it - a workspace sidebar item is the whole reason routes exist."""
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
        """A member is named `<workbook>-<title slug>`, deduped on the bench
        that wrote the file and nowhere else, so a site that installs two apps
        can hold a collision neither authoring bench could see. Reusing the row
        re-parents the other app's chart and its dashboard silently draws it."""
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
        """A dashboard answers to its route as well as to its docname, and
        `resolver.resolve` tries the docname first. The receiving site is the
        only place a collision between the two is visible, so it is the site
        that has to look."""
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
