"""Standard workbooks: the file an app ships, and the site that imports it.

The file is the source of truth, and a site never owns the row. Frappe's import
knows only the workbook's own fields. So the controller writes the members into
the file on export. On import it creates them from the file, under the names the
file gives them.
"""

import os
import shutil
from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.model.sync import get_doc_files
from frappe.modules import get_module_path
from frappe.modules.import_file import import_doc

from insights import standard
from insights.api import get_site_info
from insights.migrate import after_app_install, sync_standard_workbooks
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT

MODULE = "Insights"
WORKBOOK = "test-standard-workbook"
QUERY = "test-standard-workbook-orders"
CHART = "test-standard-workbook-revenue"
DASHBOARD = "test-standard-workbook-overview"

SOURCE_ROWS = "results = [{'amount': 1}]"
SHIPPED = "2026-01-01 00:00:00.000000"


def standard_file(**changes) -> dict:
    """A standard workbook file, as a person writes it by hand."""
    file = {
        "doctype": DT.WORKBOOK,
        "name": WORKBOOK,
        "title": "Test Standard Workbook",
        "is_standard": 1,
        "module": MODULE,
        "modified": SHIPPED,
        "folders": [{"title": "Revenue", "type": "chart", "sort_order": 0}],
        "queries": {
            QUERY: {
                "name": QUERY,
                "title": "Orders",
                "folder": None,
                "sort_order": 0,
                "use_live_connection": 0,
                "is_script_query": 1,
                "is_builder_query": 0,
                "is_native_query": 0,
                "operations": [{"type": "code", "code": SOURCE_ROWS}],
            }
        },
        "charts": {
            CHART: {
                "name": CHART,
                "title": "Revenue",
                "folder": "Revenue",
                "sort_order": 0,
                "query": QUERY,
                "chart_type": "Bar",
                "config": {},
            }
        },
        "dashboards": {
            DASHBOARD: {
                "name": DASHBOARD,
                "title": "Overview",
                "vertical_compact_layout": 0,
                "visibility": "Private",
                "visible_to_roles": [],
                "items": [
                    {"id": "1", "type": "chart", "chart": CHART},
                    {
                        "id": "2",
                        "type": "filter",
                        "filter_name": "Amount",
                        "links": {CHART: f"`{QUERY}`.`amount`"},
                    },
                ],
            }
        },
    }
    file.update(changes)
    return file


@contextmanager
def developer_mode(on=True):
    previous = frappe.conf.get("developer_mode")
    frappe.conf.developer_mode = 1 if on else 0
    try:
        yield
    finally:
        frappe.conf.developer_mode = previous


def module_folder() -> str:
    return os.path.join(get_module_path(MODULE), frappe.scrub(DT.WORKBOOK))


def delete_standard_workbooks():
    """Delete the rows and the files. A developer-mode save writes a file."""
    standard_workbooks = frappe.get_all(DT.WORKBOOK, filters={"is_standard": 1}, pluck="name")
    for name in {*standard_workbooks, *frappe.get_all(DT.WORKBOOK, {"name": WORKBOOK}, pluck="name")}:
        with developer_mode():
            frappe.delete_doc(DT.WORKBOOK, name, force=True, delete_permanently=True)

    shutil.rmtree(module_folder(), ignore_errors=True)


def migrate():
    """The step of `bench migrate` that syncs standard workbook files."""
    sync_standard_workbooks()


def is_imported() -> bool:
    return bool(frappe.db.get_value(DT.WORKBOOK, WORKBOOK, "is_standard"))


