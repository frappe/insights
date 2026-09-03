import frappe
import sqlglot as sg

from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder
from insights.tests.base import InsightsIntegrationTestCase

SITE_DB = "Site DB"


class TestNativeSQL(InsightsIntegrationTestCase):
    """A native SQL query reads its tables through a permission-filtered select.

    Two things used to put a `WITH` clause in front of the query the database runs:
    the permission rewrite named a CTE after each table, and ibis re-attached the
    query's own CTEs without clearing them first. Both ended in MariaDB's
    "Duplicate query name".
    """

    def setUp(self):
        super().setUp()
        self.data_source = frappe.get_doc("Insights Data Source v3", SITE_DB)
        self.dialect = self.data_source.get_sqlglot_dialect()
        self.builder = IbisQueryBuilder(self.make_query_doc([]))

    def make_query_doc(self, operations):
        return frappe._dict(
            name="Native SQL Test",
            title="Native SQL Test",
            use_live_connection=1,
            operations=frappe.as_json(operations),
        )

    def run_native_sql(self, raw_sql):
        """Execute `raw_sql` the way a native query operation does."""
        operations = [{"type": "sql", "data_source": SITE_DB, "raw_sql": raw_sql}]
        return IbisQueryBuilder(self.make_query_doc(operations)).build().execute()

    def rewrite(self, raw_sql, replace_map=None):
        if replace_map is None:
            tables = self.builder._get_sql_table_names(raw_sql, dialect=self.dialect)
            replace_map = self.builder._get_sql_table_bindings(
                SITE_DB,
                tables,
                dialect=self.dialect,
                use_live_connection=True,
                check_permissions=False,
            )
        return self.builder._replace_sql_tables(raw_sql, replace_map, dialect=self.dialect)

    def cte_names(self, sql):
        parsed = sg.parse_one(sql, dialect=self.dialect)
        return [cte.alias_or_name for cte in parsed.find_all(sg.exp.CTE)]

    def table_names(self, sql):
        parsed = sg.parse_one(sql, dialect=self.dialect)
        return sorted(table.name for table in parsed.find_all(sg.exp.Table))

    # --- the query the database runs ---

    def test_a_query_that_opens_with_a_cte_runs(self):
        # ibis 11 re-attaches a query's CTEs without clearing them first, because
        # sqlglot 28 renamed the key it clears. MariaDB rejects the doubled pair.
        rows = self.run_native_sql("with recent as (select name from `tabUser` limit 1) select * from recent")

        self.assertEqual(len(rows), 1)

    def test_a_query_with_several_ctes_runs(self):
        rows = self.run_native_sql(
            """
            with one as (select name from `tabUser` limit 1),
                 two as (select name from one)
            select * from two
            """
        )

        self.assertEqual(len(rows), 1)

    def test_a_query_without_a_cte_runs(self):
        rows = self.run_native_sql("select name from `tabUser` limit 1")

        self.assertEqual(len(rows), 1)

    def test_a_trailing_semicolon_survives_the_nesting(self):
        # the nesting brackets the query, and a semicolon inside them is a syntax error
        rows = self.run_native_sql(
            "with recent as (select name from `tabUser` limit 1) select * from recent;"
        )

        self.assertEqual(len(rows), 1)

    def test_a_rewritten_query_that_opens_with_a_cte_runs(self):
        # the two rewrites meet here: the tables are replaced, then the result is nested
        raw_sql = "with recent as (select name from `tabUser` limit 1) select * from recent"
        rewritten = self.rewrite(raw_sql, {"tabUser": "SELECT * FROM `tabUser`"})

        rows = (
            self.data_source._get_ibis_backend()
            .sql(self.builder._hide_ctes_from_ibis(rewritten, dialect=self.dialect))
            .execute()
        )

        self.assertEqual(len(rows), 1)

    def test_more_than_one_statement_is_refused(self):
        # ibis runs one statement, and both rewrites read the first one only
        with self.assertRaises(frappe.ValidationError):
            self.run_native_sql("select 1 as one; select 2 as two")

    # --- the permission rewrite ---

    def test_two_spellings_of_one_table_produce_no_cte(self):
        # MariaDB matches CTE names case-insensitively, so a CTE per spelling was
        # rejected with "Duplicate query name". A reference carries no name.
        raw_sql = "select a.name from `tabUser` a join tabuser b on a.name = b.name"
        replace_map = {
            "tabUser": "SELECT * FROM `tabUser`",
            "tabuser": "SELECT * FROM `tabuser`",
        }

        rewritten = self.rewrite(raw_sql, replace_map)

        # each reference reads its own binding, and neither carries a name
        self.assertEqual(self.cte_names(rewritten), [])
        self.assertEqual(self.table_names(rewritten), ["tabUser", "tabuser"])

    def test_table_name_needing_quotes_runs_on_the_source(self):
        # the alias used to be rendered with sqlglot's default dialect, which gave
        # MariaDB a string literal instead of an identifier
        rewritten = self.rewrite("select name from `tabInsights Table v3` limit 1")

        self.assertIn("`tabInsights Table v3`", rewritten)

    def test_unaliased_reference_keeps_the_table_name(self):
        rewritten = self.rewrite("select `tabUser`.name from `tabUser` limit 1")

        self.assertIn("AS `tabUser`", rewritten)

    def test_aliased_reference_keeps_its_alias(self):
        rewritten = self.rewrite("select u.name from `tabUser` u limit 1")

        self.assertIn("AS u", rewritten)

    def test_the_query_keeps_its_own_cte(self):
        raw_sql = "with recent as (select name from `tabUser`) select * from recent limit 1"

        rewritten = self.rewrite(raw_sql)

        self.assertEqual(self.cte_names(rewritten), ["recent"])

    def test_sql_is_untouched_when_no_table_is_bound(self):
        raw_sql = "select 1 as one"

        self.assertEqual(self.rewrite(raw_sql, {}), raw_sql)

    def test_a_schema_qualified_table_is_refused(self):
        # the binding is looked up by the bare name, so reading `sales.orders`
        # would bind whichever `orders` the default schema holds
        with self.assertRaises(frappe.ValidationError):
            self.builder._get_sql_table_names("select * from sales.orders", dialect=self.dialect)
