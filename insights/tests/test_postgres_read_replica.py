"""Native SQL runs on a read-only PostgreSQL replica.

ibis learns the columns of native SQL by creating a temporary view over it, and
a hot-standby replica refuses every write, temporary views included:
`cannot execute CREATE VIEW in a read-only transaction`. So nothing the replica
is sent may create anything. A data source marked as a read replica creates
the view on its primary; without a primary that answers, the columns come from
a zero-row run of the query on the replica.
"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import ibis
from frappe.tests import UnitTestCase

from insights.insights.doctype.insights_data_source_v3.connectors.postgresql import (
    InsightsPostgresBackend,
)

QUERY = "SELECT name, grand_total FROM orders;"
NUMERIC_OID = 1700
NUMERIC_12_2_MOD = (12 << 16 | 2) + 4


class HotStandby:
    """A psycopg connection to a replica in recovery: it reads and refuses every write."""

    def __init__(self):
        self.statements = []
        self.description = None

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
            self.description = [
                SimpleNamespace(name="name", type_code=25, _fmod=-1),
                SimpleNamespace(name="grand_total", type_code=NUMERIC_OID, _fmod=NUMERIC_12_2_MOD),
            ]
        return self

    def fetchall(self):
        return [("text",), ("numeric(12,2)",)]

    def close(self):
        pass


def replica(connect_primary=None):
    backend = InsightsPostgresBackend()
    backend.con = HotStandby()
    backend.connect_primary = connect_primary
    return backend


class TestPostgresReadReplica(UnitTestCase):
    def test_a_read_replica_learns_the_columns_of_native_sql_on_its_primary(self):
        primary = Mock()
        primary._get_schema_using_query.return_value = ibis.schema({"name": "string"})
        db = replica(connect_primary=lambda: primary)

        db._get_schema_using_query(QUERY)
        db._get_schema_using_query(QUERY)

        self.assertEqual(primary._get_schema_using_query.call_count, 2)
        self.assertEqual(db.con.statements, [])

    def test_without_a_primary_the_replica_reads_the_columns_off_a_zero_row_run(self):
        db = replica()

        schema = db._get_schema_using_query(QUERY)

        self.assertEqual(schema, ibis.schema({"name": "string", "grand_total": "decimal(12, 2)"}))
        first = db.con.statements[0]
        self.assertTrue(first.startswith("SELECT * FROM (SELECT"), first)
        self.assertTrue(first.endswith("LIMIT 0"), first)
        self.assertNotIn(";", first)

    def test_an_unreachable_primary_is_logged_once_and_the_replica_still_answers(self):
        connect_primary = Mock(side_effect=ConnectionError("primary.internal refused"))
        db = replica(connect_primary=connect_primary)

        with patch("frappe.log_error") as log_error:
            first = db._get_schema_using_query(QUERY)
            second = db._get_schema_using_query(QUERY)

        self.assertEqual(first, second)
        self.assertEqual(list(first.names), ["name", "grand_total"])
        connect_primary.assert_called_once()
        log_error.assert_called_once()

    def test_closing_the_replica_closes_the_primary_it_opened(self):
        primary = Mock()
        db = replica(connect_primary=lambda: primary)
        db._get_schema_using_query(QUERY)

        db.disconnect()

        primary.disconnect.assert_called_once()
