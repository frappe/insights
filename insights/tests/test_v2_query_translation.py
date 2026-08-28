"""A v2 query is one column list; a v3 query is an ordered pipeline.

The translation has to recover what v2 only expressed by accident: which
columns it grouped by (`is_measure`, not the word "group by"), that every v2
`count` was really `COUNT(*)`, and that a derived column has to exist before
anything groups by it. Where the order is wrong the query still runs and
returns different numbers, so the ordering has a test of its own.
"""

import json

from frappe.tests import UnitTestCase

from insights.migrator.v2_queries import translate_query


def v2_query(json_spec=None, **overrides):
    spec = {
        "table": {"table": "tabIssue", "label": "Issue"},
        "joins": [],
        "columns": [],
        "calculations": [],
        "filters": [],
        "measures": [],
        "dimensions": [],
        "orders": [],
        "limit": None,
    }
    spec.update(json_spec or {})
    query = {
        "name": "QRY-0001",
        "title": "Issues",
        "data_source": "frappe.io",
        "json": json.dumps(spec),
        "sql": "SELECT 1",
        "script": None,
        "is_native_query": 0,
        "is_assisted_query": 1,
        "is_script_query": 0,
        "transforms": [],
    }
    query.update(overrides)
    return query


def column(name, **overrides):
    entry = {
        "table": "tabIssue",
        "column": name,
        "label": name,
        "alias": name,
        "type": "String",
        "aggregation": "group by",
        "granularity": "",
        "order": None,
        "expression": {},
    }
    entry.update(overrides)
    return entry


def rule(name, operator, value):
    return {
        "column": {"table": "tabIssue", "column": name},
        "operator": {"value": operator, "label": operator},
        "value": {"value": value, "label": str(value)},
        "expression": {},
    }


def ast_column(name, table="tabIssue"):
    return {"type": "Column", "value": {"table": table, "column": name}}


def ast_call(function, *arguments):
    return {"type": "CallExpression", "function": function, "arguments": list(arguments)}


def ast_string(value):
    return {"type": "String", "value": value}


def expression_column(name, ast, raw="expr", **overrides):
    return column(
        name,
        column=None,
        table=None,
        expression={"raw": raw, "ast": ast},
        **overrides,
    )


def translate(query, **kwargs):
    return translate_query(query, **kwargs)


def operation_types(result):
    return [operation["type"] for operation in result.operations]


def find(result, operation_type):
    return next(op for op in result.operations if op["type"] == operation_type)


def gap_kinds(result):
    return {gap.kind for gap in result.gaps}


class TestSourceAndReferences(UnitTestCase):
    def test_a_table_becomes_a_source(self):
        result = translate(v2_query())
        self.assertEqual(result.kind, "builder")
        self.assertEqual(
            find(result, "source")["table"],
            {"type": "table", "data_source": "frappe.io", "table_name": "tabIssue"},
        )

    def test_a_table_that_names_a_query_becomes_a_query_reference(self):
        query = v2_query({"table": {"table": "QRY-0220"}}, data_source="Query Store")
        result = translate(query, query_map={"QRY-0220": "abc123"}, workbook="wb-1")
        self.assertEqual(
            find(result, "source")["table"],
            {"type": "query", "workbook": "wb-1", "query_name": "abc123"},
        )
        self.assertEqual(result.references, ("QRY-0220",))

    def test_a_query_store_table_with_no_v3_query_is_reported(self):
        query = v2_query({"table": {"table": "QRY-0220"}}, data_source="Query Store")
        result = translate(query)
        self.assertIn("unresolved_query_reference", gap_kinds(result))

    def test_a_query_with_no_table_produced_no_sql_in_v2_either(self):
        result = translate(v2_query({"table": {}}))
        self.assertEqual(result.kind, "none")
        self.assertEqual(result.operations, [])
        self.assertIn("no_source_table", gap_kinds(result))


