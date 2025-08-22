import math

import frappe
import ibis
import ibis.expr.types as ir
import ibis.selectors as s
from ibis import _

from insights.insights.query_builders.sql_functions import handle_timespan


# aggregate functions
def count(
    column: ir.Column = None,
    where: ir.BooleanValue = None,
    group_by=None,
    order_by=None,
):
    """
    def count(column=None, where=None)

    Count the number of non-null values in a column.

    Examples:
    - count()
    - count(user_id)
    - count(user_id, status == 'Active')
    - count(user_id, group_by=month(date), order_by=asc(date))
    """

    if column is None:
        query = frappe.flags.current_ibis_query
        column = query.columns[0]
        column = getattr(query, column)

    if group_by is not None:
        return column.count(where=where).over(group_by=group_by, order_by=order_by)

    return column.count(where=where)


def count_if(condition: ir.BooleanValue, column: ir.Column = None, group_by=None, order_by=None):
    """
    def count_if(condition)

    Count the number of rows that satisfy a condition.

    Examples:
    - count_if(status == 'Active')
    - count_if(status == 'Active', user_id)
    - count_if(status == 'Active', user_id, group_by=month(date), order_by=asc(date))
    """

    return count(column, where=condition, group_by=group_by, order_by=order_by)


def min(column: ir.Column, where: ir.BooleanValue = None, group_by=None, order_by=None):
    """
    def min(column, where=None)

    Find the minimum value in a column.

    Examples:
    - min(column)
    - min(column, where=status == 'Active')
    - min(column, group_by=user_id, order_by=date)
    - min(column, group_by=[user_id, month(date)], order_by=asc(date))
    """

    if group_by is not None:
        return column.min(where=where).over(group_by=group_by, order_by=order_by)

    return column.min(where=where)


def max(column: ir.Column, where: ir.BooleanValue = None, group_by=None, order_by=None):
    """
    def max(column, where=None)

    Find the maximum value in a column.

    Examples:
    - max(column)
    - max(column, status == 'Active')
    - max(column, group_by=user_id, order_by=date)
    """

    if group_by is not None:
        return column.max(where=where).over(group_by=group_by, order_by=order_by)

    return column.max(where=where)


def sum(
    column: ir.NumericColumn,
    where: ir.BooleanValue = None,
    group_by=None,
    order_by=None,
):
    """
    def sum(column, where=None)

    Find the sum of values in a column.

    Examples:
    - sum(column)
    - sum(column, status == 'Active')
    - sum(column, group_by=user_id, order_by=date)
    """

    if group_by is not None:
        return column.sum(where=where).over(group_by=group_by, order_by=order_by)

    return column.sum(where=where)


def avg(
    column: ir.NumericColumn,
    where: ir.BooleanValue = None,
    group_by=None,
    order_by=None,
):
    """
    def avg(column, where=None)

    Find the average of values in a column.

    Examples:
    - avg(column)
    - avg(column, status == 'Active')
    - avg(column, group_by=user_id, order_by=date)
    """

    if group_by is not None:
        return column.mean(where=where).over(group_by=group_by, order_by=order_by)

    return column.mean(where=where)


def median(
    column: ir.NumericColumn,
    where: ir.BooleanValue = None,
    group_by=None,
    order_by=None,
):
    """
    def median(column, where=None)

    Find the median value in a column.

    Examples:
    - median(column)
    - median(column, status == 'Active')
    - median(column, group_by=user_id, order_by=date)
    """

    if group_by is not None:
        return column.median(where=where).over(group_by=group_by, order_by=order_by)

    return column.median(where=where)


def group_concat(column: ir.Column, sep: str = ",", where: ir.BooleanValue = None):
    """
    def group_concat(column, sep=',', where=None)

    Concatenate values of a column into a single string.

    Examples:
    - group_concat(column)
    - group_concat(column, '-', status == 'Active')
    """
    return column.group_concat(sep=sep, where=where)


