import os
import re
import unittest
from datetime import datetime
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import patch

import frappe
import ibis
import pandas as pd
from ibis.backends.clickhouse import Backend as ClickHouseBackend
from ibis.backends.postgres import Backend as PostgresBackend
from ibis.backends.sql.compilers.bigquery import BigQueryCompiler
from ibis.backends.sql.compilers.clickhouse import ClickHouseCompiler
from ibis.backends.sql.compilers.duckdb import DuckDBCompiler

import insights
from insights.exceptions import QueryRefused
from insights.insights.doctype.insights_chart_v3.chart_drill import _bucket_filters
from insights.insights.doctype.insights_chart_v3.chart_query import (
    derive_operations,
    sparkline_operations,
)
from insights.insights.doctype.insights_data_source_v3.connectors.bigquery import get_bigquery_connection
from insights.insights.doctype.insights_data_source_v3.connectors.clickhouse import get_clickhouse_connection
from insights.insights.doctype.insights_data_source_v3.connectors.duckdb import connect_duckdb
from insights.insights.doctype.insights_data_source_v3.connectors.postgresql import get_postgres_connection
from insights.insights.doctype.insights_data_source_v3.ibis.functions import (
    date_diff,
    percentage_change,
    previous_period_value,
)
from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder
from insights.tests.base import FakeDataSource, InsightsIntegrationTestCase
from insights.utils import deep_convert_dict_to_dict as _dict


class IbisQueryBuilderTestCase(InsightsIntegrationTestCase):
    def make_query_doc(self, operations):
        return frappe._dict(
            name=self.__class__.__name__,
            title=self.__class__.__name__,
            use_live_connection=0,
            operations=frappe.as_json(operations),
        )

    def build_query(self, operations):
        return IbisQueryBuilder(self.make_query_doc(operations)).build()


class TestIbisQueryBuilderGranularity(IbisQueryBuilderTestCase):
    def make_time_source_operations(self):
        return [
            {
                "type": "code",
                "code": """
results = [
    {"posting_time": "09:15:42.123", "label": "alpha"},
    {"posting_time": "09:15:42.987", "label": "beta"},
    {"posting_time": "14:33:19.111", "label": "gamma"},
]
""",
            },
            {
                "type": "cast",
                "column": {"type": "column", "column_name": "posting_time"},
                "data_type": "Time",
            },
        ]

    # @feature query.summarize-grain
    def test_summary_query_groups_time_values_by_supported_granularities(self):
        cases = [
            ("hour", {"09:00:00": 2, "14:00:00": 1}),
            ("minute", {"09:15:00": 2, "14:33:00": 1}),
            ("second", {"09:15:42": 2, "14:33:19": 1}),
        ]

        for granularity, expected in cases:
            with self.subTest(granularity=granularity):
                query = self.build_query(
                    [
                        *self.make_time_source_operations(),
                        {
                            "type": "summarize",
                            "measures": [
                                {"measure_name": "row_count", "column_name": "label", "aggregation": "count"}
                            ],
                            "dimensions": [
                                {
                                    "column_name": "posting_time",
                                    "data_type": "Time",
                                    "granularity": granularity,
                                    "dimension_name": "posting_time_bucket",
                                }
                            ],
                        },
                        {
                            "type": "order_by",
                            "column": {"type": "column", "column_name": "posting_time_bucket"},
                            "direction": "asc",
                        },
                    ]
                )

                result = query.execute()
                actual = dict(zip(result["posting_time_bucket"], result["row_count"], strict=False))

                self.assertEqual(actual, expected)

    # @feature query.summarize-grain
    def test_summary_query_rejects_calendar_buckets_for_time_columns(self):
        operations = [
            *self.make_time_source_operations(),
            {
                "type": "summarize",
                "measures": [{"measure_name": "row_count", "column_name": "label", "aggregation": "count"}],
                "dimensions": [
                    {
                        "column_name": "posting_time",
                        "data_type": "Time",
                        "granularity": "month",
                        "dimension_name": "posting_time_bucket",
                    }
                ],
            },
        ]

        with self.assertRaises(frappe.ValidationError) as exc:
            self.build_query(operations)

        self.assertIn("Supported granularities: second, minute, hour", str(exc.exception))

    # @feature query.summarize-aggregations
    def test_a_row_count_reads_a_first_column_named_like_a_table_method(self):
        query = self.build_query(
            [
                {"type": "code", "code": "results = [{'execute': 'a'}, {'execute': 'b'}]"},
                {
                    "type": "summarize",
                    "measures": [{"measure_name": "rows", "column_name": "count", "aggregation": "count"}],
                    "dimensions": [],
                },
            ]
        )

        self.assertEqual(query.execute()["rows"].tolist(), [2])


