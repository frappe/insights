import datetime
import operator
from contextlib import suppress
from typing import ClassVar, NamedTuple

import frappe
from frappe.utils.data import (
    add_to_date,
    get_date_str,
    get_first_day,
    get_last_day,
    get_quarter_ending,
    get_quarter_start,
    get_year_ending,
    get_year_start,
    getdate,
    nowdate,
)
from sqlalchemy import Column, select, table
from sqlalchemy import column as sa_column
from sqlalchemy.sql import and_, case, distinct, func, or_, text

DATE_TYPES = ("Date", "Datetime")


class Aggregations:
    @classmethod
    def apply(cls, aggregation: str, column=None):
        if not aggregation:
            return column
        if aggregation == "Group By":
            return column

        agg_lower = aggregation.lower()
        if agg_lower == "sum" or agg_lower == "cumulative sum":
            return func.sum(column)
        if agg_lower == "min":
            return func.min(column)
        if agg_lower == "max":
            return func.max(column)
        if agg_lower == "avg":
            return func.avg(column)
        if agg_lower == "count" or agg_lower == "cumulative count":
            return func.count(text("*"))
        if agg_lower == "distinct":
            return distinct(column)
        if agg_lower == "distinct_count":
            return func.count(distinct(column))

        raise NotImplementedError(f"Aggregation {aggregation} not implemented")


class ColumnFormatter:
    @classmethod
    def format(cls, format_options: dict, column_type: str, column: Column) -> Column:
        if format_options and format_options.date_format and column_type in DATE_TYPES:
            date_format = format_options.date_format
            date_format = date_format if isinstance(date_format, str) else date_format.get("value")
            return cls.format_date(date_format, column)
        return column

    @classmethod
    def format_date(cls, format, column: Column):
        if format == "Minute":
            return func.date_format(column, "%Y-%m-%d %H:%i")
        if format == "Hour":
            return func.date_format(column, "%Y-%m-%d %H:00")
        if format == "Day" or format == "Day Short":
            return func.date_format(column, "%Y-%m-%d 00:00")
        if format == "Week":
            # DATE_FORMAT(install_date, '%Y-%m-%d') - INTERVAL (DAYOFWEEK(install_date) - 1) DAY,
            date = func.date_format(column, "%Y-%m-%d")
            dialect = frappe.flags._current_query_dialect
            compiled = column.compile(dialect=dialect)
            return func.DATE_SUB(date, text(f"INTERVAL (DAYOFWEEK({compiled}) - 1) DAY"))
        if format == "Month" or format == "Mon":
            return func.date_format(column, "%Y-%m-01")
        if format == "Year":
            return func.date_format(column, "%Y-01-01")
        if format == "Minute of Hour":
            return func.date_format(column, "00:%M")
        if format == "Hour of Day":
            return func.date_format(column, "%H:00")
        if format == "Day of Week":
            return func.date_format(column, "%W")
        if format == "Day of Month":
            return func.date_format(column, "%d")
        if format == "Day of Year":
            return func.date_format(column, "%j")
        if format == "Month of Year":
            return func.date_format(column, "%M")
        if format == "Quarter of Year":
            return func.quarter(column)
        if format == "Quarter":
            # 2022-02-12 -> 2022-01-01
            # STR_TO_DATE(CONCAT(YEAR(CURRENT_DATE), '-', (QUARTER(CURRENT_DATE) * 3) - 2, '-01'), '%Y-%m-%d')
            return func.str_to_date(
                func.concat(
                    func.year(column),  # 2018
                    "-",  # 2018-
                    (func.quarter(column) * 3) - 2,  # 2018-4
                    "-01",  # 2018-4-01
                ),
                "%Y-%m-%d",
            )
        else:
            return func.date_format(column, format)


