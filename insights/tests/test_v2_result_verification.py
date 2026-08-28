"""A migrated query returns what the v2 query returned - or the diff says so.

Two halves, tested apart, the same way the migrator is.

The comparison is pure - two frames in, a list of differences out - so every
rule it makes is a unit test over hand-built frames: the tolerance, the nulls,
the dates, the row order, the sanitized column name, and a real mismatch.

The execution is an integration test. It writes a v2 dashboard over `tabToDo`
with the compiled SQL v2 would have stored, migrates it, and verifies the
result against the live Site DB - the same MariaDB, through the same cached
connection, which is the whole claim the module rests on. One of the fixtures is
wrong on purpose: its stored SQL filters where its spec does not, which is what
a filter lost in translation looks like. A verifier nobody has watched fail is
not yet a verifier.
"""

import json
from datetime import date, datetime
from decimal import Decimal

import frappe
import numpy as np
import pandas as pd
from frappe.tests import UnitTestCase

from insights.migrator.v2_verification import (
    CELL,
    COLUMN_COUNT,
    COLUMN_NAME,
    COLUMN_TYPE,
    DIFFERENT,
    EXPECTED,
    IDENTITY,
    NOT_RUN,
    ROW_COUNT,
    ROW_MEMBERSHIP,
    SAME,
    TRANSLATION,
    classify,
    compare_frames,
    stated_limit,
    states_an_order,
    v2_answer,
    verdict_for,
    verify_migration,
)
from insights.migrator.v2_workbooks import migrate_dashboard
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT

SITE_DB = "Site DB"


def frame(**columns):
    return pd.DataFrame(columns)


def kinds(differences):
    return [difference.kind for difference in differences]


class TestComparisonRules(UnitTestCase):
    """Every rule `compare_frames` makes, and the reason it makes it."""

    def test_two_identical_frames_do_not_differ(self):
        left = frame(status=["Open", "Closed"], total=[3, 4])
        self.assertEqual(compare_frames(left, left.copy()), [])

    def test_a_decimal_from_mariadb_equals_a_float_from_duckdb(self):
        left = frame(status=["Open"], total=[Decimal("12.50")])
        right = frame(status=["Open"], total=[12.5])

        differences = compare_frames(left, right)
        self.assertNotIn(CELL, kinds(differences))
        self.assertEqual(verdict_for(differences), SAME)

    def test_float_noise_below_the_tolerance_is_not_a_difference(self):
        """A sum built in a different order does not land on the same last bit."""
        left = frame(total=[1_000_000.0])
        right = frame(total=[1_000_000.0000001])

        self.assertEqual(compare_frames(left, right), [])

    def test_a_real_numeric_difference_is_still_caught(self):
        left = frame(total=[1_000_000.0])
        right = frame(total=[1_000_100.0])

        differences = compare_frames(left, right)
        self.assertEqual(kinds(differences), [ROW_MEMBERSHIP, ROW_MEMBERSHIP, ROW_MEMBERSHIP])
        self.assertEqual(verdict_for(differences), DIFFERENT)

    def test_every_spelling_of_missing_means_the_same_thing(self):
        """`execute_ibis_query` hands back None where a raw frame keeps NaN."""
        left = pd.DataFrame({"a": [None, np.nan], "b": [pd.NaT, pd.NaT]})
        right = pd.DataFrame({"a": [np.nan, None], "b": [None, None]})

        self.assertEqual([d for d in compare_frames(left, right) if d.material], [])

    def test_a_date_and_the_timestamp_at_its_midnight_are_the_same_day(self):
        left = frame(day=[date(2024, 1, 1)])
        right = frame(day=[datetime(2024, 1, 1, 0, 0, 0)])

        differences = compare_frames(left, right)
        self.assertEqual(kinds(differences), [COLUMN_TYPE])
        self.assertEqual(verdict_for(differences), SAME)

    def test_a_dtype_difference_is_reported_and_does_not_count(self):
        left = frame(total=[1, 2])
        right = frame(total=[1.0, 2.0])

        differences = compare_frames(left, right)
        self.assertEqual(kinds(differences), [COLUMN_TYPE])
        self.assertFalse(differences[0].material)

    def test_row_order_is_not_a_difference_unless_both_sides_state_one(self):
        """v2 emitted ORDER BY only for a column with `order` set."""
        left = frame(status=["Open", "Closed"], total=[3, 4])
        right = frame(status=["Closed", "Open"], total=[4, 3])

        self.assertEqual(compare_frames(left, right, ordered=False), [])

        ordered = compare_frames(left, right, ordered=True)
        self.assertEqual(set(kinds(ordered)), {CELL})
        self.assertEqual(verdict_for(ordered), DIFFERENT)

    def test_a_sanitized_column_name_is_reported_apart_from_the_data(self):
        """v3 puts a mutated name through `sanitize_name`; the values do not move."""
        left = frame(**{"Count of records ": [3, 4]})
        right = frame(count_of_records=[3, 4])

        differences = compare_frames(left, right)
        self.assertEqual(kinds(differences), [])
        self.assertEqual(verdict_for(differences), SAME)

    def test_a_genuinely_different_name_at_the_same_position_is_reported(self):
        left = frame(status=["Open"])
        right = frame(priority=["Open"])

        differences = compare_frames(left, right)
        self.assertEqual(kinds(differences), [COLUMN_NAME])
        self.assertEqual(verdict_for(differences), SAME)

    def test_an_extra_v3_column_is_reported_and_the_shared_ones_still_compared(self):
        left = frame(status=["Open"], total=[3])
        right = frame(status=["Open"], total=[9], running_total=[9])

        differences = compare_frames(left, right)
        self.assertEqual(kinds(differences)[0], COLUMN_COUNT)
        self.assertIn(ROW_MEMBERSHIP, kinds(differences))

    def test_a_row_count_difference_is_named_as_one(self):
        left = frame(status=["Open"], total=[3])
        right = frame(status=["Open", "Closed"], total=[3, 4])

        differences = compare_frames(left, right)
        self.assertEqual(kinds(differences)[0], ROW_COUNT)
        self.assertEqual(verdict_for(differences), DIFFERENT)

    def test_a_changed_value_names_the_row_and_the_column(self):
        left = frame(status=["Open", "Closed"], total=[3, 4])
        right = frame(status=["Open", "Closed"], total=[3, 5])

        differences = compare_frames(left, right, ordered=True)
        self.assertEqual(kinds(differences), [CELL])
        self.assertIn("row 1, total: v2 4.0, v3 5.0", differences[0].detail)

    def test_a_string_never_equals_the_number_that_spells_it(self):
        """v2 formatted "Month of Year" as "January"; v3's month() returns 1."""
        left = frame(month=["1"])
        right = frame(month=[1])

        self.assertEqual(verdict_for(compare_frames(left, right)), DIFFERENT)


