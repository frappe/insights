"""A native query is read by the parser this module already uses.

`sqlparse` grouped comments in quadratic time, so a statement written to be slow
held a synchronous worker for seconds of pure CPU with no data source involved.
A length limit only made that slower to reach — at 10 000 characters, the bound
it replaced, the old parser still spent over a second per call, and the endpoint
that ran it is whitelisted.

`sqlglot` reads the same text in constant time for this shape of input, and the
module already runs it over every native query to find the tables. A statement
it cannot read is handed back untouched, the same rule `extract_sql_table_refs`
follows, so no query stops working because the parser got stricter.
"""

import time

import frappe
from frappe.tests import UnitTestCase

from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    count_sql_statements,
    format_sql,
    strip_sql_comments,
)

# 40 kB of comment lines. The parser this replaced took about nine seconds.
COMMENT_BOMB = "-- a\n" * 8_000

# Valid SQL Server syntax, which the MySQL dialect cannot read. This is the
# shape of statement the fallback exists for.
UNREADABLE = "SELECT * FROM t FOR XML PATH('')"


class TestCommentsAreStripped(UnitTestCase):
    def test_a_line_comment_is_removed(self):
        self.assertNotIn("secret", strip_sql_comments("select 1 -- secret\n", "mysql"))

    def test_a_block_comment_is_removed(self):
        self.assertNotIn("secret", strip_sql_comments("select /* secret */ 1", "mysql"))

    def test_a_leading_comment_does_not_hide_the_statement(self):
        stripped = strip_sql_comments("-- note\nselect 1", "mysql")
        self.assertTrue(stripped.strip().lower().startswith("select"))

    def test_a_statement_the_parser_cannot_read_is_handed_back(self):
        self.assertEqual(strip_sql_comments(UNREADABLE, "mysql"), UNREADABLE)


class TestStatementsAreCounted(UnitTestCase):
    def test_one_statement(self):
        self.assertEqual(count_sql_statements("select 1", "mysql"), 1)

    def test_two_statements(self):
        self.assertEqual(count_sql_statements("select 1; select 2", "mysql"), 2)

    def test_a_statement_the_parser_cannot_read_counts_as_one(self):
        self.assertEqual(count_sql_statements(UNREADABLE, "mysql"), 1)


class TestFormatting(UnitTestCase):
    def test_a_statement_is_laid_out(self):
        formatted = format_sql("select a,b from t where a=1", "mysql")
        self.assertIn("\n", formatted)
        self.assertIn("SELECT", formatted)

    def test_a_statement_the_parser_cannot_read_is_reported(self):
        """The button did something, so say when it could not."""
        with self.assertRaises(frappe.ValidationError):
            format_sql(UNREADABLE, "mysql")


class TestTheParserStaysOffTheWorker(UnitTestCase):
    """The bound is the parser's cost, so there is no length limit to tune."""

    def elapsed(self, call):
        started = time.perf_counter()
        call()
        return time.perf_counter() - started

    def test_a_comment_bomb_is_read_quickly(self):
        self.assertLess(self.elapsed(lambda: strip_sql_comments(COMMENT_BOMB, "mysql")), 1)

    def test_counting_a_comment_bomb_is_quick(self):
        self.assertLess(self.elapsed(lambda: count_sql_statements(COMMENT_BOMB, "mysql")), 1)