class TestIbisPivotWider(IbisQueryBuilderTestCase):
    def pivot_totals(self, sales, max_column_values):
        """Revenue by month split by region, one column total per region kept."""
        operations = [
            {"type": "code", "code": f"results = {sales}"},
            {
                "type": "pivot_wider",
                "rows": [{"column_name": "month", "data_type": "String", "dimension_name": "month"}],
                "columns": [{"column_name": "region", "data_type": "String", "dimension_name": "region"}],
                "values": [
                    {
                        "column_name": "amount",
                        "data_type": "Integer",
                        "aggregation": "sum",
                        "measure_name": "revenue",
                    }
                ],
                "max_column_values": max_column_values,
            },
        ]

        result = self.build_query(operations).execute()
        return result.drop(columns=["month"]).sum().to_dict()

    # @feature charts.split-by-max-values query.pivot-wider
    def test_pivot_keeps_the_biggest_split_value_out_of_others(self):
        # "zulu" sorts last but sells the most, so an alphabetical cut would
        # hide the biggest series inside "Others"
        sales = [
            {"month": "2026-01", "region": "alpha", "amount": 10},
            {"month": "2026-01", "region": "bravo", "amount": 5},
            {"month": "2026-01", "region": "zulu", "amount": 100},
            {"month": "2026-02", "region": "alpha", "amount": 20},
            {"month": "2026-02", "region": "zulu", "amount": 200},
        ]

        self.assertEqual(self.pivot_totals(sales, 2), {"alpha": 30, "zulu": 300, "Others": 5})

    # @feature charts.split-by-max-values query.pivot-wider
    def test_pivot_adds_no_others_column_when_it_cuts_nothing(self):
        # as many regions as the cap allows, so "Others" would hold nothing
        sales = [
            {"month": "2026-01", "region": "alpha", "amount": 10},
            {"month": "2026-02", "region": "zulu", "amount": 200},
        ]

        self.assertEqual(self.pivot_totals(sales, 2), {"alpha": 10, "zulu": 200})

    # @feature query.pivot-wider
    def test_pivot_plots_rows_with_no_split_value_as_their_own_series(self):
        sales = [
            {"month": "2026-01", "region": "alpha", "amount": 10},
            {"month": "2026-01", "region": None, "amount": 100},
            {"month": "2026-02", "region": "zulu", "amount": 200},
            {"month": "2026-02", "region": None, "amount": 50},
        ]

        with self.subTest("cut"):
            self.assertEqual(self.pivot_totals(sales, 2), {"null": 150, "zulu": 200, "Others": 10})
        with self.subTest("no cut"):
            self.assertEqual(self.pivot_totals(sales, 3), {"alpha": 10, "zulu": 200, "null": 150})

    # @feature charts.split-by-max-values query.pivot-wider
    def test_pivot_reads_a_split_and_measure_named_like_table_methods(self):
        """The cut ranks by the measure and folds the split's tail, both read by name."""
        sales = [
            {"month": "2026-01", "execute": "alpha", "sql": 10},
            {"month": "2026-01", "execute": "bravo", "sql": 5},
            {"month": "2026-01", "execute": "zulu", "sql": 100},
        ]
        operations = [
            {"type": "code", "code": f"results = {sales}"},
            {
                "type": "pivot_wider",
                "rows": [{"column_name": "month", "data_type": "String", "dimension_name": "month"}],
                "columns": [{"column_name": "execute", "data_type": "String", "dimension_name": "execute"}],
                "values": [
                    {
                        "column_name": "sql",
                        "data_type": "Integer",
                        "aggregation": "sum",
                        "measure_name": "sql",
                    }
                ],
                "max_column_values": 2,
            },
        ]

        result = self.build_query(operations).execute()
        self.assertEqual(
            result.drop(columns=["month"]).sum().to_dict(), {"alpha": 10, "zulu": 100, "Others": 5}
        )