class TestAggregations(UnitTestCase):
    def measure(self, aggregation, data_type="Integer", name="value"):
        query = v2_query(
            {
                "columns": [
                    column("status"),
                    column(name, aggregation=aggregation, type=data_type),
                ]
            }
        )
        return find(translate(query), "summarize")["measures"][0]

    def test_a_sum_carries_its_column(self):
        self.assertEqual(
            self.measure("sum", "Decimal", "amount"),
            {
                "measure_name": "amount",
                "column_name": "amount",
                "aggregation": "sum",
                "data_type": "Decimal",
            },
        )

    def test_avg_min_and_max_keep_their_names(self):
        for aggregation in ("avg", "min", "max"):
            self.assertEqual(self.measure(aggregation, "Decimal", "amount")["aggregation"], aggregation)

    def test_distinct_count_is_spelled_count_distinct_in_v3(self):
        self.assertEqual(self.measure("distinct_count", "String", "owner")["aggregation"], "count_distinct")

    def test_a_v2_count_counts_rows_whatever_column_it_named(self):
        # `Aggregations.apply` compiled every count to COUNT(*). Counting the
        # named column instead would drop every null in it.
        self.assertEqual(
            self.measure("count", "Integer", "owner"),
            {
                "measure_name": "owner",
                "column_name": "count",
                "aggregation": "count",
                "data_type": "Integer",
            },
        )

    def test_a_cumulative_count_aggregates_and_then_runs_a_window(self):
        query = v2_query(
            {
                "columns": [
                    column("status"),
                    column("total", aggregation="cumulative count", type="Integer"),
                ]
            }
        )
        result = translate(query)
        self.assertEqual(find(result, "summarize")["measures"][0]["aggregation"], "count")
        mutate = find(result, "mutate")
        self.assertIn("cumulative_window", mutate["expression"]["expression"])
        self.assertEqual(mutate["new_name"], "total")

    def test_a_cumulative_sum_runs_its_window_after_the_summarize(self):
        query = v2_query(
            {
                "columns": [
                    column("status"),
                    column("amount", aggregation="cumulative sum", type="Decimal"),
                ]
            }
        )
        types = operation_types(translate(query))
        self.assertLess(types.index("summarize"), types.index("mutate"))

    def test_a_query_with_no_aggregating_column_selects_instead_of_grouping(self):
        # 762 of 1833 production assisted queries are in this shape: v2 built no
        # GROUP BY at all, because no column was a measure.
        query = v2_query({"columns": [column("status"), column("owner")]})
        types = operation_types(translate(query))
        self.assertNotIn("summarize", types)
        self.assertIn("select", types)

    def test_a_numeric_column_marked_group_by_was_never_grouped_in_v2(self):
        # `Column.is_measure` is "numeric or aggregating", so v2 put this in
        # SELECT and left it out of GROUP BY. v3 has to group by it.
        query = v2_query(
            {
                "columns": [
                    column("amount", type="Decimal"),
                    column("total", aggregation="sum", type="Decimal"),
                ]
            }
        )
        result = translate(query)
        summarize = find(result, "summarize")
        self.assertEqual([d["column_name"] for d in summarize["dimensions"]], ["amount"])
        self.assertIn("grouped_loose_column", gap_kinds(result))


