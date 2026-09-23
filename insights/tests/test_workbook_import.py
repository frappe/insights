"""An import references its own copies, not the exporter's queries.

A file names its queries as the exporting site named them. Import rewrites every
name the file carries to the copy that replaces it, so importing asks for no
access to the queries the file was exported from.

A whole workbook, a single query and a single chart are all imported this way.
"""

import frappe

from insights.insights.doctype.insights_chart_v3.insights_chart_v3 import import_chart
from insights.insights.doctype.insights_query_v3.insights_query_v3 import (
    extract_query_deps_from_operations,
    import_query,
)
from insights.insights.doctype.insights_workbook.insights_workbook import import_workbook
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_test_workbook, delete_users
from insights.tests.permissions_utils import USER_1, USER_2, create_test_users

OWNER = USER_1
IMPORTER = USER_2

SOURCE_ROWS = "select 1 as amount"


def create_source_query(owner, workbook, title):
    """Native SQL rather than a script: a script in a file is refused to anyone
    but an admin (Q17), and nothing here runs the query."""
    with as_user(owner):
        return frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": title,
                "workbook": workbook,
                "use_live_connection": 0,
                "is_native_query": 1,
                "operations": [{"type": "sql", "data_source": "Site DB", "raw_sql": SOURCE_ROWS}],
            }
        ).insert()


class ImportedReferencesPointAtTheNewCopies(InsightsIntegrationTestCase):
    """A workbook file is importable by anyone who may make a workbook."""

    @classmethod
    def before_class(cls):
        create_test_users()

        cls.workbook = create_test_workbook(OWNER, "import source").name
        cls.source = create_source_query(OWNER, cls.workbook, "source").name

        with as_user(OWNER):
            cls.consumer = (
                frappe.get_doc(
                    {
                        "doctype": DT.QUERY,
                        "title": "consumer",
                        "workbook": cls.workbook,
                        "use_live_connection": 0,
                        "operations": [
                            {"type": "source", "table": {"type": "query", "query_name": cls.source}}
                        ],
                    }
                )
                .insert()
                .name
            )

            cls.file = frappe.get_doc(DT.WORKBOOK, cls.workbook).export()

        cls.made_workbooks = [cls.workbook]

    @classmethod
    def after_class(cls):
        for workbook in frappe.get_all(
            DT.WORKBOOK, filters={"name": ("in", cls.made_workbooks)}, pluck="name"
        ):
            frappe.delete_doc(DT.WORKBOOK, workbook, force=True, delete_permanently=True)
        delete_users(OWNER, IMPORTER)

    # @feature permissions.import-without-access
    def test_a_workbook_file_imports_for_someone_who_cannot_read_its_queries(self):
        with as_user(IMPORTER):
            self.assertFalse(
                frappe.has_permission(DT.QUERY, ptype="read", doc=self.source),
                "the fixture needs the importer to have no access to the exported queries",
            )
            imported = import_workbook(self.file)["workbook"]
        self.made_workbooks.append(imported)

        queries = frappe.get_all(DT.QUERY, filters={"workbook": imported}, pluck="name")
        self.assertEqual(len(queries), 2)

    # @feature workbook.copy-paste
    def test_the_import_answers_with_the_name_every_copy_took(self):
        """The shipped skill reads this map to edit what it just imported."""
        with as_user(IMPORTER):
            result = import_workbook(self.file)
        self.made_workbooks.append(result["workbook"])

        names = result["names"]
        self.assertEqual(names[self.workbook], result["workbook"])
        self.assertEqual(
            sorted(names[name] for name in (self.source, self.consumer)),
            sorted(frappe.get_all(DT.QUERY, filters={"workbook": result["workbook"]}, pluck="name")),
        )

    # @feature workbook.copy-paste
    def test_an_imported_reference_names_the_imported_copy(self):
        with as_user(IMPORTER):
            imported = import_workbook(self.file)["workbook"]
        self.made_workbooks.append(imported)

        deps = set()
        for name in frappe.get_all(DT.QUERY, filters={"workbook": imported}, pluck="name"):
            operations = frappe.parse_json(frappe.db.get_value(DT.QUERY, name, "operations"))
            deps |= set(extract_query_deps_from_operations(operations or []))

        self.assertTrue(deps, "the imported workbook should still hold a reference")
        self.assertNotIn(self.source, deps, "a reference must not point back at the source site")