class TestIbisWindowedNumberCard(IbisQueryBuilderTestCase):
    """The span a number card derives, executed.

    Derivation names the span and the engine turns it into dates, so the two
    halves of a span card only meet here.
    """

    def windowed_result(self, config, sales):
        return self.result_of(derive_operations("Number", "sales", config), sales)

    def result_of(self, derived, sales):
        return self.build_query(
            [
                {"type": "code", "code": f"results = {sales}"},
                {
                    "type": "cast",
                    "column": {"type": "column", "column_name": "posting_date"},
                    "data_type": "Date",
                },
                *derived[1:],
            ]
        ).execute()

    def revenue_by_window(self, config):
        sales = [
            {"posting_date": "2026-08-05", "amount": 30},
            {"posting_date": "2026-08-09", "amount": 70},
            {"posting_date": "2026-08-20", "amount": 500},  # after the anchor
            {"posting_date": "2026-07-05", "amount": 400},  # before the span
            {"posting_date": "2025-08-05", "amount": 60},
            {"posting_date": "2025-08-20", "amount": 900},  # after the shifted anchor
        ]
        return list(self.windowed_result(config, sales)["Revenue"])

    def config(self, comparison=None, span="month to date"):
        return {
            "sparkline": False,
            "number_columns": [
                {
                    "aggregation": "sum",
                    "column_name": "amount",
                    "data_type": "Decimal",
                    "measure_name": "Revenue",
                }
            ],
            "date_column": {
                "column_name": "posting_date",
                "data_type": "Date",
                "dimension_name": "posting_date",
            },
            "window": {"span": span, "anchor": "2026-08-10"},
            "number_column_options": [{"comparison": comparison} if comparison else {}],
        }

    # @feature charts.number-period
    def test_a_window_reads_the_days_it_covers(self):
        self.assertEqual(self.revenue_by_window(self.config()), [100])

    # @feature charts.number-comparison
    def test_a_comparison_window_is_the_row_before_the_reading(self):
        comparison = {"source": "last year"}
        self.assertEqual(self.revenue_by_window(self.config(comparison)), [60, 100])

    # @feature charts.number-period
    def test_a_window_of_several_periods_is_one_row_holding_the_whole_window(self):
        """`last 3 months` covers three months and reads as one number.

        Grouped by the month it names, the span comes back as three rows and
        the card reads the newest month as if it were the three months. Grouping
        by the span itself is what makes every span one row.
        """
        sales = [
            {"posting_date": "2026-05-15", "amount": 10},
            {"posting_date": "2026-06-15", "amount": 20},
            {"posting_date": "2026-07-15", "amount": 30},
            {"posting_date": "2025-05-15", "amount": 1},
            {"posting_date": "2025-06-15", "amount": 2},
            {"posting_date": "2025-07-15", "amount": 4},
            {"posting_date": "2026-08-05", "amount": 500},  # the anchor's own month
            {"posting_date": "2026-04-30", "amount": 400},  # before the span
        ]
        comparison = {"source": "last year"}
        result = self.windowed_result(self.config(comparison, span="last 3 months"), sales)

        self.assertEqual(list(result["Revenue"]), [7, 60])
        # the span is named by the date it starts on, and the card reads the
        # last row, so this order is the contract the number adapter reads
        self.assertEqual(
            [str(window)[:10] for window in result["posting_date"]],
            ["2025-05-01", "2026-05-01"],
        )

    # @feature charts.number-comparison
    def test_windows_that_overlap_each_read_their_whole_stretch(self):
        """A span longer than the shift its comparison moves by overlaps it.

        `last 12 months (include current)` anchored in August covers August
        last year too, and its year-back span ends there. Each span is its
        own aggregate, so the month they share counts in both and neither
        span reads short.
        """
        sales = [
            {"posting_date": "2025-08-15", "amount": 5},  # in both spans
            {"posting_date": "2026-01-15", "amount": 10},  # this span only
            {"posting_date": "2024-10-01", "amount": 3},  # the year-back span only
            {"posting_date": "2024-05-01", "amount": 400},  # before both
        ]
        comparison = {"source": "last year"}
        config = self.config(comparison, span="last 12 months (include current)")
        result = self.windowed_result(config, sales)

        self.assertEqual(list(result["Revenue"]), [8, 15])
        self.assertEqual(
            [str(window)[:10] for window in result["posting_date"]],
            ["2024-08-01", "2025-08-01"],
        )

    # @feature charts.number-period
    def test_a_window_holding_no_rows_is_a_row_of_nulls(self):
        """The card reads its rows by position, so a span that came back as
        nothing would print its neighbor's figure under this span's caption:
        on the 1st of a month, last month's revenue as this month's."""
        sales = [
            {"posting_date": "2025-08-05", "amount": 60},  # the comparison span only
            {"posting_date": "2026-07-05", "amount": 400},  # before both spans
        ]
        comparison = {"source": "last year"}
        result = self.windowed_result(self.config(comparison), sales)

        self.assertEqual(
            [str(window)[:10] for window in result["posting_date"]],
            ["2025-08-01", "2026-08-01"],
        )
        # the reading is the last row, and it is this span's own emptiness
        self.assertEqual(result["Revenue"].isna().tolist(), [False, True])
        self.assertEqual(result["Revenue"][0], 60)

    # @feature charts.number-sparkline
    def test_a_sparkline_reads_the_window_one_day_at_a_time(self):
        """The card's own rows are one per span. The chart under the number
        is the same span cut by the grain below the span's unit."""
        sales = [
            {"posting_date": "2026-08-05", "amount": 30},
            {"posting_date": "2026-08-05", "amount": 5},
            {"posting_date": "2026-08-09", "amount": 70},
            {"posting_date": "2026-08-20", "amount": 500},  # after the anchor
            {"posting_date": "2026-07-05", "amount": 400},  # before the span
            {"posting_date": "2025-08-05", "amount": 60},  # the comparison span
        ]
        comparison = {"source": "last year"}
        config = {**self.config(comparison), "sparkline": True}

        result = self.result_of(sparkline_operations("Number", "sales", config), sales)

        self.assertEqual(
            [str(day)[:10] for day in result["posting_date"]],
            ["2026-08-05", "2026-08-09"],
        )
        self.assertEqual(list(result["Revenue"]), [35, 70])
        # the number itself is unmoved by the second query
        self.assertEqual(list(self.windowed_result(config, sales)["Revenue"]), [60, 105])

    # @feature charts.number-period
    def test_a_window_refuses_to_group_by_anything_else(self):
        """The span is the whole of the grouping.

        A dimension beside it would cut each span again, and a second span
        dimension names no rows the first one does. Neither is a shape
        a card sends, so both are refused rather than answered.
        """
        sales = [{"posting_date": "2026-08-05", "amount": 30, "region": "north"}]
        window = {
            "column_name": "posting_date",
            "data_type": "Date",
            "dimension_name": "posting_date",
            "windows": [{"span": "month to date", "anchor": "2026-08-10"}],
        }
        region = {"column_name": "region", "data_type": "String", "dimension_name": "region"}
        measures = self.config()["number_columns"]

        for dimensions in ([region, window], [window, {**window, "dimension_name": "again"}]):
            with self.subTest(dimensions=[d["dimension_name"] for d in dimensions]):
                summarize = {"type": "summarize", "measures": measures, "dimensions": dimensions}
                self.assertRaises(frappe.ValidationError, self.result_of, [None, summarize], sales)