class Functions:
    @classmethod
    def apply(cls, function, *args):
        if function == "now":
            return func.now()
        if function == "today":
            return func.date(func.now())
        if function == "sql":
            assert isinstance(args[0], str)
            return text(args[0])
        if function == "abs":
            return func.abs(args[0])
        if function == "floor":
            return func.floor(args[0])
        if function == "lower":
            return func.lower(args[0])
        if function == "upper":
            return func.upper(args[0])
        if function == "ceil":
            return func.ceil(args[0])
        if function == "round":
            return func.round(args[0])
        if function == "is_set":
            return args[0].isnot(None)
        if function == "is_not_set":
            return args[0].is_(None)
        if function == "count_if":
            return func.sum(case((args[0], 1), else_=0))
        if function == "distinct":
            return distinct(args[0])
        if function == "distinct_count":
            return func.count(distinct(args[0]))
        if function == "in_":
            # args = [column, value1, value2, ...]
            return args[0].in_(args[1:])
        if function == "not_in":
            # args = [column, value1, value2, ...]
            return args[0].notin_(args[1:])
        if function == "contains":
            return args[0].like("%" + args[1] + "%")
        if function == "not_contains":
            return ~args[0].like("%" + args[1] + "%")
        if function == "ends_with":
            return args[0].like("%" + args[1])
        if function == "starts_with":
            return args[0].like(args[1] + "%")
        if function == "if_null":
            return func.ifnull(args[0], args[1])
        if function == "sum_if":
            return func.sum(case((args[0], args[1]), else_=0))
        if function == "between":
            dates = add_start_and_end_time([args[1], args[2]])
            return args[0].between(*dates)
        if function == "replace":
            return func.replace(args[0], args[1], args[2])
        if function == "substring":
            return func.substring(args[0], args[1], args[2])
        if function == "concat":
            return func.concat(*args)
        if function == "coalesce":
            return func.coalesce(*args)

        if function == "case":
            _args = list(args)
            if len(_args) % 2 == 0:
                raise Exception("Case function requires an odd number of arguments")
            default = _args.pop()
            conditions = []
            for i in range(0, len(_args), 2):
                conditions.append((_args[i], _args[i + 1]))
            # return case(conditions, else_=default)
            return case(*conditions, else_=default)

        if function == "timespan":
            return handle_timespan(args[0], args[1])

        if function == "time_elapsed":
            VALID_UNITS = [
                "MICROSECOND",
                "SECOND",
                "MINUTE",
                "HOUR",
                "DAY",
                "WEEK",
                "MONTH",
                "QUARTER",
                "YEAR",
            ]
            unit = args[0].upper()
            if unit not in VALID_UNITS:
                raise Exception(f"Invalid unit {unit}. Valid units are {', '.join(VALID_UNITS)}")
            return func.timestampdiff(text(unit), args[1], args[2])

        if function == "descendants":
            node = args[0]  # "India"
            tree = args[1]  # "territory"
            field = args[2]  # salesorder.territory
            query = get_descendants(node, tree, include_self=False)
            return field.in_(query)

        if function == "descendants_and_self":
            node = args[0]  # "India"
            tree = args[1]  # "territory"
            field = args[2]  # salesorder.territory
            query = get_descendants(node, tree, include_self=True)
            return field.in_(query)

        if function == "date_format":
            return ColumnFormatter.format_date(args[1], args[0])

        if function == "start_of":
            valid_units = ["day", "week", "month", "quarter", "year"]
            unit = args[0].lower()
            if unit not in valid_units:
                raise Exception(f"Invalid unit {unit}. Valid units are {', '.join(valid_units)}")
            return ColumnFormatter.format_date(args[0].title(), args[1])

        raise NotImplementedError(f"Function {function} not implemented")


def handle_timespan(column, timespan):
    dates = add_start_and_end_time(list(resolve_timespan(timespan)))
    return column.between(*dates)


def resolve_timespan(timespan) -> tuple[datetime.date, datetime.date]:
    """The dates a `within` value covers, as (start, end).

    A filter tests one span and a span number card groups by several, so both
    read a span the same way.
    """
    return get_window(*read_timespan(timespan))


def read_timespan(timespan) -> tuple[str, datetime.date | None]:
    """The span a `within` filter names, and the date to resolve it against.

    A filter written before periods names the span alone, as a string or as the
    words of one, and resolves against today. A period also pins the anchor, and
    a comparison span moves it, so both arrive beside the span.
    """
    if isinstance(timespan, list):
        # the column header seeds the count as a number, so the words are not all
        # strings
        return " ".join(str(word) for word in timespan), None
    if isinstance(timespan, str):
        return timespan, None
    if not isinstance(timespan, dict) or not timespan.get("span"):
        raise Exception(f"Invalid timespan {timespan}")

    anchor = getdate(timespan.get("anchor") or nowdate())
    shift = timespan.get("shift") or {}
    if shift.get("unit"):
        anchor = shift_anchor(anchor, shift["unit"], shift.get("count") or 0)

    return timespan["span"], anchor


