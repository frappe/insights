"""Bundle shipping and declarative reconcile.

The fixture bundle is written to disk at runtime, inside the Insights app's own
`insights/` directory — the same place any other app would ship one. Discovery
walks genuinely installed apps, so a faked app would never be found; `insights`
is the only app a test can be sure is installed.
"""

import json
import os
import shutil
from contextlib import contextmanager

import frappe

from insights.bundles import (
    FORMAT_VERSION,
    LINK_COLUMN,
    MANIFEST,
    BundleError,
    before_app_uninstall,
    discover_bundles,
    query_references,
    sync_app_bundles,
    sync_bundles,
)
from insights.resolver import resolve
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT

APP = "insights"
BUNDLE = "bundle_sync_test"
OTHER_BUNDLE = "bundle_sync_test_alt"
BUNDLE_TITLE = "Bundle Sync Test"

BASE_QUERY = "bst_todos"
SOURCE_QUERY = "bst_sales"
CHART = "bst_sales_chart"
DASHBOARD = "bst_sales_overview"
SHIPPED = (BASE_QUERY, SOURCE_QUERY, CHART, DASHBOARD)


def bundle_root() -> str:
    return frappe.get_app_path(APP, "insights")


def bundle_files() -> dict:
    """One shipped bundle, exercising every reference the format carries."""
    return {
        f"query/{BASE_QUERY}.json": {
            "title": "Bundle Sync Todos",
            "use_live_connection": 1,
            "is_builder_query": 1,
            "operations": [
                {
                    "type": "source",
                    "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
                }
            ],
        },
        f"query/{SOURCE_QUERY}.json": {
            "title": "Bundle Sync Sales",
            "use_live_connection": 1,
            "is_builder_query": 1,
            "operations": [
                {
                    "type": "source",
                    # a query reads another query by logical name. The workbook id
                    # beside it is not part of the format, but a round-tripped
                    # export carries one, and sync repoints it at the container.
                    "table": {"type": "query", "query_name": BASE_QUERY, "workbook": 0},
                }
            ],
        },
        f"chart/{CHART}.json": {
            "title": "Bundle Sync Sales Chart",
            "query": SOURCE_QUERY,
            "chart_type": "Bar",
            # counts the source query's rows by status: the least a Bar chart can
            # carry and still draw
            "config": {
                "x_axis": {"dimension": {"column_name": "status", "data_type": "String"}},
                "y_axis": {"series": []},
            },
            "visibility": "Specific Roles",
            "visible_to_roles": ["Insights User"],
            "data_authority": "Author",
            # a key from a later Insights: tolerated, not fatal
            "shipped_by_a_later_release": True,
        },
        f"dashboard/{DASHBOARD}.json": {
            "title": "Bundle Sync Sales Overview",
            "items": [
                {"id": "chart-1", "type": "chart", "chart": CHART},
                {
                    "id": "filter-1",
                    "type": "filter",
                    "links": {CHART: f"`{SOURCE_QUERY}`.`status`"},
                },
            ],
            "visibility": "Everyone",
        },
    }