def distinct_count(column: ir.Column, where: ir.BooleanValue = None, group_by=None, order_by=None):
    """
    def distinct_count(column, where=None)

    Count the number of unique values in a column.

    Examples:
    - distinct_count(column)
    - distinct_count(column, status == 'Active')
    - distinct_count(column, group_by=user_id, order_by=date)
    """

    if group_by is not None:
        return column.nunique(where=where).over(group_by=group_by, order_by=order_by)

    return column.nunique(where=where)


def sum_if(condition: ir.BooleanValue, column: ir.NumericColumn):
    """
    def sum_if(condition, column)

    Find the sum of values in a column that satisfy a condition.

    Examples:
    - sum_if(status == 'Active', column)
    """
    return sum(column, where=condition)


def distinct_count_if(condition: ir.BooleanValue, column: ir.Column):
    """
    def distinct_count_if(condition, column)

    Count the number of unique values in a column that satisfy a condition.

    Examples:
    - distinct_count_if(status == 'Active', column)
    """
    return distinct_count(column, where=condition)


def is_in(column: ir.Column, *values: tuple[ir.Value, ...]):
    """
    def is_in(column, *values)

    Check if value is in a list of values.

    Examples:
    - is_in(status, 'Active', 'Inactive')
    - is_in(user_id, 1, 2, 3)
    """
    return column.isin(values)


def is_not_in(column: ir.Column, *values: tuple[ir.Value, ...]):
    """
    def is_not_in(column, *values)

    Check if value is not in a list of values.

    Examples:
    - is_not_in(status, 'Active', 'Inactive')
    - is_not_in(user_id, 1, 2, 3)
    """
    return column.notin(values)


def is_set(column: ir.Column):
    """
    def is_set(column)

    Check if value is not null.

    Examples:
    - is_set(email)
    """
    return column.notnull()


def is_not_set(column: ir.Column):
    """
    def is_not_set(column)

    Check if value is null.

    Examples:
    - is_not_set(email)
    """
    return column.isnull()


def is_between(column: ir.Column, start: ir.Value, end: ir.Value):
    """
    def is_between(column, start, end)

    Check if value is between start and end.

    Examples:
    - is_between(age, 18, 60)
    """
    return column.between(start, end)


def is_not_between(column: ir.Column, start: ir.Value, end: ir.Value):
    """
    def is_not_between(column, start, end)

    Check if value is not between start and end.

    Examples:
    - is_not_between(age, 18, 60)
    """
    return ~column.between(start, end)


# is_within = lambda args, kwargs: None  # TODO


# conditional functions
def if_else(condition: ir.BooleanValue, true_value: ir.Value, false_value: ir.Value):
    """
    def if_else(condition, true_value, false_value)

    Return true_value if condition is true, else return false_value.

    Examples:
    - if_else(status == 'Active', 1, 0)
    """
    return ibis.case().when(condition, true_value).else_(false_value).end()


def case(condition: ir.BooleanValue, value: ir.Value, *args: tuple[ir.BooleanValue, ir.Value]):
    """
    def case(condition, value, *args)

    Return value if condition is true, else return value of the next condition.

    Examples:
    - case(age > 18, 'Eligible', 'Not Eligible')
    - case(age > 30, 'Above 30', age > 20, 'Above 20')
    """
    case = ibis.case().when(condition, value)
    for i in range(0, len(args) - 1, 2):
        case = case.when(args[i], args[i + 1])

    if len(args) % 2 == 1:
        return case.else_(args[-1]).end()
    else:
        return case.end()


# number Functions
def abs(column: ir.NumericColumn):
    """
    def abs(column)

    Return the absolute value of a column.

    Examples:
    - abs(column)
    """
    return column.abs()


def round(column: ir.NumericColumn, decimals: int = 0):
    """
    def round(column, decimals=0)

    Round the values of a column to the nearest integer.

    Examples:
    - round(column)
    - round(column, 2)
    """
    return column.round(decimals)


def floor(column: ir.NumericColumn):
    """
    def floor(column)

    Return the floor of a column.

    Examples:
    - floor(column)
    """
    return column.floor()