class ImportingOneQueryCarriesItsReferences(InsightsIntegrationTestCase):
    """A single query is imported the same way a workbook is.

    `import_query` is what the UI calls to paste a query into another workbook.
    The file names the exporter's queries, so the copies go in first.
    """

    @classmethod
    def before_class(cls):
        create_test_users()

        cls.workbook = create_test_workbook(OWNER, "one query source").name
        cls.source = create_source_query(OWNER, cls.workbook, "one query source query").name

        with as_user(OWNER):
            consumer = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "one query consumer",
                    "workbook": cls.workbook,
                    "use_live_connection": 0,
                    "operations": [{"type": "source", "table": {"type": "query", "query_name": cls.source}}],
                }
            ).insert()
            cls.file = consumer.export()

        cls.target = create_test_workbook(IMPORTER, "one query target").name

    @classmethod
    def after_class(cls):
        for workbook in (cls.workbook, cls.target):
            frappe.delete_doc(DT.WORKBOOK, workbook, force=True, delete_permanently=True)
        delete_users(OWNER, IMPORTER)

    # @feature query.copy-paste
    def test_a_query_file_imports_for_someone_who_cannot_read_its_reference(self):
        with as_user(IMPORTER):
            self.assertFalse(
                frappe.has_permission(DT.QUERY, ptype="read", doc=self.source),
                "the fixture needs the importer to have no access to the referenced query",
            )
            imported = import_query(self.file, self.target)

        self.assertTrue(frappe.db.exists(DT.QUERY, imported))

    # @feature query.copy-paste
    def test_the_imported_reference_names_the_imported_copy(self):
        with as_user(IMPORTER):
            imported = import_query(self.file, self.target)

        operations = frappe.parse_json(frappe.db.get_value(DT.QUERY, imported, "operations"))
        deps = set(extract_query_deps_from_operations(operations or []))

        self.assertTrue(deps, "the imported query should still hold a reference")
        self.assertNotIn(self.source, deps, "a reference must not point back at the source site")


class ImportingOneQueryCopiesAReferenceOnce(InsightsIntegrationTestCase):
    """`export` nests, so a query two branches both build on appears twice in the
    file. The import has to recognise it as one query, not copy it per path."""

    @classmethod
    def before_class(cls):
        create_test_users()

        cls.workbook = create_test_workbook(OWNER, "diamond source").name
        cls.base = create_source_query(OWNER, cls.workbook, "diamond base").name
        left = cls.reference(OWNER, cls.workbook, "diamond left", cls.base)
        right = cls.reference(OWNER, cls.workbook, "diamond right", cls.base)

        with as_user(OWNER):
            top = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "diamond top",
                    "workbook": cls.workbook,
                    "use_live_connection": 0,
                    "operations": [
                        {"type": "source", "table": {"type": "query", "query_name": left}},
                        {"type": "union", "table": {"type": "query", "query_name": right}},
                    ],
                }
            ).insert()
            cls.file = top.export()

        cls.target = create_test_workbook(IMPORTER, "diamond target").name

    @classmethod
    def reference(cls, owner, workbook, title, referenced):
        with as_user(owner):
            return (
                frappe.get_doc(
                    {
                        "doctype": DT.QUERY,
                        "title": title,
                        "workbook": workbook,
                        "use_live_connection": 0,
                        "operations": [
                            {"type": "source", "table": {"type": "query", "query_name": referenced}}
                        ],
                    }
                )
                .insert()
                .name
            )

    @classmethod
    def after_class(cls):
        for workbook in (cls.workbook, cls.target):
            frappe.delete_doc(DT.WORKBOOK, workbook, force=True, delete_permanently=True)
        delete_users(OWNER, IMPORTER)

    # @feature query.copy-paste
    def test_a_query_reached_by_two_branches_is_imported_once(self):
        """One import, so the count is the import's own work."""
        with as_user(IMPORTER):
            import_query(self.file, self.target)

        copies = frappe.get_all(DT.QUERY, filters={"workbook": self.target}, fields=["name", "title"])
        base = [c.name for c in copies if c.title == "diamond base"]

        self.assertEqual(len(base), 1, "the base query was copied once per path to it")
        self.assertEqual(len(copies), 4)

        deps = set()
        for copy in copies:
            operations = frappe.parse_json(frappe.db.get_value(DT.QUERY, copy.name, "operations"))
            deps |= set(extract_query_deps_from_operations(operations or []))

        self.assertIn(base[0], deps, "both branches must name the one copy")


