import frappe
import ibis
import sqlglot as sg

from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.insights.doctype.insights_table_v3.insights_table_v3 import InsightsTablev3
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
        """The rewrite alone, over a binding for every table the SQL names.

        Built here rather than through `_get_sql_table_bindings` so that these
        cases are about what the rewrite does to a bound table, whatever the
        reader they run as is narrowed by.
        """
        if replace_map is None:
            tables = self.builder._get_sql_table_names(raw_sql, dialect=self.dialect)
            replace_map = {
                table: ibis.to_sql(InsightsTablev3.get_ibis_table(SITE_DB, table, use_live_connection=True))
                for table in tables
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

    # @feature query.native-sql
    def test_a_cte_hides_a_table_only_inside_its_own_block(self):
        """A CTE's scope is the query block that declares it, so a name it hides
        inside a derived table still means the real table outside it - and the
        binding is the only thing that applies the reader's permissions."""
        raw_sql = (
            "select u.name from (with `tabUser` as (select 1 as n) select n from `tabUser`) s "
            "join `tabUser` u on 1 = 1"
        )

        self.assertEqual(self.builder._get_sql_table_names(raw_sql, dialect=self.dialect), {"tabUser"})

        # a CTE that does reach the reference still hides it
        hidden = "with `tabUser` as (select 1 as n) select n from `tabUser`"
        self.assertEqual(self.builder._get_sql_table_names(hidden, dialect=self.dialect), set())

    # @feature query.native-sql
    def test_a_derived_table_aliased_after_a_table_does_not_hide_it(self):
        """An alias names a source, it does not declare one. A subquery aliased
        with a real table's name leaves every reference to that table real, and
        the binding is the only thing that applies the reader's permissions."""
        raw_sql = "select u.name from (select 1 as n) as `tabUser` join `tabUser` as u on 1 = 1"

        self.assertEqual(self.builder._get_sql_table_names(raw_sql, dialect=self.dialect), {"tabUser"})

        rewritten = self.rewrite(raw_sql, {"tabUser": "SELECT * FROM `tabUser`"})

        # the real reference reads its binding; the subquery that borrowed the name is left alone
        self.assertIn("AS u", rewritten)
        self.assertIn("(SELECT 1 AS n) AS `tabUser`", rewritten)

    # @feature query.native-sql
    def test_a_cte_reference_is_left_alone_where_the_same_name_is_bound(self):
        """Extraction and the rewrite read one rule. A name that means a real
        table in one block and a CTE in another is bound where it is real and
        left alone where it is not - binding the CTE reference would point it at
        rows that do not carry the CTE's columns."""
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
        """A reader who may read every row of a doctype is narrowed by a
        held-back column alone, with no `WHERE`."""
        reader = "native_sql_permlevel@test.com"
        create_user(reader, first_name="Native", last_name="Reader", roles="System Manager")
        self.addCleanup(delete_users, reader)
        # `ToDo` names System Manager in its own permissions, so this reader is
        # restricted to no rows at all and the permission query carries no WHERE
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
        """`IbisQueryBuilder.apply_sql`, which `InsightsQueryv3.execute` runs for
        a native query. On the data store the rows desk admits come off the live
        site as an in-memory table, and the SQL handed to DuckDB names it."""
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
    def test_a_schema_qualified_table_is_refused(self):
        # a binding is looked up by the bare name, so reading `sales.orders`
        # would bind whichever `orders` the default schema holds
        with self.assertRaises(frappe.ValidationError):
            self.builder._validate_native_sql(
                "select * from sales.orders", use_live_connection=True, dialect=self.dialect
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