class AShippedFileRestoresItsMembersUnderTheirOwnNames(InsightsIntegrationTestCase):
    """How `after_insert` creates the members from the imported file.

    A member is the same document on every site. So the import inserts a member
    under the name in the file, updates a member the site already has, and
    deletes the members the file no longer has.
    """

    def before_test(self):
        delete_standard_workbooks()
        self.addCleanup(delete_standard_workbooks)

    def import_file(self, file=None):
        import_doc(frappe.parse_json(frappe.as_json(file or standard_file())))
        return frappe.get_doc(DT.WORKBOOK, WORKBOOK)

    # @feature standard.ship
    def test_an_imported_member_takes_the_name_the_file_gives_it(self):
        workbook = self.import_file()

        self.assertEqual(workbook.title, "Test Standard Workbook")
        self.assertEqual(frappe.get_all(DT.QUERY, {"workbook": WORKBOOK}, pluck="name"), [QUERY])
        self.assertEqual(frappe.get_all(DT.CHART, {"workbook": WORKBOOK}, pluck="name"), [CHART])
        self.assertEqual(frappe.get_all(DT.DASHBOARD, {"workbook": WORKBOOK}, pluck="name"), [DASHBOARD])
        self.assertEqual(frappe.db.get_value(DT.CHART, CHART, "query"), QUERY)

    # @feature standard.ship
    def test_an_imported_chart_is_standard_and_runs_as_its_reader(self):
        """The file cannot change this. Otherwise a hand-edited file could show
        every reader the rows the author could see on the shipping site."""
        self.import_file()

        chart = frappe.db.get_value(DT.CHART, CHART, ["is_standard", "run_as_owner"], as_dict=True)
        self.assertTrue(chart.is_standard)
        self.assertFalse(chart.run_as_owner)
        self.assertTrue(frappe.db.get_value(DT.DASHBOARD, DASHBOARD, "is_standard"))

    # @feature standard.runs-as-the-reader
    def test_a_standard_chart_cannot_be_saved_running_as_its_owner(self):
        """Its owner is Administrator on every site, so Run as owner would show
        every row to every reader."""
        self.import_file()

        with developer_mode():
            chart = frappe.get_doc(DT.CHART, CHART)
            chart.run_as_owner = 1
            self.assertRaisesRegex(frappe.ValidationError, "cannot run as its owner", chart.save)

        self.assertFalse(frappe.db.get_value(DT.CHART, CHART, "run_as_owner"))

    # @feature standard.ship
    def test_an_imported_dashboard_is_read_by_every_desk_user(self):
        """The file says `Private`, but a dashboard that no desk user may read is
        of no use to anyone."""
        self.import_file()

        dashboard = frappe.get_doc(DT.DASHBOARD, DASHBOARD)
        self.assertEqual(dashboard.visibility, "Roles")
        self.assertEqual([row.role for row in dashboard.visible_to_roles], ["Desk User"])

    # @feature standard.ship
    def test_an_imported_member_lands_in_the_folder_the_file_titles(self):
        self.import_file()

        folder = frappe.db.get_value(DT.CHART, CHART, "folder")
        self.assertEqual(
            frappe.db.get_value("Insights Folder", folder, ["title", "type", "workbook"]),
            ("Revenue", "chart", WORKBOOK),
        )

    # @feature standard.resync
    def test_a_second_import_updates_the_members_the_site_already_holds(self):
        self.import_file()
        first_folder = frappe.db.get_value(DT.CHART, CHART, "folder")

        file = standard_file()
        file["charts"][CHART]["title"] = "Revenue, restated"
        self.import_file(file)

        self.assertEqual(frappe.get_all(DT.CHART, {"workbook": WORKBOOK}, pluck="name"), [CHART])
        self.assertEqual(frappe.db.get_value(DT.CHART, CHART, "title"), "Revenue, restated")
        self.assertEqual(
            frappe.db.get_value(DT.CHART, CHART, "folder"),
            first_folder,
            "the folder the site minted survives a re-import",
        )

    # @feature standard.resync
    def test_a_second_import_deletes_the_members_the_file_has_dropped(self):
        self.import_file()

        file = standard_file()
        file["dashboards"] = {}
        file["charts"] = {}
        file["folders"] = []
        self.import_file(file)

        self.assertEqual(frappe.get_all(DT.DASHBOARD, {"workbook": WORKBOOK}, pluck="name"), [])
        self.assertEqual(frappe.get_all(DT.CHART, {"workbook": WORKBOOK}, pluck="name"), [])
        self.assertEqual(frappe.get_all("Insights Folder", {"workbook": WORKBOOK}, pluck="name"), [])
        self.assertEqual(frappe.get_all(DT.QUERY, {"workbook": WORKBOOK}, pluck="name"), [QUERY])

    # @feature standard.ship
    def test_an_import_is_not_a_workbook_a_person_created(self):
        """For a new workbook, `after_insert` sends a telemetry event and restores
        the backup of a deleted workbook. An import needs neither, and the file
        already has the members."""
        with patch("insights.insights.doctype.insights_workbook.insights_workbook.capture") as reported:
            self.import_file()

        reported.assert_not_called()