class ImportingOneChartCarriesItsQuery(InsightsIntegrationTestCase):
    """A chart is imported the same way a query and a workbook are.

    `import_chart` is what the UI calls to paste a chart into another workbook.
    `validate` reads the query link, so the copy has to exist before the insert.
    """

    @classmethod
    def before_class(cls):
        create_test_users()

        cls.workbook = create_test_workbook(OWNER, "chart source").name
        cls.query = create_source_query(OWNER, cls.workbook, "chart source query").name

        with as_user(OWNER):
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "chart to paste",
                    "workbook": cls.workbook,
                    "query": cls.query,
                    "chart_type": "Bar",
                }
            ).insert()
            cls.file = chart.export()

        cls.target = create_test_workbook(IMPORTER, "chart target").name

    @classmethod
    def after_class(cls):
        for workbook in (cls.workbook, cls.target):
            frappe.delete_doc(DT.WORKBOOK, workbook, force=True, delete_permanently=True)
        delete_users(OWNER, IMPORTER)

    # @feature charts.copy-paste permissions.import-without-access
    def test_a_chart_file_imports_for_someone_who_cannot_read_its_query(self):
        with as_user(IMPORTER):
            self.assertFalse(
                frappe.has_permission(DT.QUERY, ptype="read", doc=self.query),
                "the fixture needs the importer to have no access to the exported query",
            )
            imported = import_chart(self.file, self.target)

        query = frappe.db.get_value(DT.CHART, imported, "query")
        self.assertNotEqual(query, self.query, "the chart must not point back at the source site")
        self.assertEqual(frappe.db.get_value(DT.QUERY, query, "workbook"), self.target)


class ImportingAcrossSitesIgnoresTheWorkbookNameInTheFile(InsightsIntegrationTestCase):
    """Workbook names are a bare counter, so every site has a workbook "1".

    A file carries the exporting site's name. Reading it as a local one made the
    import decide it had nothing to copy, and the query saved naming queries that
    do not exist here.
    """

    @classmethod
    def before_class(cls):
        create_test_users()

        cls.workbook = create_test_workbook(OWNER, "collision source").name
        cls.source = create_source_query(OWNER, cls.workbook, "collision source query").name

        with as_user(OWNER):
            consumer = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "collision consumer",
                    "workbook": cls.workbook,
                    "use_live_connection": 0,
                    "operations": [{"type": "source", "table": {"type": "query", "query_name": cls.source}}],
                }
            ).insert()
            cls.file = consumer.export()

        cls.target = create_test_workbook(IMPORTER, "collision target").name

    @classmethod
    def after_class(cls):
        for workbook in (cls.workbook, cls.target):
            frappe.delete_doc(DT.WORKBOOK, workbook, force=True, delete_permanently=True)
        delete_users(OWNER, IMPORTER)

    # @feature workbook.copy-paste
    def test_a_file_naming_the_target_workbook_still_copies_its_queries(self):
        """The other site's workbook happened to be numbered like this one's."""
        file = frappe.parse_json(frappe.as_json(self.file))
        file["doc"]["workbook"] = self.target

        with as_user(IMPORTER):
            imported = import_query(file, self.target)

        operations = frappe.parse_json(frappe.db.get_value(DT.QUERY, imported, "operations"))
        deps = set(extract_query_deps_from_operations(operations or []))

        self.assertTrue(deps, "the imported query should still hold a reference")
        self.assertNotIn(self.source, deps, "a reference must not point back at the source site")
        for dep in deps:
            self.assertEqual(frappe.db.get_value(DT.QUERY, dep, "workbook"), self.target)


