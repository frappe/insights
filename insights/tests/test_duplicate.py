"""Duplicate to edit: the user copy of shipped content.

The fixture is the shipping bundle `test_bundles` writes to disk, synced the way
a migrate would sync it — the copy is only interesting against content a site
cannot edit, and that is the only way to have some.
"""

import json

import frappe

from insights.api.bundles import duplicate_bundle as duplicate_bundle_through_the_api
from insights.api.bundles import duplicate_dashboard as duplicate_through_the_api
from insights.api.bundles import get_standard_content
from insights.bundles import sync_app_bundles as sync
from insights.duplicate import duplicate_dashboard
from insights.insights.doctype.insights_data_source_v3.data_authority import get_authority_user_for
from insights.resolver import ContentNotAvailableError, resolve
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks
from insights.tests.test_bundles import (
    APP,
    BASE_QUERY,
    BUNDLE,
    BUNDLE_TITLE,
    CHART,
    DASHBOARD,
    SHIPPED,
    SOURCE_QUERY,
    bundle_files,
    developer_mode,
    remove_bundles,
    write_bundle,
)

# holds an authoring seat, and is in the shipped dashboard's audience (`Everyone`)
AUTHOR = "duplicate_author@test.com"
# in the same audience, with no Insights role at all — the desk viewer
VIEWER = "duplicate_viewer@test.com"

COPY_WORKBOOK_TITLE = "Bundle Sync Sales Overview (copy)"
COPY_BUNDLE_TITLE = f"{BUNDLE_TITLE} (copy)"

# a second dashboard over the chart the fixture already ships
SECOND_DASHBOARD = "bst_sales_overview_alt"


