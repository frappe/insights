"""Native SQL runs on a read-only PostgreSQL replica.

ibis learns the columns of native SQL by creating a temporary view over it, and
a hot-standby replica refuses every write, temporary views included:
`cannot execute CREATE VIEW in a read-only transaction`. So the columns come
from a zero-row run of the query, and nothing the server is sent creates anything.
"""

from types import SimpleNamespace
from unittest.mock import patch

import frappe
import ibis
from frappe.tests import UnitTestCase

from insights.insights.doctype.insights_data_source_v3.connectors.postgresql import (
    InsightsPostgresBackend,
    InsightsPostgresCompiler,
    get_postgres_connection,
)

QUERY = "SELECT name, grand_total FROM orders;"
TEXT_OID = 25
NUMERIC_OID = 1700
NUMERIC_12_2_MOD = (12 << 16 | 2) + 4


class HotStandby:
    """A psycopg connection to a replica in recovery: it reads and refuses every write."""

    def __init__(self, columns):
        self.columns = columns
        self.statements = []
        self.description = None
        self.pgresult = None

    def cursor(self):
        return self

    def transaction(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, statement, params=None, **kwargs):
        self.statements.append(statement)
        if statement.lstrip().upper().startswith(("CREATE", "DROP")):
            raise RuntimeError("cannot execute CREATE VIEW in a read-only transaction")
        if params is None:
            self.description = [SimpleNamespace(name=name, type_code=oid) for name, oid, _, _ in self.columns]
            self.pgresult = SimpleNamespace(fmod=lambda i: self.columns[i][2])
        else:
            # the catalog read replaces the zero-row run's result
            self.description = self.pgresult = None
        return self

    def fetchall(self):
        return [(type_name,) for _, _, _, type_name in self.columns]

    def close(self):
        pass


def replica(*columns):
    backend = InsightsPostgresBackend()
    backend.con = HotStandby(columns)
    return backend


class TestPostgresReadReplica(UnitTestCase):
    # @feature query.native-sql-read-only-source
    def test_a_replica_reads_the_columns_of_native_sql_off_a_zero_row_run(self):
        db = replica(
            ("name", TEXT_OID, -1, "text"),
            ("grand_total", NUMERIC_OID, NUMERIC_12_2_MOD, "numeric(12,2)"),
        )

        schema = db._get_schema_using_query(QUERY)

        self.assertEqual(schema, ibis.schema({"name": "string", "grand_total": "decimal(12, 2)"}))
        first, catalog_read = db.con.statements
        self.assertTrue(first.startswith("SELECT * FROM (SELECT"), first)
        self.assertTrue(first.endswith("LIMIT 0"), first)
        self.assertNotIn(";", first)
        self.assertIn("format_type", catalog_read)

    # @feature query.native-sql-read-only-source
    def test_two_result_columns_with_one_name_are_refused_by_name(self):
        db = replica(("name", TEXT_OID, -1, "text"), ("name", TEXT_OID, -1, "text"))

        with self.assertRaisesRegex(frappe.ValidationError, "more than one column named name"):
            db._get_schema_using_query("SELECT a.name, b.name FROM a, b")

    # @feature data-source.connect-postgres query.native-sql-read-only-source
    def test_a_connection_string_source_reads_columns_the_same_way(self):
        source = frappe._dict(connection_string="postgresql://reader:p%40ss@replica.internal:5433/shop")

        with patch.object(InsightsPostgresBackend, "do_connect") as do_connect:
            db = get_postgres_connection(source)

        self.assertIsInstance(db, InsightsPostgresBackend)
        self.assertIsInstance(db.compiler, InsightsPostgresCompiler)
        do_connect.assert_called_once_with(
            user="reader", password="p@ss", host="replica.internal", database="shop", port=5433
        )