class TestExpectedDifferences(UnitTestCase):
    """A difference the translators already reported is not a surprise."""

    def widened_grouping(self):
        left = frame(status=["Open"], total=[7])
        right = frame(status=["Open", "Open"], total=[3, 4])
        return compare_frames(left, right)

    def test_the_widened_grouping_is_expected_when_the_gap_says_so(self):
        differences = classify(self.widened_grouping(), {"grouped_loose_column"})

        self.assertTrue(all(d.expected for d in differences if d.material))
        self.assertEqual(verdict_for(differences), EXPECTED)

    def test_the_same_difference_with_no_gap_behind_it_is_a_failure(self):
        differences = classify(self.widened_grouping(), set())

        self.assertEqual(verdict_for(differences), DIFFERENT)

    def test_a_gap_only_explains_the_differences_it_predicts(self):
        """`granularity_part_type` changes values, not the number of columns."""
        left = frame(month=["January"], total=[3])
        right = frame(month=[1], total=[3], extra=[0])
        differences = classify(compare_frames(left, right), {"granularity_part_type"})

        column_count = next(d for d in differences if d.kind == COLUMN_COUNT)
        self.assertFalse(column_count.expected)
        self.assertEqual(verdict_for(differences), DIFFERENT)


class TestReadingTheStoredStatement(UnitTestCase):
    """v2's SQL is parsed for two facts only: does it order, and does it limit."""

    ORDERED = "select `status`, count(*) as `n` from `tabToDo` group by `status` order by `status` asc"

    def test_an_order_by_is_found_through_v2_backticks(self):
        self.assertTrue(states_an_order(self.ORDERED, "mysql"))
        self.assertFalse(states_an_order("select `status` from `tabToDo`", "mysql"))

    def test_a_subquerys_order_is_not_the_answers_order(self):
        sql = "select * from (select `a` from `t` order by `a`) `x`"
        self.assertFalse(states_an_order(sql, "mysql"))

    def test_the_v2_default_limit_is_read_off_the_statement(self):
        self.assertEqual(stated_limit("select `a` from `t` limit 100", "mysql"), 100)
        self.assertIsNone(stated_limit("select `a` from `t`", "mysql"))

    def test_a_statement_that_will_not_parse_settles_nothing(self):
        self.assertFalse(states_an_order("this is not sql at all ((", "mysql"))
        self.assertIsNone(stated_limit("this is not sql at all ((", "mysql"))