class AFileLeavesOutWhatTheSiteOwns(InsightsIntegrationTestCase):
    """`before_export` replaces the member summaries from `as_dict` with the members."""

    def before_test(self):
        delete_standard_workbooks()
        self.addCleanup(delete_standard_workbooks)
        import_doc(frappe.parse_json(frappe.as_json(standard_file())))

    def exported(self) -> dict:
        doc = frappe.get_doc(DT.WORKBOOK, WORKBOOK)
        file = doc.as_dict(no_nulls=True, ignore_computed_child_tables=True)
        doc.run_method("before_export", file)
        return file

    # @feature standard.file-format
    def test_a_file_includes_the_members_rather_than_a_summary_of_them(self):
        file = self.exported()

        self.assertEqual(list(file["queries"]), [QUERY])
        self.assertEqual(file["charts"][CHART]["title"], "Revenue")
        self.assertEqual(file["charts"][CHART]["folder"], "Revenue")
        self.assertEqual(file["folders"], [{"title": "Revenue", "type": "chart", "sort_order": 0}])

    # @feature standard.file-format
    def test_a_file_includes_nothing_a_site_owns(self):
        """A key that changes by itself would change the file on every save."""
        file = self.exported()

        for field in (
            "timestamp",
            "read_only",
            "data_backup",
        ):
            self.assertNotIn(field, file)

        self.assertNotIn("run_as_owner", file["charts"][CHART])
        self.assertNotIn("is_standard", file["charts"][CHART])
        self.assertNotIn("visibility", file["dashboards"][DASHBOARD])
        self.assertNotIn("visible_to_roles", file["dashboards"][DASHBOARD])


class AStandardWorkbookIsReadOnlyOnTheSiteThatHoldsIt(InsightsIntegrationTestCase):
    """The file is the source of truth, so a site cannot change what the app ships.

    A member is guarded through its workbook, so one rule covers the workbook
    and all four kinds of member. It refuses an edit, a delete, a rename, and a
    new member that the site adds.
    """

    def before_test(self):
        delete_standard_workbooks()
        self.addCleanup(delete_standard_workbooks)
        import_doc(frappe.parse_json(frappe.as_json(standard_file())))

    def assertRefused(self, act):
        with self.assertRaises(frappe.ValidationError):
            act()

    # @feature standard.read-only
    def test_the_workbook_and_its_members_refuse_an_edit(self):
        for doctype, name in (
            (DT.WORKBOOK, WORKBOOK),
            (DT.QUERY, QUERY),
            (DT.CHART, CHART),
            (DT.DASHBOARD, DASHBOARD),
        ):
            with self.subTest(doctype=doctype):
                doc = frappe.get_doc(doctype, name)
                doc.title = "renamed by the site"
                self.assertRefused(doc.save)

    # @feature standard.read-only
    def test_the_workbook_and_its_members_refuse_a_delete(self):
        for doctype, name in (
            (DT.CHART, CHART),
            (DT.DASHBOARD, DASHBOARD),
            (DT.QUERY, QUERY),
            (DT.WORKBOOK, WORKBOOK),
        ):
            with self.subTest(doctype=doctype):
                self.assertRefused(
                    lambda doctype=doctype, name=name: frappe.delete_doc(doctype, name, force=True)
                )

    # @feature standard.read-only
    def test_the_workbook_and_its_members_refuse_a_rename(self):
        for doctype, name in ((DT.WORKBOOK, WORKBOOK), (DT.CHART, CHART)):
            with self.subTest(doctype=doctype):
                self.assertRefused(
                    lambda doctype=doctype, name=name: frappe.rename_doc(
                        doctype, name, f"{name}-renamed", force=True
                    )
                )

    # @feature standard.read-only
    def test_a_site_cannot_add_a_member_of_its_own(self):
        chart = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": "a chart of the site's own",
                "workbook": WORKBOOK,
                "query": QUERY,
                "chart_type": "Bar",
            }
        )
        self.assertRefused(chart.insert)

    # @feature standard.read-only
    def test_a_folder_in_a_standard_workbook_is_guarded_too(self):
        folder = frappe.get_doc(
            {"doctype": "Insights Folder", "title": "Mine", "type": "chart", "workbook": WORKBOOK}
        )
        self.assertRefused(folder.insert)

    # @feature standard.read-only
    def test_the_workbook_says_it_is_read_only(self):
        """The builder reads this to show the read-only icon."""
        self.assertTrue(frappe.get_doc(DT.WORKBOOK, WORKBOOK).as_dict().read_only)
        self.assertTrue(frappe.get_doc(DT.CHART, CHART).as_dict().read_only)

        with developer_mode():
            self.assertFalse(frappe.get_doc(DT.WORKBOOK, WORKBOOK).as_dict().read_only)

    # @feature standard.read-only
    def test_developer_mode_may_change_it(self):
        with developer_mode():
            chart = frappe.get_doc(DT.CHART, CHART)
            chart.title = "Revenue, restated"
            chart.save()

        self.assertEqual(frappe.db.get_value(DT.CHART, CHART, "title"), "Revenue, restated")

    # @feature standard.read-only
    def test_a_migrate_may_change_it(self):
        """The sync deletes a workbook when an app drops its file, and the sync
        runs outside developer mode."""
        frappe.flags.in_migrate = True
        self.addCleanup(lambda: frappe.flags.pop("in_migrate", None))

        frappe.delete_doc(DT.WORKBOOK, WORKBOOK, force=True)

        self.assertFalse(frappe.db.exists(DT.WORKBOOK, WORKBOOK))
        self.assertEqual(frappe.get_all(DT.CHART, {"workbook": WORKBOOK}, pluck="name"), [])