class TestGranularity(UnitTestCase):
    def dimension(self, granularity, data_type="Datetime"):
        query = v2_query(
            {
                "columns": [
                    column("creation", type=data_type, granularity=granularity),
                    column("total", aggregation="count", type="Integer"),
                ]
            }
        )
        return translate(query)

    def test_a_bucket_v3_knows_rides_on_the_dimension(self):
        for v2_name, v3_name in (
            ("Minute", "minute"),
            ("Hour", "hour"),
            ("Day", "day"),
            ("Day Short", "day"),
            ("Week", "week"),
            ("Month", "month"),
            ("Mon", "month"),
            ("Quarter", "quarter"),
            ("Year", "year"),
        ):
            result = self.dimension(v2_name)
            dimension = find(result, "summarize")["dimensions"][0]
            self.assertEqual(dimension["granularity"], v3_name, v2_name)

    def test_a_bucket_v3_has_no_granularity_for_is_computed_first(self):
        result = self.dimension("Month of Year")
        types = operation_types(result)
        self.assertLess(types.index("mutate"), types.index("summarize"))
        self.assertEqual(find(result, "mutate")["expression"]["expression"], "month(creation)")
        self.assertIn("granularity_part_type", gap_kinds(result))

    def test_v2_ignored_a_granularity_on_a_column_that_is_not_a_date(self):
        result = self.dimension("Month", data_type="String")
        self.assertNotIn("granularity", find(result, "summarize")["dimensions"][0])
        self.assertIn("ignored_granularity", gap_kinds(result))

    def test_without_a_summarize_a_bucket_has_to_be_computed(self):
        query = v2_query({"columns": [column("creation", type="Datetime", granularity="Month")]})
        result = translate(query)
        self.assertEqual(find(result, "mutate")["expression"]["expression"], "month_start(creation)")


class TestJoins(UnitTestCase):
    def join(self, join_type, right="tabUser"):
        return {
            "left_table": {"table": "tabIssue"},
            "right_table": {"table": right},
            "join_type": {"value": join_type, "label": join_type},
            "left_column": {"column": "owner"},
            "right_column": {"column": "name"},
        }

    def test_each_join_type_carries_over(self):
        for join_type in ("inner", "left", "right", "full"):
            result = translate(v2_query({"joins": [self.join(join_type)]}))
            operation = find(result, "join")
            self.assertEqual(operation["join_type"], join_type)
            self.assertEqual(operation["join_condition"]["left_column"]["column_name"], "owner")
            self.assertEqual(operation["join_condition"]["right_column"]["column_name"], "name")

    def test_a_join_onto_a_query_carries_the_reference(self):
        result = translate(
            v2_query({"joins": [self.join("inner", right="QRY-0220")]}),
            query_map={"QRY-0220": "abc123"},
            workbook="wb-1",
        )
        self.assertEqual(find(result, "join")["table"]["type"], "query")
        self.assertEqual(result.references, ("QRY-0220",))

    def test_a_join_missing_a_column_is_dropped_the_way_v2_dropped_it(self):
        broken = self.join("inner")
        broken["right_column"] = {}
        result = translate(v2_query({"joins": [broken]}))
        self.assertNotIn("join", operation_types(result))
        self.assertIn("invalid_join", gap_kinds(result))

    def test_the_join_comes_before_the_filter(self):
        query = v2_query(
            {"joins": [self.join("left")], "filters": [rule("status", "=", "Open")]},
        )
        types = operation_types(translate(query))
        self.assertLess(types.index("join"), types.index("filter_group"))


