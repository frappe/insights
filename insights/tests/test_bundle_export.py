"""Export to app, and the developer-mode round trip.

The fixture content is authored the way a developer authors it — an ordinary
workbook with a query, a chart and a dashboard — and exported into the Insights
app's own `insights/` directory, the same place any other app would ship a
bundle from.

The invariant the whole file circles is that after an export the site's
documents *are* the app's standard documents: a sync straight afterwards has
nothing to do.

`write_back` runs on `on_update`, which `hooks.py` must register (see the three
entries in `write_back_hooked`). The tests install it on the live hook table so
they exercise the real save path either way.
"""

import json
import os
import shutil
from contextlib import contextmanager

import frappe

from insights import bundle_export
from insights.api.bundles import get_export_targets
from insights.bundle_export import export_dashboard, write_back
from insights.bundles import CARRIED_FIELDS, ITEM_TYPES, sync_app_bundles
from insights.resolver import resolve
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT
from insights.tests.test_bundles import bundle_root, developer_mode

APP = "insights"
BUNDLE = "bundle_export_test"
OTHER_BUNDLE = "bundle_export_test_alt"

SOURCE_TITLE = "Bundle Export Sales"
CHART_TITLE = "Bundle Export Sales Chart"
DASHBOARD_TITLE = "Bundle Export Sales Overview"

SOURCE = "bundle-export-sales"
CHART = "bundle-export-sales-chart"
DATA_QUERY = f"{CHART}_data"
DASHBOARD = "bundle-export-sales-overview"

FILES = {
    SOURCE: f"query/{SOURCE}.json",
    DATA_QUERY: f"query/{DATA_QUERY}.json",
    CHART: f"chart/{CHART}.json",
    DASHBOARD: f"dashboard/{DASHBOARD}.json",
}


def remove_bundles():
    for folder in (BUNDLE, OTHER_BUNDLE):
        shutil.rmtree(os.path.join(bundle_root(), folder), ignore_errors=True)


@contextmanager
def write_back_hooked():
    """The three `doc_events` entries `hooks.py` needs, on the live hook table.

    Standard content is only editable on a developer bench, so this is the one
    place the round trip can be exercised end to end — through a real save,
    not by calling the handler.
    """
    hooks = frappe.get_doc_hooks()
    handler = "insights.bundle_export.write_back"
    added = []
    for doctype in ITEM_TYPES.values():
        handlers = hooks.setdefault(doctype, {}).setdefault("on_update", [])
        if handler not in handlers:
            handlers.append(handler)
            added.append(handlers)
    try:
        yield
    finally:
        for handlers in added:
            handlers.remove(handler)


