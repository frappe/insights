# Expression language

Expressions appear in `mutate`, expression measures, expression filters, and join conditions. An expression is a **Python expression that runs against ibis**. It has this context:

- every current column of the query by bare name (`base_net_total`, `posting_date`). For a name that is not a valid identifier, use `q['column name']` (`q` is the current table)
- the function library below
- `ibis` (the module) and `literal`
- in a join condition, `t1` (the query being built) and `t2` (the right table)

Each column is an ibis column, so its methods work too: `name.re_extract('^(..)', 1)`, `name.startswith('SINV')`, `status.isnull()`, `posting_date.cast('date')`. Prefer a library function when one exists. Not every backend compiles every method: `a.delta(b, unit='hour')` fails on MariaDB.

Python syntax rules apply. Write `==`, not `=`. Put strings in quotes. `and` / `or` / `not` do NOT work on columns. Use `&`, `|`, `~`, with parentheses around each comparison.

```python
(status == 'Paid') & (base_net_total > 1000)
```

## Names

A bare name is a column when the query has that column, else a function or `ibis`. A column named like a function, such as `day`, `hour` or `month`, resolves by use: `day(posting_date)` calls the function, and `day` as a value reads the column. An expression that uses one name both ways is refused. Write the column as `q['day']` there.

A column whose name starts with `from_`, `to_` or `read_`, such as `t2.from_plan`, reads as a column. The table's own `to_*`, `read_*` and `from_*` methods stay refused: `'to_parquet' is not available in an expression`. So are a few names a table uses to run itself, such as `source`, `op`, `con` and `execute`. A column with one of those names reads only by item, and the error says so for the table that holds it: `Read the column as t2['source']`.

`q` is always the table, so a column named `q` reads only as `q['q']`. Bare, `q + 1` fails and `count(q)` counts rows. A column named `ibis`, `s` or `selectors` reads bare as the column, and `ibis.literal(1)` still reads the module. A column whose name starts with `_`, such as Site DB's `_assign`, reads only as `q['_assign']`. Bare, it is a `SyntaxError`, and the error names `q['_assign']`.

## When an expression fails

The error names the operation and quotes the expression:

```
Operation 3 (mutate 'days_open'): UnknownColumn: NameError: name 'opend_on' is not defined. Expression: date_diff(today(), opend_on)
```

The message is `Operation <n> (<type>[ '<new_name>'])[ in query '<title>']: <cause>`. Operations count from 1. The cause is `<class>: <type>: <text>`, then `. Expression: <source>`. `<class>` is the class the expression fails as, listed below, and `<type>` the Python error. A measure of a `summarize` names itself after the class: `Operation 2 (summarize): ExpressionSyntaxError: Measure 'total_length': AttributeError: ...`. A failure in a query this one reads adds that query's title, and the inner operation appears once: `Operation 1 (source): Operation 2 (mutate 'doubled') in query 'Open Tickets': ...`. An expression that runs outside a query's operations, such as an alert condition, starts at the Python error: `<type>: <text>. Expression: <source>`. An empty expression, or one of comments only, fails as `ExpressionSyntaxError: the expression is empty`.

Only a user who may edit the query reads the cause and the expression. Anyone else, such as a dashboard reader, reads the operation and the exception type only: `Operation 3 (mutate 'days_open'): UnknownColumn`.

A column the table does not have, read bare, as `q.col` or as `q['col']`, on any line of the expression, arrives as `UnknownColumn`. A misspelled function, such as `sumx(a)`, is not a column, and arrives as `ExpressionSyntaxError`. A column held back from the user arrives as `NotPermitted`, and names no operation. A Frappe error raised inside the expression, such as a refused permission, keeps its type and quotes no expression. Every other failure arrives as `ExpressionSyntaxError`.

## Older sites

A develop site older than this page lacks these engine fixes. Use the spelling that works on every site:

