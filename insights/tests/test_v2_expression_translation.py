"""A v2 expression carries meaning, not just syntax, so the translation has to hold it.

Most of v2's functions survive a rename. The ones that do not are where a migrator
quietly corrupts a number: `time_elapsed` counts in the opposite direction to
`date_diff`, `date_format` takes a granularity name where `format_date` takes a
strftime string, and a SQL fragment lifted out of its table reads a different column
if two joined tables share the name.
"""

import ast as pyast
from pathlib import Path

from frappe.tests import UnitTestCase

from insights.migrator.v2_expressions import (
    DIRECT_FUNCTIONS,
    GRANULARITY_FORMATS,
    GRANULARITY_PARTS,
    GRANULARITY_STARTS,
    RENAMED_FUNCTIONS,
    Outcome,
    TranslationError,
    split_trailing_alias,
    strip_table_qualifiers,
    translate,
)

FUNCTIONS_PY = (
    Path(__file__).parent.parent
    / "insights"
    / "doctype"
    / "insights_data_source_v3"
    / "ibis"
    / "functions.py"
)


def column(name, table="tabIssue"):
    return {"type": "Column", "value": {"table": table, "column": name}}


def string(value):
    return {"type": "String", "value": value}


def number(value):
    return {"type": "Number", "value": value}


def call(function, *arguments):
    return {"type": "CallExpression", "function": function, "arguments": list(arguments)}


def binary(operator, left, right):
    return {"type": "BinaryExpression", "operator": operator, "left": left, "right": right}


def logical(operator, *conditions):
    return {"type": "LogicalExpression", "operator": operator, "conditions": list(conditions)}


class TestLeavesAndOperators(UnitTestCase):
    def test_a_column_loses_its_table(self):
        self.assertEqual(translate(column("status")).expression, "status")

    def test_a_column_python_cannot_name_is_reached_through_the_query(self):
        self.assertEqual(translate(column("Total USD")).expression, 'q["Total USD"]')

    def test_a_column_a_v3_function_would_shadow_is_reached_through_the_query(self):
        # v3 binds its functions after the columns, so a bare `count` is the function
        self.assertEqual(translate(column("count")).expression, 'q["count"]')

    def test_equality_becomes_python_equality(self):
        translated = translate(binary("=", column("status"), string("Resolved")))
        self.assertEqual(translated.expression, '(status == "Resolved")')

    def test_the_logical_operators_become_the_ibis_ones(self):
        self.assertEqual(translate(binary("&&", column("a"), column("b"))).expression, "(a & b)")
        self.assertEqual(translate(binary("||", column("a"), column("b"))).expression, "(a | b)")

    def test_a_binary_expression_is_parenthesised(self):
        # ibis binds & tighter than ==, so `a == 1 & b == 2` would group the wrong way
        translated = translate(
            binary(
                "&&",
                binary("=", column("a"), number(1)),
                binary("=", column("b"), number(2)),
            )
        )
        self.assertEqual(translated.expression, "((a == 1) & (b == 2))")

    def test_a_logical_expression_joins_every_condition(self):
        translated = translate(
            logical(
                "||",
                binary("=", column("status"), string("Open")),
                binary("=", column("status"), string("Closed")),
            )
        )
        self.assertEqual(translated.expression, '((status == "Open") | (status == "Closed"))')

    def test_an_unknown_node_type_is_an_error(self):
        with self.assertRaises(TranslationError):
            translate({"type": "Regex", "value": ".*"})


class TestTheDirectMappings(UnitTestCase):
    def test_a_function_v3_spells_the_same_way_passes_through(self):
        translated = translate(call("sum", column("grand_total")))
        self.assertEqual(translated.expression, "sum(grand_total)")
        self.assertIs(translated.outcome, Outcome.TRANSLATED)

    def test_argument_order_is_preserved(self):
        translated = translate(call("replace", column("name"), string("a"), string("b")))
        self.assertEqual(translated.expression, 'replace(name, "a", "b")')

    def test_an_unmapped_function_is_an_error(self):
        with self.assertRaises(TranslationError):
            translate(call("regexp_like", column("name"), string("x")))

    def test_every_v3_name_the_translator_emits_exists(self):
        module = pyast.parse(FUNCTIONS_PY.read_text())
        defined = {node.name for node in module.body if isinstance(node, pyast.FunctionDef)}
        emitted = (
            set(DIRECT_FUNCTIONS)
            | set(RENAMED_FUNCTIONS.values())
            | set(GRANULARITY_STARTS.values())
            | set(GRANULARITY_PARTS.values())
            | {"date_diff", "time_diff", "format_date"}
        )
        self.assertEqual(emitted - defined, set())