class DeveloperModeWritesTheFileBack(InsightsIntegrationTestCase):
    """Editing a standard workbook edits its file.

    A member is stored in its workbook's file. So a save of the workbook or of
    any member writes the workbook's file.
    """

    def before_test(self):
        delete_standard_workbooks()
        self.addCleanup(delete_standard_workbooks)
        import_doc(frappe.parse_json(frappe.as_json(standard_file())))

    def file_path(self, name=WORKBOOK) -> str:
        stem = frappe.scrub(name)
        return os.path.join(module_folder(), stem, f"{stem}.json")

    def written(self, name=WORKBOOK) -> dict:
        with open(self.file_path(name)) as f:
            return frappe.parse_json(f.read())

    # @feature standard.export-on-save
    def test_saving_the_workbook_writes_its_file(self):
        with developer_mode():
            workbook = frappe.get_doc(DT.WORKBOOK, WORKBOOK)
            workbook.title = "Restated"
            workbook.save()

        file = self.written()
        self.assertEqual(file["title"], "Restated")
        self.assertEqual(list(file["charts"]), [CHART])

    # @feature standard.export-on-save
    def test_saving_a_member_writes_the_workbook_s_file(self):
        with developer_mode():
            chart = frappe.get_doc(DT.CHART, CHART)
            chart.title = "Revenue, restated"
            chart.save()

        self.assertEqual(self.written()["charts"][CHART]["title"], "Revenue, restated")

    # @feature standard.export-on-save
    def test_deleting_a_member_writes_the_workbook_s_file_without_it(self):
        with developer_mode():
            frappe.delete_doc(DT.DASHBOARD, DASHBOARD, force=True)

        self.assertEqual(self.written()["dashboards"], {})

    # @feature standard.export-on-save
    def test_deleting_the_workbook_removes_its_file(self):
        """Its members are deleted with it, and each member's delete writes the file."""
        with developer_mode():
            frappe.get_doc(DT.WORKBOOK, WORKBOOK).save()
            frappe.delete_doc(DT.WORKBOOK, WORKBOOK, force=True)

        self.assertFalse(os.path.exists(os.path.dirname(self.file_path())))

    # @feature standard.export-on-save
    def test_renaming_the_workbook_moves_its_file(self):
        with developer_mode():
            frappe.get_doc(DT.WORKBOOK, WORKBOOK).save()
            frappe.rename_doc(DT.WORKBOOK, WORKBOOK, "test-standard-renamed", force=True)

        self.assertFalse(os.path.exists(os.path.dirname(self.file_path())))
        self.assertEqual(self.written("test-standard-renamed")["name"], "test-standard-renamed")

    # @feature standard.export-on-save
    def test_a_workbook_the_app_no_longer_ships_loses_its_file(self):
        with developer_mode():
            workbook = frappe.get_doc(DT.WORKBOOK, WORKBOOK)
            workbook.save()
            workbook.is_standard = 0
            workbook.save()

        self.assertFalse(os.path.exists(os.path.dirname(self.file_path())))
        self.assertIsNone(frappe.db.get_value(DT.WORKBOOK, WORKBOOK, "module"))


