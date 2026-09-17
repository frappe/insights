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
    # a Python dict written with str()
    "{'product': 'crm', 'note': 'it\\'s fine'}",
    # valid JSON whose value holds a quote before a comma
    '{"product": "rock \'n\', roll"}',
    "not json",
    '{"product": "null"}',
]


class TestJsonFunctions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = ibis.duckdb.connect()
        cls.table = cls.con.create_table(
            "json_fixture", ibis.memtable({"p": ROWS, "team": ["abc", "", *["abc"] * (len(ROWS) - 2)]})
        )

    def _values(self, expr):
        return self.table.select(v=expr).to_pandas()["v"].tolist()

    def test_reads_a_key_from_pretty_printed_json(self):
        self.assertEqual(self._values(json_value(self.table.p, "product"))[0], "erpnext")

    def test_explicit_json_null_becomes_empty_not_the_text_null(self):
        # casting JSON to string otherwise yields the literal 'null', which then
        # counts as a real value in filters and group-bys
        self.assertIsNone(self._values(json_value(self.table.p, "product"))[1])

    def test_the_string_null_stays_text(self):
        self.assertEqual(self._values(json_value(self.table.p, "product"))[5], "null")

    def test_missing_key_is_empty(self):
        self.assertEqual(self._values(json_value(self.table.p, "nope")), [None] * len(ROWS))

    def test_reads_a_python_dict_row_next_to_json_rows(self):
        self.assertEqual(self._values(json_value(self.table.p, "product"))[2], "crm")
        self.assertEqual(self._values(json_value(self.table.p, "note"))[2], "it's fine")

    def test_valid_json_is_read_as_written(self):
        self.assertEqual(self._values(json_value(self.table.p, "product"))[3], "rock 'n', roll")

    def test_a_row_that_is_not_json_is_empty(self):
        self.assertIsNone(self._values(json_value(self.table.p, "product"))[4])

    def test_reads_list_positions_from_the_end(self):
        self.assertEqual(self._values(json_value(self.table.p, "items.-1.n"))[1], "first")

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
        self.assertEqual(self._values(null_if(self.table.team, ""))[:2], ["abc", None])