class TestTheRenames(UnitTestCase):
    def test_membership_is_renamed(self):
        self.assertEqual(
            translate(call("in", column("status"), string("Open"))).expression,
            'is_in(status, "Open")',
        )
        self.assertEqual(
            translate(call("not_in", column("status"), string("Open"))).expression,
            'is_not_in(status, "Open")',
        )

    def test_timespan_becomes_within(self):
        translated = translate(call("timespan", column("creation"), string("Last 7 days")))
        self.assertEqual(translated.expression, 'within(creation, "Last 7 days")')

    def test_an_upper_case_aggregation_is_lowered(self):
        self.assertEqual(translate(call("MAX", column("amount"))).expression, "max(amount)")
        self.assertEqual(translate(call("SUM", column("amount"))).expression, "sum(amount)")


class TestBetweenKeepsItsLastDay(UnitTestCase):
    """v2 widened the end bound to 23:59:59; a plain rename would drop the last day."""

    def between(self, start, end, on="creation"):
        return translate(call("between", column(on), start, end)).expression

    def test_the_end_bound_is_widened_to_the_end_of_that_day(self):
        self.assertEqual(
            self.between(string("2024-07-01"), string("2024-07-31")),
            'is_between(creation, "2024-07-01 00:00:00", "2024-07-31 23:59:59")',
        )

    def test_the_start_bound_is_pinned_to_midnight(self):
        # v2 emitted both literals, so a row before midnight stays outside the range
        self.assertIn('"2024-07-01 00:00:00"', self.between(string("2024-07-01"), string("2024-07-31")))

    def test_a_bound_that_already_carries_a_time_is_still_reduced_to_its_day(self):
        # v2's getdate() discarded the time before re-applying 00:00:00 / 23:59:59
        self.assertEqual(
            self.between(string("2024-07-01 08:30:00"), string("2024-07-31 08:30:00")),
            'is_between(creation, "2024-07-01 00:00:00", "2024-07-31 23:59:59")',
        )

    def test_a_numeric_bound_is_refused_rather_than_widened(self):
        # v2 ran every bound through getdate(), which returns None for a number and
        # then raises on strftime - there is no numeric between to be faithful to
        with self.assertRaises(TranslationError):
            translate(call("between", column("age"), number(1), number(9)))

    def test_a_column_bound_is_refused_too(self):
        with self.assertRaises(TranslationError):
            translate(call("between", column("creation"), column("start"), column("end")))

    def test_a_string_that_is_not_a_date_is_refused(self):
        with self.assertRaises(TranslationError):
            translate(call("between", column("creation"), string("soon"), string("later")))


class TestTimeElapsedReorders(UnitTestCase):
    def test_the_unit_moves_last_and_the_arguments_swap(self):
        # v2 is MySQL TIMESTAMPDIFF, which returns b - a; v3 date_diff returns a - b
        translated = translate(call("time_elapsed", string("day"), column("creation"), column("resolution")))
        self.assertEqual(translated.expression, 'date_diff(resolution, creation, "day")')

    def test_a_sub_day_unit_goes_to_time_diff_instead(self):
        translated = translate(call("time_elapsed", string("SECOND"), column("start"), column("end")))
        self.assertEqual(translated.expression, 'time_diff(end, start, "second")')

    def test_a_unit_neither_function_takes_is_an_error(self):
        with self.assertRaises(TranslationError):
            translate(call("time_elapsed", string("fortnight"), column("a"), column("b")))


