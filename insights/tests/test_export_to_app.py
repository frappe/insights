"""Export to app, and the developer-mode round trip.

The fixture content is authored the way a developer authors it — an ordinary
workbook with a query, a chart and a dashboard — and exported into the Insights
app's own `insights/` directory, the same place any other app would ship a
workbook from.

The invariant the whole file circles is that after an export the site's
documents *are* the app's standard documents: a sync straight afterwards has
nothing to do.

`write_back` runs on `on_update`, which `hooks.py` must register for every
reconciled doctype (see `write_back_hooked`). The tests install it on the live
hook table so they exercise the real save path either way.
"""

import json
import os
import shutil
from contextlib import contextmanager

import frappe

from insights import export_to_app
from insights.api.standard_content import get_export_targets
from insights.export_to_app import export_dashboard, write_back
from insights.resolver import resolve
from insights.standard_content import CARRIED_FIELDS, MANIFEST, SYNC_ORDER, sync_app_content
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT
from insights.tests.test_standard_content import developer_mode, shipped_root

APP = "insights"
FOLDER = "export_test"
OTHER_FOLDER = "export_test_alt"

BASE_TITLE = "Export Test Todos"
SOURCE_TITLE = "Export Test Sales"
CHART_TITLE = "Export Test Sales Chart"
DASHBOARD_TITLE = "Export Test Sales Overview"

BASE = "export-test-todos"
SOURCE = "export-test-sales"
CHART = "export-test-sales-chart"
DASHBOARD = "export-test-sales-overview"

FILES = {
    BASE: f"query/{BASE}.json",
    SOURCE: f"query/{SOURCE}.json",
    CHART: f"chart/{CHART}.json",
    DASHBOARD: f"dashboard/{DASHBOARD}.json",
}


def remove_fixtures():
    for folder in (FOLDER, OTHER_FOLDER):
        shutil.rmtree(os.path.join(shipped_root(), folder), ignore_errors=True)


@contextmanager
def write_back_hooked():
    """The `doc_events` entries `hooks.py` needs, on the live hook table.

    One per reconciled doctype, the workbook included: its file is the folder's
    manifest, and a retitle that never reached it would be reverted by the next
    sync.

    Standard content is only editable on a developer bench, so this is the one
    place the round trip can be exercised end to end — through a real save,
    not by calling the handler.
    """
    hooks = frappe.get_doc_hooks()
    handler = "insights.export_to_app.write_back"
    added = []
    for doctype in SYNC_ORDER:
        handlers = hooks.setdefault(doctype, {}).setdefault("on_update", [])
        if handler not in handlers:
            handlers.append(handler)
            added.append(handlers)
    try:
        yield
    finally:
        for handlers in added:
            handlers.remove(handler)


