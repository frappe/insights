# Expression language

Expressions appear in `mutate`, expression measures, expression filters, and join conditions. An
expression is a **Python expression that runs against ibis**. It has this context:

- every current column of the query by bare name (`base_net_total`, `posting_date`). For a name that
  is not a valid identifier, use `q['column name']` (`q` is the current table)
- the function library below
- `ibis` (the module) and `literal`

Python syntax rules apply. Write `==`, not `=`. Put strings in quotes. `and` / `or` / `not` do NOT
work on columns. Use `&`, `|`, `~`, with parentheses around each comparison.

```python
(status == 'Paid') & (base_net_total > 1000)
```

## Gotchas that cause real failures

- **A bare string or number as a whole `mutate` expression fails.** Insights casts the result to the
  declared `data_type`, and a Python `str` has no `.cast`. Write `ibis.literal('1. Total')` or
  `literal(0)`. The templates label union branches this way.
- **After `summarize`, only the summarized columns exist.** Use the sanitized snake_case measure and
  dimension names.
- **Aggregations belong in expression measures and `summarize`.** In `mutate` they compute
  window-style over the whole table. That is almost never the ask.
- **Division by zero** returns null or fails, depending on the backend. Guard it with
  `if_else(x != 0, a / x, 0)`.
- Dates compare against date expressions, not strings: `delivery_date < today()`.

## Function library

Aggregations (expression measures and `summarize`; most take an optional `where=`):
`sum(col)`, `count()`, `count(col)`, `avg(col)`, `min(col)`, `max(col)`, `median(col)`,
`distinct_count(col)`, `group_concat(col, sep=',')`.

Conditional aggregations, for ratios and percentages:
`sum_if(condition, col)`, `count_if(condition)`, `distinct_count_if(condition, col)`.

```python
count_if(status == 'Ordered') / count() * 100   # % converted, data_type Decimal
sum(debit) - sum(credit)                        # net from a signed ledger
```

Conditionals: `if_else(cond, then, else_)`, `one_if(cond)`,
`case(cond, value, cond2, value2, ..., default)`, `cases((cond, value), ..., else_=default)`.

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

String: `lower`, `upper`, `concat(col, ...)`, `replace(col, old, new)`, `find(col, sub)`,
`substring(col, start, length)`, `contains(col, sub)`, `not_contains`, `starts_with`, `ends_with`,
`length`, `textsplit(col, delim, max_splits)`.

## JSON columns

`json_value(col, path, type)` reads **one** value out of a JSON column. It gives you a normal
column. A `mutate` needs this one.

```python
json_value(properties, 'template_group')                # string, the default
json_value(properties, 'address.city')                  # dots reach a nested key
json_value(properties, 'items.0.name')                  # a number picks out of a list
json_value(payload, 'amount', 'float')
json_value(payload, 'signed_up_at', 'timestamp')
```

`type` is one of `string`, `int`, `float`, `bool`, `date`, `timestamp`. Name it. Otherwise the value
comes back as a string, and a chart cannot sum a string. A missing key, a JSON null or a malformed
value gives an empty value, not a failed query.

The value works anywhere: in a filter, in a summarize, inside another expression.

`json_extract(col, *fields)` is a different thing. It expands into **several** columns at once. It
samples 50 rows to guess each type. A `mutate` takes one expression and binds one name, so
`json_extract` inside a `mutate` fails with:

```
ValueError: not enough values to unpack (expected 2, got 1)
```

Use `json_value`, once per field you need.

Date/time: `year`, `quarter`, `month`, `week_of_year`, `day`, `day_of_week`, `day_name`, `hour`,
`minute`, `second`, `format_date(col, fmt)`, `date_diff(a, b, unit='day')`, `date_add(col, n, unit)`,
`date_sub(col, n, unit)`, `week_start(col)`, `month_start(col)`, `within(col, 'Last 6 months')`,
`now()`, `today()`.

```python
date_diff(today(), due_date, 'day')                                    # age in days
if_else(within(posting_date, 'Current fiscal year'), base_net_total, 0)
```

Null handling: `coalesce(*cols)`, `if_null(col, value)`, `is_set(col)`, `is_not_set(col)`.

Membership and range (expression filters): `is_in(col, v1, v2, ...)`, `is_not_in`,
`is_between(col, a, b)`, `is_not_between`.

Window (advanced): `row_number()`, `previous_value(col, group_by, order_by)`, `next_value(...)`,
`previous_period_value(col, date_col)`, `percentage_change(col, date_col)`, `is_first_row(...)`,
`is_last_row(...)`, `filter_first_row(group_by, order_by, sort_order)`.

Constants: `literal(value)` (alias `constant`), or `ibis.literal(value)`.

## The site holds the real list

This page is a working subset. Your site may run a newer Insights than this page. Ask the site
rather than guess:

```sh
frappectl -s $SITE method call insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_list
frappectl -s $SITE method call insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_description \
  -F funcName=json_value
```

`get_function_description` returns the signature and the docstring. The docstring says what a
function returns and what it costs. This page compares `json_value` with `json_extract`. The
docstring is what settles that question. The parameter is `funcName`, camelCase.

A function this page does not list is not forbidden. A function `get_function_list` does not return
does not exist.
