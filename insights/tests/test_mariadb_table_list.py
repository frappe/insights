"""Guards against regressing frappe/insights#1604.

A MariaDB database whose name contains dots, such as a site called `mydev.domain.net`,
could not be listed: `get_table_list` named the database again when the name held any
character outside `[a-zA-Z0-9_]`, and ibis reads a dotted name as a table hierarchy,
raising `Overspecified table hierarchy provided`.

Naming it was never needed, because the connection is already opened against that
database. It was introduced to carry a quoted name, and the quoting itself had to be
removed in #1179 once ibis started quoting identifiers of its own accord.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    InsightsDataSourcev3,
)


class FakeBackend:
    """Stands in for the ibis backend, recording what it was asked for."""

    def __init__(self, tables=None):
        self.tables = tables or []
        self.listed = []

    def list_tables(self, database=None, **kwargs):
        self.listed.append(database)
        if database is not None:
            # ibis splits a dotted name into catalog and schema, and refuses more
            # levels than the backend has.
            raise ValueError(f"Overspecified table hierarchy provided: {database}")
        return list(self.tables)


def make_data_source(database_name):
    return frappe.get_doc(
        {
            "doctype": "Insights Data Source v3",
            "title": "MariaDB Table List Test",
            "database_type": "MariaDB",
            "database_name": database_name,
        }
    )


class TestMariaDBTableList(FrappeTestCase):
    # @feature data-source.table-list
    def test_dotted_database_name_lists_tables(self):
        backend = FakeBackend(["tabUser", "customers"])
        ds = make_data_source("mydev.domain.net")

        with patch.object(InsightsDataSourcev3, "_get_ibis_backend", return_value=backend):
            tables = ds.get_table_list()

        self.assertEqual(tables, ["tabUser", "customers"])
        # the connection already carries the database, so it is not named again
        self.assertEqual(backend.listed, [None])

    # @feature data-source.table-list
    def test_plain_database_name_lists_tables(self):
        backend = FakeBackend(["orders"])
        ds = make_data_source("plain_db")

        with patch.object(InsightsDataSourcev3, "_get_ibis_backend", return_value=backend):
            tables = ds.get_table_list()

        self.assertEqual(tables, ["orders"])
        self.assertEqual(backend.listed, [None])