class TestExportToApp(InsightsIntegrationTestCase):
    SAVEPOINT = "test_insights_export_to_app"

    @classmethod
    def before_class(cls):
        # a crashed run can leave the fixture behind; it is a fixed name
        remove_fixtures()

    @classmethod
    def after_class(cls):
        remove_fixtures()

    def before_test(self):
        # export is an authoring surface, and authoring shipped content happens
        # on a developer bench and nowhere else
        on = developer_mode(True)
        on.__enter__()
        self.addCleanup(on.__exit__, None, None, None)

        self.workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": "Export Test Workbook"}).insert()
        self.base = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": BASE_TITLE,
                "workbook": self.workbook.name,
                "use_live_connection": 1,
                "is_builder_query": 1,
                "operations": [
                    {
                        "type": "source",
                        "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
                    }
                ],
            }
        ).insert()
        # the chart reads a query that reads another one — the reference chain
        # export has to follow
        self.source = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": SOURCE_TITLE,
                "workbook": self.workbook.name,
                "use_live_connection": 1,
                "is_builder_query": 1,
                "operations": [
                    {
                        "type": "source",
                        "table": {
                            "type": "query",
                            "query_name": self.base.name,
                            "workbook": self.workbook.name,
                        },
                    }
                ],
            }
        ).insert()
        self.chart = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": CHART_TITLE,
                "workbook": self.workbook.name,
                "query": self.source.name,
                "chart_type": "Bar",
                # counts the source query's rows by status: the least a Bar chart
                # can carry and still draw
                "config": {
                    "x_axis": {"dimension": {"column_name": "status", "data_type": "String"}},
                    "y_axis": {"series": []},
                },
                "visibility": "Specific Roles",
                "visible_to_roles": [{"role": "Insights User"}],
            }
        ).insert()

        self.dashboard = frappe.get_doc(
            {
                "doctype": DT.DASHBOARD,
                "title": DASHBOARD_TITLE,
                "workbook": self.workbook.name,
                "items": [
                    {
                        "type": "chart",
                        "chart": self.chart.name,
                        # what the builder leaves behind: a random grid key and
                        # the grid's own bookkeeping
                        "layout": {"i": "1geec587", "x": 0, "y": 0, "w": 20, "h": 3, "moved": False},
                    },
                    {
                        "type": "filter",
                        "filter_name": "Status",
                        "filter_type": "String",
                        "links": {self.chart.name: f"`{self.source.name}`.`status`"},
                        "layout": {"i": "1kpzltkq", "x": 0, "y": 3, "w": 4, "h": 1},
                    },
                    {
                        "type": "text",
                        "text": "Sales, month by month",
                        "layout": {"i": "2ab9x0lm", "x": 0, "y": 4, "w": 10, "h": 2},
                    },
                ],
            }
        ).insert()

    def after_test(self):
        remove_fixtures()

    # ------------------------------------------------------------- helpers

    def export(self, **kwargs):
        return export_dashboard(self.dashboard.name, APP, folder=FOLDER, **kwargs)

    def path(self, relative_path):
        return os.path.join(shipped_root(), FOLDER, relative_path)

    def content(self, name):
        with open(self.path(FILES[name])) as f:
            return f.read()

    def read(self, name):
        return json.loads(self.content(name))

    def on_disk(self):
        return {name: self.content(name) for name in FILES}

    def manifest(self):
        with open(self.path(MANIFEST)) as f:
            return f.read()

    def shipped_workbook(self):
        # the workbook's logical name is the folder it ships from
        docname = frappe.db.get_value(
            DT.WORKBOOK, {"standard_id": self.standard_id(FOLDER), "is_standard": 1}, "name"
        )
        self.assertIsNotNone(docname, f"{self.standard_id(FOLDER)} was not exported")
        return frappe.get_doc(DT.WORKBOOK, docname)

    def standard_id(self, name):
        return f"{APP}/{name}"

    def doctype_of(self, name):
        return {
            BASE: DT.QUERY,
            SOURCE: DT.QUERY,
            CHART: DT.CHART,
            DASHBOARD: DT.DASHBOARD,
        }[name]

    def doc(self, name):
        docname = frappe.db.get_value(
            self.doctype_of(name), {"standard_id": self.standard_id(name), "is_standard": 1}, "name"
        )
        self.assertIsNotNone(docname, f"{self.standard_id(name)} was not exported")
        return frappe.get_doc(self.doctype_of(name), docname)

    def all_standard_ids(self):
        return sorted(self.standard_id(name) for name in FILES)

    def dashboard_items(self):
        return frappe.parse_json(self.doc(DASHBOARD).items)

    # --------------------------------------------------------------- tests

    def test_export_writes_the_closure_and_flags_it_standard(self):
        report = self.export()

        self.assertEqual(sorted(report.standard_ids), self.all_standard_ids())
        for relative_path in FILES.values():
            self.assertTrue(os.path.isfile(self.path(relative_path)), f"{relative_path} was not written")
        with open(self.path(MANIFEST)) as f:
            self.assertEqual(json.load(f)["format_version"], 1)

        # the whole of what the format carries, and nothing else: no modified,
        # no owner, no docnames
        self.assertEqual(set(self.read(CHART)), set(CARRIED_FIELDS[DT.CHART]))
        self.assertEqual(set(self.read(SOURCE)), set(CARRIED_FIELDS[DT.QUERY]))
        self.assertEqual(set(self.read(DASHBOARD)), set(CARRIED_FIELDS[DT.DASHBOARD]))

        # references are logical names, on every edge sync remaps
        chart = self.read(CHART)
        self.assertEqual(chart["query"], SOURCE)
        self.assertEqual(chart["visible_to_roles"], ["Insights User"])

        table = self.read(SOURCE)["operations"][0]["table"]
        self.assertEqual(table["query_name"], BASE)
        self.assertEqual(table["workbook"], 0)

        items = self.read(DASHBOARD)["items"]
        self.assertEqual(items[0]["chart"], CHART)
        self.assertEqual(items[1]["links"], {CHART: f"`{SOURCE}`.`status`"})

        # and the documents are the app's now: standard, in the workbook the app
        # ships, addressable by Standard ID
        shipped = set()
        for name in FILES:
            doc = self.doc(name)
            self.assertEqual(doc.is_standard, 1)
            shipped.add(str(doc.workbook))
        self.assertEqual(len(shipped), 1)
        self.assertNotIn(str(self.workbook.name), shipped)

        self.assertEqual(resolve(DT.DASHBOARD, self.standard_id(DASHBOARD)), self.doc(DASHBOARD).name)
        self.assertEqual(resolve(DT.CHART, self.standard_id(CHART)), self.doc(CHART).name)

    def test_sync_after_export_changes_nothing(self):
        self.export()
        before = {name: self.doc(name).modified for name in FILES}

        report = sync_app_content(APP)

        self.assertFalse(report.changed, f"created {report.created}, updated {report.updated}")
        self.assertTrue(set(self.all_standard_ids()) <= set(report.unchanged))
        self.assertEqual({name: self.doc(name).modified for name in FILES}, before)

    def test_a_re_export_is_byte_identical(self):
        self.export()
        before = self.on_disk()

        report = self.export()

        self.assertEqual(self.on_disk(), before)
        self.assertEqual(report.written, [], "an export that changes nothing writes nothing")
        self.assertEqual(sorted(report.standard_ids), self.all_standard_ids())

    def test_dashboard_items_carry_stable_keys(self):
        self.export()

        keys = [item["layout"]["i"] for item in self.read(DASHBOARD)["items"]]
        self.assertEqual(keys, [f"chart-{CHART}", "filter-status", "text-3"])

        # the grid's own bookkeeping is not content
        self.assertNotIn("moved", self.read(DASHBOARD)["items"][0]["layout"])

        # and the key is on the document too, so the site and the file agree
        self.assertEqual([item["layout"]["i"] for item in self.dashboard_items()], keys)

        self.export()
        self.assertEqual([item["layout"]["i"] for item in self.read(DASHBOARD)["items"]], keys)

    def test_a_taken_logical_name_gets_a_deterministic_suffix(self):
        os.makedirs(os.path.join(shipped_root(), OTHER_FOLDER, "query"), exist_ok=True)
        with open(os.path.join(shipped_root(), OTHER_FOLDER, MANIFEST), "w") as f:
            json.dump({"title": "Export Test Alt", "required_apps": [], "format_version": 1}, f)
        with open(os.path.join(shipped_root(), OTHER_FOLDER, "query", f"{SOURCE}.json"), "w") as f:
            json.dump({"title": "Something Else Called Sales"}, f)

        report = self.export()

        self.assertIn(self.standard_id(f"{SOURCE}-2"), report.standard_ids)
        self.assertTrue(os.path.isfile(self.path(f"query/{SOURCE}-2.json")))
        self.assertEqual(self.read(CHART)["query"], f"{SOURCE}-2")

    def test_export_refuses_outside_developer_mode(self):
        with developer_mode(False):
            self.assertRaises(frappe.ValidationError, self.export)

        self.assertFalse(os.path.isdir(os.path.join(shipped_root(), FOLDER)))
        self.assertFalse(frappe.db.get_value(DT.DASHBOARD, self.dashboard.name, "is_standard"))

    def test_export_needs_the_target_app_installed(self):
        self.assertRaises(frappe.ValidationError, export_dashboard, self.dashboard.name, "no_such_app")

    def test_saving_a_standard_document_writes_its_file_back(self):
        self.export()
        before = json.loads(self.content(DASHBOARD))

        with write_back_hooked():
            dashboard = self.doc(DASHBOARD)
            dashboard.title = f"{DASHBOARD_TITLE} (revised)"
            dashboard.save()

        expected = before | {"title": f"{DASHBOARD_TITLE} (revised)"}
        # the same serializer as export, so a builder save is a one-line diff
        self.assertEqual(self.content(DASHBOARD), export_to_app.dumps(expected))

    def test_retitling_a_standard_workbook_writes_its_manifest_back(self):
        self.export()
        before = json.loads(self.manifest())
        revised = "Export Test Workbook (revised)"

        with write_back_hooked():
            workbook = self.shipped_workbook()
            workbook.title = revised
            workbook.save()

        # the title is the manifest's only shipped key; `required_apps` and
        # `format_version` are shipping metadata that never reach the document,
        # and a save must not be able to drop them
        self.assertEqual(self.manifest(), export_to_app.dumps(before | {"title": revised}))
        manifest = json.loads(self.manifest())
        self.assertEqual(manifest["title"], revised)
        self.assertEqual(manifest["required_apps"], before["required_apps"])
        self.assertEqual(manifest["format_version"], before["format_version"])

        # and the file now says what the document says, so the next migrate has
        # nothing to reconcile — the rename survives it
        report = sync_app_content(APP)
        self.assertIn(self.standard_id(FOLDER), report.unchanged)
        self.assertFalse(report.changed, f"created {report.created}, updated {report.updated}")
        self.assertEqual(self.shipped_workbook().title, revised)

    def test_nothing_is_written_back_outside_developer_mode(self):
        self.export()
        before = self.on_disk()

        with developer_mode(False), write_back_hooked():
            dashboard = self.doc(DASHBOARD)
            dashboard.title = f"{DASHBOARD_TITLE} (from a site)"
            # a site cannot edit standard content at all, and the write-back is
            # not a surface there either
            self.assertRaises(frappe.ValidationError, dashboard.save)
            self.assertFalse(write_back(dashboard))

        self.assertEqual(self.on_disk(), before)

    def test_export_targets_lists_the_apps_and_the_workbooks_they_ship(self):
        self.export()

        targets = get_export_targets()

        self.assertTrue(targets["developer_mode"])
        insights = next(app for app in targets["apps"] if app["app"] == APP)
        self.assertIn(FOLDER, [workbook["folder"] for workbook in insights["workbooks"]])