def ceil(column: ir.NumericColumn):
    """
    def ceil(column)

    Return the ceiling of a column.

    Examples:
    - ceil(column)
    """
    return column.ceil()


# String Functions


def lower(column: ir.StringColumn):
    """
    def lower(column)

    Convert the values of a column to lowercase.

    Examples:
    - lower(column)
    """
    return column.lower()


def upper(column: ir.StringColumn):
    """
    def upper(column)

    Convert the values of a column to uppercase.

    Examples:
    - upper(column)
    """
    return column.upper()


def concat(column: ir.StringColumn, *args: tuple[str | ir.Column, ...]):
    """
    def concat(column, *args)

    Concatenate values of multiple strings or string columns into one string.

    Examples:
    - concat(first_name, ' ', last_name)
    """
    return column.concat(*args)


def replace(column: ir.StringColumn, old: str, new: str):
    """
    def replace(column, old, new)

    Replace a substring with another substring in a column.

    Examples:
    - replace(email, '@', ' at ')
    """
    return column.replace(old, new)


def find(column: ir.StringColumn, sub: str):
    """
    def find(column, sub)

    Find the position of a substring in a column.

    Examples:
    - find(email, '@')
    """
    return column.find(sub)


def substring(column: ir.StringColumn, start: int, length: int | None = None):
    """
    def substring(column, start, length=None)

    Extract a substring from a column.

    Examples:
    - substring(email, 0, 3)
    - substring(email, find(email, '@'))
    """
    return column.substr(start, length)


def contains(column: ir.StringColumn, sub: str):
    """
    def contains(column, sub)

    Check if a substring is present in a column.

    Examples:
    - contains(email, '@')
    - contains(name, first_name)
    """
    return column.contains(sub)


# not_contains = lambda column, *args, **kwargs: ~column.contains(*args, **kwargs)
def not_contains(column: ir.StringColumn, sub: str):
    """
    def not_contains(column, sub)

    Check if a substring is not present in a column.

    Examples:
    - not_contains(email, '@')
    - not_contains(name, first_name)
    """
    return ~column.contains(sub)


def starts_with(column: ir.StringColumn, sub: str):
    """
    def starts_with(column, sub)

    Check if a column starts with a substring.

    Examples:
    - starts_with(email, 'info')
    """
    return column.startswith(sub)


def ends_with(column: ir.StringColumn, sub: str):
    """
    def ends_with(column, sub)

    Check if a column ends with a substring.

    Examples:
    - ends_with(email, '.com')
    """
    return column.endswith(sub)


def length(column: ir.StringColumn):
    """
    def length(column)

    Find the length of a column.

    Examples:
    - length(column)
    """
    return column.length()


# date functions
def year(column: ir.DateValue):
    """
    def year(column)

    Extract the year from a date column.

    Examples:
    - year(order_date)
    """
    return column.year()


def quarter(column: ir.DateValue):
    """
    def quarter(column)

    Extract the quarter from a date column.

    Examples:
    - quarter(order_date)
    """
    return column.quarter()


def month(column: ir.DateValue):
    """
    def month(column)

    Extract the month from a date column.

    Examples:
    - month(order_date)
    """
    return column.month()


def week_of_year(column: ir.DateValue):
    """
    def week_of_year(column)

    Extract the week of the year (1-53) from a date column.

    Examples:
    - week_of_year(order_date)
    """
    return column.week_of_year()


def day_of_year(column: ir.DateValue):
    """
    def day_of_year(column)

    Extract the day of the year (1-366) from a date column.

    Examples:
    - day_of_year(order_date)
    """
    return column.day_of_year()


def day_of_week(column: ir.DateValue):
    """
    def day_of_week(column)

    Extract the day of the week (0-6) from a date column.

    Examples:
    - day_of_week(order_date)
    """
    return column.day_of_week.index()


