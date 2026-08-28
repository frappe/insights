"""Translate a v2 query into a v3 `operations` array.

v2 keeps one query in three shapes and picks between them at build time. The
order matters, because 4 production rows have both `is_native_query` and
`is_assisted_query` set and `SQLQueryBuilder.build` reads native first. 24 rows
have none of the three flags - a legacy query, built by `LegacyQueryBuilder`,
which this module never reconstructs and always drops to the SQL floor.

An assisted query is one `columns` list that serves SELECT, GROUP BY and ORDER
BY at once, so the whole translation turns on how `sql_builder.py` splits it.
It splits on `Column.is_measure()`, which is *not* "the aggregation says group
by": a column is a measure when it is numeric **or** aggregating. Three
consequences that a naive reading gets wrong:

- A numeric column with `aggregation: "group by"` is a measure. v2 put it in
  SELECT and left it out of GROUP BY, which only MySQL's loose grouping allowed.
  ibis has no such thing, so it becomes a dimension here and the widened
  grouping is reported.
- 762 of 1833 assisted queries have no aggregating column at all, so v2 emitted
  no GROUP BY. Those get a `select`, not a `summarize`.
- `measures`, `dimensions`, `orders` and `calculations` are dead in the
  backend. `sql_builder` reads `columns` alone, so a column that lives only in
  one of the legacy lists never reached v2's SQL. 28 production columns are in
  that state; carrying them would add columns v2 never returned, so they are
  reported and dropped.

Two v2 aggregations do not mean what they say. `count` compiles to `COUNT(*)`
whatever column it names, so every v2 count becomes v3's count-of-rows measure
rather than a count of that column, which would drop nulls. `cumulative sum`
and `cumulative count` are a plain SQL aggregate plus a pandas `cumsum` over
the fetched rows, so they need an aggregate *and* a window afterwards.

Operation order is the correctness constraint. A derived column has to exist
before anything groups by it, and the grouping has to happen before the sort
that names its output:

    source -> join* -> [filter fragments] -> filter_group -> [column fragments
    and mutates] -> summarize | (rename* + select) -> order_by* -> limit ->
    [pivot_wider | cumulative mutates]

The transforms come last because v2 ran them in pandas over the fetched result,
after LIMIT.

Everything here is pure: dicts in, dicts out, no database.
"""

import json
import re
from dataclasses import dataclass, field

from insights.migrator.v2_expressions import (
    GRANULARITY_FORMATS,
    GRANULARITY_PARTS,
    GRANULARITY_STARTS,
    Outcome,
    TranslationError,
    reference,
    translate,
)

# v2 granularities that v3 carries on the dimension itself. v3 truncates the
# timestamp and keeps the date type; v2 formatted it to a string. Grouping is
# the same either way, and the type is better.
GRANULARITY_TO_V3 = {
    "Minute": "minute",
    "Hour": "hour",
    "Day": "day",
    "Day Short": "day",
    "Week": "week",
    "Month": "month",
    "Mon": "month",
    "Quarter": "quarter",
    "Year": "year",
}

# v3 rejects any other granularity on a dimension, so these are computed by a
# `mutate` instead. `GRANULARITY_PARTS` returns a number where v2 returned a
# formatted string ("Month of Year" was "January", it is now 1).
GRANULARITY_IS_A_PART = frozenset(GRANULARITY_PARTS)

V2_TO_V3_AGGREGATION = {
    "count": "count",
    "cumulative count": "count",
    "sum": "sum",
    "cumulative sum": "sum",
    "avg": "avg",
    "min": "min",
    "max": "max",
    "distinct_count": "count_distinct",
}

# Aggregations v2 finished in pandas, over the fetched rows, after LIMIT.
CUMULATIVE_AGGREGATIONS = frozenset({"cumulative count", "cumulative sum"})

# `Column.is_aggregate` in v2: an aggregation that is neither of these.
NON_AGGREGATIONS = frozenset({"", "custom", "group by"})

MEASURE_TYPES = frozenset({"Integer", "Decimal"})
DIMENSION_TYPES = frozenset({"String", "Date", "Datetime", "Time"})
DATE_TYPES = frozenset({"Date", "Datetime"})
COLUMN_DATA_TYPES = frozenset(
    {"String", "Integer", "Decimal", "Date", "Datetime", "Time", "Text", "JSON", "Array", "Auto"}
)

