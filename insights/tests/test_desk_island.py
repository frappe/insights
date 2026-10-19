import io
import json
import shutil
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import frappe
import frappe.client
from frappe.desk.form.load import getdoc
from frappe.utils import get_url_to_form, set_request
from frappe.utils.island import get_ui_islands

from insights.api import get_doc, run_doc_method
from insights.desk import (
    DESK_ISLANDS,
    boot_app_path,
    fill_shipped_claims,
    install_custom_fields,
    island_for,
    report_dangling_claims,
    shipped_files,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    USER_1,
    as_user,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
    create_user,
)

OWNER = "Administrator"
DESK_DASHBOARD = "Desk Island Test Dashboard"
DESK_CHART = "Desk Island Test Chart"
DESK_CARD = "Desk Island Test Card"
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
        for doctype in DESK_ISLANDS:
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

    def desk_card(self, insights_chart=None):
        return frappe.get_doc(
            {
                "doctype": "Number Card",
                "label": DESK_CARD,
                "type": "Document Type",
                "document_type": "ToDo",
                "function": "Count",
                "insights_chart": insights_chart,
            }
        ).insert()

    def onload_of(self, doctype, name):
        frappe.local.response = frappe._dict({"docs": []})
        getdoc(doctype, name)
        return frappe.response.docs[0].get("__onload") or {}

    def show_in_desk_as(self, user, docs):
        """What the builder menu gets from Show in Desk through `run_doc_method`."""
        set_request(method="POST", path="/api/method/insights.api.run_doc_method")
        frappe.local.response = frappe._dict({"docs": []})
        with as_user(user):
            return run_doc_method("show_in_desk", frappe.as_json(docs))

    def reads(self, user, doctype, name):
        """Whether `user` may open a desk document, and finds it in its list."""
        with as_user(user):
            return (
                frappe.has_permission(doctype, doc=frappe.get_doc(doctype, name)),
                name in frappe.get_list(doctype, filters={"name": name}, pluck="name"),
            )

    # @feature desk.dashboard-page
    def test_the_dashboard_page_is_rendered_by_an_island_the_build_ships(self):
        if not frappe.get_meta("Page").has_field("type"):
            self.skipTest(
                "frappe v16 has no page islands; https://github.com/nextchamp-saqib/insights/pull/3, Saqib, 2026-12-31"
            )
        page = frappe.get_doc("Page", DASHBOARD_PAGE)
        self.assertEqual(page.type, "Frappe UI")
        self.assertIn(page.island, get_ui_islands())

    # @feature desk.dashboard-page
    def test_the_dashboard_page_allows_every_desk_user(self):
        page = frappe.get_doc("Page", DASHBOARD_PAGE)
        self.assertEqual([role.role for role in page.roles], ["Desk User"])

    # @feature desk.dashboard-island desk.chart-island desk.number-card-island
    def test_island_names_are_registered(self):
        islands = get_ui_islands()
        for field in DESK_ISLANDS.values():
            self.assertIn(field["island"], islands)

    # @feature desk.dashboard-island desk.chart-island desk.number-card-island
    def test_every_claimed_doctype_runs_the_claim_on_load(self):
        """`hooks.py` names the doctypes again and cannot import `DESK_ISLANDS`.
        A doctype with a field and no hook keeps its own rendering."""
        for doctype in DESK_ISLANDS:
            self.assertIn("insights.desk.claim", frappe.get_doc_hooks().get(doctype, {}).get("onload", []))

    # @feature desk.dashboard-island desk.chart-island desk.number-card-island
    def test_custom_fields_are_installed(self):
        for doctype, field in DESK_ISLANDS.items():
            custom_field = frappe.get_doc("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]})
            self.assertEqual(custom_field.fieldtype, "Link")
            self.assertEqual(custom_field.options, field["options"])

    # @feature desk.dashboard-island
    def test_dashboard_without_a_link_is_not_ours(self):
        self.assertIsNone(island_for(self.desk_dashboard()))

    # @feature desk.dashboard-island
    def test_dashboard_with_a_link_is_rendered_by_the_dashboard_island(self):
        doc = self.desk_dashboard(self.dashboard.name)
        self.assertEqual(
            island_for(doc),
            {"name": "insights.dashboard", "props": {"dashboard": self.dashboard.name}},
        )

    # @feature desk.chart-island
    def test_chart_with_a_link_is_rendered_by_the_chart_island(self):
        doc = self.desk_chart(self.chart.name)
        self.assertEqual(
            island_for(doc),
            {"name": "insights.chart", "props": {"chart": self.chart.name}},
        )

    # @feature desk.dashboard-island desk.chart-island
    def test_a_document_with_its_own_definition_shows_it_once_the_insights_content_is_gone(self):
        """A shipped Dashboard keeps its classic charts. Show in Desk's own
        document has only a placeholder, so it keeps the island's Not Found."""
        workbook = self.dashboard.workbook
        chart = create_test_chart(OWNER, workbook, title="Desk Island Deleted Chart")
        dashboard = create_test_dashboard(OWNER, workbook, title="Desk Island Deleted Dashboard")
        desk_dashboard = self.desk_dashboard(dashboard.name)
        desk_chart = self.desk_chart(chart.name)
        placeholder = frappe.get_doc(
            {
                "doctype": "Dashboard Chart",
                "chart_name": f"{DESK_CHART} Placeholder",
                "insights_chart": chart.name,
            }
        ).insert()
        frappe.delete_doc(DT.CHART, chart.name, force=True)
        frappe.delete_doc(DT.DASHBOARD, dashboard.name, force=True)

        self.assertIsNone(island_for(desk_dashboard.reload()))
        self.assertIsNone(island_for(desk_chart.reload()))
        self.assertEqual(island_for(placeholder.reload())["props"], {"chart": chart.name})

    # @feature desk.chart-island
    def test_chart_without_a_link_is_not_ours(self):
        self.assertIsNone(island_for(self.desk_chart()))

    # @feature desk.number-card-island
    def test_a_number_card_we_render_includes_the_claim_through_getdoc(self):
        name = self.desk_card(self.chart.name).name
        self.assertEqual(
            self.onload_of("Number Card", name)["island"],
            {"name": "insights.chart", "props": {"chart": self.chart.name, "card": False}},
        )

    # @feature desk.number-card-island
    def test_a_number_card_we_do_not_render_gets_no_island_key(self):
        name = self.desk_card().name
        self.assertNotIn("island", self.onload_of("Number Card", name))

    # @feature desk.number-card-island
    def test_deleting_the_chart_a_number_card_shows_is_refused_naming_that_card(self):
        chart = create_test_chart(OWNER, self.dashboard.workbook, title="Desk Island Card Chart")
        card = self.desk_card(chart.name)

        with self.assertRaises(frappe.LinkExistsError) as refusal:
            frappe.client.delete(DT.CHART, chart.name)

        self.assertIn(card.name, str(refusal.exception))
        self.assertTrue(frappe.db.exists(DT.CHART, chart.name))

    # @feature desk.dashboard-island
    def test_the_claim_rides_onload_through_getdoc(self):
        name = self.desk_dashboard(self.dashboard.name).name
        self.assertEqual(
            self.onload_of("Dashboard", name)["island"],
            {"name": "insights.dashboard", "props": {"dashboard": self.dashboard.name}},
        )

    # @feature desk.chart-island
    def test_a_chart_we_render_includes_the_claim_through_getdoc(self):
        name = self.desk_chart(self.chart.name).name
        self.assertEqual(
            self.onload_of("Dashboard Chart", name)["island"],
            {"name": "insights.chart", "props": {"chart": self.chart.name}},
        )

    # @feature desk.dashboard-island desk.chart-island
    def test_a_desk_page_is_told_where_the_app_is_mounted(self):
        """An island builds its links from this path. A desk page is not the
        app's page, so a site that mounts Insights elsewhere would get links to
        a path the app cannot route."""
        from insights.hooks import insights_path

        bootinfo = frappe._dict()
        boot_app_path(bootinfo)

        self.assertEqual(bootinfo.insights_path, f"/{insights_path}")

    # @feature desk.dashboard-island
    def test_a_dashboard_we_do_not_render_gets_no_island_key(self):
        name = self.desk_dashboard().name
        # Desk uses its own rendering only when the key is absent. An empty value
        # tells desk an island renders the page, and the page stays blank.
        self.assertNotIn("island", self.onload_of("Dashboard", name))

    # @feature desk.dashboard-island desk.chart-island workbook.remove-item
    def test_deleting_what_a_desk_document_shows_is_refused_naming_that_document(self):
        """The sidebar's remove calls `frappe.client.delete`. Removing the link
        instead would return the desk document to the placeholder definition its
        author entered to save the form. The refusal comes before any change, so
        a script that catches it and commits keeps the chart on its dashboards."""
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
    def test_deleting_a_workbook_behind_a_desk_document_is_refused_naming_that_document(self):
        """The workbook deletes its members with `force`, and `force` skips the
        link check that refuses a member's own delete."""
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
    def test_a_resync_keeps_a_dropped_member_a_desk_document_shows(self):
        """A migrate resyncs every changed workbook file. Deleting a member that a
        desk document links would break the link, and refusing would block the
        migrate. So the member stays with its queries and folder, and an Error
        Log records it."""
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
        # an Error Log commits on its own, so a background job's log counts at once
        keep_log = {"method": f"Kept what a desk document uses in {workbook.name}"}
        logged = len(frappe.get_all("Error Log", filters=keep_log, pluck="name"))

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
        self.assertEqual(len(frappe.get_all("Error Log", filters=keep_log, pluck="name")), logged + 1)

    # @feature desk.dashboard-island standard.resync
    def test_a_resync_keeps_what_a_kept_dashboard_shows(self):
        """A desk Dashboard links only the Insights dashboard. Its charts stay
        with it, so the desk page still shows them."""
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
        """`standard.delete_unshipped` deletes a workbook its app no longer
        ships, even when desk documents link its members."""
        workbook = self.dashboard.workbook
        chart = create_test_chart(OWNER, workbook, title="Desk Island Gone Chart")
        dashboard = create_test_dashboard(OWNER, workbook, title="Desk Island Gone Dashboard")
        desk_chart = self.desk_chart(chart.name)
        desk_card = self.desk_card(chart.name)
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
        self.assertIn(f"Number Card {desk_card.name} links {chart.name}", printed.getvalue())
        self.assertIn(f"Dashboard {desk_dashboard.name} links {dashboard.name}", printed.getvalue())
        self.assertNotIn(kept.name, printed.getvalue())

    # @feature desk.shipped-claim
    def test_a_new_field_takes_the_claim_its_shipped_file_names(self):
        desk_dashboard = self.desk_dashboard()
        modified = frappe.db.get_value("Dashboard", desk_dashboard.name, "modified")
        file = Path(frappe.get_site_path("shipped_desk_dashboard.json"))
        file.write_text(json.dumps({"name": desk_dashboard.name, "insights_dashboard": self.dashboard.name}))
        self.addCleanup(file.unlink)
        with patch("insights.desk.shipped_files", return_value=[str(file)]):
            fill_shipped_claims("Dashboard")

        desk_dashboard.reload()
        self.assertEqual(desk_dashboard.insights_dashboard, self.dashboard.name)
        self.assertEqual(desk_dashboard.modified, modified)

    # @feature desk.shipped-claim
    def test_finds_the_files_sync_dashboards_imports(self):
        folder = Path(frappe.get_module_path("insights", "insights_dashboard"))
        self.assertFalse(folder.exists())
        self.addCleanup(shutil.rmtree, folder)
        (folder / "selling").mkdir(parents=True)
        (folder / "selling" / "selling.json").write_text("{}")
        (folder / "selling" / "notes.json").write_text("{}")

        files = shipped_files("Dashboard")

        self.assertIn(str(folder / "selling" / "selling.json"), files)
        self.assertNotIn(str(folder / "selling" / "notes.json"), files)

    # @feature desk.uninstall
    def test_the_fields_belong_to_the_insights_module(self):
        """`remove_app` deletes the Custom Fields of the module it removes, and no others."""
        for doctype, field in DESK_ISLANDS.items():
            module = frappe.db.get_value(
                "Custom Field", {"dt": doctype, "fieldname": field["fieldname"]}, "module"
            )
            self.assertEqual(module, "Insights")

    # @feature desk.shipped-claim
    def test_an_existing_field_keeps_its_values(self):
        with patch("insights.desk.fill_shipped_claims") as fill:
            install_custom_fields()
        fill.assert_not_called()

    # @feature desk.pick-chart
    def test_a_desk_chart_or_card_saves_with_only_its_name_and_the_insights_chart(self):
        """Desk's form requires a definition the island never reads. Picking an
        Insights chart leaves it empty, and the save fills it in."""
        reader = create_user(USER_1, roles=["Insights User", "Desk User"]).name
        bar = create_test_chart(OWNER, self.dashboard.workbook, title="Desk Island Test Picked")
        number = create_test_chart(
            OWNER, self.dashboard.workbook, title="Desk Island Test Picked Number", chart_type="Number"
        )
        desk_chart = frappe.get_doc(
            {
                "doctype": "Dashboard Chart",
                "chart_name": "Desk Island Test Picked",
                "insights_chart": bar.name,
            }
        ).insert()
        # desk's form sets a new card's type before the user picks anything
        desk_card = frappe.get_doc(
            {
                "doctype": "Number Card",
                "label": DESK_CARD,
                "type": "Document Type",
                "insights_chart": number.name,
            }
        ).insert()

        self.assertEqual(
            (desk_chart.chart_type, desk_chart.document_type, desk_chart.based_on, desk_chart.timeseries),
            ("Count", DT.CHART, "creation", 1),
        )
        self.assertEqual((desk_card.document_type, desk_card.function), (DT.CHART, "Count"))
        # like a document Show in Desk made, it is for the chart's readers only
        self.assertEqual(self.reads(reader, "Dashboard Chart", desk_chart.name), (False, False))
        self.assertEqual(self.reads(reader, "Number Card", desk_card.name), (False, False))

    # @feature desk.show-in-desk
    def test_show_in_desk_makes_a_dashboard_chart_that_shows_the_chart(self):
        chart = create_test_chart(OWNER, self.dashboard.workbook, title="Desk Island Test Shown")

        shown = chart.show_in_desk()

        self.assertEqual(shown["doctype"], "Dashboard Chart")
        self.assertEqual(
            self.onload_of("Dashboard Chart", shown["name"])["island"],
            {"name": "insights.chart", "props": {"chart": chart.name}},
        )
        self.assertEqual(shown["url"], get_url_to_form("Dashboard Chart", shown["name"]))

    # @feature desk.show-in-desk
    def test_what_show_in_desk_makes_belongs_to_the_insights_module(self):
        """Removing the app deletes a module's documents. Left behind, it would
        count a doctype that is gone."""
        for chart_type in ("Bar", "Number"):
            with self.subTest(chart_type=chart_type):
                chart = create_test_chart(
                    OWNER,
                    self.dashboard.workbook,
                    title=f"Desk Island Test Module {chart_type}",
                    chart_type=chart_type,
                )
                shown = chart.show_in_desk()
                self.assertEqual(frappe.db.get_value(shown["doctype"], shown["name"], "module"), "Insights")

    # @feature desk.show-in-desk
    def test_show_in_desk_makes_a_number_card_for_a_number_chart(self):
        chart = create_test_chart(
            OWNER, self.dashboard.workbook, title="Desk Island Test Shown Number", chart_type="Number"
        )

        shown = chart.show_in_desk()

        self.assertEqual(shown["doctype"], "Number Card")
        self.assertEqual(
            self.onload_of("Number Card", shown["name"])["island"],
            {"name": "insights.chart", "props": {"chart": chart.name, "card": False}},
        )

    # @feature desk.show-in-desk
    def test_show_in_desk_reads_the_saved_chart_not_the_request(self):
        chart = create_test_chart(OWNER, self.dashboard.workbook, title="Desk Island Test Shown Saved")
        sent = {**chart.as_dict(), "chart_type": "Number", "title": "Desk Island Test Shown Sent"}

        shown = self.show_in_desk_as(OWNER, sent)

        self.assertEqual(shown["doctype"], "Dashboard Chart")
        self.assertEqual(shown["name"], "Desk Island Test Shown Saved")

    # @feature desk.show-in-desk
    def test_the_builder_offers_show_in_desk_to_whoever_may_create_desk_charts(self):
        reader = create_user(USER_1, roles=["Insights User", "Desk User"]).name
        chart = create_test_chart(OWNER, self.dashboard.workbook, title="Desk Island Test Shown Offered")
        frappe.share.add(chart.doctype, chart.name, user=reader, read=1, notify=0)

        with as_user(reader):
            self.assertFalse(get_doc(chart.doctype, chart.name)["can_show_in_desk"])
        frappe.get_doc("User", reader).add_roles("Dashboard Manager")
        with as_user(reader):
            self.assertTrue(get_doc(chart.doctype, chart.name)["can_show_in_desk"])

    # @feature desk.show-in-desk
    def test_show_in_desk_again_opens_what_it_made(self):
        chart = create_test_chart(OWNER, self.dashboard.workbook, title="Desk Island Test Shown Twice")

        self.assertEqual(chart.show_in_desk(), chart.show_in_desk())

    # @feature desk.show-in-desk
    def test_charts_with_one_title_each_get_their_own_dashboard_chart(self):
        """A Dashboard Chart is named by its title, and two charts can share one."""
        first = create_test_chart(OWNER, self.dashboard.workbook, title="Desk Island Test Same Title")
        second = create_test_chart(OWNER, self.dashboard.workbook, title="Desk Island Test Same Title")

        self.assertNotEqual(first.show_in_desk()["name"], second.show_in_desk()["name"])

    # @feature desk.show-in-desk
    def test_only_readers_of_the_chart_see_what_show_in_desk_made(self):
        reader = create_user(USER_1, roles=["Insights User", "Desk User"]).name
        for chart_type in ("Bar", "Number"):
            chart = create_test_chart(
                OWNER,
                self.dashboard.workbook,
                title=f"Desk Island Test Private {chart_type}",
                chart_type=chart_type,
            )
            shown = chart.show_in_desk()
            self.assertEqual(self.reads(reader, shown["doctype"], shown["name"]), (False, False), chart_type)

            frappe.share.add(chart.doctype, chart.name, user=reader, read=1, notify=0)
            self.assertEqual(self.reads(reader, shown["doctype"], shown["name"]), (True, True), chart_type)

    # @feature desk.show-in-desk
    def test_a_desk_chart_claimed_by_hand_keeps_the_readers_of_what_it_counts(self):
        reader = create_user(USER_1, roles=["Insights User", "Desk User"]).name
        chart = create_test_chart(OWNER, self.dashboard.workbook, title="Desk Island Test Private Claimed")

        self.assertEqual(
            self.reads(reader, "Dashboard Chart", self.desk_chart(chart.name).name), (True, True)
        )