class TestDuplicateToEdit(InsightsIntegrationTestCase):
    SAVEPOINT = "test_insights_duplicate"

    @classmethod
    def before_class(cls):
        remove_bundles()
        cls.cleanup()
        create_user(AUTHOR, first_name="Duplicate", last_name="Author", roles="Insights User")
        create_user(VIEWER, first_name="Duplicate", last_name="Viewer")

    @classmethod
    def after_class(cls):
        remove_bundles()
        cls.cleanup()

    @classmethod
    def cleanup(cls):
        delete_workbooks(title_prefix=COPY_WORKBOOK_TITLE)
        delete_workbooks(title_prefix=COPY_BUNDLE_TITLE)
        delete_users(AUTHOR, VIEWER)

    def before_test(self):
        # a plain site, not a developer bench: standard content is read-only here,
        # which is the whole reason duplicating exists
        off = developer_mode(False)
        off.__enter__()
        self.addCleanup(off.__exit__, None, None, None)

        self.files = bundle_files()
        write_bundle(BUNDLE, self.files)

    def after_test(self):
        remove_bundles()

    # ------------------------------------------------------------- helpers

    def ship(self):
        """Sync the fixture bundle, the way a migrate would.

        Called inside a test and never from `before_test`: the savepoint that
        rolls a test back is taken after the fixtures run, so content shipped
        there would survive the run and land on the site.
        """
        return sync(APP)

    def standard(self, name):
        doctype = {
            BASE_QUERY: DT.QUERY,
            SOURCE_QUERY: DT.QUERY,
            CHART: DT.CHART,
            DASHBOARD: DT.DASHBOARD,
        }[name]
        docname = frappe.db.get_value(doctype, {"logical_id": f"{APP}/{name}", "is_standard": 1}, "name")
        self.assertIsNotNone(docname, f"{APP}/{name} was not synced")
        return frappe.get_doc(doctype, docname)

    def duplicate_as(self, user, reference=None):
        with as_user(user):
            return duplicate_dashboard(reference or self.standard(DASHBOARD).name)

    def copies_in(self, workbook):
        """The copy's documents, keyed the way the fixture names the originals."""
        queries = frappe.get_all(DT.QUERY, filters={"workbook": workbook}, fields=["name", "logical_id"])
        by_logical_id = {row.logical_id: row.name for row in queries}
        return {
            BASE_QUERY: frappe.get_doc(DT.QUERY, by_logical_id[f"{APP}/{BASE_QUERY}"]),
            SOURCE_QUERY: frappe.get_doc(DT.QUERY, by_logical_id[f"{APP}/{SOURCE_QUERY}"]),
            CHART: frappe.get_doc(DT.CHART, frappe.db.get_value(DT.CHART, {"workbook": workbook})),
            DASHBOARD: frappe.get_doc(
                DT.DASHBOARD, frappe.db.get_value(DT.DASHBOARD, {"workbook": workbook})
            ),
        }

    # --------------------------------------------------------------- tests

    def test_duplicating_a_shipped_dashboard_creates_a_user_workbook(self):
        self.ship()
        result = self.duplicate_as(AUTHOR)

        workbook = frappe.get_doc(DT.WORKBOOK, result["workbook"])
        self.assertEqual(workbook.title, COPY_WORKBOOK_TITLE)
        self.assertEqual(workbook.owner, AUTHOR)
        # never the bundle's container: a copy left in it would keep the
        # container alive after the bundle that made it is gone
        self.assertNotEqual(str(workbook.name), str(self.standard(DASHBOARD).workbook))

        copies = self.copies_in(workbook.name)
        self.assertEqual(result["dashboard"], copies[DASHBOARD].name)
        for name, copy in copies.items():
            self.assertEqual(copy.owner, AUTHOR, f"the {name} copy should belong to who asked for it")

        # the whole closure came across, and nothing of the original is left in it
        self.assertEqual(frappe.db.count(DT.QUERY, {"workbook": workbook.name}), 2)
        self.assertEqual(frappe.db.count(DT.CHART, {"workbook": workbook.name}), 1)
        self.assertEqual(frappe.db.count(DT.DASHBOARD, {"workbook": workbook.name}), 1)

    def test_every_reference_points_at_the_copies(self):
        self.ship()
        result = self.duplicate_as(AUTHOR)
        copies = self.copies_in(result["workbook"])
        base, source = copies[BASE_QUERY], copies[SOURCE_QUERY]
        chart, dashboard = copies[CHART], copies[DASHBOARD]

        self.assertEqual(chart.query, source.name)

        # the query behind the chart's query came along too, reading the copy
        table = frappe.parse_json(source.operations)[0]["table"]
        self.assertEqual(table["query_name"], base.name)
        self.assertEqual(str(table["workbook"]), str(result["workbook"]))

        items = frappe.parse_json(dashboard.items)
        self.assertEqual(items[0]["chart"], chart.name)
        self.assertEqual(items[1]["links"], {chart.name: f"`{source.name}`.`status`"})

        # and nothing points back at the shipped documents
        serialized = json.dumps(
            [chart.as_dict(), source.operations, dashboard.items],
            default=str,
        )
        for original in (self.standard(name).name for name in SHIPPED):
            self.assertNotIn(str(original), serialized)

    def test_the_copies_are_editable_documents_that_remember_where_they_came_from(self):
        self.ship()
        copies = self.copies_in(self.duplicate_as(AUTHOR)["workbook"])

        for name, copy in copies.items():
            self.assertEqual(copy.is_standard, 0, f"the {name} copy must not be standard content")
            # provenance: which shipped item this document started as
            self.assertEqual(copy.logical_id, f"{APP}/{name}")

        # and the read-only guard that stops the original does not stop the copy
        with as_user(AUTHOR):
            copy = frappe.get_doc(DT.CHART, copies[CHART].name)
            copy.title = "Edited by the person who duplicated it"
            copy.save()

        self.assertEqual(
            frappe.db.get_value(DT.CHART, copies[CHART].name, "title"),
            "Edited by the person who duplicated it",
        )

    def test_the_source_is_untouched_and_still_answers_for_its_shipped_id(self):
        self.ship()
        before = {name: self.standard(name).modified for name in SHIPPED}
        originals = {name: self.standard(name).name for name in SHIPPED}

        result = self.duplicate_as(AUTHOR)

        self.assertEqual({name: self.standard(name).modified for name in SHIPPED}, before)
        self.assertEqual(self.standard(CHART).title, "Bundle Sync Sales Chart")

        # the copy carries the logical id, and the id still resolves to the standard
        self.assertEqual(resolve(DT.DASHBOARD, f"{APP}/{DASHBOARD}"), originals[DASHBOARD])
        self.assertEqual(resolve(DT.CHART, f"{APP}/{CHART}"), originals[CHART])
        self.assertNotEqual(resolve(DT.DASHBOARD, f"{APP}/{DASHBOARD}"), result["dashboard"])
        # the slug is the original's too — the copy takes its own
        self.assertEqual(resolve(DT.DASHBOARD, DASHBOARD), originals[DASHBOARD])

    def test_the_copy_starts_private(self):
        self.ship()
        copies = self.copies_in(self.duplicate_as(AUTHOR)["workbook"])

        # the shipped audience is the vendor's declaration about the original;
        # a copy is the duplicator's draft, not a re-publication of it
        self.assertEqual(self.standard(DASHBOARD).visibility, "Everyone")
        self.assertEqual(self.standard(CHART).visibility, "Specific Roles")
        self.assertEqual(copies[DASHBOARD].visibility, "Private")
        self.assertEqual(copies[CHART].visibility, "Private")
        self.assertEqual(copies[CHART].visible_to_roles, [])

        with as_user(VIEWER):
            self.assertFalse(frappe.has_permission(DT.DASHBOARD, doc=copies[DASHBOARD].name))
            self.assertTrue(frappe.has_permission(DT.DASHBOARD, doc=self.standard(DASHBOARD).name))

    def test_the_declared_authority_carries_over_under_the_copys_owner(self):
        self.ship()
        copies = self.copies_in(self.duplicate_as(AUTHOR)["workbook"])

        # how the content runs is part of the content
        self.assertEqual(copies[CHART].data_authority, "Author")
        # but the author it means is the copy's owner, so the copy can never show
        # rows the person who made it could not already reach
        self.assertEqual(get_authority_user_for(DT.CHART, self.standard(CHART).name), "Administrator")
        self.assertEqual(get_authority_user_for(DT.CHART, copies[CHART].name), AUTHOR)

    # ------------------------------------------------------- who may duplicate

    def test_an_authoring_user_in_the_audience_may_duplicate(self):
        self.ship()
        with as_user(AUTHOR):
            result = duplicate_through_the_api(dashboard=f"{APP}/{DASHBOARD}")

        self.assertTrue(frappe.db.exists(DT.DASHBOARD, result["dashboard"]))
        self.assertEqual(frappe.db.get_value(DT.WORKBOOK, result["workbook"], "owner"), AUTHOR)

    def test_a_viewer_without_an_authoring_seat_may_not(self):
        self.ship()
        dashboard = self.standard(DASHBOARD)
        # the viewer is squarely in the audience — reading is not the question
        with as_user(VIEWER):
            self.assertTrue(frappe.has_permission(DT.DASHBOARD, doc=dashboard.name))
            with self.assertRaises(frappe.PermissionError):
                duplicate_through_the_api(dashboard=dashboard.name)

        self.assertFalse(frappe.db.exists(DT.WORKBOOK, {"owner": VIEWER}))

    def test_an_authoring_user_outside_the_audience_may_not(self):
        self.ship()
        self.files[f"dashboard/{DASHBOARD}.json"]["visibility"] = "Private"
        write_bundle(BUNDLE, self.files)
        sync(APP)

        with as_user(AUTHOR), self.assertRaises(ContentNotAvailableError):
            duplicate_through_the_api(dashboard=f"{APP}/{DASHBOARD}")

    def test_a_reference_nobody_can_have_answers_like_a_missing_one(self):
        self.ship()
        with as_user(AUTHOR):
            with self.assertRaises(ContentNotAvailableError):
                duplicate_through_the_api(dashboard=f"{APP}/no_such_dashboard")

    # ------------------------------------------------ the bundle, taken whole

    def ship_a_second_dashboard(self):
        """The fixture plus a second dashboard over the same chart — what makes
        the shared part of the closure visible."""
        self.files[f"dashboard/{SECOND_DASHBOARD}.json"] = {
            "title": "Bundle Sync Sales Overview II",
            "items": [{"id": "chart-1", "type": "chart", "chart": CHART}],
            "visibility": "Everyone",
        }
        write_bundle(BUNDLE, self.files)
        self.ship()

    def test_duplicating_a_bundle_lands_its_dashboards_in_one_workbook(self):
        self.ship_a_second_dashboard()
        container = self.standard(DASHBOARD).workbook

        with as_user(AUTHOR):
            result = duplicate_bundle_through_the_api(workbook=container)

        workbook = result["workbook"]
        self.assertEqual(frappe.db.get_value(DT.WORKBOOK, workbook, "title"), COPY_BUNDLE_TITLE)
        self.assertEqual(frappe.db.get_value(DT.WORKBOOK, workbook, "owner"), AUTHOR)
        self.assertNotEqual(str(workbook), str(container))
        self.assertEqual(frappe.db.count(DT.DASHBOARD, {"workbook": workbook}), 2)

        # the chart both dashboards carry, and the queries under it, are copied
        # once and shared — not once per dashboard
        self.assertEqual(frappe.db.count(DT.CHART, {"workbook": workbook}), 1)
        self.assertEqual(frappe.db.count(DT.QUERY, {"workbook": workbook}), 2)

        chart = frappe.db.get_value(DT.CHART, {"workbook": workbook})
        for name in frappe.get_all(DT.DASHBOARD, {"workbook": workbook}, pluck="name"):
            items = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, name, "items"))
            self.assertEqual(items[0]["chart"], chart)

    def test_a_workbook_of_the_sites_own_is_not_a_bundle_to_duplicate(self):
        self.ship()
        mine = frappe.get_doc({"doctype": DT.WORKBOOK, "title": "Not a bundle"}).insert()

        with as_user(AUTHOR), self.assertRaises(ContentNotAvailableError):
            duplicate_bundle_through_the_api(workbook=mine.name)

    # ----------------------------------------------------------- the library

    def test_the_library_lists_a_bundle_the_audience_admits(self):
        self.ship()
        with as_user(AUTHOR):
            listed = {bundle["title"]: bundle for bundle in get_standard_content()}

        self.assertIn(BUNDLE_TITLE, listed)
        bundle = listed[BUNDLE_TITLE]
        self.assertEqual(bundle["app"], APP)
        self.assertEqual(str(bundle["workbook"]), str(self.standard(DASHBOARD).workbook))
        self.assertEqual(
            [dashboard["logical_id"] for dashboard in bundle["dashboards"]],
            [f"{APP}/{DASHBOARD}"],
        )
        self.assertEqual(bundle["dashboards"][0]["slug"], DASHBOARD)

    def test_the_library_leaves_out_what_the_audience_does_not_admit(self):
        self.files[f"dashboard/{DASHBOARD}.json"]["visibility"] = "Private"
        write_bundle(BUNDLE, self.files)
        self.ship()

        with as_user(AUTHOR):
            self.assertNotIn(BUNDLE_TITLE, [bundle["title"] for bundle in get_standard_content()])