# Operators v3 spells exactly as v2 did.
DIRECT_OPERATORS = frozenset(
    {
        "=",
        "!=",
        ">",
        ">=",
        "<",
        "<=",
        "in",
        "not_in",
        "contains",
        "not_contains",
        "starts_with",
        "ends_with",
        "is_set",
        "is_not_set",
        "between",
    }
)

JOIN_TYPES = frozenset({"inner", "left", "right", "full"})

# Functions that make an expression a reduction, so it belongs in `summarize`
# as an expression measure rather than in a `mutate` before it.
AGGREGATING_FUNCTIONS = frozenset(
    {
        "sum",
        "count",
        "avg",
        "min",
        "max",
        "median",
        "distinct_count",
        "count_if",
        "sum_if",
        "distinct_count_if",
        "group_concat",
        "SUM",
        "COUNT",
        "AVG",
        "MIN",
        "MAX",
    }
)

_DATE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")


@dataclass(frozen=True)
class Gap:
    """Something the translation could not carry, phrased for a report.

    `dropped` separates a loss the user will see in the numbers from a note.
    """

    kind: str
    source: str
    detail: str
    dropped: bool = False


@dataclass
class TranslatedQuery:
    """A v3 query, and everything v2 held that did not fit in it."""

    source: str
    title: str
    data_source: str
    kind: str = "none"
    """`builder`, `sql`, `code`, or `none` when nothing can be emitted."""

    operations: list = field(default_factory=list)
    use_live_connection: bool = False
    references: tuple = ()
    """v2 query docnames this query reads, in the order they appear."""

    gaps: list = field(default_factory=list)

    @property
    def is_builder(self) -> bool:
        return self.kind == "builder"

    @property
    def fallback_reasons(self) -> tuple:
        """The gap kinds that forced this query off the builder path."""
        return tuple(dict.fromkeys(gap.kind for gap in self.gaps if gap.dropped))


def translate_query(
    query: dict,
    *,
    query_map: dict | None = None,
    workbook: str = "",
    table_columns: dict | None = None,
) -> TranslatedQuery:
    """Turn one v2 query row into a v3 operations array.

    `query_map` maps a v2 query docname to the v3 query it became. A v2 table
    name that is a key of the map is a query reference, not a table - that is
    how both a Query Store subquery and a query stored back into its own source
    are spelled. `workbook` is the v3 workbook every reference points into.

    `table_columns` maps each table to its column names, and is only used to
    warn when stripping a table qualifier off a SQL fragment had to guess.
    """
    builder = _Builder(query, query_map or {}, workbook, table_columns or {})
    return builder.run()