class TestFilters(UnitTestCase):
    def filters(self, *entries):
        result = translate(v2_query({"filters": list(entries)}))
        return result, find(result, "filter_group")["filters"] if "filter_group" in operation_types(
            result
        ) else []

    def test_filters_are_combined_with_and_because_v2_had_no_or(self):
        _, filters = self.filters(rule("status", "=", "Open"), rule("owner", "!=", "x"))
        result = translate(v2_query({"filters": [rule("status", "=", "Open")]}))
        self.assertEqual(find(result, "filter_group")["logical_operator"], "And")
        self.assertEqual(len(filters), 2)

    def test_a_direct_operator_carries_its_value(self):
        _, filters = self.filters(rule("status", "=", "Open"))
        self.assertEqual(
            filters[0],
            {"column": {"type": "column", "column_name": "status"}, "operator": "=", "value": "Open"},
        )

    def test_timespan_is_spelled_within_and_keeps_its_words(self):
        _, filters = self.filters(rule("creation", "timespan", "Current Year"))
        self.assertEqual(filters[0]["operator"], "within")
        self.assertEqual(filters[0]["value"], "Current Year")

    def test_an_in_filter_unwraps_its_label_value_pairs(self):
        _, filters = self.filters(
            rule("status", "in", [{"label": "Open", "value": "Open"}, {"label": "Closed", "value": "Closed"}])
        )
        self.assertEqual(filters[0]["value"], ["Open", "Closed"])

    def test_a_between_range_keeps_the_last_day(self):
        # v2 ran both bounds through `add_start_and_end_time`, which widened the
        # end to 23:59:59. v3 only widens a bound with no time in it.
        _, filters = self.filters(rule("creation", "between", "2024-01-01,2024-06-30"))
        self.assertEqual(filters[0]["value"], ["2024-01-01 00:00:00", "2024-06-30 23:59:59"])

    def test_a_between_bound_that_is_not_a_date_was_broken_in_v2(self):
        result, _ = self.filters(rule("creation", "between", "yesterday,today"))
        self.assertIn("broken_filter", gap_kinds(result))

    def test_the_is_operator_reads_its_value_as_the_operator(self):
        _, filters = self.filters(rule("owner", "is", "set"))
        self.assertEqual(filters[0]["operator"], "is_set")
        _, filters = self.filters(rule("owner", "is", "not set"))
        self.assertEqual(filters[0]["operator"], "is_not_set")

    def test_is_set_needs_no_value_and_v2_ignored_the_one_it_had(self):
        _, filters = self.filters(rule("owner", "is_set", None))
        self.assertEqual(
            filters[0],
            {"column": {"type": "column", "column_name": "owner"}, "operator": "is_set", "value": None},
        )

    def test_a_falsy_value_was_dropped_by_v2_including_a_real_zero(self):
        # `LabelValue.is_valid` is `bool(value)`, so `amount = 0` never filtered.
        result, filters = self.filters(rule("amount", "=", 0))
        self.assertEqual(filters, [])
        self.assertIn("dropped_filter", gap_kinds(result))

    def test_a_filter_with_no_operator_is_dropped(self):
        entry = rule("status", "=", "Open")
        entry["operator"] = {}
        result, filters = self.filters(entry)
        self.assertEqual(filters, [])
        self.assertIn("dropped_filter", gap_kinds(result))

    def test_an_expression_filter_becomes_a_filter_expression(self):
        entry = {
            "column": {},
            "operator": {},
            "value": {},
            "expression": {"raw": "is_set(status)", "ast": ast_call("is_set", ast_column("status"))},
        }
        _, filters = self.filters(entry)
        self.assertEqual(filters[0], {"expression": {"type": "expression", "expression": "is_set(status)"}})