class MarkingAWorkbookStandardSettlesItsNames(InsightsIntegrationTestCase):
    """The names identify the workbook and its members on every site that imports the file.

    A desk sidebar item links to a dashboard by its docname. So the names are
    set once, here, and nothing changes them later.
    """

    def before_test(self):
        delete_standard_workbooks()
        self.addCleanup(delete_standard_workbooks)
        self.addCleanup(self.delete_source)
        self.built = self.build()

    def delete_source(self):
        for name in frappe.get_all(DT.WORKBOOK, filters={"title": ("like", "Selling Board%")}, pluck="name"):
            with developer_mode():
                frappe.delete_doc(DT.WORKBOOK, name, force=True, delete_permanently=True)

    def build(self, title="Selling Board") -> frappe._dict:
        """A workbook as a person builds it: hash names, a chart on a query, and
        a dashboard that uses both."""
        workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": title}).insert()
        source = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": "Orders",
                "workbook": workbook.name,
                "use_live_connection": 0,
                "is_script_query": 1,
                "operations": [{"type": "code", "code": SOURCE_ROWS}],
            }
        ).insert()
        derived = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": "Revenue by Month",
                "workbook": workbook.name,
                "use_live_connection": 0,
                "operations": [
                    {
                        "type": "source",
                        "table": {
                            "type": "query",
                            "query_name": source.name,
                            "workbook": workbook.name,
                        },
                    }
                ],
            }
        ).insert()
        chart = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": "Revenue Trend",
                "workbook": workbook.name,
                "query": derived.name,
                "chart_type": "Line",
            }
        ).insert()
        dashboard = frappe.get_doc(
            {
                "doctype": DT.DASHBOARD,
                "title": "Overview",
                "workbook": workbook.name,
                "items": [
                    {"id": "1", "type": "chart", "chart": chart.name},
                    {
                        "id": "2",
                        "type": "filter",
                        "filter_name": "Amount",
                        "links": {chart.name: f"`{derived.name}`.`amount`"},
                    },
                ],
            }
        ).insert()
        return frappe._dict(
            workbook=workbook.name,
            source=source.name,
            derived=derived.name,
            chart=chart.name,
            dashboard=dashboard.name,
        )

    def mark(self, workbook=None, name="selling", module=MODULE):
        with developer_mode():
            return frappe.get_doc(DT.WORKBOOK, workbook or self.built.workbook).mark_as_standard(
                name=name, module=module
            )

    # @feature standard.mark
    def test_the_workbook_and_its_members_take_readable_names(self):
        name = self.mark()

        self.assertEqual(name, "selling")
        self.assertTrue(frappe.db.exists(DT.WORKBOOK, "selling"))
        self.assertEqual(
            sorted(frappe.get_all(DT.QUERY, {"workbook": "selling"}, pluck="name")),
            ["selling-orders", "selling-revenue-by-month"],
        )
        self.assertTrue(frappe.db.exists(DT.CHART, "selling-revenue-trend"))
        self.assertTrue(frappe.db.exists(DT.DASHBOARD, "selling-overview"))
        self.assertEqual(frappe.db.get_value(DT.WORKBOOK, "selling", ["is_standard", "module"]), (1, MODULE))

    # @feature standard.mark
    def test_a_name_the_workbook_already_uses_takes_a_number(self):
        second = self.build("Selling Board, again")
        frappe.db.set_value(DT.QUERY, second.derived, "title", "Orders")
        frappe.rename_doc(DT.WORKBOOK, second.workbook, "second-board", force=True)

        self.mark(workbook="second-board", name="second-board")

        self.assertEqual(
            sorted(frappe.get_all(DT.QUERY, {"workbook": "second-board"}, pluck="name")),
            ["second-board-orders", "second-board-orders-2"],
        )

    # @feature standard.mark
    def test_every_reference_follows_the_rename(self):
        self.mark()

        operations = frappe.parse_json(
            frappe.db.get_value(DT.QUERY, "selling-revenue-by-month", "operations")
        )
        self.assertEqual(operations[0]["table"]["query_name"], "selling-orders")
        self.assertEqual(
            operations[0]["table"]["workbook"],
            "selling",
            "a reference names the workbook its query sits in, so both move together",
        )

        self.assertEqual(
            frappe.db.get_value(DT.CHART, "selling-revenue-trend", "query"), "selling-revenue-by-month"
        )

        items = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, "selling-overview", "items"))
        self.assertEqual(items[0]["chart"], "selling-revenue-trend")
        self.assertEqual(items[1]["links"], {"selling-revenue-trend": "`selling-revenue-by-month`.`amount`"})

    # @feature standard.mark
    def test_a_marked_dashboard_is_read_by_every_desk_user(self):
        """The authoring site sets the same visibility as the import does, so the
        dashboard has the same readers on every site."""
        self.mark()

        dashboard = frappe.get_doc(DT.DASHBOARD, "selling-overview")
        self.assertEqual(dashboard.visibility, "Roles")
        self.assertEqual([row.role for row in dashboard.visible_to_roles], ["Desk User"])

    # @feature standard.mark
    def test_two_folders_of_one_type_never_share_a_title(self):
        """A file refers to a folder by title, so a second folder with the same
        title would get the first folder's members. A new folder gets the next
        free title, and a rename to a used title is refused."""
        first, second = (
            frappe.get_doc(
                {
                    "doctype": "Insights Folder",
                    "title": "Revenue",
                    "type": "chart",
                    "workbook": self.built.workbook,
                }
            ).insert()
            for _ in range(2)
        )
        self.assertEqual((first.title, second.title), ("Revenue", "Revenue 2"))

        second.title = "Revenue"
        with self.assertRaisesRegex(frappe.ValidationError, "already exists"):
            second.save()

        self.mark()

    # @feature standard.mark
    def test_a_workbook_is_marked_standard_in_developer_mode_only(self):
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(DT.WORKBOOK, self.built.workbook).mark_as_standard(name="selling", module=MODULE)

    # @feature standard.mark
    def test_a_name_whose_file_another_workbook_already_holds_is_refused(self):
        """The file name is `scrub(name)`, and two names can scrub to the same value."""
        self.mark(name="selling_report")

        other = self.build("Selling Board, other")
        with self.assertRaises(frappe.ValidationError):
            self.mark(workbook=other.workbook, name="selling-report")

    # @feature standard.mark
    def test_a_rename_onto_a_name_another_workbook_files_under_is_refused(self):
        """A rename also sets a standard workbook's name, and `after_rename`
        writes the file. Without this check, it would overwrite the other
        workbook's file."""
        self.mark(name="selling_report")

        other = self.build("Selling Board, other")
        self.mark(workbook=other.workbook, name="buying-report")

        with developer_mode(), self.assertRaises(frappe.ValidationError):
            frappe.rename_doc(DT.WORKBOOK, "buying-report", "selling-report", force=True)

    # @feature workbook.duplicate
    def test_a_duplicate_of_a_standard_workbook_belongs_to_the_site(self):
        self.mark()

        with developer_mode():
            copy = frappe.get_doc(DT.WORKBOOK, "selling").duplicate()

        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, copy, True)
        self.assertEqual(frappe.db.get_value(DT.WORKBOOK, copy, ["is_standard", "module"]), (0, None))
        for chart in frappe.get_all(DT.CHART, {"workbook": copy}, pluck="name"):
            self.assertFalse(frappe.db.get_value(DT.CHART, chart, "is_standard"))