class _Builder:
    def __init__(self, query, query_map, workbook, table_columns):
        self.query = query
        self.query_map = query_map
        self.workbook = workbook
        self.table_columns = table_columns
        self.data_source = query.get("data_source") or ""
        self.result = TranslatedQuery(
            source=query.get("name") or "",
            title=query.get("title") or query.get("name") or "",
            data_source=self.data_source,
        )
        self.references = []

    # -- reporting ---------------------------------------------------------

    def gap(self, kind, source, detail, dropped=False):
        self.result.gaps.append(Gap(kind=kind, source=source, detail=detail, dropped=dropped))

    # -- entry point -------------------------------------------------------

    def run(self) -> TranslatedQuery:
        # v2 reads `is_native_query` first, and 4 production rows set both it
        # and `is_assisted_query`. Reading the flags in any other order
        # migrates a query v2 never ran.
        if self.query.get("is_native_query"):
            return self.native()
        if self.query.get("is_script_query"):
            return self.script()
        if self.query.get("is_assisted_query"):
            return self.assisted()
        return self.legacy()

    def native(self) -> TranslatedQuery:
        return self.sql_floor("native", "the query was written as SQL in v2")

    def legacy(self) -> TranslatedQuery:
        self.gap(
            "legacy_query",
            "query",
            "no query type flag is set, so v2 built this with LegacyQueryBuilder, "
            "which stores no operation-level structure",
            dropped=True,
        )
        return self.sql_floor("legacy", "v2 built this with the legacy builder")

    def script(self) -> TranslatedQuery:
        code = self.query.get("script")
        if not code or not code.strip():
            self.gap("empty_script", "script", "the script query has no script", dropped=True)
            return self.result
        self.gap(
            "script_result_shape",
            "script",
            "v2 read a list-of-lists result as a header row plus rows; v3 reads it "
            "with pandas.DataFrame.from_records, which keeps the header as data. A "
            "script that assigns a DataFrame to `results` needs no change",
        )
        self.result.kind = "code"
        self.result.operations = [{"type": "code", "code": code}]
        return self.result

    def sql_floor(self, reason, detail) -> TranslatedQuery:
        """The whole-query floor: v2's own compiled SQL, run as one operation."""
        sql = (self.query.get("sql") or "").strip().rstrip(";")
        if not sql:
            self.gap(
                "no_compiled_sql",
                "query",
                f"{detail}, and v2 stored no compiled SQL to fall back to",
                dropped=True,
            )
            self.result.kind = "none"
            self.result.operations = []
            return self.result

        self.result.kind = "sql"
        self.result.use_live_connection = True
        self.result.operations = [{"type": "sql", "raw_sql": sql, "data_source": self.data_source}]
        self.gap("sql_floor", "query", f"{reason}: kept as one SQL operation")
        return self.result

    # -- the assisted query ------------------------------------------------

    def assisted(self) -> TranslatedQuery:
        try:
            spec = json.loads(self.query.get("json") or "{}") or {}
        except (TypeError, ValueError):
            self.gap("unreadable_json", "json", "the query json did not parse", dropped=True)
            return self.sql_floor("unreadable_json", "the query json did not parse")

        table = (spec.get("table") or {}).get("table")
        if not table:
            # `Query.is_valid` fails, so v2 built no SQL for this at all.
            self.gap("no_source_table", "table", "the query selects no table", dropped=True)
            self.result.kind = "none"
            return self.result

        self.report_legacy_lists(spec)

        operations = [{"type": "source", "table": self.table_ref(table)}]
        operations += self.join_operations(spec)

        filters = self.filter_operations(spec)
        if filters is None:
            return self.floor_or_broken()
        operations += filters

        columns = self.column_plan(spec)
        if columns is None:
            return self.floor_or_broken()
        operations += columns.operations

        operations += self.order_by_operations(columns)
        operations += self.limit_operation(spec)
        operations += self.transform_operations(columns)

        self.result.kind = "builder"
        self.result.operations = operations
        self.result.references = tuple(dict.fromkeys(self.references))
        return self.result

    def floor_or_broken(self) -> TranslatedQuery:
        """An expression stopped the builder path. Where it lands depends on why.

        `BROKEN_IN_V2` means v2 never produced SQL either, so there is no floor.
        """
        if any(gap.kind == "broken_in_v2" for gap in self.result.gaps):
            self.result.kind = "none"
            self.result.operations = []
            return self.result
        return self.sql_floor("expression_needs_sql", "an expression has no operation-level form")

    def report_legacy_lists(self, spec):
        for key in ("measures", "dimensions", "orders"):
            entries = spec.get(key) or []
            known = {(c.get("table"), c.get("column"), c.get("label")) for c in spec.get("columns") or []}
            missing = [c for c in entries if (c.get("table"), c.get("column"), c.get("label")) not in known]
            if missing:
                self.gap(
                    "legacy_column_list",
                    key,
                    f"{len(missing)} column(s) live only in `{key}`, which sql_builder never "
                    f"read, so v2 did not select them either",
                    dropped=True,
                )
        if spec.get("calculations"):
            self.gap("legacy_column_list", "calculations", "`calculations` is read by nothing in v2")

    # -- source and joins --------------------------------------------------

    def table_ref(self, name):
        if name in self.query_map:
            self.references.append(name)
            return {"type": "query", "workbook": self.workbook, "query_name": self.query_map[name]}
        if self.data_source == "Query Store":
            self.gap(
                "unresolved_query_reference",
                name,
                f"{name} is a Query Store table, so it names another v2 query, but no "
                f"v3 query was given for it",
                dropped=True,
            )
        return {"type": "table", "data_source": self.data_source, "table_name": name}

    def join_operations(self, spec):
        operations = []
        for join in spec.get("joins") or []:
            left_table = (join.get("left_table") or {}).get("table")
            right_table = (join.get("right_table") or {}).get("table")
            left_column = (join.get("left_column") or {}).get("column")
            right_column = (join.get("right_column") or {}).get("column")
            if not (left_table and right_table and left_column and right_column):
                self.gap(
                    "invalid_join",
                    right_table or "join",
                    "the join misses a table or a column, and v2 skipped it too",
                )
                continue

            join_type = (join.get("join_type") or {}).get("value") or "inner"
            if join_type not in JOIN_TYPES:
                self.gap("unknown_join_type", right_table, f"join type {join_type!r} is not one v3 has")
                join_type = "inner"

            operations.append(
                {
                    "type": "join",
                    "join_type": join_type,
                    "table": self.table_ref(right_table),
                    "select_columns": [],
                    "join_condition": {
                        "left_column": {"type": "column", "column_name": left_column},
                        "right_column": {"type": "column", "column_name": right_column},
                    },
                }
            )
        return operations

    # -- filters -----------------------------------------------------------

    def filter_operations(self, spec):
        """One `filter_group` with `And`, because v2 combined with `and_` only.

        Returns None when a filter expression cannot be expressed at all.
        """
        prelude = []
        rules = []
        for index, entry in enumerate(spec.get("filters") or []):
            expression = entry.get("expression") or {}
            if expression.get("raw") and expression.get("ast"):
                translated = self.translate_expression(expression, f"filter {index + 1}", f"filter_{index}")
                if translated is None:
                    return None
                prelude += translated.operations
                rules.append({"expression": {"type": "expression", "expression": translated.expression}})
                continue

            rule = self.filter_rule(entry, index)
            if rule is not None:
                rules.append(rule)

        if not rules:
            return prelude
        return [*prelude, {"type": "filter_group", "logical_operator": "And", "filters": rules}]

    def filter_rule(self, entry, index):
        column = entry.get("column") or {}
        operator = (entry.get("operator") or {}).get("value")
        raw_value = (entry.get("value") or {}).get("value")
        label = column.get("column") or f"filter {index + 1}"

        if not (column.get("table") and column.get("column")):
            self.gap("dropped_filter", label, "the filter names no column, and v2 skipped it too")
            return None
        if not operator:
            self.gap("dropped_filter", label, "the filter has no operator, and v2 skipped it too")
            return None

        if operator == "is":
            # v2 read the value as the word "set" or "not set".
            operator = "is_set" if str(raw_value).lower() == "set" else "is_not_set"
            raw_value = None

        if operator in ("is_set", "is_not_set"):
            # v2 ignored the value here; v3 also treats an empty string as unset
            # for a string column, which v2 did not.
            return {
                "column": {"type": "column", "column_name": column["column"]},
                "operator": operator,
                "value": None,
            }

        if not raw_value:
            # `LabelValue.is_valid` is `bool(value)`, so v2 dropped this filter -
            # including a genuine `= 0`.
            self.gap(
                "dropped_filter",
                label,
                f"the value is {raw_value!r}, which v2 read as unset and skipped",
            )
            return None

        if operator == "timespan":
            operator = "within"
        elif operator not in DIRECT_OPERATORS:
            self.gap("unknown_operator", label, f"operator {operator!r} has no v3 form", dropped=True)
            return None

        value = self.filter_value(operator, raw_value, label)
        if value is _UNUSABLE:
            return None

        return {
            "column": {"type": "column", "column_name": column["column"]},
            "operator": operator,
            "value": value,
        }

    def filter_value(self, operator, raw_value, label):
        if operator in ("in", "not_in"):
            values = raw_value if isinstance(raw_value, list) else [raw_value]
            return [v.get("value") if isinstance(v, dict) else v for v in values]

        if operator == "between":
            parts = raw_value if isinstance(raw_value, list) else str(raw_value).split(",")
            if len(parts) != 2:
                self.gap(
                    "broken_filter",
                    label,
                    f"a between filter needs two bounds, got {len(parts)}; v2 raised on this too",
                    dropped=True,
                )
                return _UNUSABLE
            bounds = [_as_date(part) for part in parts]
            if None in bounds:
                self.gap(
                    "broken_filter",
                    label,
                    f"the between bounds {raw_value!r} are not dates. v2 ran both through "
                    f"getdate(), which raised, so this query failed whenever it ran",
                    dropped=True,
                )
                return _UNUSABLE
            # v2 widened the end bound to the end of that day. v3 only widens a
            # bound with no time in it, so both are written out here.
            return [f"{bounds[0]} 00:00:00", f"{bounds[1]} 23:59:59"]

        if isinstance(raw_value, list):
            return [v.get("value") if isinstance(v, dict) else v for v in raw_value]
        return raw_value

    # -- columns -----------------------------------------------------------

    def column_plan(self, spec):
        """Split `columns` the way `sql_builder.process_columns` did.

        Returns None when an expression stops the builder path.
        """
        plan = _ColumnPlan()
        columns = spec.get("columns") or []
        # v2 emitted a GROUP BY only when a column aggregated, so whether this
        # query summarizes at all is known before any column is translated -
        # and it decides where a granularity goes.
        summarizing = any(_aggregates(column) for column in columns)

        for index, column in enumerate(columns):
            entry = self.prepare_column(column, index, plan, summarizing)
            if entry is _UNUSABLE:
                return None
            if entry is None:
                continue
            plan.columns.append(entry)

        if plan.measures():
            operations = [
                *plan.operations,
                {
                    "type": "summarize",
                    "measures": [entry.measure for entry in plan.measures()],
                    "dimensions": plan.dimensions(),
                },
            ]
            for entry in plan.columns:
                if entry.loose:
                    self.gap(
                        "grouped_loose_column",
                        entry.name,
                        "v2 selected this numeric column without grouping by it, which only "
                        "MySQL's loose grouping allowed. v3 groups by it",
                    )
        else:
            operations = plan.operations + self.projection(plan)

        plan.operations = operations
        return plan

    def projection(self, plan):
        """No aggregating column means v2 emitted no GROUP BY - just a SELECT."""
        operations = []
        if not plan.columns:
            return operations
        for entry in plan.columns:
            if entry.rename_from and entry.rename_from != entry.name:
                operations.append(
                    {
                        "type": "rename",
                        "column": {"type": "column", "column_name": entry.rename_from},
                        "new_name": entry.name,
                    }
                )
        operations.append({"type": "select", "column_names": [entry.name for entry in plan.columns]})
        return operations

    def prepare_column(self, column, index, plan, summarizing):
        aggregation = (column.get("aggregation") or "").lower()
        is_aggregate = aggregation not in NON_AGGREGATIONS
        data_type = column.get("type") or "String"
        expression = column.get("expression") or {}
        has_expression = bool(expression.get("raw") and expression.get("ast"))
        name = column.get("alias") or column.get("label") or column.get("column")

        if not has_expression and not (column.get("table") and column.get("column")):
            # `Column.is_valid` fails, and v2 skipped it.
            self.gap("dropped_column", name or f"column {index + 1}", "the column names no table")
            return None
        if has_expression and not name:
            self.gap("dropped_column", f"column {index + 1}", "an expression column with no alias")
            return None

        if has_expression:
            translated = self.translate_expression(expression, name, f"column_{index}")
            if translated is None:
                return _UNUSABLE
            if is_aggregate or _is_aggregating(expression.get("ast")):
                # A reduction belongs inside `summarize`, where ibis expects one.
                plan.operations += translated.prelude
                return _Entry(
                    name=name,
                    measure={
                        "measure_name": name,
                        "expression": {"type": "expression", "expression": translated.expression},
                        "data_type": _measure_type(data_type),
                    },
                    order=column.get("order"),
                    aggregation=aggregation,
                )
            plan.operations += translated.operations
            source_name = translated.column_name or name
            return _Entry(
                name=source_name,
                dimension=_dimension(source_name, source_name, data_type, None),
                order=column.get("order"),
                loose=data_type in MEASURE_TYPES,
                aggregation=aggregation,
            )

        source = column["column"]
        granularity = column.get("granularity") or ""
        if granularity and data_type not in DATE_TYPES:
            # `Column.has_granularity` is date-only, so v2 ignored this.
            self.gap(
                "ignored_granularity",
                name,
                f"granularity {granularity!r} on a {data_type} column, which v2 ignored",
            )
            granularity = ""

        if is_aggregate:
            if granularity:
                self.gap(
                    "ignored_granularity",
                    name,
                    f"v2 applied granularity {granularity!r} on top of the {aggregation} "
                    f"aggregate; v3 has no place for it",
                    dropped=False,
                )
            return _Entry(
                name=name,
                measure=self.measure(column, name, source, aggregation, data_type),
                order=column.get("order"),
                aggregation=aggregation,
            )

        # A dimension carries its granularity only inside a `summarize`. In a
        # projection, and for any bucket v3 has no granularity for, the value
        # has to be computed by a `mutate` instead.
        on_the_dimension = summarizing and GRANULARITY_TO_V3.get(granularity)
        if granularity and not on_the_dimension:
            derived = self.granularity_mutate(source, name, granularity)
            if derived is None:
                self.gap("unknown_granularity", name, f"granularity {granularity!r} has no v3 form")
            else:
                plan.operations.append(derived)
                if granularity in GRANULARITY_IS_A_PART:
                    self.gap(
                        "granularity_part_type",
                        name,
                        f"v2 formatted {granularity!r} as a string; v3's "
                        f"{GRANULARITY_PARTS[granularity]}() returns a number",
                    )
                return _Entry(
                    name=name,
                    dimension=_dimension(name, name, "String", None),
                    order=column.get("order"),
                    aggregation=aggregation,
                )

        return _Entry(
            name=name,
            dimension=_dimension(name, source, data_type, on_the_dimension or None),
            order=column.get("order"),
            rename_from=source,
            loose=data_type in MEASURE_TYPES,
            aggregation=aggregation,
        )

    def measure(self, column, name, source, aggregation, data_type):
        v3_aggregation = V2_TO_V3_AGGREGATION.get(aggregation)
        if not v3_aggregation:
            self.gap("unknown_aggregation", name, f"aggregation {aggregation!r} has no v3 form", dropped=True)
            v3_aggregation = "sum"

        if v3_aggregation == "count":
            # `Aggregations.apply` compiled every v2 count to COUNT(*), whatever
            # column it named. Counting the column instead would drop nulls.
            return {
                "measure_name": name,
                "column_name": "count",
                "aggregation": "count",
                "data_type": "Integer",
            }

        return {
            "measure_name": name,
            "column_name": source,
            "aggregation": v3_aggregation,
            "data_type": _measure_type(data_type),
        }

    def granularity_mutate(self, source, name, granularity):
        """Reproduce a v2 bucket that no v3 dimension granularity can hold.

        The three maps are the expression translator's, because they are the
        same v2 granularity names `date_format` took.
        """
        column = reference(source)
        if granularity in GRANULARITY_STARTS:
            expression = f"{GRANULARITY_STARTS[granularity]}({column})"
        elif granularity in GRANULARITY_PARTS:
            expression = f"{GRANULARITY_PARTS[granularity]}({column})"
        elif granularity in GRANULARITY_FORMATS:
            expression = f"format_date({column}, {json.dumps(GRANULARITY_FORMATS[granularity])})"
        else:
            return None
        return {
            "type": "mutate",
            "new_name": name,
            "data_type": "Auto",
            "expression": {"type": "expression", "expression": expression},
        }

    # -- expressions -------------------------------------------------------

    def translate_expression(self, expression, label, prefix):
        """Translate one v2 expression, and report what it forced.

        Returns None when the expression stops the whole query.
        """
        try:
            translation = translate(
                expression.get("ast"),
                table_columns=self.table_columns,
                fragment_prefix=prefix,
            )
        except TranslationError as error:
            self.gap("untranslatable_expression", label, str(error), dropped=True)
            return None

        if translation.outcome is Outcome.BROKEN_IN_V2:
            for blocker in translation.blockers:
                self.gap("broken_in_v2", label, f"{blocker.function}: {blocker.reason}", dropped=True)
            return None

        if translation.outcome is Outcome.COMPILED_SQL:
            for blocker in translation.blockers:
                self.gap("expression_needs_sql", label, f"{blocker.function}: {blocker.reason}", dropped=True)
            return None

        prelude = []
        for fragment in translation.fragments:
            if fragment.is_ambiguous:
                self.gap(
                    "ambiguous_fragment",
                    label,
                    f"stripping the table qualifier off {fragment.source!r} guessed at "
                    f"{', '.join(fragment.ambiguous_columns) or 'a column'}",
                )
            prelude.append(self.sql_column(fragment.name, fragment.sql))

        # When the whole expression is one fragment, the fragment *is* the
        # column, so it takes the name the user already knows and no `mutate`
        # has to wrap it.
        single = len(translation.fragments) == 1 and translation.expression == reference(
            translation.fragments[0].name
        )
        if single:
            fragment = translation.fragments[0]
            column_name = fragment.label or label
            return _TranslatedExpression(
                expression=translation.expression,
                prelude=prelude,
                operations=[self.sql_column(column_name, fragment.sql)],
                column_name=column_name,
            )

        mutate = {
            "type": "mutate",
            "new_name": label,
            "data_type": "Auto",
            "expression": {"type": "expression", "expression": translation.expression},
        }
        return _TranslatedExpression(
            expression=translation.expression,
            prelude=prelude,
            operations=[*prelude, mutate],
            column_name=label,
        )

    def sql_column(self, name, fragment):
        # `data_source` has to be set, or sqlglot parses v2's backtick
        # identifiers with the default dialect and rejects them.
        return {
            "type": "sql_column",
            "new_name": name,
            "data_type": "Auto",
            "fragment": fragment,
            "data_source": self.data_source,
        }

    # -- order, limit, transforms -----------------------------------------

    def order_by_operations(self, plan):
        operations = []
        for entry in plan.columns:
            if entry.order not in ("asc", "desc"):
                continue
            operations.append(
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": entry.name},
                    "direction": entry.order,
                }
            )
        return operations

    def limit_operation(self, spec):
        limit = spec.get("limit")
        if not limit:
            return []
        return [{"type": "limit", "limit": int(limit)}]

    def transform_operations(self, plan):
        """v2 ran these in pandas over the fetched rows, so they come last."""
        operations = []
        transforms = self.query.get("transforms") or []

        # `apply_transforms` returns on the first of these, so a query with a
        # pivot never reached its cumulative sums.
        for transform in transforms:
            kind = transform.get("type")
            if kind == "Pivot":
                return self.pivot(plan, transform)
            if kind == "Transpose":
                self.gap(
                    "unsupported_transform",
                    "Transpose",
                    "v3 has no transpose; the query converts without it",
                    dropped=True,
                )
                return operations
            if kind == "Unpivot":
                self.gap(
                    "unsupported_transform",
                    "Unpivot",
                    "v3 has no unpivot; the query converts without it",
                    dropped=True,
                )
                return operations

        cumulative = [
            (transform.get("options") or {}).get("column")
            if isinstance(transform.get("options"), dict)
            else _parse_options(transform.get("options")).get("column")
            for transform in transforms
            if transform.get("type") == "CumulativeSum"
        ]
        cumulative += [entry.name for entry in plan.columns if entry.aggregation in CUMULATIVE_AGGREGATIONS]

        for name in dict.fromkeys(filter(None, cumulative)):
            operations.append(self.cumulative_mutate(name, plan))
        return operations

    def cumulative_mutate(self, name, plan):
        """v2 ran `cumsum` over the fetched rows, in whatever order they arrived.

        A window needs an order to be reproducible, so the query's own sort is
        used, and the first dimension when it has none.
        """
        sorted_by = next((entry for entry in plan.columns if entry.order in ("asc", "desc")), None)
        if sorted_by is not None:
            # The running total has to climb the rows in the order they are
            # returned in, so a descending sort makes a descending window.
            order = (
                f"desc({reference(sorted_by.name)})"
                if sorted_by.order == "desc"
                else reference(sorted_by.name)
            )
        else:
            first = next((entry.name for entry in plan.dimension_entries()), None)
            order = reference(first) if first else None
        if order is None:
            self.gap(
                "cumulative_without_order",
                name,
                "the query sorts by nothing, so the running total follows an order the "
                "database is free to change",
            )
        if _sanitize(name) != name:
            self.gap(
                "cumulative_column_renamed",
                name,
                f"v2 replaced the column in place; v3 lowercases a mutated name, so the "
                f"running total lands in {_sanitize(name)!r} beside it",
            )
        window = f"ibis.cumulative_window(order_by={order})" if order else "ibis.cumulative_window()"
        return {
            "type": "mutate",
            "new_name": name,
            "data_type": "Auto",
            "expression": {
                "type": "expression",
                "expression": f"{reference(name)}.sum().over({window})",
            },
        }

    def pivot(self, plan, transform):
        options = transform.get("options")
        options = options if isinstance(options, dict) else _parse_options(options)
        index, column, value = options.get("index"), options.get("column"), options.get("value")
        if not (index and column and value):
            self.gap("dropped_transform", "Pivot", "the pivot names no index, column or value", dropped=True)
            return []

        by_name = {entry.name: entry for entry in plan.columns}
        missing = [name for name in (index, column, value) if name not in by_name]
        if missing:
            self.gap(
                "dropped_transform",
                "Pivot",
                f"the pivot reads {', '.join(missing)}, which this query does not produce",
                dropped=True,
            )
            return []

        return [
            {
                "type": "pivot_wider",
                "rows": [_as_dimension(by_name[index])],
                "columns": [_as_dimension(by_name[column])],
                "values": [_as_measure(by_name[value])],
            }
        ]