class TestDateFormatIsRewritten(UnitTestCase):
    def test_a_period_bucket_becomes_a_period_start_function(self):
        self.assertEqual(
            translate(call("date_format", column("creation"), string("Week"))).expression,
            "week_start(creation)",
        )
        self.assertEqual(
            translate(call("date_format", column("creation"), string("Mon"))).expression,
            "month_start(creation)",
        )

    def test_a_component_becomes_a_date_part_function(self):
        translated = translate(call("date_format", column("creation"), string("Hour of Day")))
        self.assertEqual(translated.expression, "hour(creation)")

    def test_a_bucket_with_no_v3_function_keeps_the_v2_string(self):
        # v2 returned a formatted string for these, so format_date reproduces it
        translated = translate(call("date_format", column("creation"), string("Minute")))
        self.assertEqual(translated.expression, 'format_date(creation, "%Y-%m-%d %H:%M")')

    def test_the_mysql_minute_specifier_is_translated_to_strftime(self):
        self.assertIn("%H:%M", GRANULARITY_FORMATS["Minute"])
        self.assertNotIn("%i", GRANULARITY_FORMATS["Minute"])

    def test_an_unknown_granularity_is_an_error(self):
        with self.assertRaises(TranslationError):
            translate(call("date_format", column("creation"), string("Fortnight")))


class TestCaseKeepsItsVariadicShape(UnitTestCase):
    def test_a_single_branch_with_a_default(self):
        translated = translate(
            call(
                "case",
                binary("=", column("status"), string("Open")),
                string("Active"),
                string("Done"),
            )
        )
        self.assertEqual(translated.expression, 'case((status == "Open"), "Active", "Done")')

    def test_several_branches_stay_in_order(self):
        translated = translate(
            call(
                "case",
                binary(">", column("age"), number(30)),
                string("Above 30"),
                binary(">", column("age"), number(20)),
                string("Above 20"),
                string("Young"),
            )
        )
        self.assertEqual(
            translated.expression,
            'case((age > 30), "Above 30", (age > 20), "Above 20", "Young")',
        )


class TestNestedExpressions(UnitTestCase):
    def test_a_call_inside_a_call_inside_an_operator(self):
        translated = translate(
            call(
                "abs",
                call(
                    "sum_if",
                    binary("=", column("root_type"), string("Income")),
                    binary("-", column("credit"), column("debit")),
                ),
            )
        )
        self.assertEqual(
            translated.expression,
            'abs(sum_if((root_type == "Income"), (credit - debit)))',
        )

    def test_a_rewrite_nested_under_a_direct_function(self):
        translated = translate(call("count_if", call("date_format", column("creation"), string("Year"))))
        self.assertEqual(translated.expression, "count_if(year_start(creation))")

    def test_the_result_is_valid_python(self):
        translated = translate(
            logical(
                "&&",
                call("is_set", column("owner")),
                binary("<", call("today"), column("due_date")),
            )
        )
        pyast.parse(translated.expression, mode="eval")


class TestSqlBecomesAFragment(UnitTestCase):
    def body(self, sql):
        return translate(call("sql", string(sql)))

    def test_the_expression_refers_to_the_fragment_column(self):
        translated = self.body("`tabIssue`.`status`")
        self.assertIs(translated.outcome, Outcome.FRAGMENT)
        self.assertEqual(len(translated.fragments), 1)
        self.assertEqual(translated.expression, translated.fragments[0].name)

    def test_a_fragment_nested_in_a_larger_expression(self):
        translated = translate(binary(">", call("sql", string("`tabIssue`.`age`")), number(3)))
        fragment = translated.fragments[0]
        self.assertEqual(translated.expression, f"({fragment.name} > 3)")
        self.assertEqual(fragment.sql, "`age`")

    def test_each_fragment_gets_its_own_name(self):
        translated = translate(
            binary(
                "+",
                call("sql", string("`tabIssue`.`a`")),
                call("sql", string("`tabIssue`.`b`")),
            )
        )
        names = [fragment.name for fragment in translated.fragments]
        self.assertEqual(len(set(names)), 2)

    def test_a_trailing_alias_is_lifted_out_as_the_label(self):
        # sql_column appends its own alias, so a second one is a syntax error
        translated = self.body("lag(`tabX`.`amount`, 1) AS `Prev`")
        fragment = translated.fragments[0]
        self.assertEqual(fragment.sql, "lag(`amount`, 1)")
        self.assertEqual(fragment.label, "Prev")