def day_name(column: ir.DateValue):
    """
    def day_name(column)

    Extract the name of the day (Monday-Sunday) from a date column.

    Examples:
    - day_name(order_date)
    """
    return column.day_of_week.full_name()


def day(column: ir.DateValue):
    """
    def day(column)

    Extract the day from a date column.

    Examples:
    - day(order_date)
    """
    return column.day()


def hour(column: ir.TimeValue):
    """
    def hour(column)

    Extract the hour from a time column.

    Examples:
    - hour(time_column)
    """
    return column.hour()


def minute(column: ir.TimeValue):
    """
    def minute(column)

    Extract the minute from a time column.

    Examples:
    - minute(time_column)
    """
    return column.minute()


def second(column: ir.TimeValue):
    """
    def second(column)

    Extract the second from a time column.

    Examples:
    - second(time_column)
    """
    return column.second()


def microsecond(column: ir.TimeValue):
    """
    def microsecond(column)

    Extract the microsecond from a time column.

    Examples:
    - microsecond(time_column)
    """
    return column.microsecond()


def format_date(column: ir.DateValue, format_str: str):
    """
    def format_date(column, format_str)

    Format a date column according to a format string.

    Examples:
    - format_date(order_date, '%Y-%m-%d')
    """
    return column.strftime(format_str)


def date_diff(column: ir.DateValue, other: ir.DateValue, unit: str = "day"):
    """
    def date_diff(column, other, unit)

    Calculate the difference between two date columns. The unit can be year, quarter, month, week, or day.

    Examples:
    - date_diff(order_date, delivery_date, 'day')
    - date_diff(order_date, delivery_date, 'week')
    """

    if not column.type().is_date():
        column = column.cast("date")
    if not other.type().is_date():
        other = other.cast("date")

    return column.delta(other, unit)


def time_diff(
    column: ir.TimeValue,
    other: ir.TimeValue,
    unit: str = "second",
):
    """
    def time_diff(column, other, unit)

    Calculate the difference between two time columns. The unit can be hour, minute, second, millisecond, microsecond, nanosecond

    Examples:
    - time_diff(start_time, end_time, 'hour')
    - time_diff(start_time, end_time, 'minute')
    """

    if not column.type().is_time():
        column = column.cast("time")
    if not other.type().is_time():
        other = other.cast("time")

    return column.delta(other, unit)


def date_add(column: ir.DateValue, value: int, unit: str):
    """
    def date_add(column, value, unit)

    Add a value to a date column. The unit can be seconds, minutes, hours, days, weeks, months, or years.

    Examples:
    - date_add(order_date, 1, 'days')
    - date_add(order_date, 1, 'weeks')
    """
    return column + ibis.interval(value, unit)


def date_sub(column: ir.DateValue, value: int, unit: str):
    """
    def date_sub(column, value, unit)

    Subtract a value from a date column. The unit can be seconds, minutes, hours, days, weeks, months, or years.

    Examples:
    - date_sub(order_date, 1, 'days')
    - date_sub(order_date, 1, 'weeks')
    """
    return column - ibis.interval(value, unit)


def within(column: ir.DateValue, timespan: str):
    """
    def within(column, timespan)

    Filter rows within a timespan. The timespan can be 'Last [N] [Parts]', 'Current [Parts]', or 'Next [N] [Parts]'.
    Parts can be 'day', 'week', 'month', 'quarter', 'year' or 'fiscal year'.

    Examples:
    - within(order_date, 'Last 7 days')
    - within(order_date, 'Current month')
    - within(order_date, 'Next 2 weeks')
    """
    return handle_timespan(column, timespan)


def now():
    """
    def now()

    Get the current timestamp.

    Examples:
    - now()
    """
    return ibis.now()


def today():
    """
    def today()

    Get the current date.

    Examples:
    - today()
    """
    return ibis.today()


# utility functions
def to_inr(curr: ir.StringValue, amount: ir.NumericValue, rate: int = 83):
    """
    def to_inr(curr, amount, rate=83)

    Convert an amount from USD to INR.

    Examples:
    - to_inr('USD', amount)
    - to_inr('USD', amount, 75)
    - to_inr('USD', amount, exchange_rate)
    """
    return if_else(curr == "USD", amount * rate, amount)


