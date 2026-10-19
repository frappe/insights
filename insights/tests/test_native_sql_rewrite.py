import frappe
import ibis
import sqlglot as sg

from insights.exceptions import QueryRefused
from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.insights.doctype.insights_table_v3.insights_table_v3 import InsightsTablev3, get_table_name
from insights.insights.query_utils import (
    alias_qualified_tables,
    extract_sql_table_refs,
    extract_table_deps_from_sql_operations,
    fold_identifiers,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import as_user, create_user, delete_users

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

    def make_query_doc(self, operations, use_live_connection=1):
        return frappe._dict(
            name="Native SQL Test",
            title="Native SQL Test",
            use_live_connection=use_live_connection,
            operations=frappe.as_json(operations),
        )

    def run_native_sql(self, raw_sql, use_live_connection=1):
        """Execute `raw_sql` the way a native query operation does."""
        operations = [{"type": "sql", "data_source": SITE_DB, "raw_sql": raw_sql}]
        return IbisQueryBuilder(self.make_query_doc(operations, use_live_connection)).build().execute()

    def rewrite(self, raw_sql, replace_map=None):
        """Runs only the rewrite, with an unfiltered binding for each table.

        It skips `_get_sql_table_bindings`, so the result does not depend on the
        permissions of the user who runs the test.
        """
        if replace_map is None:
            tables = self.builder._get_sql_table_names(raw_sql, self.data_source, dialect=self.dialect)
            replace_map = {
                reference: ibis.to_sql(
                    InsightsTablev3.get_ibis_table(SITE_DB, table, use_live_connection=True)
                )
                for reference, table in tables.items()
            }
        return self.builder._replace_sql_tables(raw_sql, replace_map, dialect=self.dialect)

    def cte_names(self, sql):
        parsed = sg.parse_one(sql, dialect=self.dialect)
        return [cte.alias_or_name for cte in parsed.find_all(sg.exp.CTE)]

    def table_names(self, sql):
        parsed = sg.parse_one(sql, dialect=self.dialect)
        return sorted(table.name for table in parsed.find_all(sg.exp.Table))

    # --- the query the database runs ---

    # @feature query.native-sql
    def test_a_query_that_opens_with_a_cte_runs(self):
        # ibis 11 re-attaches a query's CTEs without clearing them first, because
        # sqlglot 28 renamed the key it clears. MariaDB rejects the doubled pair.
        rows = self.run_native_sql("with recent as (select name from `tabUser` limit 1) select * from recent")

        self.assertEqual(len(rows), 1)

    # @feature query.native-sql
    def test_a_query_with_several_ctes_runs(self):
        rows = self.run_native_sql(
            """
            with one as (select name from `tabUser` limit 1),
                 two as (select name from one)
            select * from two
            """
        )

        self.assertEqual(len(rows), 1)

    # @feature query.native-sql
    def test_a_query_without_a_cte_runs(self):
        rows = self.run_native_sql("select name from `tabUser` limit 1")

        self.assertEqual(len(rows), 1)

    # @feature query.native-sql
    def test_a_trailing_semicolon_survives_the_nesting(self):
        # the nesting brackets the query, and a semicolon inside them is a syntax error
        rows = self.run_native_sql(
            "with recent as (select name from `tabUser` limit 1) select * from recent;"
        )

        self.assertEqual(len(rows), 1)

    # @feature query.native-sql
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

    # @feature query.native-sql-one-statement
    def test_more_than_one_statement_is_refused(self):
        # ibis runs one statement, and both rewrites read the first one only
        with self.assertRaises(frappe.ValidationError):
            self.run_native_sql("select 1 as one; select 2 as two")

    # --- the permission rewrite ---

    # @feature query.native-sql
    def test_two_spellings_of_one_table_produce_no_cte(self):
        # MariaDB matches CTE names case-insensitively, so a CTE per spelling was
        # rejected with "Duplicate query name". A reference has no name.
        raw_sql = "select a.name from `tabUser` a join tabuser b on a.name = b.name"
        replace_map = {
            "tabUser": "SELECT * FROM `tabUser`",
            "tabuser": "SELECT * FROM `tabuser`",
        }

        rewritten = self.rewrite(raw_sql, replace_map)

        # each reference reads its own binding, and neither has a name
        self.assertEqual(self.cte_names(rewritten), [])
        self.assertEqual(self.table_names(rewritten), ["tabUser", "tabuser"])

    # @feature query.native-sql
    def test_a_cte_hides_a_table_only_inside_its_own_block(self):
        """A CTE applies only inside the query block that declares it. Outside
        that block the name is the real table, and it must get a binding: only
        the binding applies the reader's permissions."""
        raw_sql = (
            "select u.name from (with `tabUser` as (select 1 as n) select n from `tabUser`) s "
            "join `tabUser` u on 1 = 1"
        )

        self.assertEqual(
            self.builder._get_sql_table_names(raw_sql, self.data_source, dialect=self.dialect),
            {"tabUser": "tabUser"},
        )

        # inside its own block, the CTE does hide the table
        hidden = "with `tabUser` as (select 1 as n) select n from `tabUser`"
        self.assertEqual(
            self.builder._get_sql_table_names(hidden, self.data_source, dialect=self.dialect), {}
        )

    # @feature query.native-sql
    def test_every_table_of_an_aliased_grouped_join_gets_a_binding(self):
        """A scope does not list the first table of `(a JOIN b) AS g`. Unbound, it
        would be read without the reader's permissions."""
        raw_sql = "select g.name from (`tabUser` join `tabToDo` on true) as g"

        self.assertEqual(
            self.builder._get_sql_table_names(raw_sql, self.data_source, dialect=self.dialect),
            {"tabUser": "tabUser", "tabToDo": "tabToDo"},
        )

    # @feature query.native-sql
    def test_a_cte_in_an_aliased_grouped_join_is_not_a_table(self):
        raw_sql = "with c as (select 1 as id) select g.id from (c cross join `tabToDo`) as g"

        self.assertEqual(
            self.builder._get_sql_table_names(raw_sql, self.data_source, dialect=self.dialect),
            {"tabToDo": "tabToDo"},
        )

    # @feature query.native-sql
    def test_a_commented_query_names_the_tables_it_runs_on(self):
        """The run strips comments before it binds tables, so the tables read
        for permission checks must come from the same text. PostgreSQL and
        DuckDB do not read `#` as a comment."""
        raw_sql = "# users by role\n-- active only\nSELECT name FROM tabUser"

        for dialect in ("postgres", "duckdb", "mysql"):
            with self.subTest(dialect=dialect):
                refs = extract_sql_table_refs(raw_sql, dialect=dialect)
                self.assertEqual([ref.name for ref in refs], ["tabUser"])

    # @feature query.native-sql
    def test_a_derived_table_aliased_after_a_table_does_not_hide_it(self):
        """An alias does not declare a table. A subquery aliased with a real
        table's name does not hide that table, and only the table's binding
        applies the reader's permissions."""
        raw_sql = "select u.name from (select 1 as n) as `tabUser` join `tabUser` as u on 1 = 1"

        self.assertEqual(
            self.builder._get_sql_table_names(raw_sql, self.data_source, dialect=self.dialect),
            {"tabUser": "tabUser"},
        )

        rewritten = self.rewrite(raw_sql, {"tabUser": "SELECT * FROM `tabUser`"})

        # the real table gets its binding; the aliased subquery is unchanged
        self.assertIn("AS u", rewritten)
        self.assertIn("(SELECT 1 AS n) AS `tabUser`", rewritten)

    # @feature query.native-sql
    def test_a_cte_reference_is_left_alone_where_the_same_name_is_bound(self):
        """Table extraction and the rewrite use the same scope rule. Binding the
        CTE reference would point it at rows without the CTE's columns."""
        raw_sql = (
            "select u.name from (with `tabUser` as (select 1 as n) select n from `tabUser`) s "
            "join `tabUser` u on 1 = 1"
        )

        rewritten = self.rewrite(raw_sql, {"tabUser": "SELECT * FROM `tabUser`"})

        self.assertEqual(self.cte_names(rewritten), ["tabUser"])
        self.assertIn("SELECT n FROM `tabUser`", rewritten)
        self.assertIn("AS u", rewritten)

    # @feature query.native-sql permissions.not-permitted-chart
    def test_a_reader_with_every_row_still_loses_a_column_they_may_not_read(self):
        """A reader who may read every row gets no `WHERE`. A held-back column
        must still be removed."""
        reader = "native_sql_permlevel@test.com"
        create_user(reader, first_name="Native", last_name="Reader", roles="System Manager")
        self.addCleanup(delete_users, reader)
        # `ToDo` gives System Manager read on every row, so the permission query
        # adds no WHERE
        setter = frappe.get_doc(
            {
                "doctype": "Property Setter",
                "doctype_or_field": "DocField",
                "doc_type": "ToDo",
                "field_name": "status",
                "property": "permlevel",
                "value": 1,
                "property_type": "Int",
            }
        ).insert(ignore_permissions=True)
        frappe.clear_cache(doctype="ToDo")
        self.addCleanup(frappe.clear_cache, doctype="ToDo")
        self.addCleanup(frappe.delete_doc, "Property Setter", setter.name, force=True)

        with as_user(reader), db_connections():
            rows = self.run_native_sql("select * from `tabToDo` limit 1")

        self.assertIn("description", rows.columns)
        self.assertNotIn("status", rows.columns)

    # @feature query.native-sql permissions.site-user-permissions
    def test_a_reader_narrowed_by_rows_runs_native_sql_on_the_data_store(self):
        """On the data store, the rows desk permits are read from the live site
        into an in-memory table. The SQL sent to DuckDB reads that table."""
        reader = "native_sql_rows@test.com"
        create_user(reader, first_name="Native", last_name="Rows", roles="Insights User")
        self.addCleanup(delete_users, reader)

        with as_user(reader), db_connections():
            rows = self.run_native_sql(
                "select status, count(*) as todos from tabToDo group by status", use_live_connection=0
            )

        self.assertEqual(list(rows.columns), ["status", "todos"])

    # @feature query.native-sql
    def test_table_name_needing_quotes_runs_on_the_source(self):
        # the alias used to be rendered with sqlglot's default dialect, which gave
        # MariaDB a string literal instead of an identifier
        rewritten = self.rewrite("select name from `tabInsights Table v3` limit 1")

        self.assertIn("`tabInsights Table v3`", rewritten)

    # @feature query.native-sql
    def test_unaliased_reference_keeps_the_table_name(self):
        rewritten = self.rewrite("select `tabUser`.name from `tabUser` limit 1")

        self.assertIn("AS `tabUser`", rewritten)

    # @feature query.native-sql
    def test_aliased_reference_keeps_its_alias(self):
        rewritten = self.rewrite("select u.name from `tabUser` u limit 1")

        self.assertIn("AS u", rewritten)

    # @feature query.native-sql
    def test_the_query_keeps_its_own_cte(self):
        raw_sql = "with recent as (select name from `tabUser`) select * from recent limit 1"

        rewritten = self.rewrite(raw_sql)

        self.assertEqual(self.cte_names(rewritten), ["recent"])

    # @feature query.native-sql
    def test_sql_is_untouched_when_no_table_is_bound(self):
        raw_sql = "select 1 as one"

        self.assertEqual(self.rewrite(raw_sql, {}), raw_sql)

    # @feature query.native-sql-one-statement
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
                    self.builder._validate_native_sql(
                        raw_sql,
                        use_live_connection=True,
                        data_source=data_source,
                        dialect=data_source.get_sqlglot_dialect(),
                    )

    # @feature query.native-sql-schema-qualified
    def test_a_schema_qualified_table_reads_the_table_the_data_source_lists(self):
        raw_sql = "select o.amount, i.paid from sales.orders o join finance.invoices i on i.order_id = o.id"

        for schema, tables in (
            ("sales, finance", {"sales.orders": "sales.orders", "finance.invoices": "finance.invoices"}),
            # one schema leaves names unqualified, as `get_table_list` lists them
            ("sales", None),
        ):
            with self.subTest(schema=schema):
                postgres = self.postgres_data_source(schema)
                if tables is None:
                    with self.assertRaises(QueryRefused):
                        self.builder._validate_native_sql(
                            raw_sql, use_live_connection=True, data_source=postgres, dialect="postgres"
                        )
                    self.assertEqual(
                        self.builder._get_sql_table_names("select * from sales.orders", postgres, "postgres"),
                        {"sales.orders": "orders"},
                    )
                    continue

                self.builder._validate_native_sql(
                    raw_sql, use_live_connection=True, data_source=postgres, dialect="postgres"
                )
                self.assertEqual(self.builder._get_sql_table_names(raw_sql, postgres, "postgres"), tables)

    # @feature query.native-sql-schema-qualified
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

    # @feature query.native-sql-schema-qualified
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

    # @feature query.native-sql-schema-qualified
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

    # @feature query.native-sql
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

    # @feature query.native-sql-schema-qualified
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

    # @feature query.native-sql-schema-qualified
    def test_an_aliased_grouped_join_hides_the_tables_it_joins(self):
        # outside the group, `orders` is its alias, not either of the tables it joins
        self.assertEqual(
            alias_qualified_tables(
                "select orders.id from (sales.orders join finance.orders using (id)) as orders", "postgres"
            ),
            'SELECT orders.id FROM (sales.orders AS "sales.orders" JOIN finance.orders AS "finance.orders" USING (id)) AS orders',
        )

    # @feature query.native-sql-schema-qualified
    def test_a_column_that_could_name_two_tables_is_refused(self):
        # as the database refuses it
        with self.assertRaises(QueryRefused):
            alias_qualified_tables(
                "select orders.id from sales.orders join finance.orders on true", "postgres"
            )

    # @feature query.native-sql-one-statement
    def test_a_table_function_is_refused(self):
        # it names no table, so no binding replaces it: on the data store DuckDB
        # reads the stored copy whole
        for raw_sql in ("select * from query('select 1 as one')", "select * from query_table('tabUser')"):
            with self.subTest(raw_sql=raw_sql), self.assertRaises(QueryRefused):
                self.builder._validate_native_sql(
                    raw_sql, use_live_connection=False, data_source=self.data_source, dialect=self.dialect
                )

    # @feature query.native-sql-schema-qualified
    def test_an_alias_spelled_as_a_full_table_name_is_refused(self):
        # the rewrite would alias `sales.orders` as `"sales.orders"` too
        with self.assertRaises(QueryRefused):
            alias_qualified_tables(
                'select 1 from sales.orders join finance.orders on true join sales.refunds as "sales.orders" on true',
                "postgres",
            )

    # @feature query.native-sql-schema-qualified
    def test_a_table_named_with_a_dot_is_refused(self):
        # its name is spelled as `sales.orders` is, so it cannot get a binding of its own
        with self.assertRaises(QueryRefused):
            self.builder._validate_native_sql(
                'select s.id from "sales.orders" s cross join sales.orders o',
                use_live_connection=True,
                data_source=self.postgres_data_source("sales, finance"),
                dialect="postgres",
            )

    # @feature query.native-sql-schema-qualified
    def test_a_cte_does_not_hide_a_qualified_table(self):
        # a CTE name has no schema; unbound, `sales.orders` would skip the permission filter
        raw_sql = "with orders as (select 1 as id) select * from sales.orders join orders on true"

        self.assertEqual(
            [ref.reference for ref in extract_sql_table_refs(raw_sql, "postgres")], ["sales.orders"]
        )

    # @feature query.native-sql-schema-qualified
    def test_an_unquoted_name_is_read_lowercased(self):
        # as PostgreSQL reads it; a quoted name keeps its case
        self.assertEqual(
            fold_identifiers('select * from Sales.Orders join "Finance".invoices on true', "postgres"),
            'SELECT * FROM sales.orders JOIN "Finance".invoices ON TRUE',
        )
        # the Data Store returns an output column as written
        self.assertEqual(
            fold_identifiers("select Amount as Total from Sales.Orders", "postgres"),
            "SELECT Amount AS Total FROM sales.orders",
        )
        # DuckDB lowercases a quoted name too, so only PostgreSQL folds
        for dialect in ("duckdb", "mysql"):
            self.assertEqual(fold_identifiers("select * from Orders", dialect), "select * from Orders")

    # @feature query.native-sql-schema-qualified
    def test_a_deleted_data_source_still_names_its_tables(self):
        # an unnamed table would let a chart reading it pass the permission check
        operations = [
            {"type": "sql", "data_source": "Deleted Source", "raw_sql": "select * from sales.orders"}
        ]

        self.assertEqual(
            extract_table_deps_from_sql_operations(operations),
            [{"data_source": "Deleted Source", "table_name": "orders"}],
        )

    # @feature query.native-sql-schema-qualified
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

    # @feature query.native-sql-one-statement
    def test_a_table_function_that_makes_rows_from_its_arguments_is_accepted(self):
        # v3 ran these: a date spine, rows from a JSON column, a list of values
        for dialect, raw_sql in (
            (
                "postgres",
                """select d::date as day, count(so.name) from generate_series('2026-01-01'::date,
                '2026-03-31'::date, interval '1 day') as d left join "tabSales Order" so
                on so.transaction_date = d::date group by 1""",
            ),
            ("postgres", "select x from unnest(array['Open', 'Closed']) as u(x)"),
            ("postgres", """select e->>'item' from "tabToDo", jsonb_array_elements('[]'::jsonb) as e"""),
            (
                "mysql",
                """select jt.item from tabToDo, json_table('[{"item": "a"}]', '$[*]'
                columns (item varchar(140) path '$.item')) as jt""",
            ),
            ("mysql", "select * from (values (1, 'Open'), (2, 'Closed')) as v(id, status)"),
            ("duckdb", "select range as n from range(10)"),
            ("sqlite", "select value from json_each('[1, 2]')"),
        ):
            with self.subTest(raw_sql=raw_sql):
                self.builder._validate_native_sql(
                    raw_sql, use_live_connection=True, data_source=self.data_source, dialect=dialect
                )

    # @feature query.native-sql
    def test_json_table_runs_on_the_site_database(self):
        rows = self.run_native_sql(
            """select jt.status from json_table('[{"status": "Open"}, {"status": "Closed"}]', '$[*]'
            columns (status varchar(140) path '$.status')) as jt"""
        )
        self.assertEqual(list(rows["status"]), ["Open", "Closed"])

    # @feature query.native-sql-one-statement
    def test_a_function_that_runs_a_query_is_refused(self):
        # the query it runs is a string, so no binding replaces the table it reads
        for dialect, raw_sql in (
            ("postgres", """select query_to_xml('select * from "tabUser"', true, true, '')"""),
            ("postgres", """select ts_stat('select to_tsvector(email) from "tabUser"')"""),
            ("postgres", """select ts_rewrite(to_tsquery('a'), 'select * from "tabUser"')"""),
            ("postgres", """select * from crosstab('select * from "tabUser"') as ct(a text)"""),
            ("postgres", "select pg_catalog.pg_read_file('postgresql.conf')"),
            ("postgres", "select pg_stat_file('postgresql.conf')"),
            ("mysql", "select load_file('/etc/passwd')"),
            ("sqlite", "select readfile('/etc/passwd')"),
            ("sqlite", "select load_extension('fileio')"),
            ("duckdb", "select parquet_metadata('x.parquet')"),
            ("duckdb", "select sniff_csv('x.csv')"),
            ("duckdb", "select * from postgres_query('db', 'select 1')"),
        ):
            with self.subTest(raw_sql=raw_sql), self.assertRaises(QueryRefused):
                self.builder._validate_native_sql(
                    raw_sql, use_live_connection=True, data_source=self.data_source, dialect=dialect
                )

    # --- the format button ---

    # @feature query.native-sql-format
    def test_format_reindents_a_native_query_and_hands_a_builder_query_back_untouched(self):
        raw_sql = "select name,status from tabToDo where status='Open'"

        native_query = frappe.new_doc("Insights Query v3")
        native_query.is_native_query = 1
        builder_query = frappe.new_doc("Insights Query v3")
        builder_query.is_builder_query = 1

        self.assertEqual(
            native_query.format(raw_sql),
            "SELECT name,\n       status\nFROM tabToDo\nWHERE status='Open'",
        )
        self.assertEqual(builder_query.format(raw_sql), raw_sql)