class TestInsightsBundleExport(InsightsIntegrationTestCase):
    SAVEPOINT = "test_insights_bundle_export"

    @classmethod
    def before_class(cls):
        # a crashed run can leave the fixture behind; it is a fixed name
        remove_bundles()

    @classmethod
    def after_class(cls):
        remove_bundles()

    def before_test(self):
        # export is an authoring surface, and authoring bundles happens on a
        # developer bench and nowhere else
        on = developer_mode(True)
        on.__enter__()
        self.addCleanup(on.__exit__, None, None, None)

        self.workbook = frappe.get_doc(
            {"doctype": DT.WORKBOOK, "title": "Bundle Export Test Workbook"}
        ).insert()
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
                        "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
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
                "config": {"x_axis": "status"},
                "visibility": "Specific Roles",
                "visible_to_roles": [{"role": "Insights User"}],
            }
        ).insert()

        # the chart-shaped query the controller mints: untitled, and reading
        # the chart's source query — the reference chain export has to follow
        self.data_query = frappe.get_doc(DT.QUERY, self.chart.data_query)
        self.data_query.operations = [
            {
                "type": "source",
                "table": {
                    "type": "query",
                    "query_name": self.source.name,
                    "workbook": self.workbook.name,
                },
            }
        ]
        self.data_query.save()

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
        remove_bundles()

    # ------------------------------------------------------------- helpers

    def export(self, **kwargs):
        return export_dashboard(self.dashboard.name, APP, bundle=BUNDLE, **kwargs)

    def path(self, relative_path):
        return os.path.join(bundle_root(), BUNDLE, relative_path)

    def content(self, name):
        with open(self.path(FILES[name])) as f:
            return f.read()

    def read(self, name):
        return json.loads(self.content(name))

    def on_disk(self):
        return {name: self.content(name) for name in FILES}

    def logical_id(self, name):
        return f"{APP}/{name}"

    def doctype_of(self, name):
        return {
            SOURCE: DT.QUERY,
            DATA_QUERY: DT.QUERY,
            CHART: DT.CHART,
            DASHBOARD: DT.DASHBOARD,
        }[name]

    def doc(self, name):
        docname = frappe.db.get_value(
            self.doctype_of(name), {"logical_id": self.logical_id(name), "is_standard": 1}, "name"
        )
        self.assertIsNotNone(docname, f"{self.logical_id(name)} was not exported")
        return frappe.get_doc(self.doctype_of(name), docname)

    def all_logical_ids(self):
        return sorted(self.logical_id(name) for name in FILES)

    def dashboard_items(self):
        return frappe.parse_json(self.doc(DASHBOARD).items)

    # --------------------------------------------------------------- tests

    def test_export_writes_the_closure_and_flags_it_standard(self):
        report = self.export()

        self.assertEqual(sorted(report.logical_ids), self.all_logical_ids())
        for relative_path in FILES.values():
            self.assertTrue(os.path.isfile(self.path(relative_path)), f"{relative_path} was not written")
        with open(self.path("bundle.json")) as f:
            self.assertEqual(json.load(f)["format_version"], 1)

        # the whole of what the format carries, and nothing else: no modified,
        # no owner, no docnames
        self.assertEqual(set(self.read(CHART)), set(CARRIED_FIELDS[DT.CHART]))
        self.assertEqual(set(self.read(SOURCE)), set(CARRIED_FIELDS[DT.QUERY]))
        self.assertEqual(set(self.read(DASHBOARD)), set(CARRIED_FIELDS[DT.DASHBOARD]))

        # references are logical names, on every edge sync remaps
        chart = self.read(CHART)
        self.assertEqual(chart["query"], SOURCE)
        self.assertEqual(chart["data_query"], DATA_QUERY)
        self.assertEqual(chart["visible_to_roles"], ["Insights User"])

        table = self.read(DATA_QUERY)["operations"][0]["table"]
        self.assertEqual(table["query_name"], SOURCE)
        self.assertEqual(table["workbook"], 0)

        items = self.read(DASHBOARD)["items"]
        self.assertEqual(items[0]["chart"], CHART)
        self.assertEqual(items[1]["links"], {CHART: f"`{SOURCE}`.`status`"})

        # and the documents are the app's now: standard, in the bundle's
        # container workbook, addressable by logical id
        containers = set()
        for name in FILES:
            doc = self.doc(name)
            self.assertEqual(doc.is_standard, 1)
            containers.add(str(doc.workbook))
        self.assertEqual(len(containers), 1)
        self.assertNotIn(str(self.workbook.name), containers)

        self.assertEqual(resolve(DT.DASHBOARD, self.logical_id(DASHBOARD)), self.doc(DASHBOARD).name)
        self.assertEqual(resolve(DT.CHART, self.logical_id(CHART)), self.doc(CHART).name)

    def test_sync_after_export_changes_nothing(self):
        self.export()
        before = {name: self.doc(name).modified for name in FILES}

        report = sync_app_bundles(APP)

        self.assertFalse(report.changed, f"created {report.created}, updated {report.updated}")
        self.assertTrue(set(self.all_logical_ids()) <= set(report.unchanged))
        self.assertEqual({name: self.doc(name).modified for name in FILES}, before)

    def test_a_re_export_is_byte_identical(self):
        self.export()
        before = self.on_disk()

        report = self.export()

        self.assertEqual(self.on_disk(), before)
        self.assertEqual(report.written, [], "an export that changes nothing writes nothing")
        self.assertEqual(sorted(report.logical_ids), self.all_logical_ids())

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
        os.makedirs(os.path.join(bundle_root(), OTHER_BUNDLE, "query"), exist_ok=True)
        with open(os.path.join(bundle_root(), OTHER_BUNDLE, "bundle.json"), "w") as f:
            json.dump({"title": "Bundle Export Alt", "required_apps": [], "format_version": 1}, f)
        with open(os.path.join(bundle_root(), OTHER_BUNDLE, "query", f"{SOURCE}.json"), "w") as f:
            json.dump({"title": "Something Else Called Sales"}, f)

        report = self.export()

        self.assertIn(self.logical_id(f"{SOURCE}-2"), report.logical_ids)
        self.assertTrue(os.path.isfile(self.path(f"query/{SOURCE}-2.json")))
        self.assertEqual(self.read(CHART)["query"], f"{SOURCE}-2")

    def test_export_refuses_outside_developer_mode(self):
        with developer_mode(False):
            self.assertRaises(frappe.ValidationError, self.export)

        self.assertFalse(os.path.isdir(os.path.join(bundle_root(), BUNDLE)))
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
        self.assertEqual(self.content(DASHBOARD), bundle_export.dumps(expected))

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

    def test_export_targets_lists_the_apps_and_their_bundles(self):
        self.export()

        targets = get_export_targets()

        self.assertTrue(targets["developer_mode"])
        insights = next(app for app in targets["apps"] if app["app"] == APP)
        self.assertIn(BUNDLE, [bundle["folder"] for bundle in insights["bundles"]])
