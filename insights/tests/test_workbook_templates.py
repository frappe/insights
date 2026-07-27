import json
import os
from unittest.mock import patch

import frappe

from insights.api.templates import (
    MANIFEST_REQUIRED_KEYS,
    _discover_templates,
    _is_customized,
    create_workbook_from_template,
    get_template_manifest,
    get_template_names,
    get_template_path,
    get_template_workbook,
    get_workbook_templates,
    sync_workbook_template_updates,
    update_workbook_from_template,
)
from insights.insights.doctype.insights_workbook.insights_workbook import (
    InsightsWorkbook,
    import_workbook,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import USER_1, create_test_user, delete_users
from insights.tests.workbook_utils import get_workbook

# ids are qualified by the app that ships the template ("{app}/{folder}")
TEMPLATE = "insights/sales"
TEMPLATE_TITLE = "Sales Performance"
TEMPLATE_MODULE = "Selling"
# a committed template that ships a preview.png, so preview handling stays covered
TEMPLATE_WITH_PREVIEW = "insights/stock"

# derived from the shipped manifest so a template version bump doesn't need edits
# scattered across every assertion; NEXT_VERSION stands in for a newer release
TEMPLATE_VERSION = get_template_manifest(TEMPLATE)["version"]
NEXT_VERSION = TEMPLATE_VERSION + 1

# importing is admin-only for v1; two extra actors let us prove the shared-copy model
ADMIN_USER = "workbook_template_admin@test.com"
USER_2 = "workbook_template_user2@test.com"

APPS_WITHOUT_ERPNEXT = ["frappe", "insights"]
APPS_WITH_ERPNEXT = ["frappe", "insights", "erpnext"]


def installed_apps(apps):
    # patch our narrow seam, not the global — patching frappe.get_installed_apps
    # breaks other apps' insert hooks on multi-app sites
    return patch("insights.api.templates.get_installed_apps", return_value=set(apps))


def bumped_version(template_name, version):
    # simulate the app shipping a newer version of a template without a second
    # fixture: reuse the real folder (so workbook.json still resolves) but override
    # the discovered manifest's version
    registry = {name: dict(entry) for name, entry in _discover_templates().items()}
    entry = dict(registry[template_name])
    entry["manifest"] = {**entry["manifest"], "version": version}
    registry[template_name] = entry
    return patch("insights.api.templates._discover_templates", return_value=registry)


def cleanup_template_workbooks():
    # template workbooks are owned by Administrator now, so owner-scoped cleanup
    # can't reach them — delete by their derived origin tag instead
    for name in frappe.get_all("Insights Workbook", filters={"from_template": ["!=", ""]}, pluck="name"):
        frappe.delete_doc("Insights Workbook", name, force=True)


class TestWorkbookTemplates(InsightsIntegrationTestCase):
    COMMIT_AFTER_TEST_SETUP = True
    COMMIT_AFTER_TEST_TEARDOWN = True

    @classmethod
    def before_class(cls):
        cleanup_template_workbooks()
        delete_users(USER_1, USER_2, ADMIN_USER)
        create_test_user(USER_1)  # Insights User (non-admin)
        create_test_user(USER_2)  # Insights User (non-admin)
        create_test_user(ADMIN_USER, role="Insights Admin")

    @classmethod
    def after_class(cls):
        cleanup_template_workbooks()
        delete_users(USER_1, USER_2, ADMIN_USER)

    def after_test(self):
        cleanup_template_workbooks()

    def test_templates_hidden_when_required_apps_missing(self):
        with self.as_user(USER_1), installed_apps(APPS_WITHOUT_ERPNEXT):
            self.assertEqual(get_workbook_templates(), [])

    def test_templates_listed_when_required_apps_installed(self):
        with self.as_user(USER_1), installed_apps(APPS_WITH_ERPNEXT):
            templates = {t["name"]: t for t in get_workbook_templates()}

        self.assertIn(TEMPLATE, templates)
        sales = templates[TEMPLATE]
        self.assertEqual(sales["title"], TEMPLATE_TITLE)
        self.assertEqual(sales["module"], TEMPLATE_MODULE)
        self.assertIn("has_data", sales)
        self.assertTrue(sales["notes"])  # technical caveats split out of the description
        self.assertIsNone(sales["imported_workbook"])
        # grouped under the app it's for (its required app), not the shipping app.
        # required_apps is faked here, so erpnext may not be a real module — the
        # title resolves to "ERPNext" when it is, else falls back to the name.
        self.assertEqual(sales["app"], "erpnext")
        self.assertIn(sales["app_title"], ("ERPNext", "erpnext"))
        self.assertEqual(sales["version"], TEMPLATE_VERSION)

        # a template that ships a preview exposes it as a data URI
        self.assertTrue(
            templates[TEMPLATE_WITH_PREVIEW]["preview_image"].startswith("data:image/png;base64,")
        )

    def test_import_is_shared_site_wide_and_marks_template(self):
        with self.as_user(ADMIN_USER), installed_apps(APPS_WITH_ERPNEXT):
            result = create_workbook_from_template(TEMPLATE)

        workbook_name = result["workbook"]
        # the created workbook remembers its origin and points at its first dashboard
        self.assertEqual(
            frappe.db.get_value("Insights Workbook", workbook_name, "from_template"),
            TEMPLATE,
        )
        self.assertTrue(result["dashboard"])

        # a *different* non-admin sees the shared copy marked as imported (site-wide)
        with self.as_user(USER_2), installed_apps(APPS_WITH_ERPNEXT):
            sales = {t["name"]: t for t in get_workbook_templates()}[TEMPLATE]
            self.assertEqual(sales["imported_workbook"], workbook_name)

        # deleting the workbook re-enables the template (state is derived, not stored)
        frappe.delete_doc("Insights Workbook", workbook_name, force=True)
        with self.as_user(USER_2), installed_apps(APPS_WITH_ERPNEXT):
            sales = {t["name"]: t for t in get_workbook_templates()}[TEMPLATE]
            self.assertIsNone(sales["imported_workbook"])

    def test_imported_workbook_owned_by_administrator_and_org_shared(self):
        with self.as_user(ADMIN_USER), installed_apps(APPS_WITH_ERPNEXT):
            workbook_name = create_workbook_from_template(TEMPLATE)["workbook"]

        # owned by Administrator, not the admin who clicked — workbook and children
        self.assertEqual(frappe.db.get_value("Insights Workbook", workbook_name, "owner"), "Administrator")
        child_owners = frappe.get_all("Insights Chart v3", filters={"workbook": workbook_name}, pluck="owner")
        self.assertTrue(child_owners)
        self.assertEqual(set(child_owners), {"Administrator"})

        # implicit organization: view share — everyone read, no write
        share = frappe.db.get_value(
            "DocShare",
            {"share_doctype": "Insights Workbook", "share_name": str(workbook_name), "everyone": 1},
            ["read", "write"],
            as_dict=True,
        )
        self.assertTrue(share)
        self.assertTrue(share["read"])
        self.assertFalse(share["write"])

    def test_non_admin_can_read_but_not_write_shared_copy(self):
        with self.as_user(ADMIN_USER), installed_apps(APPS_WITH_ERPNEXT):
            workbook_name = create_workbook_from_template(TEMPLATE)["workbook"]

        self.assert_visible_to(USER_2, "Insights Workbook", workbook_name)
        with self.as_user(USER_2):
            self.assertFalse(
                frappe.has_permission("Insights Workbook", ptype="write", doc=str(workbook_name))
            )

    def test_double_import_returns_existing_without_duplicating(self):
        with self.as_user(ADMIN_USER), installed_apps(APPS_WITH_ERPNEXT):
            first = create_workbook_from_template(TEMPLATE)
            second = create_workbook_from_template(TEMPLATE)

        self.assertEqual(first["workbook"], second["workbook"])
        self.assertEqual(frappe.db.count("Insights Workbook", {"from_template": TEMPLATE}), 1)

    def test_non_admin_cannot_import(self):
        with self.as_user(USER_1), installed_apps(APPS_WITH_ERPNEXT):
            with self.assertRaises(frappe.PermissionError):
                create_workbook_from_template(TEMPLATE)
        # and nothing was created
        self.assertEqual(frappe.db.count("Insights Workbook", {"from_template": TEMPLATE}), 0)

    def test_create_blocked_when_required_apps_missing(self):
        with self.as_user(ADMIN_USER), installed_apps(APPS_WITHOUT_ERPNEXT):
            with self.assertRaises(frappe.ValidationError):
                create_workbook_from_template(TEMPLATE)

    def test_create_rejects_unknown_template(self):
        with self.as_user(ADMIN_USER):
            with self.assertRaises(frappe.ValidationError):
                create_workbook_from_template("../../../etc/passwd")

    def test_create_workbook_from_template_round_trips(self):
        template = get_template_workbook(TEMPLATE)

        with self.as_user(ADMIN_USER), installed_apps(APPS_WITH_ERPNEXT):
            workbook_name = create_workbook_from_template(TEMPLATE)["workbook"]

        # read back as Administrator (owner of the shared copy)
        workbook = get_workbook(workbook_name)

        template_queries = template["dependencies"]["queries"]
        template_charts = template["dependencies"]["charts"]
        template_dashboards = template["dependencies"]["dashboards"]

        self.assertEqual(workbook["title"], template["doc"]["title"])
        self.assertEqual(
            {q["title"] for q in workbook["queries"]},
            {q["title"] for q in template_queries.values()},
        )
        self.assertEqual(
            {c["title"] for c in workbook["charts"]},
            {c["title"] for c in template_charts.values()},
        )
        self.assertEqual(
            {d["title"] for d in workbook["dashboards"]},
            {d["title"] for d in template_dashboards.values()},
        )

        # chart -> query and dashboard -> chart links must be remapped to the new names
        new_query_names = {q["name"] for q in workbook["queries"]}
        new_chart_names = {c["name"] for c in workbook["charts"]}
        for chart in frappe.get_all(
            "Insights Chart v3",
            filters={"workbook": workbook_name},
            fields=["query"],
        ):
            self.assertIn(chart["query"], new_query_names)
        dashboard_name = workbook["dashboards"][0]["name"]
        items = frappe.parse_json(frappe.db.get_value("Insights Dashboard v3", dashboard_name, "items"))
        chart_items = [item for item in items if item["type"] == "chart"]
        self.assertEqual(len(chart_items), len(template_charts))
        for item in chart_items:
            self.assertIn(item["chart"], new_chart_names)

    def test_import_records_version_and_is_pristine(self):
        with self.as_user(ADMIN_USER), installed_apps(APPS_WITH_ERPNEXT):
            workbook_name = create_workbook_from_template(TEMPLATE)["workbook"]

        # the copy remembers which shipped version it holds, and reads as pristine
        self.assertEqual(
            frappe.db.get_value("Insights Workbook", workbook_name, "imported_version"), TEMPLATE_VERSION
        )
        self.assertFalse(_is_customized(workbook_name))

        # same version shipped -> no update offered
        with self.as_user(USER_2), installed_apps(APPS_WITH_ERPNEXT):
            sales = {t["name"]: t for t in get_workbook_templates()}[TEMPLATE]
        self.assertEqual(sales["imported_version"], TEMPLATE_VERSION)
        self.assertFalse(sales["update_available"])
        self.assertFalse(sales["customized"])

    def test_update_offered_when_newer_version_ships(self):
        with self.as_user(ADMIN_USER), installed_apps(APPS_WITH_ERPNEXT):
            create_workbook_from_template(TEMPLATE)

        with installed_apps(APPS_WITH_ERPNEXT), bumped_version(TEMPLATE, NEXT_VERSION), self.as_user(USER_2):
            sales = {t["name"]: t for t in get_workbook_templates()}[TEMPLATE]
        self.assertTrue(sales["update_available"])
        self.assertFalse(sales["customized"])  # untouched copy

    def test_update_replaces_contents_in_place(self):
        with self.as_user(ADMIN_USER), installed_apps(APPS_WITH_ERPNEXT):
            workbook_name = create_workbook_from_template(TEMPLATE)["workbook"]
            chart = frappe.get_all("Insights Chart v3", {"workbook": workbook_name}, pluck="name")[0]
            # a local edit that the update must roll back to the shipped definition
            frappe.db.set_value("Insights Chart v3", chart, "title", "Edited")

        with (
            self.as_user(ADMIN_USER),
            installed_apps(APPS_WITH_ERPNEXT),
            bumped_version(TEMPLATE, NEXT_VERSION),
        ):
            result = update_workbook_from_template(TEMPLATE)

        # same workbook name (URLs/shares survive), version advanced, edit gone
        self.assertEqual(result["workbook"], workbook_name)
        self.assertEqual(
            frappe.db.get_value("Insights Workbook", workbook_name, "imported_version"), NEXT_VERSION
        )
        self.assertFalse(frappe.db.exists("Insights Chart v3", chart))
        # stays an Administrator-owned shared copy after the rebuild
        self.assertEqual(frappe.db.get_value("Insights Workbook", workbook_name, "owner"), "Administrator")
        self.assertFalse(_is_customized(workbook_name))

    def test_migrate_sync_auto_updates_pristine_copy(self):
        with self.as_user(ADMIN_USER), installed_apps(APPS_WITH_ERPNEXT):
            workbook_name = create_workbook_from_template(TEMPLATE)["workbook"]

        with bumped_version(TEMPLATE, NEXT_VERSION):
            sync_workbook_template_updates()

        self.assertEqual(
            frappe.db.get_value("Insights Workbook", workbook_name, "imported_version"), NEXT_VERSION
        )

    def test_migrate_sync_leaves_customized_copy_for_manual_update(self):
        with self.as_user(ADMIN_USER), installed_apps(APPS_WITH_ERPNEXT):
            workbook_name = create_workbook_from_template(TEMPLATE)["workbook"]
            chart = frappe.get_all("Insights Chart v3", {"workbook": workbook_name}, pluck="name")[0]
            frappe.db.set_value("Insights Chart v3", chart, "title", "Locally Edited")

        self.assertTrue(_is_customized(workbook_name))

        with bumped_version(TEMPLATE, NEXT_VERSION):
            sync_workbook_template_updates()

        # not silently overwritten: kept at its imported version with the edit intact
        self.assertEqual(
            frappe.db.get_value("Insights Workbook", workbook_name, "imported_version"), TEMPLATE_VERSION
        )
        self.assertEqual(frappe.db.get_value("Insights Chart v3", chart, "title"), "Locally Edited")

        # the library still offers the update, flagged as a clobber
        with installed_apps(APPS_WITH_ERPNEXT), bumped_version(TEMPLATE, NEXT_VERSION), self.as_user(USER_2):
            sales = {t["name"]: t for t in get_workbook_templates()}[TEMPLATE]
        self.assertTrue(sales["update_available"])
        self.assertTrue(sales["customized"])

    def test_migrate_sync_rolls_back_a_failed_update(self):
        with self.as_user(ADMIN_USER), installed_apps(APPS_WITH_ERPNEXT):
            workbook_name = create_workbook_from_template(TEMPLATE)["workbook"]
        charts_before = frappe.get_all("Insights Chart v3", {"workbook": workbook_name}, pluck="name")
        self.assertTrue(charts_before)

        def boom(*args, **kwargs):
            # fail mid-rebuild, after _replace_workbook_contents has dropped the children
            raise RuntimeError("restore failed")

        with (
            bumped_version(TEMPLATE, NEXT_VERSION),
            patch.object(InsightsWorkbook, "restore_workbook_contents", boom),
        ):
            sync_workbook_template_updates()  # must swallow the failure, not raise

        # the copy is left whole: children rolled back in, version not advanced
        charts_after = frappe.get_all("Insights Chart v3", {"workbook": workbook_name}, pluck="name")
        self.assertEqual(set(charts_after), set(charts_before))
        self.assertEqual(
            frappe.db.get_value("Insights Workbook", workbook_name, "imported_version"), TEMPLATE_VERSION
        )

    def test_legacy_copy_without_version_adopts_current_as_baseline(self):
        with self.as_user(ADMIN_USER), installed_apps(APPS_WITH_ERPNEXT):
            workbook_name = create_workbook_from_template(TEMPLATE)["workbook"]
        # simulate a copy imported before versioning existed
        frappe.db.set_value(
            "Insights Workbook",
            workbook_name,
            {"imported_version": 0, "imported_checksum": ""},
        )

        sync_workbook_template_updates()

        # backfilled to the current version so it reads as up-to-date, not stale
        self.assertEqual(
            frappe.db.get_value("Insights Workbook", workbook_name, "imported_version"), TEMPLATE_VERSION
        )

    def test_every_committed_template_is_valid_and_importable(self):
        """CI guard: every committed manifest parses with the required keys and
        every committed workbook.json imports without error."""
        template_names = get_template_names()
        self.assertGreater(len(template_names), 0)

        # every committed id is app-qualified, not a bare folder name
        for name in template_names:
            self.assertIn("/", name, f"template id {name!r} must be qualified as app/folder")

        for name in template_names:
            with self.subTest(template=name):
                manifest = get_template_manifest(name)
                for key in MANIFEST_REQUIRED_KEYS:
                    self.assertIn(key, manifest, f"{name}/manifest.json is missing '{key}'")
                self.assertIsInstance(manifest["required_apps"], list)
                self.assertIsInstance(manifest["source_doctypes"], list)

                workbook_path = os.path.join(get_template_path(name), "workbook.json")
                self.assertTrue(os.path.isfile(workbook_path), f"{name} has no workbook.json")
                with open(workbook_path) as f:
                    workbook = json.load(f)
                self.assertTrue(workbook.get("doc", {}).get("title"), f"{name}/workbook.json has no title")

                imported_name = import_workbook(workbook)
                self.assertTrue(frappe.db.exists("Insights Workbook", imported_name))
                frappe.delete_doc("Insights Workbook", imported_name, force=True)
