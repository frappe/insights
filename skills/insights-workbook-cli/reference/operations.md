# Query operations

A query's `operations` is a JSON array executed top to bottom. The first operation must be `source`.

## Shared building blocks

```jsonc
// Column reference
{ "type": "column", "column_name": "customer" }

// Expression (see reference/expressions.md)
{ "type": "expression", "expression": "sum(debit) - sum(credit)" }

// Table reference — a real table:
{ "type": "table", "data_source": "Site DB", "table_name": "tabSales Invoice" }
// ...or another query in the same workbook (layering):
{ "type": "query", "workbook": "<workbook_name>", "query_name": "<query_doc_name>" }

// Column measure (aggregation: sum | count | avg | min | max | count_distinct)
{ "measure_name": "Revenue", "column_name": "base_net_total", "data_type": "Decimal", "aggregation": "sum" }

// Row-count measure — column_name is the literal string "count"
{ "measure_name": "Invoices", "column_name": "count", "data_type": "Integer", "aggregation": "count" }

// Expression measure
{ "measure_name": "Outstanding", "data_type": "Decimal",
  "expression": { "type": "expression", "expression": "sum(debit) - sum(credit)" } }

// Dimension (granularity applies to Date/Datetime only: day | week | month | quarter | year | fiscal_year)
{ "dimension_name": "posting_date", "column_name": "posting_date", "data_type": "Date", "granularity": "month" }
```

`data_type`: `String | Integer | Decimal | Date | Datetime | Time | Text`. Measures take
`String | Integer | Decimal`. Dimensions take `String | Date | Datetime | Time`.

Datetime columns also accept `second`, `minute` and `hour` granularity. A Time column accepts only
those three. Anything else fails with an "Unsupported Granularity" error that names the list.

## source

Always first, exactly once.

```json
{ "type": "source", "table": { "type": "table", "data_source": "Site DB", "table_name": "tabSales Invoice" } }
```

## filter_group

The only way to filter. `filters` mixes rules and expression filters. `logical_operator`
(`And` | `Or`) joins them. To nest, use an expression filter. Several `filter_group` ops in a row
are normal and readable. The shipped templates express "submitted AND under-delivered AND past due"
that way.

```json
{
  "type": "filter_group",
  "logical_operator": "And",
  "filters": [
    { "column": { "type": "column", "column_name": "docstatus" }, "operator": "=", "value": 1 },
    { "column": { "type": "column", "column_name": "status" }, "operator": "in", "value": ["Paid", "Unpaid", "Overdue"] },
    { "column": { "type": "column", "column_name": "posting_date" }, "operator": "within", "value": "Last 12 months" },
    { "expression": { "type": "expression", "expression": "delivery_date < today()" } }
  ]
}
```

Operators: `= != > >= < <= in not_in between within contains not_contains starts_with ends_with
is_set is_not_set`.

- `in` / `not_in`: value is an array.
- `between`: value is `[start, end]`. Bare date strings expand to full-day bounds.
- `within` (Date columns): value is a timespan string, such as
  `"Last N days|weeks|months|quarters|years"`, `"Current month"`, `"Next N weeks"` or
  `"Last 1 fiscal year"`. For the running period, append `" (include current)"`.
- `contains` / `not_contains` match `%value%`. Numerics become strings first.
- `is_set` / `is_not_set` ignore `value`. For String columns an empty string counts as unset.
- Column-vs-column: set `value` to a column ref `{ "type": "column", "column_name": "..." }`.
- ERPNext data: submitted documents are `docstatus = 1`. Filter it or you will count drafts and
  cancelled documents.

## select / remove / rename / cast

```json
{ "type": "select", "column_names": ["name", "customer", "posting_date", "base_net_total"] }
{ "type": "remove", "column_names": ["amended_from"] }
{ "type": "rename", "column": { "type": "column", "column_name": "base_net_total" }, "new_name": "revenue" }
{ "type": "cast", "column": { "type": "column", "column_name": "posting_date" }, "data_type": "Date" }
```

An early `select` keeps a wide table readable. Keep every column a chart or a dashboard filter
needs. `rename` sanitizes new names (spaces and hyphens become underscores). Write snake_case
yourself, so later operations reference what you expect. `remove` skips missing columns silently.

## mutate

`mutate` adds one computed column. It casts the result to `data_type`, so pick that type with care.
A Decimal expression declared `Integer` truncates.

```json
{ "type": "mutate", "new_name": "days_overdue", "data_type": "Integer",
  "expression": { "type": "expression", "expression": "date_diff(today(), due_date, 'day')" } }
```