class AWorkbookFileCarriesItsMembersAtTheTop(InsightsIntegrationTestCase):
    """One format for the download, Duplicate, the delete backup and a shipped file.

    The keys are the contract an app's shipped file is written against, and the
    folder a member sits in travels as a title, because the folder's own name is a
    hash the importing site mints for itself.
    """

    @classmethod
    def before_class(cls):
        create_test_users()

        cls.workbook = create_test_workbook(OWNER, "format source").name
        with as_user(OWNER):
            cls.folder = (
                frappe.get_doc(
                    {
                        "doctype": "Insights Folder",
                        "title": "Revenue",
                        "type": "chart",
                        "workbook": cls.workbook,
                    }
                )
                .insert()
                .name
            )
        cls.query = create_source_query(OWNER, cls.workbook, "format query").name
        with as_user(OWNER):
            cls.chart = (
                frappe.get_doc(
                    {
                        "doctype": DT.CHART,
                        "title": "format chart",
                        "workbook": cls.workbook,
                        "query": cls.query,
                        "chart_type": "Bar",
                        "folder": cls.folder,
                    }
                )
                .insert()
                .name
            )
            cls.dashboard = (
                frappe.get_doc(
                    {
                        "doctype": DT.DASHBOARD,
                        "title": "format dashboard",
                        "workbook": cls.workbook,
                        "items": [
                            {"id": "1", "type": "chart", "chart": cls.chart},
                            {
                                "id": "2",
                                "type": "filter",
                                "filter_name": "Description",
                                "links": {cls.chart: f"`{cls.query}`.`description`"},
                            },
                        ],
                    }
                )
                .insert()
                .name
            )
            cls.file = frappe.get_doc(DT.WORKBOOK, cls.workbook).export()

        cls.made_workbooks = [cls.workbook]

    @classmethod
    def after_class(cls):
        for workbook in frappe.get_all(
            DT.WORKBOOK, filters={"name": ("in", cls.made_workbooks)}, pluck="name"
        ):
            frappe.delete_doc(DT.WORKBOOK, workbook, force=True, delete_permanently=True)
        delete_users(OWNER, IMPORTER)

    # @feature standard.file-format
    def test_a_file_carries_the_workbook_and_its_members_under_one_key_each(self):
        self.assertEqual(
            set(self.file),
            {"doctype", "name", "title", "folders", "queries", "charts", "dashboards"},
        )
        self.assertEqual(self.file["name"], self.workbook)
        self.assertEqual(list(self.file["queries"]), [self.query])
        self.assertEqual(list(self.file["charts"]), [self.chart])
        self.assertEqual(list(self.file["dashboards"]), [self.dashboard])

    # @feature standard.file-format
    def test_a_file_names_the_folder_a_member_sits_in_by_title(self):
        self.assertEqual(self.file["folders"], [{"title": "Revenue", "type": "chart", "sort_order": 0}])
        self.assertEqual(self.file["charts"][self.chart]["folder"], "Revenue")

    # @feature standard.file-format
    def test_an_imported_member_lands_in_a_folder_of_the_same_title(self):
        with as_user(IMPORTER):
            imported = import_workbook(self.file)
        self.made_workbooks.append(imported["workbook"])

        chart = frappe.get_doc(DT.CHART, imported["names"][self.chart])
        self.assertEqual(frappe.db.get_value("Insights Folder", chart.folder, "title"), "Revenue")
        self.assertEqual(
            frappe.db.get_value("Insights Folder", chart.folder, "workbook"), imported["workbook"]
        )

    # @feature standard.file-format
    def test_two_folders_of_one_title_keep_their_own_members(self):
        """A folder travels as its title, and a title is unique only within a
        type — `InsightsFolder.validate_title` permits exactly this shape."""
        with as_user(OWNER):
            frappe.get_doc(
                {
                    "doctype": "Insights Folder",
                    "title": "Revenue",
                    "type": "query",
                    "workbook": self.workbook,
                }
            ).insert()
            query = frappe.get_doc(DT.QUERY, self.query)
            query.folder = frappe.db.get_value(
                "Insights Folder",
                {"workbook": self.workbook, "type": "query", "title": "Revenue"},
            )
            query.save()
            file = frappe.get_doc(DT.WORKBOOK, self.workbook).export()

        with as_user(IMPORTER):
            imported = import_workbook(file)
        self.made_workbooks.append(imported["workbook"])

        landed = {
            doctype: frappe.db.get_value(
                "Insights Folder",
                frappe.db.get_value(doctype, imported["names"][member], "folder"),
                ["title", "type"],
            )
            for doctype, member in ((DT.QUERY, self.query), (DT.CHART, self.chart))
        }
        self.assertEqual(landed[DT.QUERY], ("Revenue", "query"))
        self.assertEqual(landed[DT.CHART], ("Revenue", "chart"))

    # @feature workbook.copy-paste standard.file-format
    def test_a_pasted_file_is_a_workbook_in_either_shape(self):
        """`workbook_file.ts` `pastedWorkbook` asks this of every JSON object a
        user pastes on the workbook list, before it offers to import it. The
        released version's Copy JSON writes the wrapped shape, as the sample file
        this app ships does."""
        from insights.api.workbooks import is_workbook_file

        with open(frappe.get_app_path("insights", "setup", "sample_workbook.json")) as f:
            shipped = f.read()

        with as_user(OWNER):
            chart = frappe.get_doc(DT.CHART, self.chart).export()

        with as_user(IMPORTER):
            self.assertTrue(is_workbook_file(self.file))
            self.assertTrue(is_workbook_file(shipped))
            self.assertFalse(is_workbook_file(chart))
            self.assertFalse(is_workbook_file({"type": "Query", "name": self.query}))

    # @feature standard.file-format
    def test_a_file_in_the_wrapped_shape_still_imports(self):
        """Every file a site exported until now, and every file an app ships."""
        wrapped = {
            "version": "1.0",
            "type": "Workbook",
            "name": self.file["name"],
            "doc": {"name": self.file["name"], "title": "wrapped copy"},
            "dependencies": {
                "folders": [{"name": self.folder, "title": "Revenue", "type": "chart", "sort_order": 0}],
                "queries": self.file["queries"],
                "charts": {
                    name: {**chart, "folder": self.folder} for name, chart in self.file["charts"].items()
                },
                "dashboards": self.file["dashboards"],
            },
        }

        with as_user(IMPORTER):
            imported = import_workbook(wrapped)
        self.made_workbooks.append(imported["workbook"])

        self.assertEqual(frappe.db.get_value(DT.WORKBOOK, imported["workbook"], "title"), "wrapped copy")
        chart = frappe.get_doc(DT.CHART, imported["names"][self.chart])
        self.assertEqual(frappe.db.get_value("Insights Folder", chart.folder, "title"), "Revenue")
        self.assertEqual(chart.query, imported["names"][self.query])
