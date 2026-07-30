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
import pandas as pd
from frappe.tests.utils import FrappeTestCase

from insights.insights.doctype.insights_data_source_v3.connectors.frappe_db import (
    get_frappedb_table_links,
)
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


class FakeFieldTable:
    """Stands in for an ibis table of docfields — every expression yields the same rows."""

    def __init__(self, rows):
        self.rows = rows

    def select(self, *args, **kwargs):
        return self

    def filter(self, *args):
        return self

    def execute(self):
        return pd.DataFrame(self.rows)


class FakeFrappeBackend:
    """Serves the two field tables `get_frappedb_table_links` reads."""

    def __init__(self, docfields=(), custom_fields=()):
        self.rows = {
            "tabDocField": list(docfields),
            "tabCustom Field": list(custom_fields),
        }

    def table(self, name, database=None):
        return FakeFieldTable(self.rows[name])


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

    def test_formatting_a_name_is_the_inverse_of_splitting_it(self):
        for ds in (make_data_source(), make_data_source(schema="sales")):
            self.assertEqual(ds.format_table_name("orders"), "orders")
            self.assertEqual(ds.split_table_name(ds.format_table_name("orders"))[1], "orders")

        multi = make_data_source(schema="public, sales")
        self.assertEqual(multi.format_table_name("orders", "sales"), "sales.orders")
        self.assertEqual(multi.split_table_name("sales.orders"), ("sales", "orders"))
        # no schema given — frappe tables live in the first one configured
        self.assertEqual(multi.format_table_name("tabUser"), "public.tabUser")


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


DOCFIELDS = [
    {
        "fieldname": "customer",
        "fieldtype": "Link",
        "options": "Customer",
        "parent": "Sales Invoice",
    },
    {
        "fieldname": "items",
        "fieldtype": "Table",
        "options": "Sales Invoice Item",
        "parent": "Sales Invoice",
    },
]
CUSTOM_FIELDS = [
    {
        "fieldname": "sales_person",
        "fieldtype": "Link",
        "options": "Sales Person",
        "parent": "Sales Invoice",
    },
]


class TestFrappeDbTableLinks(FrappeTestCase):
    """Links have to name their tables exactly as `Insights Table v3` stores them."""

    def get_links(self, data_source):
        backend = FakeFrappeBackend(DOCFIELDS, CUSTOM_FIELDS)
        with patch.object(InsightsDataSourcev3, "_get_ibis_backend", return_value=backend):
            return get_frappedb_table_links(data_source)

    def test_links_are_unqualified_for_a_single_schema(self):
        links = self.get_links(make_data_source())

        self.assertEqual(
            links,
            [
                {
                    "left_table": "tabCustomer",
                    "left_column": "name",
                    "right_table": "tabSales Invoice",
                    "right_column": "customer",
                },
                {
                    "left_table": "tabSales Invoice",
                    "left_column": "name",
                    "right_table": "tabSales Invoice Item",
                    "right_column": "parent",
                },
                {
                    "left_table": "tabSales Person",
                    "left_column": "name",
                    "right_table": "tabSales Invoice",
                    "right_column": "sales_person",
                },
            ],
        )

    def test_links_are_qualified_when_schemas_can_collide(self):
        # tables are stored qualified here, so links that named `tabX` would never match
        links = self.get_links(make_data_source(schema="public, sales"))

        self.assertTrue(
            all(
                link[side].startswith("public.tab")
                for link in links
                for side in ("left_table", "right_table")
            ),
            links,
        )

    def test_mariadb_links_are_never_qualified(self):
        data_source = make_data_source()
        data_source.database_type = "MariaDB"

        links = self.get_links(data_source)

        self.assertEqual(links[0]["left_table"], "tabCustomer")