class TestExpressionColumns(UnitTestCase):
    def test_a_translatable_expression_becomes_a_mutate(self):
        query = v2_query({"columns": [expression_column("Upper", ast_call("upper", ast_column("status")))]})
        result = translate(query)
        self.assertEqual(
            find(result, "mutate"),
            {
                "type": "mutate",
                "new_name": "Upper",
                "data_type": "Auto",
                "expression": {"type": "expression", "expression": "upper(status)"},
            },
        )

    def test_a_sql_fragment_becomes_a_sql_column_named_by_its_alias(self):
        ast = ast_call("sql", ast_string("`tabIssue`.`status` + 1 AS `Bumped`"))
        result = translate(v2_query({"columns": [expression_column("Bumped", ast)]}))
        operation = find(result, "sql_column")
        self.assertEqual(operation["new_name"], "Bumped")
        self.assertEqual(operation["fragment"], "`status` + 1")
        # sqlglot rejects v2's backtick identifiers without the source dialect.
        self.assertEqual(operation["data_source"], "frappe.io")

    def test_a_fragment_inside_a_larger_expression_keeps_its_generated_name(self):
        ast = ast_call("upper", ast_call("sql", ast_string("`tabIssue`.`status`")))
        result = translate(v2_query({"columns": [expression_column("Loud", ast)]}))
        types = operation_types(result)
        self.assertLess(types.index("sql_column"), types.index("mutate"))
        self.assertEqual(
            find(result, "mutate")["expression"]["expression"],
            f"upper({find(result, 'sql_column')['new_name']})",
        )

    def test_an_aggregating_expression_belongs_in_the_summarize(self):
        ast = ast_call("sum", ast_column("amount"))
        query = v2_query({"columns": [column("status"), expression_column("Total", ast, type="Decimal")]})
        result = translate(query)
        self.assertEqual(
            find(result, "summarize")["measures"][0],
            {
                "measure_name": "Total",
                "expression": {"type": "expression", "expression": "sum(amount)"},
                "data_type": "Decimal",
            },
        )

    def test_an_expression_that_needs_a_subquery_drops_to_the_whole_query_sql(self):
        ast = ast_call("descendants", ast_string("India"), ast_string("Territory"), ast_column("territory"))
        result = translate(v2_query({"columns": [expression_column("Under India", ast)]}))
        self.assertEqual(result.kind, "sql")
        self.assertEqual(find(result, "sql")["raw_sql"], "SELECT 1")
        self.assertTrue(result.use_live_connection)
        self.assertIn("expression_needs_sql", gap_kinds(result))

    def test_an_expression_that_was_broken_in_v2_emits_no_query_at_all(self):
        # The compiled SQL cannot rescue it: v2 never generated any.
        ast = ast_call("time_elapsed", ast_string("fortnight"), ast_column("a"), ast_column("b"))
        result = translate(v2_query({"columns": [expression_column("Elapsed", ast)]}))
        self.assertEqual(result.kind, "none")
        self.assertEqual(result.operations, [])
        self.assertIn("broken_in_v2", gap_kinds(result))


class TestQueryTypes(UnitTestCase):
    def test_a_native_query_is_one_sql_operation(self):
        query = v2_query(is_native_query=1, is_assisted_query=0, sql="SELECT * FROM `tabIssue`;")
        result = translate(query)
        self.assertEqual(result.kind, "sql")
        self.assertEqual(
            result.operations,
            [{"type": "sql", "raw_sql": "SELECT * FROM `tabIssue`", "data_source": "frappe.io"}],
        )
        self.assertTrue(result.use_live_connection)

    def test_native_wins_over_assisted_because_v2_read_it_first(self):
        # 4 production rows set both flags, and `SQLQueryBuilder.build` returns
        # the native SQL before it ever looks at the assisted json.
        query = v2_query({"columns": [column("status")]}, is_native_query=1, is_assisted_query=1)
        self.assertEqual(translate(query).kind, "sql")

    def test_a_script_query_is_one_code_operation(self):
        query = v2_query(is_assisted_query=0, is_script_query=1, script="results = []")
        result = translate(query)
        self.assertEqual(result.kind, "code")
        self.assertEqual(result.operations, [{"type": "code", "code": "results = []"}])
        self.assertIn("script_result_shape", gap_kinds(result))

    def test_a_legacy_query_has_no_structure_to_rebuild(self):
        query = v2_query(is_assisted_query=0, sql="SELECT 2")
        result = translate(query)
        self.assertEqual(result.kind, "sql")
        self.assertIn("legacy_query", gap_kinds(result))

    def test_a_query_with_no_stored_sql_has_no_floor_to_fall_to(self):
        query = v2_query(is_native_query=1, is_assisted_query=0, sql=None)
        result = translate(query)
        self.assertEqual(result.kind, "none")
        self.assertIn("no_compiled_sql", gap_kinds(result))


