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

SOURCE_ROWS = "results = [{'amount': 1}]"


def create_source_query(owner, workbook, title):
    with as_user(owner):
        return frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": title,
                "workbook": workbook,
                "use_live_connection": 0,
                "is_script_query": 1,
                "operations": [{"type": "code", "code": SOURCE_ROWS}],
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

    def test_a_workbook_file_imports_for_someone_who_cannot_read_its_queries(self):
        with as_user(IMPORTER):
            self.assertFalse(
                frappe.has_permission(DT.QUERY, ptype="read", doc=self.source),
                "the fixture needs the importer to have no access to the exported queries",
            )
            imported = import_workbook(self.file)
        self.made_workbooks.append(imported)

        queries = frappe.get_all(DT.QUERY, filters={"workbook": imported}, pluck="name")
        self.assertEqual(len(queries), 2)

    def test_an_imported_reference_names_the_imported_copy(self):
        with as_user(IMPORTER):
            imported = import_workbook(self.file)
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

    def test_a_query_file_imports_for_someone_who_cannot_read_its_reference(self):
        with as_user(IMPORTER):
            self.assertFalse(
                frappe.has_permission(DT.QUERY, ptype="read", doc=self.source),
                "the fixture needs the importer to have no access to the referenced query",
            )
            imported = import_query(self.file, self.target)

        self.assertTrue(frappe.db.exists(DT.QUERY, imported))

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