class _Unusable:
    """Sentinel: this column or filter stops the whole builder path."""

    def __repr__(self):
        return "<unusable>"


_UNUSABLE = _Unusable()


@dataclass
class _TranslatedExpression:
    expression: str
    prelude: list
    operations: list
    column_name: str | None = None


@dataclass
class _Entry:
    """One v2 column, and the v3 shape it takes."""

    name: str
    measure: dict | None = None
    dimension: dict | None = None
    order: str | None = None
    rename_from: str | None = None
    loose: bool = False
    """v2 selected this numeric column without grouping by it."""

    aggregation: str = ""


@dataclass
class _ColumnPlan:
    columns: list = field(default_factory=list)
    operations: list = field(default_factory=list)

    def measures(self):
        return [entry for entry in self.columns if entry.measure]

    def dimension_entries(self):
        return [entry for entry in self.columns if entry.dimension]

    def dimensions(self):
        return [entry.dimension for entry in self.dimension_entries()]


def _dimension(name, column_name, data_type, granularity):
    dimension = {
        "dimension_name": name,
        "column_name": column_name,
        "data_type": data_type if data_type in DIMENSION_TYPES else "String",
    }
    if granularity:
        dimension["granularity"] = granularity
    return dimension


def _measure_type(data_type):
    return data_type if data_type in ("String", "Integer", "Decimal") else "Decimal"