class TheWalkTakesEveryFileAnAppShips(InsightsIntegrationTestCase):
    """What a migrate does, end to end.

    A migrate imports a file when its `modified` is newer than the row. It
    deletes a workbook when an app drops its file. It runs outside developer
    mode, with `frappe.flags.in_migrate` set.
    """

    def before_test(self):
        delete_standard_workbooks()
        self.addCleanup(delete_standard_workbooks)
        frappe.flags.in_migrate = True
        self.addCleanup(lambda: frappe.flags.pop("in_migrate", None))

    def ship(self, file=None):
        """Write a standard workbook file where the sync looks for it."""
        stem = frappe.scrub(WORKBOOK)
        folder = os.path.join(module_folder(), stem)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, f"{stem}.json"), "w") as f:
            f.write(frappe.as_json(file or standard_file()))

    def unship(self):
        shutil.rmtree(module_folder(), ignore_errors=True)

    # @feature standard.ship
    def test_a_migrate_takes_the_workbook_the_file_ships(self):
        self.ship()
        migrate()

        self.assertTrue(frappe.db.get_value(DT.WORKBOOK, WORKBOOK, "is_standard"))
        self.assertEqual(frappe.get_all(DT.CHART, {"workbook": WORKBOOK}, pluck="name"), [CHART])

    # @feature standard.ship
    def test_frappe_s_own_sync_leaves_the_file_alone(self):
        """Frappe syncs apps in install order. It would import an earlier app's
        file before the Insights Workbook schema is synced."""
        self.ship()

        walked = get_doc_files([], get_module_path(MODULE))

        self.assertFalse([path for path in walked if path.startswith(module_folder())])

    # @feature standard.ship
    def test_installing_insights_takes_the_files_installed_apps_ship(self):
        self.ship()

        for fn in frappe.get_hooks("after_install", app_name="insights"):
            frappe.get_attr(fn)()

        self.assertTrue(is_imported())

    # @feature standard.ship
    def test_installing_an_app_takes_the_files_it_ships(self):
        self.ship()

        after_app_install("frappe")
        self.assertFalse(is_imported())

        for fn in frappe.get_hooks("after_app_install", app_name="insights"):
            frappe.get_attr(fn)("insights")
        self.assertTrue(is_imported())

    # @feature standard.resync
    def test_a_migrate_takes_the_change_a_release_makes(self):
        self.ship()
        migrate()

        file = standard_file(modified="2026-02-01 00:00:00.000000")
        file["charts"][CHART]["title"] = "Revenue, restated"
        self.ship(file)
        migrate()

        self.assertEqual(frappe.db.get_value(DT.CHART, CHART, "title"), "Revenue, restated")

    # @feature standard.resync
    def test_a_member_edit_reaches_a_site_that_took_the_earlier_file(self):
        """A member's edit does not change the workbook's `modified`, and frappe
        skips a file that is not newer than the row."""
        self.ship()
        migrate()

        with developer_mode():
            chart = frappe.get_doc(DT.CHART, CHART)
            chart.title = "Revenue, restated"
            chart.save()

        # act as another site that still has the rows from the earlier file
        frappe.db.set_value(DT.CHART, CHART, "title", "Revenue", update_modified=False)
        frappe.db.set_value(DT.WORKBOOK, WORKBOOK, "modified", SHIPPED, update_modified=False)
        migrate()

        self.assertEqual(frappe.db.get_value(DT.CHART, CHART, "title"), "Revenue, restated")

    # @feature standard.resync
    def test_a_migrate_deletes_the_workbook_no_app_ships_any_more(self):
        self.ship()
        migrate()

        self.unship()
        migrate()

        self.assertFalse(frappe.db.exists(DT.WORKBOOK, WORKBOOK))
        self.assertEqual(frappe.get_all(DT.CHART, {"workbook": WORKBOOK}, pluck="name"), [])

    # @feature standard.resync
    def test_a_migrate_keeps_the_workbooks_the_site_made(self):
        workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": "The site's own"}).insert()
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, workbook.name, force=True)

        migrate()

        self.assertTrue(frappe.db.exists(DT.WORKBOOK, workbook.name))

    # @feature standard.resync
    def test_a_file_never_replaces_a_workbook_the_site_made(self):
        """Frappe deletes the row with the file's name before it inserts the file.
        The site would lose its workbook, and `is_standard` would let its charts
        past the site's team grants."""
        frappe.get_doc({"doctype": DT.WORKBOOK, "title": "The site's own"}).insert(set_name=WORKBOOK)
        frappe.db.set_value(DT.WORKBOOK, WORKBOOK, "modified", "2025-01-01", update_modified=False)
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, WORKBOOK, force=True)
        # a refused import leaves `in_import` set. A real migrate stops at the
        # error, but this test continues
        self.addCleanup(lambda: frappe.flags.pop("in_import", None))
        self.ship()

        self.assertRaisesRegex(frappe.ValidationError, "already has a document of that name", migrate)
        self.assertEqual(frappe.db.get_value(DT.WORKBOOK, WORKBOOK, "title"), "The site's own")
        self.assertFalse(frappe.db.get_value(DT.WORKBOOK, WORKBOOK, "is_standard"))


