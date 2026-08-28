# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import dataclasses
import hashlib
import os
import tempfile
import unittest

from insights.setup.demo_data import DEMO_SPEC, BrokenFixture, check_integrity, generate
from insights.setup.demo_data.generator import build_rows


def fingerprint(rows):
    """Hash the generated rows, so a failure prints a digest and not 12,000 rows."""
    digest = hashlib.sha256()
    for name in sorted(rows):
        digest.update(name.encode())
        for row in rows[name]:
            digest.update(repr(sorted(row.items())).encode())
    return digest.hexdigest()


class TestDemoDataGenerator(unittest.TestCase):
    """The generator has no Frappe dependency, so these tests need no site."""

    def test_same_seed_gives_same_rows(self):
        first = build_rows(DEMO_SPEC, DEMO_SPEC.seed)
        second = build_rows(DEMO_SPEC, DEMO_SPEC.seed)
        self.assertEqual(fingerprint(first), fingerprint(second))

    def test_another_seed_gives_other_rows(self):
        first = build_rows(DEMO_SPEC, DEMO_SPEC.seed)
        second = build_rows(DEMO_SPEC, DEMO_SPEC.seed + 1)
        self.assertNotEqual(fingerprint(first), fingerprint(second))

    def test_every_foreign_key_joins(self):
        with tempfile.TemporaryDirectory() as directory:
            path = generate(os.path.join(directory, "demo.duckdb"))
            for table, key, matched, orphans in check_integrity(path):
                self.assertGreater(matched, 0, f"{table}.{key} matched no rows")
                self.assertEqual(orphans, 0, f"{table}.{key} left orphans")

    def test_a_trimmed_parent_fails_the_check(self):
        """The committed fixture was trimmed per table, which orphaned every child row."""
        import duckdb

        with tempfile.TemporaryDirectory() as directory:
            path = generate(os.path.join(directory, "demo.duckdb"))
            connection = duckdb.connect(path)
            connection.execute("delete from customers")
            connection.close()

            with self.assertRaises(BrokenFixture):
                check_integrity(path)

    def test_an_invalid_spec_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "demo.duckdb")
            with self.assertRaises(BrokenFixture):
                generate(path, spec=_spec_with_no_customers())
            self.assertFalse(os.path.exists(path), "a rejected spec must leave no file")

    def test_sample_workbook_query_returns_rows(self):
        """The seeded workbook charts undelivered orders joined to their line items."""
        import duckdb

        with tempfile.TemporaryDirectory() as directory:
            path = generate(os.path.join(directory, "demo.duckdb"))
            connection = duckdb.connect(path, read_only=True)
            rows, prices, months, statuses = connection.execute(
                """
                select count(*), count(i.price),
                       count(distinct date_trunc('month', o.order_purchase_timestamp)),
                       count(distinct o.order_status)
                from orders o
                left join orderitems i on o.order_id = i.order_id
                where o.order_status not in ('delivered')
                  and o.order_purchase_timestamp between '2016-10-01' and '2018-08-31'
                """
            ).fetchone()
            connection.close()

        self.assertGreater(rows, 100)
        self.assertEqual(rows, prices, "every joined row must carry a price")
        self.assertGreaterEqual(months, 18)
        self.assertGreaterEqual(statuses, 4)


def _spec_with_no_customers():
    tables = tuple(
        dataclasses.replace(table, rows=0) if table.name == "customers" else table
        for table in DEMO_SPEC.tables
    )
    return dataclasses.replace(DEMO_SPEC, tables=tables)
