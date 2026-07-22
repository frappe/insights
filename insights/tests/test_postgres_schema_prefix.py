"""Guards against regressing frappe/insights#1195.

Postgres table names used to be qualified with their schema unconditionally, so a Site DB
running on postgres listed `public.tabSales Invoice` instead of `tabSales Invoice`. Besides
leaking the prefix into every label, it broke the table -> doctype mapping used by user
permissions, and executing any query failed with `DoesNotExistError`.

Names are now only qualified when a data source actually spans several schemas — but names
stored before that must still resolve, which is what these tests pin down.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    InsightsDataSourcev3,
)
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    get_permitted_columns_for_table,
    strip_schema_prefix,
)


class FakeBackend:
    """Stands in for the ibis backend, recording what it was asked for."""

    def __init__(self, tables_by_schema=None):
        self.tables_by_schema = tables_by_schema or {}
        self.listed = []
        self.requested = []

    def list_tables(self, database=None, **kwargs):
        self.listed.append(database)
        _catalog, schema = database
        return list(self.tables_by_schema.get(schema, []))

    def table(self, name, database=None):
        self.requested.append((name, database))
        return f"{database}.{name}"


def make_data_source(schema=None):
    return frappe.get_doc(
        {
            "doctype": "Insights Data Source v3",
            "title": "Postgres Prefix Test",
            "database_type": "PostgreSQL",
            "database_name": "test_db",
            "schema": schema,
        }
    )


class TestPostgresSchemaPrefix(FrappeTestCase):
    def test_single_schema_tables_are_not_qualified(self):
        backend = FakeBackend({"public": ["tabUser", "customers"]})
        ds = make_data_source()

        with patch.object(InsightsDataSourcev3, "_get_ibis_backend", return_value=backend):
            tables = ds.get_table_list()

        self.assertEqual(tables, ["tabUser", "customers"])
        # the schema is still the one we read from, it just isn't part of the name
        self.assertEqual(backend.listed, [("test_db", "public")])

    def test_named_single_schema_tables_are_not_qualified(self):
        backend = FakeBackend({"sales": ["orders"]})
        ds = make_data_source(schema="sales")

        with patch.object(InsightsDataSourcev3, "_get_ibis_backend", return_value=backend):
            tables = ds.get_table_list()

        self.assertEqual(tables, ["orders"])

    def test_multiple_schemas_keep_the_prefix(self):
        backend = FakeBackend({"public": ["customers"], "sales": ["customers", "orders"]})
        ds = make_data_source(schema="public, sales")

        with patch.object(InsightsDataSourcev3, "_get_ibis_backend", return_value=backend):
            tables = ds.get_table_list()

        # without the prefix the two `customers` tables would collide
        self.assertEqual(tables, ["public.customers", "sales.customers", "sales.orders"])

    def test_unqualified_names_resolve_against_the_configured_schema(self):
        backend = FakeBackend()
        ds = make_data_source(schema="sales")

        with patch.object(InsightsDataSourcev3, "_get_ibis_backend", return_value=backend):
            ds.get_ibis_table("orders")

        self.assertEqual(backend.requested, [("orders", "sales")])

    def test_previously_stored_qualified_names_still_resolve(self):
        backend = FakeBackend()
        ds = make_data_source()

        with patch.object(InsightsDataSourcev3, "_get_ibis_backend", return_value=backend):
            ds.get_ibis_table("public.tabSales Invoice")

        self.assertEqual(backend.requested, [("tabSales Invoice", "public")])

    def test_a_dot_in_the_table_name_is_not_mistaken_for_a_schema(self):
        backend = FakeBackend()
        ds = make_data_source()

        with patch.object(InsightsDataSourcev3, "_get_ibis_backend", return_value=backend):
            ds.get_ibis_table("v1.2 metrics")

        self.assertEqual(backend.requested, [("v1.2 metrics", "public")])


class TestSchemaQualifiedDoctypeMapping(FrappeTestCase):
    def test_strip_schema_prefix(self):
        self.assertEqual(strip_schema_prefix("public.tabUser"), "tabUser")
        self.assertEqual(strip_schema_prefix("tabUser"), "tabUser")
        # not a frappe table — leave it alone, the prefix is part of the name we were given
        self.assertEqual(strip_schema_prefix("public.customers"), "public.customers")

    def test_qualified_frappe_table_maps_to_its_doctype(self):
        # this used to raise DoesNotExistError from `get_meta("public.tabUser")`
        allowed = get_permitted_columns_for_table(strip_schema_prefix("public.tabUser"))

        self.assertIn("name", allowed)
        self.assertIn("email", allowed)
