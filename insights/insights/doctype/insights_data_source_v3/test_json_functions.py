# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import ibis

from insights.insights.doctype.insights_data_source_v3.ibis.functions import (
    json_value,
    null_if,
)

ROWS = [
    # pretty-printed, the shape Pulse writes
    '{\n "product": "erpnext",\n "site": "a.frappe.cloud"\n}',
    # an explicit null, and a nested object
    '{"product": null, "amount": "12.5", "ok": true, "address": {"city": "Pune"}, "items": [{"n": "first"}]}',
]


class TestJsonFunctions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = ibis.duckdb.connect()
        cls.table = cls.con.create_table("json_fixture", ibis.memtable({"p": ROWS, "team": ["abc", ""]}))

    def _values(self, expr):
        return self.table.select(v=expr).to_pandas()["v"].tolist()

    def test_reads_a_key_from_pretty_printed_json(self):
        self.assertEqual(self._values(json_value(self.table.p, "product"))[0], "erpnext")

    def test_explicit_json_null_becomes_empty_not_the_text_null(self):
        # casting JSON to string otherwise yields the literal 'null', which then
        # counts as a real value in filters and group-bys
        self.assertIsNone(self._values(json_value(self.table.p, "product"))[1])

    def test_missing_key_is_empty(self):
        self.assertEqual(self._values(json_value(self.table.p, "nope")), [None, None])

    def test_reads_nested_keys_and_list_positions(self):
        self.assertEqual(self._values(json_value(self.table.p, "address.city"))[1], "Pune")
        self.assertEqual(self._values(json_value(self.table.p, "items.0.n"))[1], "first")

    def test_returns_a_typed_value(self):
        self.assertEqual(self._values(json_value(self.table.p, "amount", "float"))[1], 12.5)
        self.assertTrue(self._values(json_value(self.table.p, "ok", "bool"))[1])

    def test_composes_inside_a_filter(self):
        # the point of json_value over json_extract: it is a value, not a query
        matched = self.table.filter(json_value(self.table.p, "product") == "erpnext")
        self.assertEqual(matched.count().to_pandas(), 1)

    def test_rejects_an_unknown_type(self):
        with self.assertRaises(Exception):
            json_value(self.table.p, "amount", "monetary")

    def test_null_if_blanks_a_placeholder_value(self):
        self.assertEqual(self._values(null_if(self.table.team, "")), ["abc", None])
