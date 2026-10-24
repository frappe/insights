"""What the preview browser opens, and what its key opens in return.

Generating a preview image starts a browser on the server and hands it a key,
because the dashboard it renders is not public. Two things follow. The page it
opens must be this site's, not one a request header named. And the key must open
the documents that image already shows, not every document a public link could.
"""

import io
import os
from unittest.mock import patch

import frappe
from PIL import Image
from werkzeug.test import EnvironBuilder

from insights.api.dashboards import get_dashboards
from insights.api.view import get_dashboard, get_dashboard_preview
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
from insights.insights.doctype.insights_team.insights_team import clear_cache as clear_team_cache
from insights.permission_user import permission_user_for
from insights.permissions import has_doc_permission, same_rows_for_every_reader
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    as_user,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
    delete_users,
)
from insights.tests.permissions_utils import (
    NON_INSIGHTS_USER,
    USER_1,
    USER_2,
    create_test_team,
    create_test_users,
    update_dashboard_access,
)

OWNER = USER_1
ATTACKER_HOST = "attacker.example"


class TestDashboardPreview(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_test_users()
        cls.workbook = create_test_workbook(OWNER, title="Preview Workbook").name
        cls.query = create_test_query(OWNER, cls.workbook, title="Preview Query").name
        cls.chart = create_test_chart(OWNER, cls.workbook, query=cls.query, title="Preview Chart").name
        cls.dashboard = create_test_dashboard(
            OWNER, cls.workbook, chart=cls.chart, title="Preview Dashboard"
        ).name

        cls.other_workbook = create_test_workbook(OWNER, title="Unpreviewed Workbook").name
        cls.other_query = create_test_query(OWNER, cls.other_workbook, title="Unpreviewed Query").name
        cls.other_chart = create_test_chart(
            OWNER, cls.other_workbook, query=cls.other_query, title="Unpreviewed Chart"
        ).name
        cls.other_dashboard = create_test_dashboard(
            OWNER, cls.other_workbook, chart=cls.other_chart, title="Unpreviewed Dashboard"
        ).name

    @classmethod
    def after_class(cls):
        for workbook in (cls.workbook, cls.other_workbook):
            frappe.delete_doc(DT.WORKBOOK, workbook, force=True, ignore_permissions=True)
        delete_users(OWNER)

    def before_test(self):
        self.request_was = getattr(frappe.local, "request", None)
        self.addCleanup(setattr, frappe.local, "request", self.request_was)
        frappe.local.request = EnvironBuilder(headers={"Host": ATTACKER_HOST}).get_request()

    def reads_with_key(self, key, doctype, name):
        request_was = frappe.local.request
        frappe.local.request = EnvironBuilder(headers={"X-Insights-Preview-Key": key}).get_request()
        try:
            return bool(has_doc_permission(frappe.get_doc(doctype, name), "read", "Guest"))
        finally:
            frappe.local.request = request_was

    def as_render(self, key, run):
        """Run `run` the way the preview browser does: as Guest, with the key."""
        request_was = frappe.local.request
        user_was = frappe.session.user
        frappe.local.request = EnvironBuilder(headers={"X-Insights-Preview-Key": key}).get_request()
        frappe.set_user("Guest")
        try:
            return run()
        finally:
            frappe.set_user(user_was)
            frappe.local.request = request_was

    def render(self, dashboard):
        """Run a preview and return the URL opened and the key it passed."""
        opened = {}

        def record(url, headers=None):
            opened["url"] = url
            opened["key"] = (headers or {})["X-Insights-Preview-Key"]
            # what the browser sees when it comes back with the key
            opened["reads"] = {
                (doctype, name): self.reads_with_key(opened["key"], doctype, name)
                for doctype, name in (
                    (DT.DASHBOARD, self.dashboard),
                    (DT.CHART, self.chart),
                    (DT.QUERY, self.query),
                    (DT.DASHBOARD, self.other_dashboard),
                    (DT.CHART, self.other_chart),
                    (DT.QUERY, self.other_query),
                )
            }
            # the preview page loads through the viewer like any other reader,
            # and its charts run as the user the key was made for
            opened["viewer_title"] = self.as_render(
                opened["key"], lambda: get_dashboard(self.dashboard)["title"]
            )
            opened["runs_as"] = {
                name: self.as_render(
                    opened["key"],
                    lambda name=name: permission_user_for(frappe.get_doc(DT.CHART, name)),
                )
                for name in (self.chart, self.other_chart)
            }
            return b"preview"

        doc = frappe.get_doc(DT.DASHBOARD, dashboard)
        with (
            patch(
                "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.get_page_preview",
                side_effect=record,
            ),
            patch(
                "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.create_preview_file",
                return_value="/files/preview.jpeg",
            ),
        ):
            doc.generate_dashboard_preview()
        return opened

    # @feature dashboard.preview-image
    def test_the_browser_opens_this_site(self):
        self.assertNotIn(ATTACKER_HOST, self.render(self.dashboard)["url"])

    # @feature dashboard.preview-image
    def test_the_key_opens_the_dashboard_being_previewed(self):
        reads = self.render(self.dashboard)["reads"]
        self.assertTrue(reads[(DT.DASHBOARD, self.dashboard)])
        self.assertTrue(reads[(DT.CHART, self.chart)])
        self.assertTrue(reads[(DT.QUERY, self.query)])

    # @feature dashboard.preview-image
    def test_the_key_opens_nothing_else(self):
        reads = self.render(self.dashboard)["reads"]
        self.assertFalse(reads[(DT.DASHBOARD, self.other_dashboard)])
        self.assertFalse(reads[(DT.CHART, self.other_chart)])
        self.assertFalse(reads[(DT.QUERY, self.other_query)])

    # @feature dashboard.preview-image
    def test_the_previewed_page_reads_through_the_viewer(self):
        self.assertEqual(self.render(self.dashboard)["viewer_title"], "Preview Dashboard")

    # @feature dashboard.preview-image
    def test_the_render_runs_as_the_dashboards_owner_whoever_asks(self):
        """Administrator asks here. Under the rule the owner's rows are the
        ones every reader sees."""
        runs_as = self.render(self.dashboard)["runs_as"]
        self.assertEqual(runs_as[self.chart], OWNER)
        # a chart the key does not open runs as the caller
        self.assertEqual(runs_as[self.other_chart], "Guest")

    # @feature dashboard.preview-image
    def test_a_spent_key_opens_nothing(self):
        opened = self.render(self.dashboard)
        frappe.local.request = EnvironBuilder(headers={"X-Insights-Preview-Key": opened["key"]}).get_request()
        dashboard = frappe.get_doc(DT.DASHBOARD, self.dashboard)
        self.assertFalse(has_doc_permission(dashboard, "read", "Guest"))

    # @feature dashboard.preview-image
    def test_an_apps_dashboard_renders_no_preview(self):
        """A preview shows its renderer's rows to every reader, and an app's
        dashboard is read by roles whose members may see other rows."""
        frappe.db.set_value(DT.WORKBOOK, self.other_workbook, "is_standard", 1)
        self.addCleanup(frappe.db.set_value, DT.WORKBOOK, self.other_workbook, "is_standard", 0)
        self.assertEqual(self.render(self.other_dashboard), {})

    # @feature dashboard.preview-image
    def test_the_patch_deletes_the_preview_file_of_an_apps_dashboard(self):
        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
            create_preview_file,
        )
        from insights.patches import clear_standard_dashboard_previews

        image = io.BytesIO()
        Image.new("RGB", (2, 2)).save(image, "JPEG")
        file_url = create_preview_file(image.getvalue(), self.other_dashboard)
        frappe.db.set_value(DT.DASHBOARD, self.other_dashboard, "preview_image", f"{file_url}?ab12")
        frappe.db.set_value(DT.WORKBOOK, self.other_workbook, "is_standard", 1)
        self.addCleanup(frappe.db.set_value, DT.WORKBOOK, self.other_workbook, "is_standard", 0)

        clear_standard_dashboard_previews.execute()

        self.assertIsNone(frappe.db.get_value(DT.DASHBOARD, self.other_dashboard, "preview_image"))
        self.assertFalse(frappe.db.exists("File", {"file_url": file_url}))

    # @feature dashboard.preview-image
    def test_a_page_that_does_not_answer_is_not_captured(self):
        """Chromium captures its own error page, which was saved as the preview."""
        import requests

        from insights.insights.doctype.insights_dashboard_v3 import insights_dashboard_v3

        with (
            patch.object(requests, "get", side_effect=requests.ConnectionError("refused")),
            patch("frappe.utils.preview.get_preview_from_url", return_value=b"error page") as capture,
        ):
            with self.assertRaises(frappe.ValidationError):
                insights_dashboard_v3.get_page_preview("http://site.localhost:8000/insights/shared/x")

        capture.assert_not_called()