class AMemberKeptForDeskLeavesWithItsClaim(InsightsIntegrationTestCase):
    """A release drops a chart that a desk Dashboard Chart shows. The sync keeps
    the chart for the desk document, but the app no longer ships it. So the file
    is written without it, and a migrate deletes it once no desk document shows
    it."""

    def before_test(self):
        from insights.desk import install_custom_fields

        install_custom_fields()
        delete_standard_workbooks()
        self.addCleanup(delete_standard_workbooks)
        frappe.flags.in_migrate = True
        self.addCleanup(lambda: frappe.flags.pop("in_migrate", None))

        TheWalkTakesEveryFileAnAppShips.ship(self)
        migrate()

        self.desk_chart = frappe.get_doc(
            {
                "doctype": "Dashboard Chart",
                "chart_name": "Test Standard Kept Chart",
                "chart_type": "Count",
                "document_type": "ToDo",
                "based_on": "creation",
                "filters_json": "[]",
                "insights_chart": CHART,
            }
        ).insert()
        self.addCleanup(
            lambda: frappe.db.exists("Dashboard Chart", self.desk_chart.name)
            and frappe.delete_doc("Dashboard Chart", self.desk_chart.name, force=True)
        )

        file = standard_file(modified="2026-02-01 00:00:00.000000")
        file["dashboards"] = {}
        file["charts"] = {}
        file["folders"] = []
        TheWalkTakesEveryFileAnAppShips.ship(self, file)
        migrate()

    def written(self) -> dict:
        stem = frappe.scrub(WORKBOOK)
        with open(os.path.join(module_folder(), stem, f"{stem}.json")) as f:
            return frappe.parse_json(f.read())

    # @feature standard.resync standard.export-on-save
    def test_a_developer_mode_save_writes_the_file_without_it(self):
        """A developer-mode save writes the file through `standard.export` and
        `InsightsWorkbook.before_export`. The file has only the members the app
        still ships. A download still has the kept chart, because the chart is
        on the site."""
        self.assertTrue(frappe.db.exists(DT.CHART, CHART))

        with developer_mode():
            frappe.get_doc(DT.WORKBOOK, WORKBOOK).save()

        self.assertEqual(self.written()["charts"], {})
        self.assertEqual(list(self.written()["queries"]), [QUERY])
        self.assertEqual(list(frappe.get_doc(DT.WORKBOOK, WORKBOOK).export()["charts"]), [CHART])

    # @feature standard.resync
    def test_a_migrate_deletes_it_once_no_desk_document_shows_it(self):
        """The file did not change on this migrate. The chart stays while the
        desk document shows it."""
        migrate()
        self.assertTrue(frappe.db.exists(DT.CHART, CHART))

        frappe.delete_doc("Dashboard Chart", self.desk_chart.name, force=True)
        migrate()

        self.assertFalse(frappe.db.exists(DT.CHART, CHART))
        self.assertEqual(frappe.get_all(DT.QUERY, {"workbook": WORKBOOK}, pluck="name"), [QUERY])