class TestTransforms(UnitTestCase):
    def pivoted(self, options):
        query = v2_query(
            {
                "columns": [
                    column("Creation", type="Datetime"),
                    column("Plan"),
                    column("Amount", aggregation="sum", type="Decimal"),
                ]
            },
            transforms=[{"type": "Pivot", "options": json.dumps(options)}],
        )
        return translate(query)

    def test_a_pivot_becomes_pivot_wider(self):
        result = self.pivoted({"index": "Creation", "column": "Plan", "value": "Amount"})
        pivot = find(result, "pivot_wider")
        self.assertEqual(pivot["rows"][0]["column_name"], "Creation")
        self.assertEqual(pivot["columns"][0]["column_name"], "Plan")
        self.assertEqual(pivot["values"][0]["aggregation"], "sum")

    def test_a_pivot_over_a_column_the_query_does_not_produce_is_dropped(self):
        result = self.pivoted({"index": "Creation", "column": "Region", "value": "Amount"})
        self.assertNotIn("pivot_wider", operation_types(result))
        self.assertIn("dropped_transform", gap_kinds(result))

    def test_a_cumulative_sum_transform_becomes_a_window(self):
        query = v2_query(
            {"columns": [column("status"), column("total", aggregation="sum", type="Decimal")]},
            transforms=[{"type": "CumulativeSum", "options": json.dumps({"column": "total"})}],
        )
        result = translate(query)
        mutate = find(result, "mutate")
        self.assertEqual(mutate["new_name"], "total")
        self.assertEqual(
            mutate["expression"]["expression"],
            "total.sum().over(ibis.cumulative_window(order_by=status))",
        )

    def test_a_running_total_climbs_the_rows_in_the_order_they_are_returned(self):
        # v2 ran `cumsum` down the fetched rows, so a descending sort has to
        # make a descending window or the total runs the wrong way.
        query = v2_query(
            {
                "columns": [
                    column("status", order="desc"),
                    column("total", aggregation="cumulative sum", type="Decimal"),
                ]
            }
        )
        self.assertIn("desc(status)", find(translate(query), "mutate")["expression"]["expression"])

    def test_transpose_has_no_v3_form_and_is_reported_rather_than_faked(self):
        query = v2_query(
            {"columns": [column("status")]},
            transforms=[{"type": "Transpose", "options": json.dumps({"index_column": "status"})}],
        )
        result = translate(query)
        self.assertEqual(result.kind, "builder")
        self.assertNotIn("pivot_wider", operation_types(result))
        self.assertIn("unsupported_transform", gap_kinds(result))

    def test_a_pivot_hides_a_cumulative_sum_the_way_v2_hid_it(self):
        # `apply_transforms` returns on the first Pivot, so the cumulative sums
        # below it never ran.
        query = v2_query(
            {"columns": [column("Plan"), column("Amount", aggregation="sum", type="Decimal")]},
            transforms=[
                {
                    "type": "Pivot",
                    "options": json.dumps({"index": "Plan", "column": "Plan", "value": "Amount"}),
                },
                {"type": "CumulativeSum", "options": json.dumps({"column": "Amount"})},
            ],
        )
        types = operation_types(translate(query))
        self.assertIn("pivot_wider", types)
        self.assertNotIn("mutate", types)