def to_usd(curr: ir.StringValue, amount: ir.NumericValue, rate: int = 83):
    """
    def to_usd(curr, amount, rate=83)

    Convert an amount from INR to USD.

    Examples:
    - to_usd('INR', amount)
    - to_usd('INR', amount, 75)
    - to_usd('INR', amount, exchange_rate)
    """
    return if_else(curr == "INR", amount / rate, amount)


def literal(value):
    """
    def literal(value)

    Create a literal value.

    Examples:
    - literal(1)
    - literal('Active')
    """
    return ibis.literal(value)


def constant(value):
    """
    def constant(value)

    Create a constant value.

    Examples:
    - constant(1)
    - constant('Active')
    """
    return ibis.literal(value)


def row_number():
    """
    def row_number()

    Assign a unique number to each row.
    """
    return ibis.row_number()


def sql(query):
    """
    def sql(query)

    Execute a SQL query.

    Examples:
    - sql('SELECT * FROM table')
    """
    return _.sql(query)


def coalesce(*args):
    """
    def coalesce(*args)

    Return the first non-null value in a list of columns.

    Examples:
    - coalesce(column1, column2, column3)
    """
    return ibis.coalesce(*args)


def if_null(column, value):
    """
    def if_null(column, value)

    Replace null values in a column with a default value.

    Examples:
    - if_null(email, 'No Email')
    """
    return ibis.coalesce(column, value)


def asc(column):
    """
    def asc(column)

    Sort a column in ascending order.

    Examples:
    - asc(column)
    """
    return ibis.asc(column)


def desc(column):
    """
    def desc(column)

    Sort a column in descending order.

    Examples:
    - desc(column)
    """
    return ibis.desc(column)


def previous_value(column: ir.Column, group_by=None, order_by=None, offset=1):
    """
    def previous_value(column, group_by=None, order_by=None, offset=1)

    Get the value of a column in the previous row. Provide group_by and order_by columns for partitioning and ordering.

    Examples:
    - previous_value(amount)
    - previous_value(amount, group_by=user_id, order_by=date)
    - previous_value(amount, group_by=[user_id, month(date)], order_by=asc(date))
    """
    return column.lag(offset).over(group_by=group_by, order_by=order_by)


def next_value(column: ir.Column, group_by=None, order_by=None, offset=1):
    """
    def next_value(column, group_by=None, order_by=None, offset=1)

    Get the value of a column in the next row. Provide group_by and order_by columns for partitioning and ordering.

    Examples:
    - next_value(amount)
    - next_value(amount, group_by=user_id, order_by=date)
    - next_value(amount, group_by=[user_id, month(date)], order_by=asc(date))
    """
    return column.lead(offset).over(group_by=group_by, order_by=order_by)


def previous_period_value(column: ir.Column, date_column: ir.DateColumn, offset=1):
    """
    def previous_period_value(column, date_column, offset=1)

    Get the value of a column in the previous period. If the date values are at month level then the previous month value will be returned. Similarly, at year level, the previous year value will be returned.

    Examples:
    - previous_period_value(amount, date)
    - previous_period_value(amount, date, 2)
    """
    date_column_name = date_column.get_name() if hasattr(date_column, "get_name") else date_column
    return column.lag(offset).over(
        group_by=(~s.numeric() & ~s.matches(date_column_name)),
        order_by=ibis.asc(date_column_name),
    )


def next_period_value(column: ir.Column, date_column: ir.DateColumn, offset=1):
    """
    def next_period_value(column, date_column, offset=1)

    Get the value of a column in the next period. If the date values are at month level then the next month value will be returned. Similarly, at year level, the next year value will be returned.

    Examples:
    - next_period_value(amount, date)
    - next_period_value(amount, date, 2)
    """
    date_column_name = date_column.get_name() if hasattr(date_column, "get_name") else date_column
    return column.lead(offset).over(
        group_by=(~s.numeric() & ~s.matches(date_column_name)),
        order_by=ibis.asc(date_column_name),
    )