READER = USER_2
EXTERNAL = frappe.scrub("Same Rows DuckDB")


class TestSameRowsForEveryReader(InsightsIntegrationTestCase):
    """A preview shows the rows of the user it was rendered for. It may show to
    every reader of a dashboard only when they would all see those rows."""

    SAVEPOINT = "test_same_rows_for_every_reader"

    @classmethod
    def before_class(cls):
        create_test_users()
        frappe.get_doc(
            {
                "doctype": DT.DATA_SOURCE,
                "title": "Same Rows DuckDB",
                "database_type": "DuckDB",
                "database_name": "same_rows_test_duckdb",
            }
        ).insert()
        for table in ("orders", "customers"):
            frappe.get_doc(
                {"doctype": DT.TABLE, "table": table, "label": table, "data_source": EXTERNAL}
            ).insert()

    @classmethod
    def after_class(cls):
        if frappe.db.exists(DT.DATA_SOURCE, EXTERNAL):
            frappe.delete_doc(DT.DATA_SOURCE, EXTERNAL, force=True)
        delete_users(OWNER, READER, NON_INSIGHTS_USER)

    def board(self, run_as_owner=(False,), table="tabToDo"):
        """A Private dashboard of OWNER's on `table`, with one chart per entry of `run_as_owner`."""
        workbook = create_test_workbook(OWNER, title="Same Rows Workbook").name
        source = {"type": "table", "data_source": "Site DB", "table_name": table}
        query = create_test_query(
            OWNER, workbook, title="Same Rows Query", operations=[{"type": "source", "table": source}]
        ).name
        charts = []
        for runs_as_owner in run_as_owner:
            chart = create_test_chart(OWNER, workbook, query=query, title="Same Rows Chart")
            if runs_as_owner:
                with as_user(OWNER):
                    chart.run_as_owner = 1
                    chart.save()
            charts.append(chart.name)
        items = [{"id": f"chart-{i}", "type": "chart", "chart": chart} for i, chart in enumerate(charts)]
        return create_test_dashboard(OWNER, workbook, title="Same Rows Dashboard", items=items)

    def holds(self, dashboard) -> bool:
        return dashboard.name in same_rows_for_every_reader([dashboard.name])

    def share_with_role(self, dashboard):
        with as_user(OWNER):
            dashboard.reload()
            dashboard.visibility = "Roles"
            dashboard.append("visible_to_roles", {"role": "Insights User"})
            dashboard.save()

    # @feature dashboard.preview-same-rows
    def test_a_dashboard_only_its_owner_reads_shows_one_preview(self):
        self.assertTrue(self.holds(self.board()))

    # @feature dashboard.preview-same-rows
    def test_any_grant_to_another_user_takes_the_preview_away(self):
        def dashboard_share(dashboard):
            with as_user(OWNER):
                update_dashboard_access(dashboard.name, [READER])

        def workbook_share(dashboard, everyone=0):
            frappe.share.add(
                DT.WORKBOOK,
                dashboard.workbook,
                user=None if everyone else READER,
                everyone=everyone,
                notify=0,
            )

        def visibility(level):
            return lambda dashboard: frappe.db.set_value(DT.DASHBOARD, dashboard.name, "visibility", level)

        def team_grant(dashboard):
            create_test_team("same-rows-team", [READER], grants=[(DT.DASHBOARD, dashboard.name)])

        for label, grant in (
            ("shared with a user", dashboard_share),
            ("shown to a role", self.share_with_role),
            ("workbook shared with a user", workbook_share),
            ("workbook shared with everyone", lambda dashboard: workbook_share(dashboard, everyone=1)),
            ("shown to everyone", visibility("Everyone")),
            ("public link", visibility("Public")),
            ("granted to a team", team_grant),
        ):
            with self.subTest(label):
                dashboard = self.board()
                grant(dashboard)
                self.assertFalse(self.holds(dashboard))

    # @feature dashboard.preview-same-rows
    def test_a_shared_dashboard_whose_charts_all_run_as_their_owner_shows_one_preview(self):
        dashboard = self.board(run_as_owner=(True, True))
        self.share_with_role(dashboard)
        self.assertTrue(self.holds(dashboard))

    # @feature dashboard.preview-same-rows
    def test_one_chart_that_runs_as_its_reader_takes_the_preview_away(self):
        dashboard = self.board(run_as_owner=(True, False))
        self.share_with_role(dashboard)
        self.assertFalse(self.holds(dashboard))

    # @feature dashboard.preview-same-rows
    def test_an_apps_dashboard_never_shows_a_preview(self):
        dashboard = self.board()
        frappe.db.set_value(DT.WORKBOOK, dashboard.workbook, "is_standard", 1)
        self.assertFalse(self.holds(dashboard))

    def query(self, workbook, operations) -> str:
        """A query of OWNER's in `workbook`, stored with `operations` as they are."""
        query = create_test_query(OWNER, workbook, title="Same Rows Query").name
        frappe.db.set_value(DT.QUERY, query, "operations", frappe.as_json(operations))
        return query

    def shared_board(self, workbook, queries, run_as_owner=(), config=None):
        """A dashboard of OWNER's that every signed-in user may open, with one
        chart per query. The charts at the indexes in `run_as_owner` run as OWNER."""
        items = []
        for i, query in enumerate(queries):
            chart = create_test_chart(OWNER, workbook, query=query, title="Same Rows Chart", config=config)
            if i in run_as_owner:
                with as_user(OWNER):
                    chart.run_as_owner = 1
                    chart.save()
            items.append({"id": f"chart-{i}", "type": "chart", "chart": chart.name})
        dashboard = create_test_dashboard(OWNER, workbook, title="Same Rows Dashboard", items=items)
        frappe.db.set_value(DT.DASHBOARD, dashboard.name, "visibility", "Everyone")
        return dashboard

    def holds_for(self, dashboard, user) -> bool:
        return dashboard.name in same_rows_for_every_reader([dashboard.name], user=user)

    def grant(self, user, table, restriction=None):
        """A team that grants `user` the `table` of the external source."""
        team = create_test_team(f"same-rows-{frappe.generate_hash(length=6)}", [user])
        team.append(
            "team_permissions",
            {
                "resource_type": DT.TABLE,
                "resource_name": get_table_name(EXTERNAL, table),
                "table_restrictions": restriction,
            },
        )
        team.save(ignore_permissions=True)
        clear_team_cache()
        self.addCleanup(clear_team_cache)

    # @feature dashboard.preview-same-rows
    def test_a_shared_dashboard_on_another_data_source_shows_one_preview(self):
        """Only desk and Table Restrictions give readers other rows, and neither
        applies to an external table without a restriction."""
        workbook = create_test_workbook(OWNER, title="Same Rows Workbook").name
        orders = self.query(workbook, read(EXTERNAL, "orders"))
        site = self.query(workbook, read("Site DB", "tabToDo"))

        for label, queries, holds in (
            ("an external table", [orders], True),
            ("a site table", [site], False),
            ("a query that reads an external table", [self.query(workbook, read_query(orders))], True),
            ("a query that reads a site table", [self.query(workbook, read_query(site))], False),
            ("a query that no longer exists", [self.query(workbook, read_query("no-such-query"))], True),
        ):
            with self.subTest(label):
                self.assertEqual(self.holds(self.shared_board(workbook, queries)), holds)

    # @feature dashboard.preview-same-rows
    def test_one_chart_that_may_give_readers_other_rows_takes_the_preview_away(self):
        workbook = create_test_workbook(OWNER, title="Same Rows Workbook").name
        orders = self.query(workbook, read(EXTERNAL, "orders"))
        site = self.query(workbook, read("Site DB", "tabToDo"))
        script = self.query(workbook, [*read(EXTERNAL, "orders"), {"type": "code", "code": "df = df"}])

        self.assertFalse(self.holds(self.shared_board(workbook, [orders, site])))
        self.assertTrue(self.holds(self.shared_board(workbook, [orders, site], run_as_owner=(1,))))
        self.assertFalse(self.holds(self.shared_board(workbook, [orders, script])))
        self.assertFalse(
            self.holds(
                self.shared_board(workbook, [orders], config={"label": {"expression": "frappe.session.user"}})
            )
        )

    # @feature dashboard.preview-same-rows permissions.table-row-restriction
    def test_a_table_restriction_on_one_table_takes_the_preview_away(self):
        workbook = create_test_workbook(OWNER, title="Same Rows Workbook").name
        dashboard = self.shared_board(
            workbook,
            [
                self.query(workbook, read(EXTERNAL, "orders")),
                self.query(workbook, read(EXTERNAL, "customers")),
            ],
        )
        self.set_team_permissions(1)
        self.assertTrue(self.holds(dashboard))

        self.grant(READER, "customers", restriction="region == 'North'")
        self.assertFalse(self.holds(dashboard))

    # @feature dashboard.preview-same-rows permissions.team-grant
    def test_the_preview_shows_only_to_a_reader_who_may_read_its_tables(self):
        """The chart refuses such a reader, so the image would show them rows
        they may not read. The chart that runs as its owner lets them open the
        dashboard."""
        workbook = create_test_workbook(OWNER, title="Same Rows Workbook").name
        dashboard = self.shared_board(
            workbook,
            [
                self.query(workbook, read(EXTERNAL, "orders")),
                self.query(workbook, read("Site DB", "tabToDo")),
            ],
            run_as_owner=(1,),
        )
        self.with_preview(dashboard)

        self.assertTrue(self.holds_for(dashboard, READER))
        self.assertTrue(self.fetch(dashboard).startswith(b"\xff\xd8"))
        self.assertFalse(self.holds_for(dashboard, NON_INSIGHTS_USER))
        with self.assertRaises(frappe.DoesNotExistError):
            self.fetch(dashboard, user=NON_INSIGHTS_USER)

        self.set_team_permissions(1)
        self.assertFalse(self.holds_for(dashboard, READER))
        self.grant(READER, "orders")
        self.assertTrue(self.holds_for(dashboard, READER))
        self.assertTrue(self.fetch(dashboard).startswith(b"\xff\xd8"))

    # @feature dashboard.preview-same-rows dashboard.list
    def test_the_list_sends_a_preview_only_where_every_reader_sees_the_same_rows(self):
        private = self.board()
        shared = self.board()
        self.share_with_role(shared)
        for dashboard in (private, shared):
            frappe.db.set_value(
                DT.DASHBOARD,
                dashboard.name,
                "preview_image",
                f"/private/files/x.jpeg?{version_of(dashboard)}",
            )

        with as_user(OWNER):
            listed = {row.name: row for row in get_dashboards(limit=0)}

        self.assertEqual(
            listed[private.name].preview_image,
            f"/api/method/insights.api.view.get_dashboard_preview?dashboard={private.name}&v={version_of(private)}",
        )
        self.assertTrue(listed[private.name].same_rows_for_every_reader)
        self.assertIsNone(listed[shared.name].preview_image)
        self.assertFalse(listed[shared.name].same_rows_for_every_reader)

    def with_preview(self, dashboard) -> str:
        """Give `dashboard` a preview rendered from what it shows now, and return its file's URL."""
        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
            create_preview_file,
        )

        image = io.BytesIO()
        Image.new("RGB", (2, 2)).save(image, "JPEG")
        file_url = create_preview_file(image.getvalue(), dashboard.name)
        self.addCleanup(remove_file_on_disk, file_url)
        frappe.db.set_value(
            DT.DASHBOARD, dashboard.name, "preview_image", f"{file_url}?{version_of(dashboard)}"
        )
        return file_url

    def fetch(self, dashboard, user=READER) -> bytes:
        self.addCleanup(clear_download_response)
        with as_user(user):
            get_dashboard_preview(dashboard.name)
        return frappe.response.filecontent

    def downloads(self, file_url, user=READER) -> bool:
        """Whether Frappe's own `/private/files` route serves `file_url` to `user`."""
        from frappe.core.doctype.file.utils import find_file_by_url

        with as_user(user):
            return bool(find_file_by_url(file_url))

    # @feature dashboard.preview-same-rows
    def test_no_preview_is_rendered_where_readers_see_different_rows(self):
        from insights.api.dashboards import update_dashboard_preview

        shared = self.board()
        self.share_with_role(shared)
        with patch(
            "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.get_page_preview"
        ) as capture:
            self.assertIsNone(frappe.get_doc(DT.DASHBOARD, shared.name).generate_dashboard_preview())
            with as_user(OWNER), self.assertRaises(frappe.ValidationError):
                update_dashboard_preview(shared.name)
        capture.assert_not_called()

    # @feature dashboard.preview-image
    def test_no_preview_is_rendered_of_a_dashboard_its_owner_cannot_read(self):
        """The page refuses such a dashboard, and the browser captured the
        sign-in page it falls back to."""
        from insights.api.dashboards import update_dashboard_preview

        dashboard = self.board(table="tabError Log")
        self.assertTrue(self.holds(dashboard))
        with patch(
            "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.get_page_preview"
        ) as capture:
            self.assertIsNone(frappe.get_doc(DT.DASHBOARD, dashboard.name).generate_dashboard_preview())
            with as_user(OWNER), self.assertRaises(frappe.ValidationError):
                update_dashboard_preview(dashboard.name)
        capture.assert_not_called()
        self.assertFalse(frappe.db.get_value(DT.DASHBOARD, dashboard.name, "preview_image"))

    # @feature dashboard.preview-same-rows
    def test_a_reader_fetches_a_preview_only_while_every_reader_sees_the_same_rows(self):
        shared = self.board(run_as_owner=(True,))
        self.share_with_role(shared)
        self.with_preview(shared)
        self.assertTrue(self.fetch(shared).startswith(b"\xff\xd8"))

        with as_user(OWNER):
            shared.reload()
            chart = frappe.get_doc(DT.CHART, shared.linked_charts[0].chart)
            chart.run_as_owner = 0
            chart.save()
        with self.assertRaises(frappe.DoesNotExistError):
            self.fetch(shared)

    # @feature dashboard.preview-image
    def test_a_render_shows_until_a_chart_on_it_changes(self):
        dashboard = self.board()
        image = io.BytesIO()
        Image.new("RGB", (2, 2)).save(image, "JPEG")
        with patch(
            "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.get_page_preview",
            return_value=image.getvalue(),
        ):
            file_url = frappe.get_doc(DT.DASHBOARD, dashboard.name).generate_dashboard_preview()
        self.addCleanup(remove_file_on_disk, file_url.partition("?")[0])
        self.assertTrue(self.listed(dashboard).preview_image)

        frappe.db.set_value(DT.CHART, dashboard.linked_charts[0].chart, "config", frappe.as_json({"x": 1}))
        self.assertIsNone(self.listed(dashboard).preview_image)

    def listed(self, dashboard, user=OWNER):
        with as_user(user):
            return next(row for row in get_dashboards(limit=0) if row.name == dashboard.name)

    # @feature dashboard.preview-same-rows
    def test_a_preview_drawn_before_its_chart_moved_to_another_owner_shows_to_nobody(self):
        """A chart that runs as its owner shows its new owner's rows."""
        shared = self.board(run_as_owner=(True,))
        self.share_with_role(shared)
        self.with_preview(shared)
        self.assertTrue(self.listed(shared).preview_image)

        frappe.db.set_value(
            DT.CHART, shared.linked_charts[0].chart, "owner", "Administrator", update_modified=False
        )
        self.assertIsNone(self.listed(shared).preview_image)

    # @feature dashboard.preview-same-rows
    def test_a_preview_drawn_before_its_query_changed_shows_to_nobody(self):
        """It shows the rows of the charts it was drawn from, which only its
        owner could read."""
        dashboard = self.board()
        self.with_preview(dashboard)
        query = frappe.db.get_value(DT.CHART, dashboard.linked_charts[0].chart, "query")
        frappe.db.set_value(DT.QUERY, query, "operations", frappe.as_json(read(EXTERNAL, "orders")))
        frappe.db.set_value(DT.DASHBOARD, dashboard.name, "visibility", "Everyone")
        self.assertTrue(self.holds_for(dashboard, READER))

        self.assertIsNone(self.listed(dashboard, READER).preview_image)
        with self.assertRaises(frappe.DoesNotExistError):
            self.fetch(dashboard)

    # @feature dashboard.preview-same-rows
    def test_a_user_who_cannot_open_the_dashboard_cannot_fetch_its_preview(self):
        private = self.board()
        self.with_preview(private)
        self.assertTrue(self.fetch(private, user=OWNER))
        with self.assertRaises(frappe.PermissionError):
            self.fetch(private)

    # @feature dashboard.preview-same-rows
    def test_a_reader_of_the_dashboard_cannot_download_its_preview_file(self):
        """Frappe serves an attachment to every reader of its document, so the
        preview file belongs to none."""
        dashboard = self.board()
        file_url = self.with_preview(dashboard)
        with as_user(OWNER):
            update_dashboard_access(dashboard.name, [READER])

        self.assertFalse(self.downloads(file_url))
        self.assertFalse(self.downloads(file_url, user=OWNER))

    # @feature dashboard.preview-same-rows
    def test_the_patch_detaches_a_preview_file_from_its_dashboard(self):
        from insights.patches import detach_dashboard_previews

        dashboard = self.board()
        copy = self.board()
        file_url = self.with_preview(dashboard)
        attached = frappe.get_doc("File", {"file_url": file_url})
        attached.db_set({"attached_to_doctype": DT.DASHBOARD, "attached_to_name": dashboard.name})
        frappe.db.set_value(DT.DASHBOARD, copy.name, "preview_image", f"{file_url}?cd34")
        with as_user(OWNER):
            update_dashboard_access(dashboard.name, [READER])
        self.assertTrue(self.downloads(file_url))

        detach_dashboard_previews.execute()

        self.assertFalse(self.downloads(file_url))
        self.assertEqual(
            frappe.db.get_value(DT.DASHBOARD, dashboard.name, "preview_image"),
            f"{file_url}?{version_of(dashboard)}",
        )
        self.assertIsNone(frappe.db.get_value(DT.DASHBOARD, copy.name, "preview_image"))

    # @feature dashboard.preview-same-rows
    def test_deleting_a_dashboard_deletes_its_preview_file(self):
        dashboard = self.board()
        file_url = self.with_preview(dashboard)
        frappe.delete_doc(DT.DASHBOARD, dashboard.name, force=True, ignore_permissions=True)
        self.assertFalse(frappe.db.exists("File", {"file_url": file_url}))


def version_of(dashboard) -> str:
    from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import preview_versions

    return preview_versions([dashboard.name])[dashboard.name]


def read(data_source, table):
    return [{"type": "source", "table": {"type": "table", "data_source": data_source, "table_name": table}}]


def read_query(query):
    return [{"type": "source", "table": {"type": "query", "workbook": "", "query_name": query}}]


def remove_file_on_disk(file_url):
    path = frappe.get_site_path(file_url.lstrip("/"))
    if os.path.exists(path):
        os.remove(path)


def clear_download_response():
    for key in ("type", "display_content_as", "filename", "filecontent"):
        frappe.response.pop(key, None)