def get_descendants(node, tree, include_self=False):
    Tree = table(tree, sa_column("lft"), sa_column("rgt"), sa_column("name"))
    lft_rgt = select(Tree.c.lft, Tree.c.rgt).where(Tree.c.name == node).alias("lft_rgt")
    return (
        (select(Tree.c.name).where(Tree.c.lft > lft_rgt.c.lft).where(Tree.c.rgt < lft_rgt.c.rgt))
        if not include_self
        else (select(Tree.c.name).where(Tree.c.lft >= lft_rgt.c.lft).where(Tree.c.rgt <= lft_rgt.c.rgt))
    )


DATE_UNITS = (
    "day",
    "week",
    "month",
    "quarter",
    "year",
    "fiscal year",
)


WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def get_week_start_day_index():
    day = frappe.db.get_single_value("Insights Settings", "week_starts_on") or "Monday"
    return WEEKDAYS.index(day)


def get_first_day_of_week(date):
    date = getdate(date)
    return date - datetime.timedelta(days=(date.weekday() - get_week_start_day_index()) % 7)


def get_last_day_of_week(date):
    return get_first_day_of_week(date) + datetime.timedelta(days=6)


def get_current_date_range(unit, anchor=None):
    today = anchor or nowdate()
    if unit == "day":
        today_date = getdate(today)
        return [today_date, today_date]
    if unit == "week":
        return [get_first_day_of_week(today), get_last_day_of_week(today)]
    if unit == "month":
        return [get_first_day(today), get_last_day(today)]
    if unit == "quarter":
        return [get_quarter_start(today), get_quarter_ending(today)]
    if unit == "year":
        return [get_year_start(today), get_year_ending(today)]
    if unit == "fiscal year":
        return [get_fy_start(today), get_fiscal_year_ending(today)]


def get_fiscal_year_start_date():
    fiscal_year_start = frappe.db.get_single_value("Insights Settings", "fiscal_year_start")
    if not fiscal_year_start or get_date_str(fiscal_year_start) == "0001-01-01":
        return getdate("1995-04-01")
    return getdate(fiscal_year_start)


def get_fy_start(date):
    fy_start = get_fiscal_year_start_date()
    dt = getdate(date)  # eg. 2019-01-01
    if dt.month < fy_start.month:
        return getdate(f"{dt.year - 1}-{fy_start.month}-{fy_start.day}")  # eg. 2018-04-01
    return getdate(f"{dt.year}-{fy_start.month}-{fy_start.day}")  # eg. 2019-04-01


def get_fiscal_year_ending(date):
    fy_start = get_fiscal_year_start_date()
    fy_end = add_to_date(fy_start, years=1, days=-1)
    dt = getdate(date)  # eg. 2019-04-01
    if dt.month < fy_start.month:
        return getdate(f"{dt.year}-{fy_end.month}-{fy_end.day}")  # eg. 2018-03-31
    return getdate(f"{dt.year + 1}-{fy_end.month}-{fy_end.day}")  # eg. 2019-03-31


def get_directional_date_range(direction, unit, number_of_unit, anchor=None):
    """The N whole periods on one side of the anchor's own period.

    The anchor's period is never one of them: the span starts at the period next
    to it and runs N periods outwards. So one end is one period away and the
    other is N, and the direction says which of the two opens the range:
    backwards the N-th period opens it, forwards it closes it.
    """
    dates = []
    today = anchor or nowdate()
    opens, closes = (number_of_unit, 1) if direction < 0 else (1, number_of_unit)
    start, end = direction * opens, direction * closes
    if unit == "day":
        dates = [
            add_to_date(today, days=start),
            add_to_date(today, days=end),
        ]
    if unit == "week":
        dates = [
            get_first_day_of_week(add_to_date(today, days=start * 7)),
            get_last_day_of_week(add_to_date(today, days=end * 7)),
        ]
    if unit == "month":
        dates = [
            get_first_day(add_to_date(today, months=start)),
            get_last_day(add_to_date(today, months=end)),
        ]
    if unit == "quarter":
        dates = [
            get_quarter_start(add_to_date(today, months=start * 3)),
            get_quarter_ending(add_to_date(today, months=end * 3)),
        ]
    if unit == "year":
        dates = [
            get_year_start(add_to_date(today, years=start)),
            get_year_ending(add_to_date(today, years=end)),
        ]
    if unit == "fiscal year":
        dates = [
            get_fy_start(add_to_date(today, years=start)),
            get_fiscal_year_ending(add_to_date(today, years=end)),
        ]

    if isinstance(dates[0], str):
        dates[0] = getdate(dates[0])
    if isinstance(dates[1], str):
        dates[1] = getdate(dates[1])

    return dates