class TestIbisDateFilterOnDatetime(IbisQueryBuilderTestCase):
    STAMPS = ("2026-08-04 23:00:00", "2026-08-05 00:00:00", "2026-08-05 17:30:00", "2026-08-06 00:00:00")

    def filtered(self, operator, value, stamps=STAMPS):
        rows = [{"posted_at": stamp} for stamp in stamps]
        operations = [
            {"type": "code", "code": f"results = {rows}"},
            {
                "type": "cast",
                "column": {"type": "column", "column_name": "posted_at"},
                "data_type": "Datetime",
            },
            {
                "type": "filter",
                "column": {"type": "column", "column_name": "posted_at"},
                "operator": operator,
                "value": value,
            },
        ]
        result = self.build_query(operations).execute()
        return sorted(str(stamp) for stamp in result["posted_at"])

    # @feature query.filter-date-on-datetime
    def test_a_date_on_a_datetime_column_compares_by_the_whole_day(self):
        before, midnight, evening, next_day = self.STAMPS
        cases = {
            "=": [midnight, evening],
            "!=": [before, next_day],
            ">": [next_day],
            ">=": [midnight, evening, next_day],
            "<": [before],
            "<=": [before, midnight, evening],
        }
        for operator, expected in cases.items():
            with self.subTest(operator=operator):
                self.assertEqual(self.filtered(operator, "2026-08-05"), expected)

        # the last instant of a day is past 23:59:59
        last_instant = "2026-08-05 23:59:59.500000"
        stamps = (before, midnight, last_instant, next_day)
        self.assertEqual(
            self.filtered("between", ["2026-08-05", "2026-08-05"], stamps), [midnight, last_instant]
        )

    # @feature query.filter-date-on-datetime
    def test_a_time_on_a_datetime_column_compares_by_that_instant(self):
        _, midnight, evening, next_day = self.STAMPS
        self.assertEqual(self.filtered(">", "2026-08-05 00:00:00"), [evening, next_day])


class TestIbisDivision(IbisQueryBuilderTestCase):
    # @feature data-source.division-by-zero
    def test_a_division_compiles_to_null_on_a_zero_divisor_on_postgres(self):
        mutations = {
            "ratio": "net_profit / income",
            "whole": "net_profit // income",
            "rest": "net_profit % income",
        }
        query = self.build_query(
            [
                {"type": "code", "code": 'results = [{"income": 0, "net_profit": 5}]'},
                *(
                    {
                        "type": "mutate",
                        "new_name": name,
                        "data_type": "Decimal",
                        "expression": {"type": "expression", "expression": expression},
                    }
                    for name, expression in mutations.items()
                ),
            ]
        )
        with patch("ibis.postgres.connect", return_value=PostgresBackend()):
            connection = get_postgres_connection(FakeDataSource())
        sql = connection.compile(query.unbind())
        self.assertEqual(sql.count('NULLIF("t0"."income", 0)'), len(mutations))


def picker_operators(kind):
    """The operators the filter picker offers a column of `kind`, read off its table."""
    path = os.path.join(
        frappe.get_app_path("insights"),
        "..",
        "frontend",
        "src2",
        "components",
        "filter_picker",
        "filter_picker.ts",
    )
    with open(path) as source:
        table = re.search(rf"\n\t{kind}: \[(.*?)\n\t\]", source.read(), re.S).group(1)
    operators = re.findall(r"operator: '([^']+)'", table)
    assert operators, f"read no operator off the picker's {kind} table"
    return operators


ENGINES = ("duckdb", "sqlite")