class WhatTheExportToAppDialogReads(InsightsIntegrationTestCase):
    """What the Export to app dialog reads: whether the bench can write app
    files, and which modules it may write to."""

    # @feature standard.export-to-app
    def test_a_module_names_its_app_and_the_folder_its_file_goes_in(self):
        with developer_mode():
            modules = standard.export_modules()

        insights = next(module for module in modules if module["module"] == MODULE)
        self.assertEqual(insights["app"], "insights")
        self.assertEqual(insights["folder"], module_folder())

        installed = set(frappe.get_installed_apps())
        self.assertTrue(
            all(module["app"] in installed for module in modules),
            "a module of an app this site does not have cannot take a file",
        )

        # the list must match the framework's module list. Frappe never reads a
        # module that no app's `modules.txt` lists, so the next migrate deletes a
        # file written there as an orphan
        from frappe.modules.utils import get_module_list

        shipped = {(app, module) for app in installed for module in get_module_list(app)}
        self.assertTrue(
            all((module["app"], module["module"]) in shipped for module in modules),
            "a module no app ships cannot take a file",
        )

    # @feature standard.export-to-app
    def test_a_site_outside_developer_mode_has_no_module_to_ship_in(self):
        with developer_mode(on=False):
            self.assertEqual(standard.export_modules(), [])

    # @feature standard.export-to-app
    def test_the_browser_learns_the_bench_runs_in_developer_mode(self):
        with developer_mode():
            self.assertTrue(get_site_info()["developer_mode"])
        with developer_mode(on=False):
            self.assertFalse(get_site_info()["developer_mode"])