class Span(NamedTuple):
    """A relative span, read.

    `shape` is one of "to date", "current", "last", "next". `count` is how many
    whole periods a "last" or "next" span covers, one otherwise.
    """

    shape: str
    unit: str
    count: int
    include_current: bool


def parse_span(span: str) -> Span | None:
    """The grammar, read once.

        <unit> to date          the period so far, up to the anchor
        current <unit>          the whole period the anchor falls in
        last <N> <unit>s        N whole periods behind the current one
        next <N> <unit>s        N whole periods ahead of it
        … (include current)     extends a "last" or "next" span over the current

    A "last" or "next" span that names no count covers one period: "last month"
    reads as "last 1 month".

    One parser for this runtime. The browser reads the same grammar, in
    `frontend/src2/helpers/span_grammar.ts`, which is also where the grammar is
    written down. A span it writes is a span this runs.
    """
    if not isinstance(span, str):
        return None

    rest = " ".join(span.lower().split())
    include_current = "(include current)" in rest
    rest = rest.replace("(include current)", "").strip()

    if rest.endswith("to date"):
        # A count and "to date" cannot both be said: the period so far is one
        # period, so "last 7 days to date" names nothing.
        unit = _span_unit_word(rest[: -len("to date")])
        return Span("to date", unit, 1, False) if unit else None

    words = rest.split(" ")
    head, tail = words[0], words[1:]

    if head == "current":
        unit = _span_unit_word(" ".join(tail))
        return Span("current", unit, 1, False) if unit else None

    if head not in ("last", "next"):
        return None

    counted = tail and tail[0].isdigit()
    count = max(1, int(tail[0])) if counted else 1
    unit = _span_unit_word(" ".join(tail[1:] if counted else tail))
    return Span(head, unit, count, include_current) if unit else None


def _span_unit_word(words: str) -> str | None:
    unit = words.strip()
    unit = unit[:-1] if unit.endswith("s") else unit
    return unit if unit in DATE_UNITS else None


def get_date_range(timespan, include_current=False, anchor=None):
    """The days a span covers. `timespan` is "last 7 days", "next 3 months", …

    `include_current` is here for a caller that says it beside the span rather
    than inside it. A span carrying "(include current)" says it for itself.
    """
    parsed = parse_span(timespan)
    if not parsed:
        return None
    return _date_range(parsed, anchor, include_current=include_current)


def _date_range(span: Span, anchor=None, include_current=False):
    if span.shape == "current":
        return get_current_date_range(span.unit, anchor)

    if span.shape not in ("last", "next"):
        return None

    direction = -1 if span.shape == "last" else 1
    dates = get_directional_date_range(direction, span.unit, span.count, anchor)

    if include_current or span.include_current:
        current_dates = get_current_date_range(span.unit, anchor)
        dates[0] = min(dates[0], current_dates[0])
        dates[1] = max(dates[1], current_dates[1])

    return dates


def span_unit(span: str) -> str:
    """The unit a span names ("month", "fiscal year"), read out of the string.

    A caller that needs the unit without resolving the dates asks here rather
    than reading the string again.
    """
    parsed = parse_span(span)
    return parsed.unit if parsed else ""


def get_window(span: str, anchor: datetime.date | None = None) -> tuple[datetime.date, datetime.date]:
    """The dates a span names, as (start, end).

    Accepts every span `get_date_range` accepts, plus "<unit> to date", which
    ends at the anchor instead of at the end of the period. `anchor` defaults to
    today.
    """
    anchor = getdate(anchor or nowdate())

    parsed = parse_span(span)
    if not parsed:
        raise Exception(f"Invalid timespan {span}")

    if parsed.shape == "to date":
        start = get_current_date_range(parsed.unit, anchor)[0]
        return (getdate(start), anchor)

    dates = _date_range(parsed, anchor)
    if not dates:
        raise Exception(f"Invalid timespan {span}")
    return (getdate(dates[0]), getdate(dates[1]))