class TestIbisDateOperators(IbisQueryBuilderTestCase):
    """Every date operator the picker offers, given the one day a reader picked."""

    DAY = "2026-08-05"
    VALUES: ClassVar[dict] = {
        "between": [DAY, DAY],
        "within": {"span": "current day", "anchor": DAY},
    }
    ROWS: ClassVar[dict] = {
        "Date": {
            "before": "2026-08-04",
            "day": "2026-08-05",
            "after": "2026-08-06",
            "unset": None,
        },
        "Datetime": {
            "before": "2026-08-04 23:00:00",
            "midnight": "2026-08-05 00:00:00",
            "evening": "2026-08-05 17:30:00",
            "last instant": "2026-08-05 23:59:59.500000",
            "after": "2026-08-06 00:00:00",
            "unset": None,
        },
    }
    DAY_ROWS: ClassVar[dict] = {"Date": ["day"], "Datetime": ["midnight", "evening", "last instant"]}

    def expected(self, data_type, operator):
        day = self.DAY_ROWS[data_type]
        return {
            "between": day,
            "within": day,
            "=": day,
            "!=": ["before", "after"],
            ">": ["after"],
            ">=": [*day, "after"],
            "<": ["before"],
            "<=": ["before", *day],
            "is_set": ["before", *day, "after"],
            "is_not_set": ["unset"],
        }[operator]

    SQLITE_TYPES: ClassVar[dict] = {"Date": "DATE", "Datetime": "TIMESTAMP", "String": "TEXT"}
    TEXT_DATES: ClassVar[dict] = {
        "before": "2026-08-04",
        "day": "2026-08-05",
        "afternoon": "2026-08-05 13:00:00",
        "after": "2026-08-06",
        "blank": "",
        "not a date": "n/a",
    }

    def matched(self, engine, data_type, rules, rows=None):
        """The labels of the rows each `(operator, value)` rule keeps, on DuckDB or SQLite."""
        rows = rows or self.ROWS[data_type]
        column = {"type": "column", "column_name": "at"}
        filters = [
            {"type": "filter", "column": column, "operator": operator, "value": value}
            for operator, value in rules
        ]
        if engine == "duckdb":
            table = [{"label": label, "at": at} for label, at in rows.items()]
            operations = [
                {"type": "code", "code": f"results = {table}"},
                {"type": "cast", "column": column, "data_type": data_type},
                *filters,
            ]
            return list(self.build_query(operations).execute()["label"])

        connection = ibis.sqlite.connect()
        connection.raw_sql(f"create table stamps (label TEXT, at {self.SQLITE_TYPES[data_type]})")
        values = ", ".join(
            f"('{label}', {'NULL' if at is None else f"'{at}'"})" for label, at in rows.items()
        )
        connection.raw_sql(f"insert into stamps values {values}")
        builder = IbisQueryBuilder(self.make_query_doc([]))
        builder.query = connection.table("stamps")
        for rule in filters:
            builder.query = builder.apply_filter(_dict(rule))
        return list(builder.query.execute()["label"])

    def assert_matches(self, engine, data_type, rules, expected, rows=None):
        order = list(rows or self.ROWS[data_type])
        matched = self.matched(engine, data_type, rules, rows)
        self.assertEqual(sorted(matched, key=order.index), expected)

    # @feature query.filter-date-on-datetime
    def test_every_picker_date_operator_reads_a_day_as_the_whole_day(self):
        for engine in ENGINES:
            for operator in picker_operators("date"):
                for data_type in self.ROWS:
                    with self.subTest(engine=engine, operator=operator, data_type=data_type):
                        value = self.VALUES.get(operator, self.DAY)
                        self.assert_matches(
                            engine, data_type, [(operator, value)], self.expected(data_type, operator)
                        )

    # @feature query.filter-date-on-datetime
    def test_a_drill_into_a_day_reads_the_rows_its_card_counts(self):
        day = _bucket_filters("at", (datetime(2026, 8, 5), datetime(2026, 8, 6)))
        rules = [(rule["operator"], rule["value"]) for rule in day]
        cases = [(data_type, self.ROWS[data_type], self.DAY_ROWS[data_type]) for data_type in self.ROWS]
        cases.append(("String", self.TEXT_DATES, ["day", "afternoon"]))
        for engine in ENGINES:
            for data_type, rows, expected in cases:
                with self.subTest(engine=engine, data_type=data_type):
                    self.assert_matches(engine, data_type, rules, expected, rows)

    # @feature query.filter-date-on-datetime
    def test_a_bound_with_a_time_of_day_takes_the_column_type(self):
        """An hour of a chart, drilled: SQL Server reads a text bound by the login's date format."""
        hour = _bucket_filters("at", (datetime(2026, 8, 5, 17), datetime(2026, 8, 5, 18)))
        builder = IbisQueryBuilder(self.make_query_doc([]))
        builder.query = ibis.table({"at": "timestamp"}, name="stamps")
        for rule in hour:
            builder.query = builder.apply_filter(_dict(rule))
        self.assertIn("DATETIME2FROMPARTS(2026, 8, 5, 17", ibis.to_sql(builder.query, dialect="mssql"))

    # @feature query.filter-date-on-datetime
    def test_a_span_on_a_time_column_is_refused(self):
        builder = IbisQueryBuilder(self.make_query_doc([]))
        builder.query = ibis.table({"at": "time"}, name="stamps")
        rule = {
            "type": "filter",
            "column": {"type": "column", "column_name": "at"},
            "operator": "within",
            "value": {"span": "current day"},
        }
        self.assertRaises(QueryRefused, builder.apply_filter, _dict(rule))

    # @feature query.filter-relative-date
    def test_a_span_on_dates_held_as_text_takes_in_the_whole_day(self):
        for engine in ENGINES:
            for operator in ("within", "between"):
                with self.subTest(engine=engine, operator=operator):
                    rule = (operator, self.VALUES[operator])
                    self.assert_matches(engine, "String", [rule], ["day", "afternoon"], self.TEXT_DATES)