class TestQualifierStripping(UnitTestCase):
    def stripped(self, sql):
        return strip_table_qualifiers(sql)[0]

    def test_a_backtick_qualified_column_loses_its_table(self):
        self.assertEqual(self.stripped("`tabIssue`.`status`"), "`status`")

    def test_an_unquoted_column_is_quoted_on_the_way_out(self):
        self.assertEqual(self.stripped("`tabIssue`.status"), "`status`")

    def test_whitespace_around_the_expression_survives(self):
        self.assertEqual(
            self.stripped("EXTRACT(HOUR FROM `tabIncident`.`creation`)"),
            "EXTRACT(HOUR FROM `creation`)",
        )

    def test_a_dot_inside_a_string_literal_is_not_a_qualifier(self):
        sql = "date(strftime('%Y-%m-%d', `tabX`.`creation`))"
        self.assertEqual(self.stripped(sql), "date(strftime('%Y-%m-%d', `creation`))")

    def test_the_tables_and_columns_are_reported(self):
        sql = "lag(`QRY-1`.`Total USD`, 1) over (partition by `QRY-1`.`Team`)"
        stripped, tables, columns = strip_table_qualifiers(sql)
        self.assertEqual(stripped, "lag(`Total USD`, 1) over (partition by `Team`)")
        self.assertEqual(tables, ("QRY-1",))
        self.assertEqual(columns, ("Total USD", "Team"))

    def test_an_unqualified_fragment_is_left_alone(self):
        self.assertEqual(self.stripped("'all'"), "'all'")

    def test_a_cast_is_not_mistaken_for_an_alias(self):
        self.assertEqual(split_trailing_alias("cast(`x` as INT)"), ("cast(`x` as INT)", None))

    def test_a_quoted_alias_of_any_quote_style_is_found(self):
        self.assertEqual(split_trailing_alias("`x` - `y` as 'Diff'"), ("`x` - `y`", "Diff"))
        self.assertEqual(split_trailing_alias("`x` AS `Diff`"), ("`x`", "Diff"))


class TestCollisionDetection(UnitTestCase):
    def fragment(self, table_columns):
        translated = translate(call("sql", string("`tabIssue`.`status`")), table_columns=table_columns)
        return translated.fragments[0]

    def test_a_name_only_one_table_owns_is_unambiguous(self):
        fragment = self.fragment({"tabIssue": ["status", "owner"], "tabUser": ["email", "full_name"]})
        self.assertEqual(fragment.ambiguous_columns, ())
        self.assertFalse(fragment.is_ambiguous)

    def test_a_name_two_joined_tables_share_is_flagged(self):
        fragment = self.fragment({"tabIssue": ["status", "owner"], "tabTask": ["status", "subject"]})
        self.assertEqual(fragment.ambiguous_columns, ("status",))
        self.assertTrue(fragment.is_ambiguous)

    def test_nothing_is_flagged_without_a_schema_to_check_against(self):
        # no table_columns means no claim either way, not a claim of safety
        self.assertEqual(self.fragment({}).ambiguous_columns, ())

    def test_a_fragment_reading_two_tables_is_ambiguous_by_itself(self):
        translated = translate(call("sql", string("`tabA`.`x` + `tabB`.`y`")))
        fragment = translated.fragments[0]
        self.assertEqual(fragment.tables, ("tabA", "tabB"))
        self.assertTrue(fragment.is_ambiguous)


class TestDescendantsHasNoQueryLevelHome(UnitTestCase):
    def tree_call(self, function="descendants_and_self"):
        return call(function, string("India"), string("tabTerritory"), column("territory"))

    def test_the_outcome_is_the_compiled_sql_fallback(self):
        translated = translate(self.tree_call())
        self.assertIs(translated.outcome, Outcome.COMPILED_SQL)

    def test_no_expression_comes_back(self):
        # a partial expression would look translatable; the caller must not use one
        self.assertIsNone(translate(self.tree_call()).expression)

    def test_the_blocker_names_the_function_and_says_why(self):
        blocker = translate(self.tree_call()).blockers[0]
        self.assertEqual(blocker.function, "descendants_and_self")
        self.assertIn("subquery", blocker.reason)

    def test_both_tree_functions_block(self):
        self.assertIs(translate(self.tree_call("descendants")).outcome, Outcome.COMPILED_SQL)

    def test_a_blocker_nested_deep_in_a_tree_still_blocks(self):
        translated = translate(call("case", self.tree_call(), string("Inside"), string("Outside")))
        self.assertIs(translated.outcome, Outcome.COMPILED_SQL)
        self.assertIsNone(translated.expression)

    def test_a_blocker_outranks_a_fragment(self):
        translated = translate(logical("&&", call("sql", string("`tabX`.`a`")), self.tree_call()))
        self.assertIs(translated.outcome, Outcome.COMPILED_SQL)
        self.assertTrue(translated.fragments)