## join

```json
{
  "type": "join",
  "join_type": "inner",
  "table": { "type": "table", "data_source": "Site DB", "table_name": "tabSales Invoice" },
  "select_columns": [
    { "type": "column", "column_name": "posting_date" },
    { "type": "column", "column_name": "company" }
  ],
  "join_condition": {
    "left_column": { "type": "column", "column_name": "parent" },
    "right_column": { "type": "column", "column_name": "name" }
  }
}
```

(From the Sales template. It joins invoice items to their parent invoice to get `posting_date` and
`company` per item row. The dashboard filters need those columns.)

- `join_type`: `inner | left | right | full`.
- `select_columns` are the columns to pull from the right table. The join key comes along too.
- The right table may be a `query` table. To change grain, join a summarized helper query back to
  detail. That is the standard pattern.
- The join adds a suffix to a conflicting right-side name. Do not rely on that. Use `rename` first.
- Expression condition:
  `"join_condition": { "join_expression": { "type": "expression", "expression": "left.customer == right.name" } }`.

## union

```json
{ "type": "union", "table": { "type": "query", "workbook": "<wb>", "query_name": "<other_query>" }, "distinct": false }
```

Both sides need the same column names and types. To label each side, `mutate` a constant on both
first. Use `ibis.literal('1. Total')`, never a bare string (see reference/expressions.md).

## summarize — grain change only

Charts aggregate. Queries stay per-row. Use `summarize` mid-pipeline. Then usually `join` back to
detail. The example below is AR ageing from the Accounting template. It rolls ledger rows up to one
row per invoice. It then joins back to the invoice for its customer and due date.

```json
[
  { "type": "summarize",
    "measures": [
      { "measure_name": "outstanding", "data_type": "Decimal",
        "expression": { "type": "expression", "expression": "sum(amount)" } }
    ],
    "dimensions": [
      { "dimension_name": "against_voucher", "column_name": "against_voucher_no", "data_type": "String" }
    ] },
  { "type": "filter_group", "logical_operator": "And",
    "filters": [ { "column": { "type": "column", "column_name": "outstanding" }, "operator": ">", "value": 0.5 } ] },
  { "type": "join", "join_type": "inner",
    "table": { "type": "table", "data_source": "Site DB", "table_name": "tabSales Invoice" },
    "select_columns": [
      { "type": "column", "column_name": "company" },
      { "type": "column", "column_name": "customer" },
      { "type": "column", "column_name": "due_date" }
    ],
    "join_condition": {
      "left_column": { "type": "column", "column_name": "against_voucher" },
      "right_column": { "type": "column", "column_name": "name" }
    } }
]
```

After `summarize`, only the measure and dimension output columns exist, under their sanitized
snake_case names. `dimensions: []` collapses everything to a single row. The funnel template does
that before a `union`.

## pivot_wider

`pivot_wider` turns long to wide inside a query. You rarely need it. A Table chart with non-empty
`columns` pivots for you.

```json
{ "type": "pivot_wider",
  "rows": [ { "dimension_name": "customer", "column_name": "customer", "data_type": "String" } ],
  "columns": [ { "dimension_name": "status", "column_name": "status", "data_type": "String" } ],
  "values": [ { "measure_name": "revenue", "column_name": "base_net_total", "data_type": "Decimal", "aggregation": "sum" } ],
  "max_column_values": 10 }
```

## order_by / limit

```json
{ "type": "order_by", "column": { "type": "column", "column_name": "posting_date" }, "direction": "desc" }
{ "type": "limit", "limit": 500 }
```

A base query rarely needs these. Charts apply their own order and limit from config. A `limit` in
the base query silently caps every chart built on it.

## sql — last resort

One operation, no others, and the query doc flips to `is_native_query: 1`, `is_builder_query: 0`
(`use_live_connection` stays `1`).

```json
{ "type": "sql", "raw_sql": "SELECT ... FROM `tabSales Invoice` ...", "data_source": "Site DB" }
```

The SQL must start with SELECT or WITH. Aliases become the column names. The dialect is the data
source's own. Dashboard filters still work. They append a `filter_group` after the `sql` op, so
still expose filterable columns per-row.

# Layering queries

A query can source from another query in the same workbook
(`{ "type": "query", "workbook": ..., "query_name": ... }`) in `source`, `join`, or `union`. If more
than one chart uses a helper result, prefer layering over one long pipeline. The helper is then a
single place to fix.
