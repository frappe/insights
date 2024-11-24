import math

import frappe
import ibis
from ibis import _
from ibis import selectors as s

# from ibis.expr.types.numeric import NumericValue
# from ibis.expr.types.strings import StringValue
# from ibis.expr.types.temporal import DateValue, TimestampValue

# aggregate functions
f_count = lambda column, *args, **kwargs: column.count(*args, **kwargs)
f_min = lambda column, *args, **kwargs: column.min(*args, **kwargs)
f_max = lambda column, *args, **kwargs: column.max(*args, **kwargs)
f_sum = lambda column, *args, **kwargs: column.sum(*args, **kwargs)
f_avg = lambda column, *args, **kwargs: column.mean(*args, **kwargs)
f_group_concat = lambda column, *args, **kwargs: column.group_concat(*args, **kwargs)
f_distinct_count = lambda column: column.nunique()
f_sum_if = lambda condition, column: f_sum(column, where=condition)
f_count_if = lambda condition, column: f_count(column, where=condition)
f_distinct_count_if = lambda condition, column: column.nunique(where=condition)

# boolean functions
f_is_in = lambda column, *values: column.isin(values)
f_is_not_in = lambda column, *values: column.notin(values)
f_is_set = lambda column: column.notnull()
f_is_not_set = lambda column: column.isnull()
f_is_between = lambda column, start, end: column.between(start, end)
f_is_not_between = lambda column, start, end: ~column.between(start, end)
f_is_within = lambda args, kwargs: None  # TODO

# conditional functions
f_if_else = (
    lambda condition, true_value, false_value: ibis.case()
    .when(condition, true_value)
    .else_(false_value)
    .end()
)


def f_case(*args):
    # args = [condition1, value1, condition2, value2, ..., default_value]
    if len(args) % 2 == 0:
        raise ValueError("Odd number of arguments expected")

    case = ibis.case()
    for i in range(0, len(args) - 1, 2):
        case = case.when(args[i], args[i + 1])

    return case.else_(args[-1]).end()


# number Functions
f_abs = lambda column, *args, **kwargs: column.abs(*args, **kwargs)
f_round = lambda column, *args, **kwargs: column.round(*args, **kwargs)
f_floor = lambda column, *args, **kwargs: column.floor(*args, **kwargs)
f_ceil = lambda column, *args, **kwargs: column.ceil(*args, **kwargs)

# String Functions
f_lower = lambda column, *args, **kwargs: column.lower(*args, **kwargs)
f_upper = lambda column, *args, **kwargs: column.upper(*args, **kwargs)
f_concat = lambda column, *args, **kwargs: column.concat(*args, **kwargs)
f_replace = lambda column, *args, **kwargs: column.replace(*args, **kwargs)
f_substring = lambda column, *args, **kwargs: column.substr(*args, **kwargs)
f_contains = lambda column, *args, **kwargs: column.contains(*args, **kwargs)
f_not_contains = lambda column, *args, **kwargs: ~column.contains(*args, **kwargs)
f_starts_with = lambda column, *args, **kwargs: column.startswith(*args, **kwargs)
f_ends_with = lambda column, *args, **kwargs: column.endswith(*args, **kwargs)
f_length = lambda column, *args, **kwargs: column.length(*args, **kwargs)

# date functions
f_year = lambda column: column.year()
f_quarter = lambda column: column.quarter()
f_month = lambda column: column.month()
f_week_of_year = lambda column: column.week_of_year()
f_day_of_year = lambda column: column.day_of_year()
f_day_of_week = lambda column: column.day_of_week()
f_day = lambda column: column.day()
f_hour = lambda column: column.hour()
f_minute = lambda column: column.minute()
f_second = lambda column: column.second()
f_microsecond = lambda column: column.microsecond()
f_format_date = lambda column, *args, **kwargs: column.strftime(*args, **kwargs)
f_date_diff = lambda column, *args, **kwargs: column.delta(*args, **kwargs)
f_now = ibis.now
f_today = ibis.today
f_start_of = lambda unit, date: None  # TODO

# utility functions
f_to_inr = lambda curr, amount, rate=83: f_if_else(curr == "USD", amount * rate, amount)
f_to_usd = lambda curr, amount, rate=83: f_if_else(curr == "INR", amount / rate, amount)
f_literal = ibis.literal
f_row_number = ibis.row_number
f_sql = lambda query: _.sql(query)
f_coalesce = ibis.coalesce
f_if_null = ibis.coalesce
f_asc = ibis.asc
f_desc = ibis.desc


def f_previous_value(column, group_by, order_by, offset=1):
    return column.lag(offset).over(group_by=group_by, order_by=order_by)


def f_next_value(column, group_by, order_by, offset=1):
    return column.lead(offset).over(group_by=group_by, order_by=order_by)


def f_previous_period_value(column, date_column, offset=1):
    date_column_name = (
        date_column.get_name() if hasattr(date_column, "get_name") else date_column
    )
    return column.lag(offset).over(
        group_by=(~s.numeric() & ~s.matches(date_column_name)),
        order_by=ibis.asc(date_column_name),
    )


def f_next_period_value(column, date_column, offset=1):
    date_column_name = (
        date_column.get_name() if hasattr(date_column, "get_name") else date_column
    )
    return column.lead(offset).over(
        group_by=(~s.numeric() & ~s.matches(date_column_name)),
        order_by=ibis.asc(date_column_name),
    )


def f_percentage_change(column, date_column, offset=1):
    prev_value = f_previous_period_value(column, date_column, offset)
    return ((column - prev_value) * 100) / prev_value


def f_is_first_row(group_by, order_by, sort_order="asc"):
    _order_by = ibis.asc(order_by) if sort_order == "asc" else ibis.desc(order_by)
    row_number = f_row_number().over(group_by=group_by, order_by=_order_by)
    return f_if_else(row_number == 1, 1, 0)


def f_create_buckets(column, num_buckets):
    query = frappe.flags.current_ibis_query
    if query is None:
        frappe.throw("Failed to create buckets. Query not found")

    values_df = query.select(column).distinct().execute()
    values = [v[0] for v in values_df.values.tolist()]
    values = sorted(values)

    if not values:
        frappe.throw("Failed to create buckets. No data found in the column")

    if len(values) < num_buckets:
        frappe.throw(
            "Number of unique values in the column is less than the number of buckets"
        )

    bucket_size = math.ceil(len(values) / num_buckets)
    buckets = []
    for i in range(0, len(values), bucket_size):
        buckets.append(values[i : i + bucket_size])

    case = ibis.case()
    for bucket in buckets:
        min_val = bucket[0]
        max_val = bucket[-1]
        label = f"{min_val}-{max_val}"
        case = case.when(f_is_in(column, *bucket), label)

    return case.else_(None).end()


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