def _as_dimension(entry):
    if entry.dimension:
        return dict(entry.dimension)
    return _dimension(entry.name, entry.name, "String", None)


def _as_measure(entry):
    # v2 pivoted with `aggfunc="sum"`, and v3's pivot_wider aggregates with sum
    # too, so a re-aggregated measure reproduces the v2 numbers.
    return {
        "measure_name": entry.name,
        "column_name": entry.name,
        "aggregation": "sum",
        "data_type": "Decimal",
    }


def _aggregates(column):
    """`Column.is_aggregate`, plus an expression column that calls a reduction."""
    aggregation = (column.get("aggregation") or "").lower()
    if aggregation not in NON_AGGREGATIONS:
        return True
    expression = column.get("expression") or {}
    if expression.get("raw") and expression.get("ast"):
        return _is_aggregating(expression.get("ast"))
    return False


def _is_aggregating(node):
    """True when the expression tree calls a reduction anywhere inside it."""
    if isinstance(node, dict):
        if node.get("type") == "CallExpression" and node.get("function") in AGGREGATING_FUNCTIONS:
            return True
        return any(_is_aggregating(value) for value in node.values())
    if isinstance(node, list):
        return any(_is_aggregating(value) for value in node)
    return False


def _as_date(value):
    """Reduce a bound to its date the way v2's `getdate()` did, or None."""
    match = _DATE.search(str(value or ""))
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _parse_options(options):
    if isinstance(options, dict):
        return options
    try:
        parsed = json.loads(options or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _sanitize(name):
    """`ibis_utils.sanitize_name`, which every mutated column name goes through."""
    if not name:
        return name
    return (
        name.strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace("/", "_")
        .replace("(", "_")
        .replace(")", "_")
        .lower()
    )