def write_bundle(folder: str, files: dict, title=BUNDLE_TITLE, required_apps=None, format_version=None):
    path = os.path.join(bundle_root(), folder)
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path)

    manifest = {
        "title": title,
        "required_apps": required_apps or [],
        "format_version": format_version or FORMAT_VERSION,
    }
    with open(os.path.join(path, MANIFEST), "w") as f:
        json.dump(manifest, f)

    for relative_path, data in files.items():
        file_path = os.path.join(path, relative_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(data, f)


def remove_bundles():
    for folder in (BUNDLE, OTHER_BUNDLE):
        shutil.rmtree(os.path.join(bundle_root(), folder), ignore_errors=True)


def references_of(item) -> list[str]:
    """Every logical name one bundle file names — the edges sync has to resolve."""
    data = item.data
    if item.doctype == DT.QUERY:
        return [str(name) for name in query_references(data.get("operations"))]

    if item.doctype == DT.CHART:
        return [data["query"]] if data.get("query") else []

    references = []
    for entry in data.get("items") or []:
        if entry.get("type") == "chart" and entry.get("chart"):
            references.append(entry["chart"])
        for chart, column in (entry.get("links") or {}).items():
            match = LINK_COLUMN.match(column or "")
            if match:
                references += [chart, match.group(1)]
    return references


@contextmanager
def developer_mode(enabled):
    previous = frappe.conf.developer_mode
    frappe.conf.developer_mode = 1 if enabled else 0
    try:
        yield
    finally:
        frappe.conf.developer_mode = previous


class TestInsightsBundles(InsightsIntegrationTestCase):
    SAVEPOINT = "test_insights_bundles"

    @classmethod
    def before_class(cls):
        # a crashed run can leave the fixture behind; it is a fixed name
        remove_bundles()

    @classmethod
    def after_class(cls):
        remove_bundles()

    def before_test(self):
        # a plain site, not a developer bench, is the condition to hold sync to:
        # it has to write standard content through the read-only guards
        off = developer_mode(False)
        off.__enter__()
        self.addCleanup(off.__exit__, None, None, None)

        self.files = bundle_files()
        write_bundle(BUNDLE, self.files)

    def after_test(self):
        remove_bundles()

    # ------------------------------------------------------------- helpers

    def sync(self):
        return sync_app_bundles(APP)

    def logical_id(self, name):
        return f"{APP}/{name}"

    def doctype_of(self, name):
        return {
            BUNDLE: DT.WORKBOOK,
            BASE_QUERY: DT.QUERY,
            SOURCE_QUERY: DT.QUERY,
            CHART: DT.CHART,
            DASHBOARD: DT.DASHBOARD,
        }[name]

    def docname(self, name):
        return frappe.db.get_value(
            self.doctype_of(name),
            {"logical_id": self.logical_id(name), "is_standard": 1},
            "name",
        )

    def doc(self, name):
        docname = self.docname(name)
        self.assertIsNotNone(docname, f"{self.logical_id(name)} was not synced")
        return frappe.get_doc(self.doctype_of(name), docname)

    def modified_of(self, names=SHIPPED):
        return {name: self.doc(name).modified for name in names}

    def all_shipped_ids(self):
        # the workbook is shipped too, and its logical name is the folder — so a
        # report that leaves it out is a reconcile that missed it
        return sorted(self.logical_id(name) for name in (BUNDLE, *SHIPPED))

    def mine(self, logical_ids):
        """The fixture's ids out of a report. Insights ships real bundles of its
        own beside the fixture, so a report is only ever asserted on the part of
        it this test wrote."""
        fixture = set(self.all_shipped_ids())
        return sorted(logical_id for logical_id in logical_ids if logical_id in fixture)

    # --------------------------------------------------------------- tests

    def test_sync_creates_standard_documents_in_a_shipped_workbook(self):
        report = self.sync()

        self.assertEqual(self.mine(report.created), self.all_shipped_ids())
        self.assertEqual(report.errors, [])

        workbooks = set()
        for name in SHIPPED:
            doc = self.doc(name)
            self.assertEqual(doc.is_standard, 1, f"{name} should be standard")
            self.assertEqual(doc.logical_id, self.logical_id(name))
            self.assertEqual(doc.owner, "Administrator")
            workbooks.add(str(doc.workbook))

        # the workbook is shipped content like everything in it: one per folder,
        # titled from workbook.json, flagged standard and owned by the site
        self.assertEqual(len(workbooks), 1)
        container = self.doc(BUNDLE)
        self.assertEqual(str(container.name), workbooks.pop())
        self.assertEqual(container.title, BUNDLE_TITLE)
        self.assertEqual(container.owner, "Administrator")
        self.assertEqual(container.is_standard, 1)

        # its logical name is the folder, so identity is the repo layout
        self.assertEqual(container.logical_id, f"{APP}/{BUNDLE}")

        # the shipped dashboard's external key is its logical name
        self.assertEqual(self.doc(DASHBOARD).slug, DASHBOARD)

        # the carried declarations are the vendor's, not the site's
        chart = self.doc(CHART)
        self.assertEqual(chart.visibility, "Specific Roles")
        self.assertEqual([row.role for row in chart.visible_to_roles], ["Insights User"])
        self.assertEqual(chart.data_authority, "Author")
        self.assertEqual(self.doc(DASHBOARD).visibility, "Everyone")

    def test_a_retitled_manifest_retitles_the_workbook(self):
        self.sync()
        before = self.doc(BUNDLE).name

        write_bundle(BUNDLE, self.files, title="Bundle Sync Test Renamed")
        report = self.sync()

        after = self.doc(BUNDLE)
        # retitled in place: the folder is the identity, so the title is just a
        # field that changed, and nothing inside the workbook moves
        self.assertEqual(str(after.name), str(before))
        self.assertEqual(after.title, "Bundle Sync Test Renamed")
        self.assertEqual(self.mine(report.updated), [f"{APP}/{BUNDLE}"])
        self.assertEqual(self.mine(report.created), [])

    def test_a_removed_folder_deletes_the_workbook_and_its_contents(self):
        self.sync()
        container = str(self.doc(BUNDLE).name)

        shutil.rmtree(os.path.join(bundle_root(), BUNDLE), ignore_errors=True)
        report = self.sync()

        self.assertEqual(self.mine(report.deleted), self.all_shipped_ids())
        self.assertFalse(frappe.db.exists(DT.WORKBOOK, container))
        for name in SHIPPED:
            self.assertIsNone(self.docname(name), f"{name} outlived its workbook")

        # deletion reverses the creation order, so the workbook goes last — by
        # then it is empty, which is why it can go at all
        self.assertEqual(report.deleted[-1], f"{APP}/{BUNDLE}")

    def test_discovery_reads_apps_off_disk(self):
        bundles = {b.key: b for b in discover_bundles(APP)}
        fixture = bundles[f"{APP}/{BUNDLE}"]
        self.assertEqual(fixture.title, BUNDLE_TITLE)
        self.assertEqual(len(fixture.items), 4)

        # an app that ships nothing is not a special case, it is the common one
        self.assertEqual(discover_bundles("frappe"), [])

    def test_the_bundles_insights_ships_are_readable(self):
        """CI guard over the committed bundles: they parse, their names are legal
        and unique across the app, and every reference names an item the app
        ships. What sync would refuse, this refuses first — and it holds on a
        site without the apps those bundles need, where sync ships nothing."""
        shipped = [b for b in discover_bundles(APP) if b.folder not in (BUNDLE, OTHER_BUNDLE)]
        self.assertTrue(shipped, "Insights ships no bundles of its own")

        names = {}
        for bundle in shipped:
            self.assertTrue(bundle.title, f"{bundle.key} has no title")
            self.assertLessEqual(bundle.format_version, FORMAT_VERSION)
            self.assertTrue(bundle.items, f"{bundle.key} ships nothing")
            for item in bundle.items:
                self.assertNotIn(item.name, names, f"{item.logical_id} is shipped twice")
                names[item.name] = item

        for bundle in shipped:
            for item in bundle.items:
                for reference in references_of(item):
                    self.assertIn(
                        reference,
                        names,
                        f"{item.logical_id} references '{reference}', which the app does not ship",
                    )

    def test_references_resolve_to_site_documents(self):
        self.sync()

        base, source = self.doc(BASE_QUERY), self.doc(SOURCE_QUERY)
        chart, dashboard = self.doc(CHART), self.doc(DASHBOARD)

        self.assertEqual(chart.query, source.name)

        table = frappe.parse_json(source.operations)[0]["table"]
        self.assertEqual(table["query_name"], base.name)
        self.assertEqual(str(table["workbook"]), str(source.workbook))

        items = frappe.parse_json(dashboard.items)
        self.assertEqual(items[0]["chart"], chart.name)
        self.assertEqual(items[1]["links"], {chart.name: f"`{source.name}`.`status`"})
        self.assertEqual([row.chart for row in dashboard.linked_charts], [chart.name])

        # and the logical ids are what a consumer outside Insights references
        self.assertEqual(resolve(DT.DASHBOARD, self.logical_id(DASHBOARD)), dashboard.name)
        self.assertEqual(resolve(DT.CHART, self.logical_id(CHART)), chart.name)
        self.assertEqual(resolve(DT.DASHBOARD, dashboard.slug), dashboard.name)

    def test_resync_writes_nothing(self):
        self.sync()
        before = self.modified_of()
        container = self.doc(CHART).workbook

        report = self.sync()

        self.assertFalse(report.changed)
        self.assertEqual(self.mine(report.unchanged), self.all_shipped_ids())
        self.assertEqual(self.modified_of(), before)
        # the container is what a second run has to find again: miss it and every
        # shipped document is rewritten into a new one
        self.assertEqual(self.doc(CHART).workbook, container)
        self.assertEqual(frappe.db.count(DT.WORKBOOK, {"logical_id": f"{APP}/{BUNDLE}"}), 1)

    def test_a_changed_file_updates_only_its_document(self):
        self.sync()
        before = self.modified_of()

        self.files[f"query/{SOURCE_QUERY}.json"]["title"] = "Bundle Sync Sales (revised)"
        write_bundle(BUNDLE, self.files)
        report = self.sync()

        self.assertEqual(report.updated, [self.logical_id(SOURCE_QUERY)])
        # the other three items and the workbook they live in
        self.assertEqual(len(self.mine(report.unchanged)), 4)
        self.assertEqual(self.doc(SOURCE_QUERY).title, "Bundle Sync Sales (revised)")
        self.assertNotEqual(self.doc(SOURCE_QUERY).modified, before[SOURCE_QUERY])
        self.assertEqual(self.doc(CHART).modified, before[CHART])

    def test_a_removed_file_deletes_its_document(self):
        self.sync()
        dashboard = self.docname(DASHBOARD)

        del self.files[f"dashboard/{DASHBOARD}.json"]
        write_bundle(BUNDLE, self.files)
        report = self.sync()

        self.assertEqual(report.deleted, [self.logical_id(DASHBOARD)])
        self.assertFalse(frappe.db.exists(DT.DASHBOARD, dashboard))
        self.assertIsNotNone(self.docname(CHART))
        self.assertIsNotNone(self.docname(SOURCE_QUERY))

    def test_a_bundle_whose_required_app_is_missing_ships_nothing(self):
        self.sync()

        write_bundle(BUNDLE, self.files, required_apps=["no_such_app"])
        report = self.sync()

        self.assertEqual(self.mine(report.deleted), self.all_shipped_ids())
        for name in SHIPPED:
            self.assertIsNone(self.docname(name), f"{name} should have gone with its bundle")

    def test_uninstall_deletes_standard_documents_and_spares_user_copies(self):
        self.sync()
        chart = self.doc(CHART)
        container = chart.workbook

        mine = frappe.get_doc({"doctype": DT.WORKBOOK, "title": "Bundle Sync User Workbook"}).insert()
        copy = frappe.copy_doc(chart)
        copy.is_standard = 0
        copy.workbook = mine.name
        copy.title = f"{chart.title} (Copy)"
        copy.insert()

        report = before_app_uninstall(APP)

        self.assertEqual(self.mine(report.deleted), self.all_shipped_ids())
        for name in SHIPPED:
            self.assertIsNone(self.docname(name), f"{name} should have gone with its app")

        # the copy keeps the logical id it was made from, and keeps existing
        self.assertTrue(frappe.db.exists(DT.CHART, copy.name))
        self.assertEqual(frappe.db.get_value(DT.CHART, copy.name, "logical_id"), self.logical_id(CHART))
        # an emptied container is site state with nothing left in it
        self.assertFalse(frappe.db.exists(DT.WORKBOOK, container))
        self.assertTrue(frappe.db.exists(DT.WORKBOOK, mine.name))

    def test_standard_documents_are_read_only_outside_developer_mode(self):
        self.sync()
        chart = self.doc(CHART)

        with developer_mode(False):
            edit = frappe.get_doc(DT.CHART, chart.name)
            edit.title = "Edited on a site"
            self.assertRaises(frappe.ValidationError, edit.save)

            # clearing the flag is itself an edit of standard content
            unflag = frappe.get_doc(DT.CHART, chart.name)
            unflag.is_standard = 0
            self.assertRaises(frappe.ValidationError, unflag.save)

            # nor may a site mint standard content of its own
            minted = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Home-made standard chart",
                    "workbook": chart.workbook,
                    "is_standard": 1,
                }
            )
            self.assertRaises(frappe.ValidationError, minted.insert)

            dashboard = self.doc(DASHBOARD)
            self.assertRaises(frappe.ValidationError, dashboard.delete)
            self.assertTrue(frappe.db.exists(DT.DASHBOARD, dashboard.name))

        # a developer bench is where shipped content is authored
        with developer_mode(True):
            edit = frappe.get_doc(DT.CHART, chart.name)
            edit.title = "Edited on a developer bench"
            edit.save()

        self.assertEqual(frappe.db.get_value(DT.CHART, chart.name, "title"), "Edited on a developer bench")

    def test_a_taken_slug_is_app_qualified_with_a_warning(self):
        workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": "Bundle Sync Slug Holder"}).insert()
        frappe.get_doc(
            {"doctype": DT.DASHBOARD, "title": DASHBOARD, "workbook": workbook.name, "items": []}
        ).insert()

        report = self.sync()

        self.assertEqual(self.doc(DASHBOARD).slug, f"{APP}-{DASHBOARD}")
        self.assertTrue(any(DASHBOARD in warning for warning in report.warnings))
        self.assertEqual(resolve(DT.DASHBOARD, f"{APP}-{DASHBOARD}"), self.docname(DASHBOARD))

    def test_one_name_shipped_twice_by_an_app_fails_loudly(self):
        # a second bundle, same app, same logical name — and a different doctype,
        # to show the namespace is flat across types too
        write_bundle(OTHER_BUNDLE, {f"chart/{SOURCE_QUERY}.json": {"title": "Clashing Chart"}})

        with self.assertRaises(BundleError):
            sync_bundles([APP], strict=True)

        # unstrict, the app is rolled back whole: nothing half-shipped
        report = sync_bundles([APP])
        self.assertTrue(report.errors)
        self.assertEqual(report.created, [])
        for name in SHIPPED:
            self.assertIsNone(self.docname(name), f"{name} should not have been shipped")

    def test_a_later_format_version_is_refused(self):
        write_bundle(BUNDLE, self.files, format_version=FORMAT_VERSION + 1)

        with self.assertRaises(BundleError):
            sync_bundles([APP], strict=True)

    def test_sync_over_the_installed_apps_reports_no_errors(self):
        report = sync_bundles()

        self.assertEqual(report.errors, [])
        self.assertTrue(set(self.all_shipped_ids()) <= set(report.created))