class TestOperationOrder(UnitTestCase):
    """Order is the correctness constraint: a wrong one still runs, and lies."""

    def full_query(self):
        return v2_query(
            {
                "joins": [
                    {
                        "left_table": {"table": "tabIssue"},
                        "right_table": {"table": "tabUser"},
                        "join_type": {"value": "left"},
                        "left_column": {"column": "owner"},
                        "right_column": {"column": "name"},
                    }
                ],
                "filters": [rule("status", "=", "Open")],
                "columns": [
                    expression_column(
                        "Loud", ast_call("upper", ast_call("sql", ast_string("`tabIssue`.`status`")))
                    ),
                    column("creation", type="Datetime", granularity="Month of Year"),
                    column("total", aggregation="sum", type="Decimal", order="desc"),
                ],
                "limit": 100,
            },
            transforms=[{"type": "CumulativeSum", "options": json.dumps({"column": "total"})}],
        )

    def test_the_whole_pipeline_is_in_the_one_order_that_is_correct(self):
        types = operation_types(translate(self.full_query()))
        self.assertEqual(
            types,
            [
                "source",
                "join",
                "filter_group",
                "sql_column",
                "mutate",
                "mutate",
                "summarize",
                "order_by",
                "limit",
                "mutate",
            ],
        )

    def test_every_derived_column_exists_before_the_summarize_groups_by_it(self):
        result = translate(self.full_query())
        types = operation_types(result)
        summarize_at = types.index("summarize")
        produced = set()
        for operation in result.operations[:summarize_at]:
            if operation["type"] in ("mutate", "sql_column"):
                produced.add(operation["new_name"])

        summarize = result.operations[summarize_at]
        derived = {"Loud", "creation"}
        grouped = {dimension["column_name"] for dimension in summarize["dimensions"]}
        self.assertTrue(derived <= produced)
        self.assertTrue(derived <= grouped)

    def test_a_sql_column_precedes_the_expression_that_reads_it(self):
        result = translate(self.full_query())
        sql_column = find(result, "sql_column")
        mutate = next(op for op in result.operations if op["type"] == "mutate")
        self.assertLess(
            result.operations.index(sql_column),
            result.operations.index(mutate),
        )
        self.assertIn(sql_column["new_name"], mutate["expression"]["expression"])

    def test_the_sort_comes_after_the_grouping_that_names_its_column(self):
        result = translate(self.full_query())
        types = operation_types(result)
        self.assertLess(types.index("summarize"), types.index("order_by"))
        self.assertLess(types.index("order_by"), types.index("limit"))
        self.assertEqual(find(result, "order_by")["column"]["column_name"], "total")

    def test_the_running_total_runs_after_the_limit_the_way_v2_ran_it(self):
        # v2 fetched, then ran `cumsum` in pandas over the fetched rows.
        result = translate(self.full_query())
        types = operation_types(result)
        self.assertLess(types.index("limit"), len(types) - 1)
        self.assertEqual(types[-1], "mutate")
        self.assertEqual(result.operations[-1]["new_name"], "total")


class TestLegacyColumnLists(UnitTestCase):
    def test_measures_and_dimensions_never_reached_v2s_sql(self):
        # `sql_builder.process_columns` reads `columns` alone. A column that
        # lives only in `measures` was never selected.
        query = v2_query(
            {
                "columns": [column("status")],
                "measures": [column("amount", aggregation="sum", type="Decimal")],
            }
        )
        result = translate(query)
        self.assertEqual(operation_types(result), ["source", "select"])
        self.assertIn("legacy_column_list", gap_kinds(result))

    def test_calculations_is_read_by_nothing_in_v2(self):
        query = v2_query({"columns": [column("status")], "calculations": [column("x")]})
        self.assertIn("legacy_column_list", gap_kinds(translate(query)))


class TestProjection(UnitTestCase):
    def test_an_aliased_column_is_renamed_before_it_is_selected(self):
        query = v2_query({"columns": [column("status", alias="Issue Status", label="Issue Status")]})
        result = translate(query)
        self.assertEqual(
            find(result, "rename"),
            {
                "type": "rename",
                "column": {"type": "column", "column_name": "status"},
                "new_name": "Issue Status",
            },
        )
        self.assertEqual(find(result, "select")["column_names"], ["Issue Status"])

    def test_a_limit_carries_over(self):
        query = v2_query({"columns": [column("status")], "limit": 25})
        self.assertEqual(find(translate(query), "limit"), {"type": "limit", "limit": 25})

    def test_no_limit_means_no_limit_operation(self):
        query = v2_query({"columns": [column("status")], "limit": None})
        self.assertNotIn("limit", operation_types(translate(query)))