| On a newer site | On every site |
|---|---|
| `date_diff(a, b, 'hour')` counts whole hours. An older site compares the dates only. | `(a.epoch_seconds() - b.epoch_seconds()) // 3600`, which rounds a negative span down where `date_diff` rounds it toward zero |
| `remove` of fewer than half of the columns works on the data store, ClickHouse and BigQuery. An older site fails it there. | `select` the columns to keep |
| `previous_period_value`, `next_period_value` and `percentage_change` read the period `offset` grains away, and take `grain`. An older site reads `offset` rows away. | `summarize` to one row per period, with no period missing. Then `offset` rows is `offset` periods |
| `desc(captured_at)` as an `order_by` key of `is_first_row`, `is_last_row` or `filter_first_row` | `order_by=captured_at, sort_order='desc'` |
| `day` reads a column named `day`, and `t2.from_plan` a column named `from_plan` | `q['day']`, `t2['from_plan']` |
| An error that names the operation, and keeps its type | `--debug` shows the server messages |

## Gotchas that cause real failures

- **A bare constant as a whole `mutate` expression fails.** Insights casts the result to the declared `data_type`, and a Python string, number or `None` has no `.cast`. Write `ibis.literal('1. Total')`, `literal(0)` or `literal(None)`. Shipped workbooks label union branches this way.
- **After `summarize`, only the summarized columns exist.** Use the sanitized snake_case measure and dimension names.
- **Aggregations belong in expression measures and `summarize`.** In `mutate` they compute window-style over the whole table. That is almost never the ask.
- **Division by zero** returns null on every backend, the data store too. To show 0 instead, write `coalesce(a / x, 0)`.
- Dates compare against date expressions, not strings: `delivery_date < today()`.
- A number that holds a Unix timestamp does not compare with a date. Add a `cast` operation to `Datetime` before the comparison (see reference/operations.md).

## Function library

Aggregations (expression measures and `summarize`; most take an optional `where=`): `sum(col)`, `count()`, `count(col)`, `avg(col)`, `min(col)`, `max(col)`, `median(col)`, `distinct_count(col)`, `group_concat(col, sep=',')`.

`distinct_count` is the expression function. A column measure spells the same aggregation `count_distinct`. `count_distinct(col)` in an expression fails with `UnknownColumn`.

Conditional aggregations, for ratios and percentages: `sum_if(condition, col)`, `count_if(condition)`, `distinct_count_if(condition, col)`.

```python
count_if(status == 'Ordered') / count() * 100   # % converted, data_type Decimal
sum(debit) - sum(credit)                        # net from a signed ledger
```

A measure with `format: "percent"` holds a ratio. Leave out the `* 100`, or the chart prints 100 times the value.

Conditionals: `if_else(cond, then, else_)`, `one_if(cond)`, `case(cond, value, cond2, value2, ..., default)`, `cases((cond, value), ..., else_=default)`.

```python
cases(
  (days_overdue <= 0, '1. Not Due'),
  (days_overdue <= 30, '2. 1-30 Days'),
  (days_overdue <= 60, '3. 31-60 Days'),
  (days_overdue <= 90, '4. 61-90 Days'),
  else_='5. 90+ Days',
)
```

Number the bucket labels (`1.`, `2.`, ...). Charts then sort them correctly as strings.

Numeric: `abs`, `round(col, decimals)`, `floor`, `ceil`, `create_buckets(col, n)`.

String: `lower`, `upper`, `concat(col, ...)`, `replace(col, old, new)`, `find(col, sub)`, `substring(col, start, length)`, `contains(col, sub)`, `not_contains`, `starts_with`, `ends_with`, `length`, `textsplit(col, delim, max_splits)`.

## JSON columns

`json_value(col, path, type)` reads **one** value out of a JSON column. It gives you a normal column. A `mutate` needs this one.

```python
json_value(properties, 'template_group')                # string, the default
json_value(properties, 'address.city')                  # dots reach a nested key
json_value(properties, 'items.0.name')                  # a number picks out of a list
json_value(payload, 'amount', 'float')
json_value(payload, 'signed_up_at', 'timestamp')
```

`type` is one of `string`, `int`, `float`, `bool`, `date`, `timestamp`. Name it. Otherwise the value comes back as a string, and a chart cannot sum a string. A missing key, a JSON null or a malformed value gives an empty value, not a failed query.

The value works anywhere: in a filter, in a summarize, inside another expression.

`json_extract(col, *fields)` is a different thing. It expands into **several** columns at once. It samples 50 rows to guess each type. A `mutate` takes one expression and binds one name, so `json_extract` inside a `mutate` fails with:

```
ValueError: not enough values to unpack (expected 2, got 1)
```

Use `json_value`, once per field you need.