class TestIbisRemoveColumns(IbisQueryBuilderTestCase):
    """ibis drops fewer than half of a table's columns by star, and the stock
    DuckDB, ClickHouse and BigQuery compilers lose the star's exclusions."""

    def remove_note(self, query):
        builder = IbisQueryBuilder(self.make_query_doc([]))
        builder.query = query
        return builder.apply_remove(_dict({"column_names": ["note"]}))

    def remove_after_join(self, orders, customers):
        joined = orders.left_join(customers, orders.id == customers.order_id)
        return self.remove_note(joined.mutate(double=joined.amount * 2))

    def unbound_tables(self):
        orders = ibis.table({"id": "int64", "note": "string", "amount": "int64"}, name="orders")
        customers = ibis.table({"order_id": "int64", "customer": "string"}, name="customers")
        return orders, customers

    # @feature query.remove-column
    def test_a_remove_takes_the_column_off_on_duckdb(self):
        orders = connect_duckdb().create_table(
            "orders",
            ibis.memtable(
                {"id": [1, 2], "note": ["a", "b"], "amount": [10, 20], "kind": ["x", "y"], "paid": [1, 0]}
            ),
        )

        result = self.remove_note(orders).order_by("id").execute()

        self.assertEqual(list(result.columns), ["id", "amount", "kind", "paid"])

    # @feature query.remove-column query.join
    def test_a_remove_after_a_join_takes_the_column_off_on_duckdb(self):
        connection = connect_duckdb()
        orders = connection.create_table(
            "orders", ibis.memtable({"id": [1, 2], "note": ["a", "b"], "amount": [10, 20]})
        )
        customers = connection.create_table("customers", ibis.memtable({"order_id": [1], "customer": ["x"]}))

        result = self.remove_after_join(orders, customers).order_by("id").execute()

        self.assertNotIn("note", result.columns)
        self.assertEqual(list(result["double"]), [20, 40])

    # @feature query.remove-column query.join
    def test_a_remove_after_a_join_compiles_to_except_on_clickhouse(self):
        with patch("ibis.clickhouse.connect", return_value=ClickHouseBackend()):
            connection = get_clickhouse_connection(FakeDataSource())

        sql = connection.compile(self.remove_after_join(*self.unbound_tables()))

        self.assertIn('.* EXCEPT ("note")', sql)

    # @feature query.remove-column query.join
    def test_a_remove_after_a_join_compiles_to_except_on_bigquery(self):
        # the BigQuery backend is an optional extra, so its module is a stand-in
        ibis.bigquery = SimpleNamespace(connect=lambda **kwargs: SimpleNamespace())
        self.addCleanup(delattr, ibis, "bigquery")
        with patch("google.oauth2.service_account.Credentials.from_service_account_info"):
            connection = get_bigquery_connection(FakeDataSource(bigquery_service_account_key="{}"))

        expr = self.remove_after_join(*self.unbound_tables())
        sql = connection.compiler.to_sqlglot(expr).sql(dialect="bigquery")

        self.assertIn(".* EXCEPT (`note`)", sql)

    @unittest.expectedFailure
    # @feature query.remove-column query.join
    def test_the_stock_compilers_keep_a_star_exclusion(self):
        """ibis 12 fixes them. When this passes, delete `connectors/compilers.py`."""
        expr = self.remove_after_join(*self.unbound_tables())
        for compiler in (DuckDBCompiler(), ClickHouseCompiler(), BigQueryCompiler()):
            with self.subTest(compiler=type(compiler).__name__):
                self.assertRegex(
                    compiler.to_sqlglot(expr).sql(dialect=compiler.dialect), r"\.\* (EXCLUDE|EXCEPT) \("
                )

    # @feature query.remove-column
    def test_insights_opens_duckdb_only_through_connect_duckdb(self):
        """`connect_duckdb` sets the compiler that keeps a removed column off."""
        package = os.path.dirname(insights.__file__)
        opener = os.path.join(
            package, "insights", "doctype", "insights_data_source_v3", "connectors", "duckdb.py"
        )
        direct = re.compile(r"ibis\.duckdb\.connect\(|ibis\.connect\(\s*[\"']duckdb")
        bypasses = []
        for root, _, files in os.walk(package):
            for name in files:
                path = os.path.join(root, name)
                if not name.endswith(".py") or name.startswith("test_") or path == opener:
                    continue
                if os.path.join(package, "tests") in path:
                    continue
                with open(path) as source:
                    if direct.search(source.read()):
                        bypasses.append(os.path.relpath(path, package))

        self.assertEqual(bypasses, [])


DATE_DIFF_UNITS = ("second", "minute", "hour", "day")
DATE_DIFF_CASES = (
    ("2025-12-31 23:00:00", "2026-01-02 01:00:00", {"second": 93600, "minute": 1560, "hour": 26, "day": 2}),
    ("2026-01-01 23:59:00", "2026-01-02 00:01:00", {"second": 120, "minute": 2, "hour": 0, "day": 1}),
    ("1969-12-31 20:00:00", "1969-12-31 23:00:00", {"second": 10800, "minute": 180, "hour": 3, "day": 0}),
)


class TestIbisDateDiff(IbisQueryBuilderTestCase):
    # @feature query.expression-date-diff
    def test_date_diff_counts_whole_units_between_two_datetimes_on_duckdb(self):
        rows = [{"started_at": start, "ended_at": end} for start, end, _ in DATE_DIFF_CASES]
        operations = [{"type": "code", "code": f"results = {rows}"}]
        for name in ("started_at", "ended_at"):
            operations.append(
                {
                    "type": "cast",
                    "column": {"type": "column", "column_name": name},
                    "data_type": "Datetime",
                }
            )
        for unit in DATE_DIFF_UNITS:
            operations.append(
                {
                    "type": "mutate",
                    "new_name": unit,
                    "data_type": "Integer",
                    "expression": {
                        "type": "expression",
                        "expression": f"date_diff(ended_at, started_at, '{unit}')",
                    },
                }
            )

        result = self.build_query(operations).execute()

        self.assertEqual(
            [{unit: int(row[unit]) for unit in DATE_DIFF_UNITS} for _, row in result.iterrows()],
            [expected for _, _, expected in DATE_DIFF_CASES],
        )

    # @feature query.expression-date-diff
    def test_date_diff_counts_a_second_across_its_boundary_on_sqlite(self):
        start = ibis.literal("2026-01-01 09:59:59.900").cast("timestamp")
        end = ibis.literal("2026-01-01 10:00:01.100").cast("timestamp")

        seconds = ibis.sqlite.connect().execute(date_diff(end, start, "second").name("seconds"))

        self.assertEqual(seconds, 1)


FIRST_ROW_CASES = (
    ("filter_first_row(group_by=status, order_by=date)", ["Alpha", "Beta"]),
    ("filter_first_row(group_by=status, order_by=date, sort_order='desc')", ["Beta", "Gamma"]),
    ("filter_first_row(group_by=status, order_by=desc(date))", ["Beta", "Gamma"]),
    ("filter_first_row(group_by=status, order_by=asc(date), sort_order='desc')", ["Alpha", "Beta"]),
    ("is_first_row(group_by=status, order_by=desc(date)) == 1", ["Beta", "Gamma"]),
    ("is_last_row(group_by=status, order_by=desc(date)) == 1", ["Alpha", "Beta"]),
    ("is_last_row(group_by=status, order_by=[desc(date)]) == 1", ["Alpha", "Beta"]),
)