# -- the integration fixture ------------------------------------------------


def insert_row(doctype, row):
    """Put a row in a v2 table without asking the meta whether the doctype exists."""
    row = {
        "creation": frappe.utils.now(),
        "modified": frappe.utils.now(),
        "modified_by": "Administrator",
        "owner": "Administrator",
        "docstatus": 0,
        **row,
    }
    columns = ", ".join(f"`{key}`" for key in row)
    placeholders = ", ".join(["%s"] * len(row))
    frappe.db.sql(f"insert into `tab{doctype}` ({columns}) values ({placeholders})", tuple(row.values()))


def group_by(column, label):
    return {
        "aggregation": "group by",
        "alias": label,
        "label": label,
        "column": column,
        "table": "tabToDo",
        "type": "String",
        "expression": {},
        "granularity": "",
        "order": None,
    }


def count_column(label="Count of records"):
    return {
        "aggregation": "count",
        "alias": label,
        "label": label,
        "column": "*",
        "table": "tabToDo",
        "type": "Integer",
        "expression": {},
        "granularity": "",
        "order": None,
    }


def v2_query(name, sql, columns, *, data_source=SITE_DB, table="tabToDo", **overrides):
    spec = {
        "table": {"table": table, "label": table},
        "joins": [],
        "columns": columns,
        "calculations": [],
        "filters": [],
        "measures": [],
        "dimensions": [],
        "orders": [],
        "limit": None,
    }
    row = {
        "name": name,
        "title": name,
        "data_source": data_source,
        "json": json.dumps(spec),
        "sql": sql,
        "script": None,
        "is_native_query": 0,
        "is_assisted_query": 1,
        "is_script_query": 0,
    }
    row.update(overrides)
    return row


GROUPED_SQL = (
    "select `tabToDo`.`status` as `Status`, count(*) as `Count of records ` "
    "from `tabToDo` group by `tabToDo`.`status` limit 100"
)

# The same query, with a filter its spec does not carry. This is what a filter
# lost in translation looks like from the outside.
FILTERED_SQL = (
    "select `tabToDo`.`status` as `Status`, count(*) as `Count of records ` "
    "from `tabToDo` where `tabToDo`.`status` = 'Open' "
    "group by `tabToDo`.`status` limit 100"
)


