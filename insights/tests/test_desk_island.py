import io
from contextlib import redirect_stdout

import frappe
import frappe.client
from frappe.desk.form.load import getdoc
from frappe.utils.island import get_ui_islands

from insights.desk import (
    DESK_ISLANDS,
    boot_app_path,
    install_custom_fields,
    island_for,
    report_dangling_claims,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
)

OWNER = "Administrator"
DESK_DASHBOARD = "Desk Island Test Dashboard"
DESK_CHART = "Desk Island Test Chart"
DASHBOARD_PAGE = "insights-dashboard"


class TestDeskIsland(InsightsIntegrationTestCase):
    SAVEPOINT = "test_desk_island"

    @classmethod
    def before_class(cls):
        install_custom_fields()

        workbook = create_test_workbook(OWNER, title="Desk Island Test Workbook")
        query = create_test_query(OWNER, workbook.name)
        cls.chart = create_test_chart(OWNER, workbook.name, query.name)
        cls.dashboard = create_test_dashboard(OWNER, workbook.name, chart=cls.chart.name)

    @classmethod
    def after_class(cls):
        for doctype in ("Dashboard", "Dashboard Chart"):
            for name in frappe.get_all(
                doctype, filters={"name": ["like", "Desk Island Test%"]}, pluck="name"
            ):
                frappe.delete_doc(doctype, name, force=True)

        frappe.delete_doc("Insights Workbook", cls.dashboard.workbook, force=True)

    def desk_dashboard(self, insights_dashboard=None):
        return frappe.get_doc(
            {
                "doctype": "Dashboard",
                "dashboard_name": DESK_DASHBOARD,
                "insights_dashboard": insights_dashboard,
            }
        ).insert()

    def desk_chart(self, insights_chart=None):
        return frappe.get_doc(
            {
                "doctype": "Dashboard Chart",
                "chart_name": DESK_CHART,
                "chart_type": "Count",
                "document_type": "ToDo",
                "based_on": "creation",
                "filters_json": "[]",
                "insights_chart": insights_chart,
            }
        ).insert()

    def onload_of(self, doctype, name):
        frappe.local.response = frappe._dict({"docs": []})
        getdoc(doctype, name)
        return frappe.response.docs[0].get("__onload") or {}

    # @feature desk.dashboard-page
    def test_the_dashboard_page_is_drawn_by_an_island_the_build_ships(self):
        page = frappe.get_doc("Page", DASHBOARD_PAGE)
        self.assertEqual(page.type, "Frappe UI")
        self.assertIn(page.island, get_ui_islands())

    # @feature desk.dashboard-page
    def test_the_dashboard_page_admits_every_desk_user(self):
        page = frappe.get_doc("Page", DASHBOARD_PAGE)
        self.assertEqual([role.role for role in page.roles], ["Desk User"])

    # @feature desk.dashboard-island desk.chart-island
    def test_island_names_are_registered(self):
        islands = get_ui_islands()
        for field in DESK_ISLANDS.values():
            self.assertIn(field["island"], islands)

    # @feature desk.dashboard-island desk.chart-island
    def test_custom_fields_are_installed(self):
        for doctype, field in DESK_ISLANDS.items():
            custom_field = frappe.get_doc("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]})
            self.assertEqual(custom_field.fieldtype, "Link")
            self.assertEqual(custom_field.options, field["options"])

    # @feature desk.dashboard-island
    def test_dashboard_without_a_link_is_not_ours(self):
        self.assertIsNone(island_for(self.desk_dashboard()))

    # @feature desk.dashboard-island
    def test_dashboard_with_a_link_is_drawn_by_the_dashboard_island(self):
        doc = self.desk_dashboard(self.dashboard.name)
        self.assertEqual(
            island_for(doc),
            {"name": "insights.dashboard", "props": {"dashboard": self.dashboard.name}},
        )

    # @feature desk.chart-island
    def test_chart_with_a_link_is_drawn_by_the_chart_island(self):
        doc = self.desk_chart(self.chart.name)
        self.assertEqual(
            island_for(doc),
            {"name": "insights.chart", "props": {"chart": self.chart.name}},
        )

    # @feature desk.chart-island
    def test_chart_without_a_link_is_not_ours(self):
        self.assertIsNone(island_for(self.desk_chart()))

    # @feature desk.dashboard-island
    def test_the_claim_rides_onload_through_getdoc(self):
        name = self.desk_dashboard(self.dashboard.name).name
        self.assertEqual(
            self.onload_of("Dashboard", name)["island"],
            {"name": "insights.dashboard", "props": {"dashboard": self.dashboard.name}},
        )

    # @feature desk.chart-island
    def test_a_chart_we_draw_carries_the_claim_through_getdoc(self):
        name = self.desk_chart(self.chart.name).name
        self.assertEqual(
            self.onload_of("Dashboard Chart", name)["island"],
            {"name": "insights.chart", "props": {"chart": self.chart.name}},
        )

    # @feature desk.dashboard-island desk.chart-island
    def test_a_desk_page_is_told_where_the_app_is_mounted(self):
        """An island builds every link it offers out of it, and a desk page is
        not the app's own page - a site that mounts Insights elsewhere would
        otherwise send every reader of an island to a path the app cannot
        route."""
        from insights.hooks import insights_path

        bootinfo = frappe._dict()
        boot_app_path(bootinfo)

        self.assertEqual(bootinfo.insights_path, f"/{insights_path}")

    # @feature desk.dashboard-island
    def test_a_dashboard_we_do_not_draw_carries_no_key(self):
        name = self.desk_dashboard().name
        # absence is the answer desk falls back on, so an empty claim would read
        # as "an island draws this" and leave the page blank
        self.assertNotIn("island", self.onload_of("Dashboard", name))

    # @feature desk.dashboard-island desk.chart-island workbook.remove-item
    def test_deleting_what_a_desk_document_draws_is_refused_naming_that_document(self):
        """The sidebar's remove calls `frappe.client.delete`. Taking the claim off
        instead would hand the desk document back to the placeholder definition
        its author filled in to save the form. The refusal comes before the
        delete changes anything: a script that catches it and commits keeps the
        chart on every dashboard that shows it."""
        workbook = self.dashboard.workbook
        chart = create_test_chart(OWNER, workbook, title="Desk Island Deleted Chart")
        dashboard = create_test_dashboard(OWNER, workbook, title="Desk Island Deleted Dashboard")
        holder = create_test_dashboard(OWNER, workbook, chart.name, title="Desk Island Holding Dashboard")
        desk_chart = self.desk_chart(chart.name)
        desk_dashboard = self.desk_dashboard(dashboard.name)

        for doctype, name, desk_doc in (
            (DT.CHART, chart.name, desk_chart),
            (DT.DASHBOARD, dashboard.name, desk_dashboard),
        ):
            with self.assertRaises(frappe.LinkExistsError) as refusal:
                frappe.client.delete(doctype, name)
            self.assertIn(desk_doc.name, str(refusal.exception))
            self.assertTrue(frappe.db.exists(doctype, name))
            self.assertIsNotNone(island_for(desk_doc.reload()))

        self.assertEqual(
            [
                item["chart"]
                for item in frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, holder.name, "items"))
            ],
            [chart.name],
        )

    # @feature desk.dashboard-island desk.chart-island workbook.delete
    def test_deleting_a_workbook_a_desk_document_draws_from_is_refused_naming_that_document(self):
        """The sidebar's workbook delete calls `frappe.client.delete`. The
        workbook deletes its members with `force`, which skips the link check a
        member's own delete is refused by."""
        workbook = create_test_workbook(OWNER, title="Desk Island Deleted Workbook")
        chart = create_test_chart(OWNER, workbook.name, title="Desk Island Deleted Chart")
        dashboard = create_test_dashboard(OWNER, workbook.name, title="Desk Island Deleted Dashboard")
        desk_chart = self.desk_chart(chart.name)
        desk_dashboard = self.desk_dashboard(dashboard.name)

        with self.assertRaises(frappe.LinkExistsError) as refusal:
            frappe.client.delete(DT.WORKBOOK, workbook.name)

        self.assertIn(desk_chart.name, str(refusal.exception))
        self.assertIn(desk_dashboard.name, str(refusal.exception))
        self.assertTrue(frappe.db.exists(DT.WORKBOOK, workbook.name))
        self.assertTrue(frappe.db.exists(DT.CHART, chart.name))
        self.assertTrue(frappe.db.exists(DT.DASHBOARD, dashboard.name))

    # @feature desk.dashboard-island desk.chart-island standard.resync
    def test_a_resync_keeps_a_dropped_member_a_desk_document_draws(self):
        """`InsightsWorkbook.after_import`, which `standard.sync` reaches on
        every migrate that ships a changed file. Dropping what a desk document
        draws would leave it linking nothing, and refusing would block the
        migrate, so the member stays with the queries it reads and its folder,
        and the keep is logged. The dashboard the desk document draws stays too;
        what nothing draws goes."""
        workbook = create_test_workbook(OWNER, title="Desk Island Resync Workbook")
        source = create_test_query(OWNER, workbook.name, title="Desk Island Resync Source")
        query = create_test_query(
            OWNER,
            workbook.name,
            title="Desk Island Resync Query",
            operations=[{"type": "source", "table": {"type": "query", "query_name": source.name}}],
        )
        chart = create_test_chart(OWNER, workbook.name, query.name, title="Desk Island Resync Chart")
        folder = frappe.get_doc(
            {"doctype": "Insights Folder", "workbook": workbook.name, "title": "Kept", "type": "chart"}
        ).insert()
        frappe.db.set_value(DT.CHART, chart.name, "folder", folder.name)
        other_query = create_test_query(OWNER, workbook.name, title="Desk Island Resync Other")
        other_chart = create_test_chart(
            OWNER, workbook.name, other_query.name, title="Desk Island Resync Other"
        )
        dashboard = create_test_dashboard(OWNER, workbook.name, chart.name, title="Desk Island Resync Board")
        other_dashboard = create_test_dashboard(OWNER, workbook.name, title="Desk Island Resync Other")
        self.desk_chart(chart.name)
        self.desk_dashboard(dashboard.name)
        logged = frappe.db.count("Error Log")

        frappe.get_doc(DT.WORKBOOK, workbook.name).restore_workbook_contents(
            {"name": workbook.name}, workbook.name, ignore_permissions=True, keep_names=True
        )

        for doctype, name in (
            (DT.QUERY, source.name),
            (DT.QUERY, query.name),
            (DT.CHART, chart.name),
            (DT.DASHBOARD, dashboard.name),
            ("Insights Folder", folder.name),
        ):
            self.assertTrue(frappe.db.exists(doctype, name), (doctype, name))
        for doctype, name in (
            (DT.QUERY, other_query.name),
            (DT.CHART, other_chart.name),
            (DT.DASHBOARD, other_dashboard.name),
        ):
            self.assertFalse(frappe.db.exists(doctype, name), (doctype, name))
        self.assertEqual(frappe.db.count("Error Log"), logged + 1)

    # @feature desk.dashboard-island standard.resync
    def test_a_resync_keeps_what_a_kept_dashboard_draws(self):
        """`InsightsWorkbook.after_import`, reached from `standard.sync`. A desk
        Dashboard claims the Insights dashboard only; the charts on it are
        claimed by nothing, and they stay with it so the desk page draws what
        it drew. A dropped chart on no kept dashboard still goes."""
        workbook = create_test_workbook(OWNER, title="Desk Island Board Workbook")
        query = create_test_query(OWNER, workbook.name, title="Desk Island Board Query")
        chart = create_test_chart(OWNER, workbook.name, query.name, title="Desk Island Board Chart")
        other_chart = create_test_chart(OWNER, workbook.name, query.name, title="Desk Island Board Other")
        dashboard = create_test_dashboard(OWNER, workbook.name, chart.name, title="Desk Island Board")
        self.desk_dashboard(dashboard.name)

        frappe.get_doc(DT.WORKBOOK, workbook.name).restore_workbook_contents(
            {"name": workbook.name}, workbook.name, ignore_permissions=True, keep_names=True
        )

        self.assertTrue(frappe.db.exists(DT.CHART, chart.name))
        self.assertTrue(frappe.db.exists(DT.QUERY, query.name))
        self.assertFalse(frappe.db.exists(DT.CHART, other_chart.name))
        self.assertEqual(
            [
                item["chart"]
                for item in frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard.name, "items"))
            ],
            [chart.name],
        )

    # @feature desk.dangling-claim
    def test_a_migrate_names_each_desk_document_left_linking_missing_insights_content(self):
        """`insights.migrate.sync_standard_workbooks`, after `standard.sync`
        deletes a workbook its app stopped shipping with every member a desk
        document draws. A desk document that links content still there is not
        named."""
        workbook = self.dashboard.workbook
        chart = create_test_chart(OWNER, workbook, title="Desk Island Gone Chart")
        dashboard = create_test_dashboard(OWNER, workbook, title="Desk Island Gone Dashboard")
        desk_chart = self.desk_chart(chart.name)
        desk_dashboard = self.desk_dashboard(dashboard.name)
        kept = frappe.get_doc(
            {
                "doctype": "Dashboard",
                "dashboard_name": f"{DESK_DASHBOARD} Kept",
                "insights_dashboard": self.dashboard.name,
            }
        ).insert()
        frappe.delete_doc(DT.CHART, chart.name, force=True)
        frappe.delete_doc(DT.DASHBOARD, dashboard.name, force=True)

        with redirect_stdout(io.StringIO()) as printed:
            report_dangling_claims()

        self.assertIn(f"Dashboard Chart {desk_chart.name} links {chart.name}", printed.getvalue())
        self.assertIn(f"Dashboard {desk_dashboard.name} links {dashboard.name}", printed.getvalue())
        self.assertNotIn(kept.name, printed.getvalue())
