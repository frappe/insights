import frappe
import ibis
from ibis import _
from ibis import selectors as s
from ibis.expr.types import Column, NumericColumn, StringColumn, TimestampColumn, Value

# generic functions
f_count = Column.count
f_min = Column.min
f_max = Column.max
f_group_concat = Column.group_concat
f_is_in = Value.isin
f_is_not_in = Value.notin
f_is_set = Value.notnull
f_is_not_set = Value.isnull
f_is_between = Value.between
f_coalesce = Value.coalesce
f_distinct_count = Column.nunique
f_sum_if = lambda condition, column: f_sum(column, where=condition)
f_count_if = lambda condition, column: f_count(column, where=condition)
f_if_else = (
    lambda condition, true_value, false_value: ibis.case()
    .when(condition, true_value)
    .else_(false_value)
    .end()
)
f_case = lambda *args: ibis.case().when(*args).end()
f_sql = lambda query: _.sql(query)
f_asc = ibis.asc
f_desc = ibis.desc


# number Functions
f_abs = NumericColumn.abs
f_sum = NumericColumn.sum
f_avg = NumericColumn.mean
f_round = NumericColumn.round
f_floor = NumericColumn.floor
f_ceil = NumericColumn.ceil

# String Functions
f_lower = StringColumn.lower
f_upper = StringColumn.upper
f_concat = StringColumn.concat
f_replace = StringColumn.replace
f_substring = StringColumn.substr
f_contains = StringColumn.contains
f_not_contains = lambda args, kwargs: ~f_contains(args, kwargs)
f_starts_with = StringColumn.startswith
f_ends_with = StringColumn.endswith


# date functions
f_year = TimestampColumn.year
f_quarter = TimestampColumn.quarter
f_month = TimestampColumn.month
f_week_of_year = TimestampColumn.week_of_year
f_day_of_year = TimestampColumn.day_of_year
f_day_of_week = TimestampColumn.day_of_week
f_day = TimestampColumn.day
f_hour = TimestampColumn.hour
f_minute = TimestampColumn.minute
f_second = TimestampColumn.second
f_microsecond = TimestampColumn.microsecond
f_now = ibis.now
f_today = ibis.today
f_format_date = TimestampColumn.strftime
f_date_diff = TimestampColumn.delta
f_start_of = lambda unit, date: None  # TODO
f_is_within = lambda args, kwargs: None  # TODO

# utility functions
f_to_inr = lambda curr, amount, rate=83: f_if_else(curr == "USD", amount * rate, amount)
f_to_usd = lambda curr, amount, rate=83: f_if_else(curr == "INR", amount / rate, amount)
f_literal = ibis.literal
f_row_number = ibis.row_number
f_previous_period_value = lambda column, date_column, offset=1: column.lag(offset).over(
    group_by=(~s.numeric() & ~s.matches(date_column)),
    order_by=ibis.asc(date_column),
)
f_next_period_value = lambda column, date_column, offset=1: column.lead(offset).over(
    group_by=(~s.numeric() & ~s.matches(date_column)),
    order_by=ibis.asc(date_column),
)


def get_functions():
    context = frappe._dict()

    functions = globals()
    for key in functions:
        if key.startswith("f_"):
            context[key[2:]] = functions[key]

    selectors = frappe._dict()
    for key in get_whitelisted_selectors():
        selectors[key] = getattr(s, key)

    context["s"] = selectors
    context["selectors"] = selectors

    return context


@frappe.whitelist()
def get_function_list():
    return [key for key in get_functions() if not key.startswith("_")]


def get_whitelisted_selectors():
    # all the selectors that are decorated with @public
    # are added to __all__ in the selectors module
    # check: ibis.selectors.py & public.py
    try:
        whitelisted_selectors = s.__dict__["__all__"]
    except KeyError:
        whitelisted_selectors = []
    return whitelisted_selectors