def shift_anchor(anchor: datetime.date, unit: str, count: int) -> datetime.date:
    """The anchor moved `count` units.

    "The same span a year ago" is `get_window(span, shift_anchor(anchor,
    "year", -1))`. The span is recomputed from the moved anchor, never shifted
    at its endpoints. That is what keeps a to-date span to-date, and it lands a
    leap day or a month end on the nearest real date with no case for either.
    """
    anchor = getdate(anchor)
    unit = unit.lower()

    if unit == "day":
        return getdate(add_to_date(anchor, days=count))
    if unit == "week":
        return getdate(add_to_date(anchor, days=7 * count))
    if unit == "month":
        return getdate(add_to_date(anchor, months=count))
    if unit == "quarter":
        return getdate(add_to_date(anchor, months=3 * count))
    # a fiscal year is twelve months long wherever it starts, so it moves by the year
    if unit == "year" or unit == "fiscal year":
        return getdate(add_to_date(anchor, years=count))

    raise Exception(f"Invalid shift unit - {unit}")


def add_start_and_end_time(dates):
    if not dates:
        return dates

    dates[0] = getdate(dates[0])
    dates[1] = getdate(dates[1])
    dates[0] = dates[0].strftime("%Y-%m-%d 00:00:00")
    dates[1] = dates[1].strftime("%Y-%m-%d 23:59:59")

    return dates


class BinaryOperations:
    ARITHMETIC_OPERATIONS: ClassVar[dict] = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
    }
    COMPARE_OPERATIONS: ClassVar[dict] = {
        "=": operator.eq,
        "!=": operator.ne,
        "<": operator.lt,
        ">": operator.gt,
        "<=": operator.le,
        ">=": operator.ge,
    }
    LOGICAL_OPERATIONS: ClassVar[dict] = {
        "&&": lambda a, b: and_(a, b),
        "||": lambda a, b: or_(a, b),
    }

    @classmethod
    def get_operation(cls, operator):
        if operator in cls.ARITHMETIC_OPERATIONS:
            return cls.ARITHMETIC_OPERATIONS[operator]

        if operator in cls.COMPARE_OPERATIONS:
            return cls.COMPARE_OPERATIONS[operator]

        if operator in cls.LOGICAL_OPERATIONS:
            return cls.LOGICAL_OPERATIONS[operator]

        raise NotImplementedError(f"Operation {operator} not implemented")

    @classmethod
    def is_binary_operator(cls, operator):
        return (
            operator in cls.ARITHMETIC_OPERATIONS
            or operator in cls.COMPARE_OPERATIONS
            or operator in cls.LOGICAL_OPERATIONS
        )


def get_eval_globals():
    function_list = [
        "now",
        "today",
        "sql",
        "abs",
        "floor",
        "lower",
        "upper",
        "ceil",
        "round",
        "is_set",
        "is_not_set",
        "count_if",
        "distinct",
        "distinct_count",
        "in_",
        "not_in",
        "contains",
        "not_contains",
        "ends_with",
        "starts_with",
        "if_null",
        "sum_if",
        "between",
        "replace",
        "concat",
        "coalesce",
        "case",
        "timespan",
        "time_elapsed",
        "descendants",
        "descendants_and_self",
        "date_format",
        "start_of",
        "substring",
        "sum",
        "min",
        "max",
        "avg",
        "count",
        "distinct",
        "distinct_count",
        "and_",
        "or_",
    ]

    eval_globals = {}
    for fn in function_list:
        eval_globals[fn] = lambda *args, fn=fn: call_function(fn, *args)

    return eval_globals


def call_function(function, *args):
    if not function:
        return None

    if function == "and_":
        return and_(*args)
    if function == "or_":
        return or_(*args)

    with suppress(NotImplementedError):
        _func = "in_" if function == "in" else function
        return Functions.apply(_func, *args)

    if len(args) <= 2:
        with suppress(NotImplementedError):
            return Aggregations.apply(function, *args)

    raise NotImplementedError(f"Function {function} not implemented")