Date/time: `year`, `quarter`, `month`, `week_of_year`, `day`, `day_of_week`, `day_name`, `hour`, `minute`, `second`, `format_date(col, fmt)`, `date_diff(a, b, unit='day')`, `time_diff(a, b, unit='second')`, `date_add(col, n, unit)`, `date_sub(col, n, unit)`, `week_start(col)`, `month_start(col)`, `within(col, 'Last 6 months')`, `now()`, `today()`.

```python
date_diff(today(), due_date, 'day')                                    # age in days
if_else(within(posting_date, 'Current fiscal year'), base_net_total, 0)
date_diff(closed_at, opened_at, 'hour')                                # whole hours between two datetimes
```

`date_diff(a, b, unit)` gives `a` minus `b`. Its `hour`, `minute` and `second` units count the whole units elapsed between the two datetimes, exact to the millisecond, before 1970 too. `day` counts the days between the two dates. Larger units compare the dates, and each database counts them its own way, so the same query can give a different number live and from the data store. DuckDB, which runs the data store, counts the month, quarter and year boundaries crossed and the whole weeks elapsed: 31 January to 1 February is 1 month. MariaDB and MySQL count whole units elapsed: that is 0 months. Postgres counts whole months and years elapsed, and rounds weeks and quarters to the nearest unit. SQLite has only `day` and smaller units. `time_diff` compares the times of day only, so do not use it for two datetimes on different days.

Null handling: `coalesce(*cols)`, `if_null(col, value)`, `is_set(col)`, `is_not_set(col)`.

Membership and range (expression filters): `is_in(col, v1, v2, ...)`, `is_not_in`, `is_between(col, a, b)`, `is_not_between`.

Window (advanced): `row_number()`, `previous_value(col, group_by, order_by)`, `next_value(...)`, `previous_period_value(col, date_col, offset=1, grain=None)`, `next_period_value(...)`, `percentage_change(...)`, `is_first_row(...)`, `is_last_row(...)`, `filter_first_row(group_by, order_by, sort_order)`.

`previous_period_value` reads `col` in the period `offset` periods before the row's own, and `next_period_value` in the period after. A period with no row reads null, and so does a row with no date. The period is the granularity a `summarize` grouped `date_col` by, in this query or one it reads. A `Date` or `Datetime` nothing summarized is refused unless you pass `grain`, such as `'day'`, `'week'`, `'month'`, `'quarter'`, `'year'` or `'fiscal_year'`: `cannot tell the period of posting_date`. That is any table's own date column, and a date from a union, a code operation or a SQL query. A `Datetime` also takes `'hour'`, `'minute'` and `'second'`. A `Date` refuses them: `posting_date has no hour period. Pass one of: ...`. Rows compare within groups of the same values in every column that is neither numeric nor `date_col`. So `summarize` to one row per period with only the dimensions you want as groups. A leftover text column such as `name` puts each row in its own group, and every value is null. `percentage_change` compares `col` with `previous_period_value`, and is null where that is null or zero.

A period with no row is not in the result, so a chart skips it. To show it as zero, left-join the summarized query onto a query with one row per period, and `coalesce` the value. The spine's date is one nothing summarized, so pass `grain`.

`is_first_row`, `is_last_row` and `filter_first_row` need `order_by`, and refuse a call without it: which row is first is the order's to say. `sort_order` (`'asc'` or `'desc'`) sets the direction of a bare `order_by` column. A key wrapped in `asc()` or `desc()` keeps its own direction.

The latest row per entity is an expression filter:

```python
filter_first_row(group_by=site, order_by=captured_at, sort_order='desc')
```

`is_last_row(group_by=site, order_by=captured_at) == 1` keeps the same rows. For several keys, pass a list: `group_by=[site, app]`. Rows that tie on `order_by` keep one of them at random.

Constants: `literal(value)` (alias `constant`), or `ibis.literal(value)`.

## The site holds the real list

This page is a working subset. Your site may run a newer Insights than this page. Ask the site rather than guess:

```sh
frappectl -s $SITE method call insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_list
frappectl -s $SITE method call insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_description \
  -F funcName=json_value
```

`get_function_description` returns the signature and the docstring. The docstring says what a function returns and what it costs. This page compares `json_value` with `json_extract`. The docstring is what settles that question. The parameter is `funcName`, camelCase.

A function this page does not list is not forbidden. A function `get_function_list` does not return does not exist.