class TestIbisFirstRow(IbisQueryBuilderTestCase):
    # @feature query.expression-first-last-row
    def test_first_and_last_row_follow_the_direction_of_a_sorted_key_on_duckdb(self):
        rows = [
            {"name": "Alpha", "status": "Open", "date": "2026-01-01"},
            {"name": "Beta", "status": "Closed", "date": "2026-01-02"},
            {"name": "Gamma", "status": "Open", "date": "2026-01-03"},
        ]
        for expression, expected in FIRST_ROW_CASES:
            operations = [
                {"type": "code", "code": f"results = {rows}"},
                {"type": "filter", "expression": {"type": "expression", "expression": expression}},
            ]

            result = self.build_query(operations).execute()

            with self.subTest(expression=expression):
                self.assertEqual(sorted(result["name"]), expected)

    # @feature query.expression-first-last-row
    def test_first_and_last_row_with_no_order_by_are_refused(self):
        rows = [{"name": "Alpha", "status": "Open"}, {"name": "Gamma", "status": "Open"}]
        for expression in (
            "is_first_row(group_by=status) == 1",
            "is_last_row(group_by=status) == 1",
            "filter_first_row()",
        ):
            operations = [
                {"type": "code", "code": f"results = {rows}"},
                {"type": "filter", "expression": {"type": "expression", "expression": expression}},
            ]

            with (
                self.subTest(expression=expression),
                self.assertRaisesRegex(frappe.ValidationError, "pass order_by"),
            ):
                self.build_query(operations)


# March holds no Open row and February no Closed row, so a row read would reach
# across the gap
PERIOD_VALUE_ROWS = (
    ("Open", "2026-01-05"),
    ("Open", "2026-01-20"),
    ("Open", "2026-02-10"),
    ("Open", "2026-04-03"),
    ("Closed", "2026-01-07"),
    ("Closed", "2026-03-15"),
    ("Open", None),
)
PERIOD_VALUE_EXPRESSIONS = {
    "previous": "previous_period_value(todo_count, month)",
    "previous_2": "previous_period_value(todo_count, month, 2)",
    "next": "next_period_value(todo_count, month)",
    "change": "percentage_change(todo_count, month)",
}
PERIOD_VALUE_CASES = {
    ("Closed", "2026-01-01"): {"previous": None, "previous_2": None, "next": None, "change": None},
    ("Closed", "2026-03-01"): {"previous": None, "previous_2": 1, "next": None, "change": None},
    ("Open", "2026-01-01"): {"previous": None, "previous_2": None, "next": 1, "change": None},
    ("Open", "2026-02-01"): {"previous": 2, "previous_2": None, "next": None, "change": -50},
    ("Open", "2026-04-01"): {"previous": None, "previous_2": 1, "next": None, "change": None},
    ("Open", None): {"previous": None, "previous_2": None, "next": None, "change": None},
}


def period_value_operations(source_operations):
    return [
        *source_operations,
        {
            "type": "summarize",
            "measures": [{"measure_name": "todo_count", "column_name": "name", "aggregation": "count"}],
            "dimensions": [
                {"column_name": "status", "data_type": "String", "dimension_name": "status"},
                {
                    "column_name": "date",
                    "data_type": "Date",
                    "granularity": "month",
                    "dimension_name": "month",
                },
            ],
        },
        *(
            {
                "type": "mutate",
                "new_name": new_name,
                "data_type": "Decimal",
                "expression": {"type": "expression", "expression": expression},
            }
            for new_name, expression in PERIOD_VALUE_EXPRESSIONS.items()
        ),
    ]


def read_period_values(rows):
    def value(v):
        return None if pd.isna(v) else int(v)

    return {
        (row["status"], None if pd.isna(row["month"]) else str(row["month"])[:10]): {
            key: value(row[key]) for key in PERIOD_VALUE_EXPRESSIONS
        }
        for row in rows
    }


# 2026-01-03 holds no row, so a row read would take 2026-01-04 back to 2026-01-02
RAW_DATE_ROWS = ("2026-01-01", "2026-01-02", "2026-01-04")
RAW_DATE_CASES = {"2026-01-01": None, "2026-01-02": "2026-01-01", "2026-01-04": None}
RAW_DATE_EXPRESSION = "previous_period_value(date, date, 1, 'day')"


def read_raw_date_values(rows):
    return {
        str(row["date"])[:10]: None
        if row["previous"] is None or pd.isna(row["previous"])
        else str(row["previous"])[:10]
        for row in rows
    }


