from unittest.mock import patch

import frappe
import ibis
import sqlglot as sg

from insights.exceptions import QueryRefused
from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder
from insights.insights.doctype.insights_table_v3.insights_table_v3 import InsightsTablev3, get_table_name
from insights.insights.query_utils import (
    alias_qualified_tables,
    extract_sql_table_refs,
    extract_table_deps_from_sql_operations,
)
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
            tables = self.builder._get_sql_table_names(raw_sql, self.data_source, dialect=self.dialect)
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

    def test_a_table_in_a_schema_the_data_source_does_not_read_is_refused(self):
        # binding the bare name would read whichever `orders` the data source's schema holds
        postgres = self.postgres_data_source("sales, finance")
        for raw_sql, data_source in (
            ("select * from sales.orders", self.data_source),
            ("select * from hr.employees", postgres),
            ("select * from shop.sales.orders", postgres),
        ):
            with self.subTest(raw_sql=raw_sql, data_source=data_source.database_type):
                with self.assertRaises(QueryRefused):
                    self.builder._get_sql_table_names(
                        raw_sql, data_source, dialect=data_source.get_sqlglot_dialect()
                    )

    def test_a_schema_qualified_table_reads_the_table_the_data_source_lists(self):
        raw_sql = "select o.amount, i.paid from sales.orders o join finance.invoices i on i.order_id = o.id"

        self.assertEqual(
            self.builder._get_sql_table_names(
                raw_sql, self.postgres_data_source("sales, finance"), "postgres"
            ),
            {"sales.orders": "sales.orders", "finance.invoices": "finance.invoices"},
        )
        # one schema leaves names unqualified, as `get_table_list` lists them
        self.assertEqual(
            self.builder._get_sql_table_names(
                "select * from sales.orders", self.postgres_data_source("sales"), "postgres"
            ),
            {"sales.orders": "orders"},
        )

    def test_a_schema_qualified_table_is_replaced_by_its_binding(self):
        raw_sql = "select orders.amount from sales.orders join orders as o on o.id = orders.id"

        rewritten = self.builder._replace_sql_tables(
            raw_sql,
            {"sales.orders": 'SELECT * FROM "sales"."orders" WHERE region = \'north\''},
            dialect="postgres",
        )

        # the unqualified `orders` names another table, so it keeps its own reference
        self.assertEqual(
            rewritten,
            'SELECT orders.amount FROM (SELECT * FROM "sales"."orders" WHERE region = \'north\') AS orders '
            "JOIN orders AS o ON o.id = orders.id",
        )

    def test_a_qualified_table_is_aliased_by_its_full_name_where_its_name_is_shared(self):
        """A binding has no schema, so the alias keeps `sales.orders` and
        `finance.orders` apart, in one block or across a correlated subquery."""
        for raw_sql, aliased in (
            (
                "select sales.orders.amount, finance.orders.total from sales.orders "
                "join finance.orders on finance.orders.id = sales.orders.id",
                'SELECT "sales.orders".amount, "finance.orders".total FROM sales.orders AS "sales.orders" '
                'JOIN finance.orders AS "finance.orders" ON "finance.orders".id = "sales.orders".id',
            ),
            (
                "select id from sales.orders "
                "where exists (select 1 from finance.refunds as orders where orders.order_id = sales.orders.id)",
                'SELECT id FROM sales.orders AS "sales.orders" '
                'WHERE EXISTS(SELECT 1 FROM finance.refunds AS orders WHERE orders.order_id = "sales.orders".id)',
            ),
        ):
            with self.subTest(raw_sql=raw_sql):
                self.assertEqual(alias_qualified_tables(raw_sql, "postgres"), aliased)

        # a query with no qualified table reaches the database as written
        self.assertEqual(
            alias_qualified_tables("select `tabUser`.name from `tabUser`", "mysql"),
            "select `tabUser`.name from `tabUser`",
        )

    def test_a_qualified_table_keeps_the_name_the_database_knows_it_by(self):
        # so a whole-row `orders` still names the table
        for raw_sql, aliased in (
            (
                "select row_to_json(orders) from sales.orders",
                "SELECT ROW_TO_JSON(orders) FROM sales.orders AS orders",
            ),
            (
                "select sales.orders.amount from sales.orders",
                "SELECT orders.amount FROM sales.orders AS orders",
            ),
            (
                "with o as (select * from sales.orders) select o.id from o",
                "WITH o AS (SELECT * FROM sales.orders AS orders) SELECT o.id FROM o",
            ),
            (
                "with c as (select 1 as id) select c2.id, sales.orders.amount from sales.orders join c as c2 on true",
                "WITH c AS (SELECT 1 AS id) SELECT c2.id, orders.amount FROM sales.orders AS orders "
                "JOIN c AS c2 ON TRUE",
            ),
            (
                # the CTE is not in the subquery's FROM, so `orders` is the outer table
                "with orders as (select 1 as id) select (select orders.id from finance.x) from sales.orders",
                "WITH orders AS (SELECT 1 AS id) SELECT (SELECT orders.id FROM finance.x AS x) "
                "FROM sales.orders AS orders",
            ),
            (
                # one UNION branch does not see the other's `orders`
                "select row_to_json(orders) from sales.orders "
                "union all select row_to_json(orders) from finance.orders",
                "SELECT ROW_TO_JSON(orders) FROM sales.orders AS orders "
                "UNION ALL SELECT ROW_TO_JSON(orders) FROM finance.orders AS orders",
            ),
            (
                # an aliased group hides the `orders` it joins
                "select row_to_json(orders) from sales.orders "
                "cross join (finance.orders cross join finance.invoices) as g",
                "SELECT ROW_TO_JSON(orders) FROM sales.orders AS orders CROSS JOIN "
                '(finance.orders AS "finance.orders" CROSS JOIN finance.invoices AS invoices) AS g',
            ),
        ):
            with self.subTest(raw_sql=raw_sql):
                self.assertEqual(alias_qualified_tables(raw_sql, "postgres"), aliased)

    def test_a_grouped_join_is_read_by_the_tables_it_joins(self):
        self.assertEqual(
            alias_qualified_tables(
                "select sales.orders.id from (sales.orders join finance.invoices "
                "on sales.orders.id = finance.invoices.order_id)",
                "postgres",
            ),
            "SELECT orders.id FROM (sales.orders AS orders JOIN finance.invoices AS invoices "
            "ON orders.id = invoices.order_id)",
        )

    def test_a_grouped_join_keeps_the_tables_it_joins(self):
        # sqlglot hangs the joins of `(a JOIN b)` on `a`, so replacing `a` alone drops `b`
        rewritten = self.builder._replace_sql_tables(
            "select orders.id from (orders join invoices on orders.id = invoices.order_id)",
            {"orders": "SELECT * FROM orders", "invoices": "SELECT * FROM invoices"},
            dialect="postgres",
        )

        self.assertEqual(
            rewritten,
            "SELECT orders.id FROM ((SELECT * FROM orders) AS orders JOIN (SELECT * FROM invoices) AS invoices "
            "ON orders.id = invoices.order_id)",
        )

    def test_an_aliased_grouped_join_hides_the_tables_it_joins(self):
        # outside the group, `orders` is its alias, not either of the tables it joins
        self.assertEqual(
            alias_qualified_tables(
                "select orders.id from (sales.orders join finance.orders using (id)) as orders", "postgres"
            ),
            'SELECT orders.id FROM (sales.orders AS "sales.orders" JOIN finance.orders AS "finance.orders" USING (id)) AS orders',
        )

    def test_a_column_that_could_name_two_tables_is_refused(self):
        # as the database refuses it
        with self.assertRaises(QueryRefused):
            alias_qualified_tables(
                "select orders.id from sales.orders join finance.orders on true", "postgres"
            )

    def test_an_alias_spelled_as_a_full_table_name_is_refused(self):
        # the rewrite would alias `sales.orders` as `"sales.orders"` too
        with self.assertRaises(QueryRefused):
            alias_qualified_tables(
                'select 1 from sales.orders join finance.orders on true join sales.refunds as "sales.orders" on true',
                "postgres",
            )

    def test_a_cte_named_like_a_qualified_table_keeps_its_rows(self):
        # `"sales.orders"` is one name, so its reference is the CTE, not the table
        raw_sql = 'with "sales.orders" as (select 1 as id) select c.id from "sales.orders" as c cross join sales.orders as o'

        rewritten = self.builder._replace_sql_tables(
            raw_sql, {"sales.orders": "SELECT * FROM sales.orders WHERE 1 = 1"}, dialect="postgres"
        )

        self.assertEqual(
            rewritten,
            'WITH "sales.orders" AS (SELECT 1 AS id) SELECT c.id FROM "sales.orders" AS c '
            "CROSS JOIN (SELECT * FROM sales.orders WHERE 1 = 1) AS o",
        )

    def test_a_table_named_with_a_dot_is_refused(self):
        # its name is spelled as `sales.orders` is, so it cannot get a binding of its own
        with self.assertRaises(QueryRefused):
            self.builder._get_sql_table_names(
                'select s.id from "sales.orders" s cross join sales.orders o',
                self.postgres_data_source("sales, finance"),
                dialect="postgres",
            )

    def test_a_cte_does_not_hide_a_qualified_table(self):
        # a CTE name has no schema; unbound, `sales.orders` would skip the permission filter
        raw_sql = "with orders as (select 1 as id) select * from sales.orders join orders on true"

        self.assertEqual(
            [ref.reference for ref in extract_sql_table_refs(raw_sql, "postgres")], ["sales.orders"]
        )

    def test_an_unqualified_name_reads_the_first_schema_that_lists_it(self):
        # as PostgreSQL's search path does, so the permission check names the table read
        postgres = self.postgres_data_source("sales, finance")
        self.list_tables(postgres, "sales.orders", "finance.orders", "finance.invoices")

        self.assertEqual(
            self.builder._get_sql_table_names(
                "select * from orders, invoices, refunds", postgres, "postgres"
            ),
            {"orders": "sales.orders", "invoices": "finance.invoices", "refunds": "sales.refunds"},
        )

    def test_a_name_resolved_to_another_table_is_always_bound(self):
        # unbound, `orders` would read whichever table the search path finds first,
        # not `finance.orders`, whose grant was checked
        def unfiltered(data_source, table_name, use_live_connection):
            return ibis.table({"id": "int"}, name=table_name)

        # and PostgreSQL reads an unquoted `sales.Orders` as `sales.orders`
        with patch.object(InsightsTablev3, "get_ibis_table", side_effect=unfiltered):
            replace_map = self.builder._get_sql_table_bindings(
                SITE_DB,
                {"orders": "finance.orders", "sales.orders": "sales.orders", "sales.Orders": "sales.Orders"},
                dialect="postgres",
                use_live_connection=True,
                check_permissions=True,
            )
            mariadb_map = self.builder._get_sql_table_bindings(
                SITE_DB,
                {"tabUser": "tabUser"},
                dialect="mysql",
                use_live_connection=True,
                check_permissions=True,
            )

        self.assertEqual(list(replace_map), ["orders", "sales.Orders"])
        self.assertEqual(mariadb_map, {})

    def test_a_deleted_data_source_still_names_its_tables(self):
        # an unnamed table would let a chart reading it pass the permission check
        operations = [
            {"type": "sql", "data_source": "Deleted Source", "raw_sql": "select * from sales.orders"}
        ]

        self.assertEqual(
            extract_table_deps_from_sql_operations(operations),
            [{"data_source": "Deleted Source", "table_name": "orders"}],
        )

    def list_tables(self, data_source, *tables):
        self.addCleanup(frappe.db.delete, "Insights Table v3", {"data_source": data_source.name})
        for table in tables:
            frappe.get_doc(
                {
                    "doctype": "Insights Table v3",
                    "name": get_table_name(data_source.name, table),
                    "data_source": data_source.name,
                    "table": table,
                }
            ).db_insert()

    def postgres_data_source(self, schema):
        data_source = frappe.get_doc(
            {
                "doctype": "Insights Data Source v3",
                "title": "Native SQL Postgres",
                "database_type": "PostgreSQL",
                "database_name": "shop",
                "schema": schema,
            }
        )
        data_source.name = "native_sql_postgres"
        return data_source
