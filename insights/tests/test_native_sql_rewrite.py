import frappe
import sqlglot as sg

from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder
from insights.tests.base import InsightsIntegrationTestCase

SITE_DB = "Site DB"


class TestNativeSQLTableRewrite(InsightsIntegrationTestCase):
    """A native SQL query reads its tables through a permission-filtered select.

    The rewrite replaces each table reference in place. It used to prepend one CTE
    per table, which made the CTE name a collision surface.
    """

    def setUp(self):
        super().setUp()
        self.data_source = frappe.get_doc("Insights Data Source v3", SITE_DB)
        self.dialect = self.data_source.get_sqlglot_dialect()
        self.builder = IbisQueryBuilder(
            frappe._dict(
                name="Native SQL Rewrite Test",
                title="Native SQL Rewrite Test",
                use_live_connection=1,
                operations=frappe.as_json([]),
            )
        )

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

    def execute(self, sql):
        return self.data_source._get_ibis_backend().sql(sql).execute()

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
        self.execute(rewritten)

    def test_unaliased_reference_keeps_the_table_name(self):
        rewritten = self.rewrite("select `tabUser`.name from `tabUser` limit 1")

        self.execute(rewritten)

    def test_aliased_reference_keeps_its_alias(self):
        rewritten = self.rewrite("select u.name from `tabUser` u limit 1")

        self.execute(rewritten)

    def test_the_query_keeps_its_own_cte(self):
        raw_sql = "with recent as (select name from `tabUser`) select * from recent limit 1"

        rewritten = self.rewrite(raw_sql)

        self.assertEqual(self.cte_names(rewritten), ["recent"])
        self.execute(rewritten)

    def test_sql_is_untouched_when_no_table_is_bound(self):
        raw_sql = "select 1 as one"

        self.assertEqual(self.rewrite(raw_sql, {}), raw_sql)

    def test_an_empty_statement_does_not_break_the_rewrite(self):
        rewritten = self.rewrite("select `tabUser`.name from `tabUser` limit 1;;")

        self.execute(rewritten)

    def test_a_schema_qualified_table_is_refused(self):
        # the binding is looked up by the bare name, so reading `sales.orders`
        # would bind whichever `orders` the default schema holds
        with self.assertRaises(frappe.ValidationError):
            self.builder._get_sql_table_names("select * from sales.orders", dialect=self.dialect)