class TestResultVerification(InsightsIntegrationTestCase):
    """The real thing: v2's own SQL and the migrated query, against Site DB."""

    DASHBOARD = "DSH-VERIFYTEST"
    FAITHFUL = "QRY-VERIFYTEST-1"
    WRONG = "QRY-VERIFYTEST-2"
    STORED = "QRY-VERIFYTEST-3"
    NATIVE = "QRY-VERIFYTEST-4"

    NAMES = (FAITHFUL, WRONG, STORED, NATIVE)

    TODO_PREFIX = "Insights Verification Test"

    @classmethod
    def before_class(cls):
        cls.delete_v2_fixture()
        cls.seed_todos()
        cls.create_v2_dashboard()

    @classmethod
    def after_class(cls):
        cls.delete_v3_output()
        cls.delete_v2_fixture()
        cls.delete_todos()

    @classmethod
    def seed_todos(cls):
        """Rows in more than one status, so a lost filter has something to lose.

        A `where status = 'Open'` the migration drops changes nothing on a table
        where every row is open, and the test would pass while proving nothing.
        """
        cls.delete_todos()
        for status in ("Open", "Open", "Closed", "Cancelled"):
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": f"{cls.TODO_PREFIX} {status}",
                    "status": status,
                }
            ).insert(ignore_permissions=True)

    @classmethod
    def delete_todos(cls):
        for name in frappe.get_all(
            "ToDo", filters={"description": ["like", f"{cls.TODO_PREFIX}%"]}, pluck="name"
        ):
            frappe.delete_doc("ToDo", name, force=True, ignore_permissions=True)

    @classmethod
    def create_v2_dashboard(cls):
        columns = [group_by("status", "Status"), count_column("Count of records ")]

        rows = [
            v2_query(cls.FAITHFUL, GROUPED_SQL, columns),
            v2_query(cls.WRONG, FILTERED_SQL, columns),
            # a Query Store query: its stored SQL selects from v2's result store
            v2_query(
                cls.STORED,
                f"select `Status` from `{cls.FAITHFUL}` limit 100",
                [group_by("Status", "Status")],
                data_source="Query Store",
                table=cls.FAITHFUL,
            ),
            # a native query: the SQL floor stores this same text as the v3 query
            v2_query(cls.NATIVE, GROUPED_SQL, [], is_native_query=1, is_assisted_query=0),
        ]
        for row in rows:
            insert_row("Insights Query", row)

        insert_row("Insights Dashboard", {"name": cls.DASHBOARD, "title": "Verification Test"})
        for idx, name in enumerate(cls.NAMES, start=1):
            insert_row(
                "Insights Dashboard Item",
                {
                    "parent": cls.DASHBOARD,
                    "parenttype": "Insights Dashboard",
                    "parentfield": "items",
                    "idx": idx,
                    "name": 910000 + idx,
                    "item_id": str(910000 + idx),
                    "item_type": "Bar",
                    "layout": json.dumps({"i": 910000 + idx, "x": 0, "y": 0, "w": 10, "h": 8}),
                    "options": json.dumps(
                        {
                            "query": name,
                            "title": name,
                            "xAxis": "Status",
                            "yAxis": ["Count of records "],
                        }
                    ),
                },
            )

    @classmethod
    def delete_v2_fixture(cls):
        frappe.db.sql("delete from `tabInsights Dashboard Item` where parent = %s", (cls.DASHBOARD,))
        frappe.db.sql("delete from `tabInsights Dashboard` where name = %s", (cls.DASHBOARD,))
        frappe.db.sql("delete from `tabInsights Query` where name in %(names)s", {"names": cls.NAMES})

    @classmethod
    def delete_v3_output(cls):
        for workbook in frappe.get_all(DT.WORKBOOK, filters={"title": "Verification Test"}, pluck="name"):
            frappe.delete_doc(DT.WORKBOOK, workbook, force=True, ignore_permissions=True)

    def setUp(self):
        super().setUp()
        self.delete_v3_output()
        self.result = migrate_dashboard(self.DASHBOARD)
        self.report = verify_migration(self.result)
        self.checks = {check.source: check for check in self.report.verifications}

    # -- the mechanism -----------------------------------------------------

    def test_v2s_stored_sql_runs_through_the_v3_backend_untouched(self):
        """The claim the whole module rests on, with no v2 code loaded."""
        answer = v2_answer(GROUPED_SQL, SITE_DB, dialect="mysql")

        # backticks, an alias with spaces, and a trailing space, all preserved
        self.assertEqual(list(answer.columns), ["Status", "Count of records "])
        self.assertGreater(len(answer), 0)

    # -- the verdicts ------------------------------------------------------

    def test_a_faithful_translation_verifies_as_the_same(self):
        check = self.checks[self.FAITHFUL]

        self.assertEqual(check.verdict, SAME, check.differences)
        self.assertEqual(check.check, TRANSLATION)
        self.assertEqual(check.v2_rows, check.v3_rows)

    def test_a_lost_filter_is_caught(self):
        """The deliberate mismatch: v2 filtered, the migrated query does not."""
        check = self.checks[self.WRONG]

        self.assertEqual(check.verdict, DIFFERENT)
        self.assertTrue(check.unexpected)
        self.assertIn(ROW_COUNT, kinds(check.differences))
        self.assertLess(check.v2_rows, check.v3_rows)

    def test_the_sql_floor_is_verified_but_only_against_itself(self):
        """v3 runs v2's own statement, so agreement says nothing about translation."""
        check = self.checks[self.NATIVE]

        self.assertEqual(check.kind, "sql")
        self.assertEqual(check.check, IDENTITY)
        self.assertEqual(check.verdict, SAME, check.differences)

    def test_a_query_store_query_cannot_be_run_and_says_why(self):
        check = self.checks[self.STORED]

        self.assertEqual(check.verdict, NOT_RUN)
        self.assertIn("Query Store", check.reason)
        self.assertIsNone(check.v2_rows)

    # -- the report --------------------------------------------------------

    def test_the_report_is_not_trustworthy_while_one_query_differs(self):
        self.assertFalse(self.report.trustworthy)
        self.assertEqual(self.report.counts[DIFFERENT], 1)
        self.assertEqual(self.report.counts[NOT_RUN], 1)

    def test_the_report_names_the_query_a_human_has_to_look_at(self):
        report = self.report.report

        self.assertIn(f"DIFFERENT {self.WRONG}", report)
        self.assertIn("! row_count: v2 returned", report)
        self.assertIn("identity check", report)
        self.assertIn(f"cap {self.report.row_cap} rows", report)