def percentage_change(column: ir.Column, date_column: ir.DateColumn, offset=1):
    """
    def percentage_change(column, date_column, offset=1)

    Calculate the percentage change of a column in the previous period. If the date values are at month level then percentage change from the previous month will be calculated. Similarly, at year level, percentage change from the previous year will be calculated.

    Examples:
    - percentage_change(amount, date)
    - percentage_change(amount, date, 2)
    """
    prev_value = previous_period_value(column, date_column, offset)
    return ((column - prev_value) * 100) / abs(prev_value)


def is_first_row(group_by=None, order_by=None, sort_order="asc"):
    """
    def is_first_row(group_by=None, order_by=None, sort_order="asc")

    Check if the row is the first row in the group. Provide group_by and order_by columns for partitioning and ordering.

    Examples:
    - is_first_row()
    - is_first_row(group_by=user_id, order_by=date)
    - is_first_row(group_by=[user_id, month(date)], order_by=asc(date))
    """
    _order_by = ibis.asc(order_by) if sort_order == "asc" else ibis.desc(order_by)
    index = row_number().over(group_by=group_by, order_by=_order_by)
    return if_else(index == 0, 1, 0)


def is_last_row(group_by=None, order_by=None, sort_order="asc"):
    """
    def is_last_row(group_by=None, order_by=None, sort_order="asc")

    Check if the row is the last row in the group. Provide group_by and order_by columns for partitioning and ordering.

    Examples:
    - is_last_row()
    - is_last_row(group_by=user_id, order_by=date)
    - is_last_row(group_by=[user_id, month(date)], order_by=asc(date))
    """
    _order_by = ibis.desc(order_by) if sort_order == "asc" else ibis.asc(order_by)
    index = row_number().over(group_by=group_by, order_by=_order_by)
    return if_else(index == 0, 1, 0)


def filter_first_row(group_by=None, order_by=None, sort_order="asc"):
    """
    def filter_first_row(group_by=None, order_by=None, sort_order="asc")

    Filter to keep only the first row of each group. Provide group_by and order_by columns for partitioning and ordering.

    Examples:
    - filter_first_row()
    - filter_first_row(group_by=user_id, order_by=date)
    - filter_first_row(group_by=[user_id, month(date)], order_by=asc(date))
    """
    _order_by = ibis.asc(order_by) if sort_order == "asc" else ibis.desc(order_by)
    index = row_number().over(group_by=group_by, order_by=_order_by)
    return index == 0


def create_buckets(column: ir.Column, num_buckets: int):
    """
    def create_buckets(column, num_buckets)

    Create buckets based on the values in a column. The number of buckets will be equal to num_buckets.

    Examples:
    - create_buckets(age, 3)
      -> 0-33, 34-66, 67-100
    """
    query = frappe.flags.current_ibis_query
    if query is None:
        frappe.throw("Failed to create buckets. Query not found")

    values_df = query.select(column).distinct().execute()
    values = [v[0] for v in values_df.values.tolist()]
    values = sorted(values)

    if not values:
        frappe.throw("Failed to create buckets. No data found in the column")

    if len(values) < num_buckets:
        num_buckets = len(values)

    bucket_size = math.ceil(len(values) / num_buckets)
    buckets = []
    for i in range(0, len(values), bucket_size):
        buckets.append(values[i : i + bucket_size])

    case = ibis.case()
    for bucket in buckets:
        min_val = bucket[0]
        max_val = bucket[-1]
        label = f"{min_val}-{max_val}"
        case = case.when(is_in(column, *bucket), label)

    return case.else_(None).end()