class TestIbisPeriodValue(IbisQueryBuilderTestCase):
    def source_operations(self, rows, data_type="Date"):
        return [
            {"type": "code", "code": f"results = {rows}"},
            {"type": "cast", "column": {"type": "column", "column_name": "date"}, "data_type": data_type},
        ]

    def mutate_previous(self, expression):
        return {
            "type": "mutate",
            "new_name": "previous",
            "data_type": "Decimal",
            "expression": {"type": "expression", "expression": expression},
        }

    # @feature query.expression-period-value
    def test_period_values_read_the_period_n_grains_away_on_duckdb(self):
        rows = [
            {"name": str(i), "status": status, "date": date}
            for i, (status, date) in enumerate(PERIOD_VALUE_ROWS)
        ]

        result = self.build_query(period_value_operations(self.source_operations(rows))).execute()

        self.assertEqual(read_period_values(result.to_dict("records")), PERIOD_VALUE_CASES)

    # @feature query.expression-period-value
    def test_a_date_nothing_grouped_reads_the_day_before_at_the_day_grain_on_duckdb(self):
        rows = [{"date": date} for date in RAW_DATE_ROWS]
        operations = [
            *self.source_operations(rows),
            {**self.mutate_previous(RAW_DATE_EXPRESSION), "data_type": "Date"},
        ]

        result = self.build_query(operations).execute()

        self.assertEqual(read_raw_date_values(result.to_dict("records")), RAW_DATE_CASES)

    # @feature query.expression-period-value
    def test_a_datetime_summarized_by_month_and_renamed_reads_the_month_before(self):
        rows = [
            {"amount": 10, "date": "2026-01-15 10:00:00"},
            {"amount": 20, "date": "2026-02-02 09:00:00"},
            {"amount": 30, "date": "2026-04-20 18:00:00"},
        ]
        operations = [
            *self.source_operations(rows, "Datetime"),
            {
                "type": "summarize",
                "measures": [{"measure_name": "amount", "column_name": "amount", "aggregation": "sum"}],
                "dimensions": [
                    {
                        "column_name": "date",
                        "data_type": "Datetime",
                        "granularity": "month",
                        "dimension_name": "date",
                    }
                ],
            },
            {"type": "rename", "column": {"type": "column", "column_name": "date"}, "new_name": "month"},
            self.mutate_previous("previous_period_value(amount, month)"),
        ]

        result = self.build_query(operations).execute()

        previous = {str(row["month"])[:7]: row["previous"] for row in result.to_dict("records")}
        self.assertEqual(previous["2026-02"], 10)
        self.assertTrue(pd.isna(previous["2026-01"]) and pd.isna(previous["2026-04"]))

    # @feature query.expression-period-value
    def test_a_period_value_reads_the_grain_it_is_given(self):
        rows = [{"amount": 10, "date": "2026-01-01"}, {"amount": 20, "date": "2026-03-01"}]
        operations = [
            *self.source_operations(rows),
            self.mutate_previous("previous_period_value(amount, date, 2, 'month')"),
        ]

        result = self.build_query(operations).execute()

        previous = {str(row["date"])[:10]: row["previous"] for row in result.to_dict("records")}
        self.assertEqual(previous["2026-03-01"], 10)
        self.assertTrue(pd.isna(previous["2026-01-01"]))

    # @feature query.expression-period-value
    def test_a_period_value_on_a_date_nothing_grouped_is_refused(self):
        for data_type in ("Date", "Datetime"):
            rows = [{"amount": 10, "date": "2026-01-01 10:00:00"}]
            operations = [
                *self.source_operations(rows, data_type),
                self.mutate_previous("previous_period_value(amount, date)"),
            ]

            with (
                self.subTest(data_type=data_type),
                self.assertRaisesRegex(frappe.ValidationError, "cannot tell the period of date"),
            ):
                self.build_query(operations)

    # @feature query.expression-period-value
    def test_a_percentage_change_from_zero_is_null(self):
        table = ibis.memtable(
            {"date": pd.to_datetime(["2026-01-01", "2026-02-01"]).date, "amount": [0, 5]},
            schema={"date": "date", "amount": "int64"},
        )

        result = table.mutate(change=percentage_change(table.amount, table.date, 1, "month")).execute()

        self.assertTrue(result["change"].isna().all())

    # @feature query.expression-period-value
    def test_period_values_read_the_grain_they_are_given_on_sqlite(self):
        # mid-period dates: Postgres rounded a quarter's date difference, and
        # SQLite has none above a day. SQLite before 3.46, which CI runs, cannot
        # subtract a computed number of days
        monthly = ("2025-12-10", "2026-01-10", "2026-02-10", "2026-03-10", "2026-04-10")
        cases = {
            "week": (("2026-01-07", "2026-01-14", "2026-01-28"), [None, 1, None]),
            "month": (monthly, [None, 1, 2, 3, 4]),
            "quarter": (monthly, [None, 1, 1, 1, 4]),
            "year": (monthly, [None, 1, 1, 1, 1]),
        }
        con = ibis.sqlite.connect()
        for grain, (dates, previous) in cases.items():
            table = con.create_table(
                f"period_values_{grain}",
                pd.DataFrame({"date": pd.to_datetime(dates).date, "amount": range(1, len(dates) + 1)}),
                schema=ibis.schema({"date": "date", "amount": "int64"}),
            )
            result = table.mutate(
                previous=previous_period_value(table.amount, table.date, 1, grain)
            ).order_by("date")

            with self.subTest(grain=grain), patch("sqlite3.sqlite_version_info", (3, 45, 1)):
                self.assertEqual(
                    [None if pd.isna(v) else int(v) for v in result.execute()["previous"]], previous
                )

    # @feature query.expression-period-value
    def test_period_values_group_by_every_column_but_the_date_itself(self):
        # a regex reading of the name kept "Date (Month)" as a group, and took
        # "posting_date" for "date"
        for date_column, other_column in (("Date (Month)", "Date (Month) label"), ("date", "posting_date")):
            table = ibis.memtable(
                {
                    date_column: pd.to_datetime(
                        ["2026-01-01", "2026-02-01", "2026-01-01", "2026-02-01"]
                    ).date,
                    other_column: ["a", "a", "b", "b"],
                    "amount": [1, 2, 10, 20],
                },
                schema={date_column: "date", other_column: "string", "amount": "int64"},
            )
            result = table.mutate(
                previous=previous_period_value(table.amount, table[date_column], 1, "month")
            ).order_by([other_column, date_column])

            with self.subTest(date_column=date_column):
                self.assertEqual(
                    [None if pd.isna(v) else int(v) for v in result.execute()["previous"]],
                    [None, 1, None, 10],
                )