def week_start(column: ir.DateValue):
    """
    def week_start(column)

    Get the start date of the week for a given date.

    Examples:
    - week_start(order_date)
    """

    week_start_day = frappe.db.get_single_value("Insights Settings", "week_starts_on") or "Monday"
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    week_starts_on = days.index(week_start_day)
    day_of_week = column.day_of_week.index().cast("int32")
    adjusted_week_start = (day_of_week - week_starts_on + 7) % 7
    week_start = column - adjusted_week_start.as_interval(unit="D")
    return week_start


def month_start(column: ir.DateValue):
    """
    def month_start(column)

    Get the start date of the month for a given date.

    Examples:
    - month_start(order_date)
    """

    month_start = column.strftime("%Y-%m-01").cast("date")
    return month_start


def quarter_start(column: ir.DateValue):
    """
    def quarter_start(column)

    Get the start date of the quarter for a given date.

    Examples:
    - quarter_start(order_date)
    """

    year = column.year()
    quarter = column.quarter()
    month = (quarter * 3) - 2
    quarter_start = ibis.date(year, month, 1)
    return quarter_start


def year_start(column: ir.DateValue):
    """
    def year_start(column)

    Get the start date of the year for a given date.

    Examples:
    - year_start(order_date)
    """

    year_start = column.strftime("%Y-01-01").cast("date")
    return year_start


def fiscal_year_start(column: ir.DateValue):
    """
    def fiscal_year_start(column)

    Get the start date of the fiscal year for a given date.

    Examples:
    - fiscal_year_start(order_date)
    """

    fiscal_year_start_month = 4
    fiscal_year_start_day = 1

    year = column.year()
    month = column.month()

    return if_else(
        month < fiscal_year_start_month,
        ibis.date(year - 1, fiscal_year_start_month, fiscal_year_start_day),
        ibis.date(year, fiscal_year_start_month, fiscal_year_start_day),
    ).cast("date")


def get_retention_data(date_column: ir.DateValue, id_column: ir.Column, unit: str):
    """
    def get_retention_data(date_column, id_column, unit)

    Calculate retention data based on the cohort analysis. The unit can be day, week, month, or year.

    Examples:
    - get_retention_data(date, user_id, 'day')
    """

    query = frappe.flags.current_ibis_query
    if query is None:
        frappe.throw("Query not found")

    if isinstance(date_column, str):
        date_column = getattr(query, date_column)

    if isinstance(id_column, str):
        id_column = getattr(query, id_column)

    if date_column.type().is_timestamp():
        date_column = date_column.cast("date")

    if not date_column.type().is_date():
        frappe.throw(f"Invalid date column. Expected date, got {date_column.type()}")

    unit_start = {
        "day": lambda column: column.strftime("%Y-%m-%d").cast("date"),
        "week": week_start,
        "month": lambda column: column.strftime("%Y-%m-01").cast("date"),
        "quarter": quarter_start,
        "year": lambda column: column.strftime("%Y-01-01").cast("date"),
    }[unit]

    query = query.mutate(cohort_start=unit_start(date_column).min().over(group_by=id_column))

    query = query.mutate(cohort_size=id_column.nunique().over(group_by=query.cohort_start))

    query = query.mutate(offset=date_column.delta(query.cohort_start, unit))

    zero_padded_offset = (query.offset < 10).ifelse(
        literal("0").concat(query.offset.cast("string")), query.offset.cast("string")
    )
    query = query.mutate(offset_label=ibis.literal(f"{unit}_").concat(zero_padded_offset))

    query = query.group_by(["cohort_start", "cohort_size", "offset_label"]).aggregate(
        unique_ids=id_column.nunique()
    )

    query = query.mutate(retention=(query.unique_ids / query.cohort_size) * 100)

    return query


def pad_number(number: ir.NumericValue, digits: int):
    """
    def pad_number(number, digits)

    Convert an integer into an n digit string.

    Examples:
    - pad_number(1, 2) -> '01'
    - pad_number(1, 3) -> '001'
    """
    string_number = number.cast("string")
    zero_literal = ibis.literal("0")

    return if_else(
        string_number.length() < digits,
        zero_literal.repeat(digits - string_number.length()).concat(string_number),
        string_number,
    )
