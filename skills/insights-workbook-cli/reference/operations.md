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

`data_type`: `String | Integer | Decimal | Date | Datetime | Time | Text`. Measures are
`String | Integer | Decimal`; dimensions are `String | Date | Datetime | Time`.

Datetime columns also accept `second`, `minute` and `hour` granularity; a Time column accepts only
those three. Anything else is rejected with an "Unsupported Granularity" error naming the list.

## source

Always first, exactly once.

```json
{ "type": "source", "table": { "type": "table", "data_source": "Site DB", "table_name": "tabSales Invoice" } }
```

## filter_group

The only way to filter. `filters` mixes rules and expression filters, combined with
`logical_operator` (`And` | `Or`). Nest by using an expression filter. Several `filter_group` ops in
a row are normal and readable — that is how the shipped templates express "submitted AND
under-delivered AND past due".

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
- `between`: value is `[start, end]`; bare date strings expand to full-day bounds.
- `within` (Date columns): a timespan string — `"Last N days|weeks|months|quarters|years"`,
  `"Current month"`, `"Next N weeks"`, `"Last 1 fiscal year"`; append `" (include current)"` for
  the running period.
- `contains` / `not_contains` are `%value%` matches; numerics are cast to string first.
- `is_set` / `is_not_set` ignore `value`; for String columns an empty string counts as unset.
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

An early `select` keeps a wide table readable, but keep every column a chart or a dashboard filter
will need. `rename` sanitizes new names (spaces and hyphens become underscores) — write snake_case
yourself so later operations reference what you expect. `remove` skips missing columns silently.

## mutate

Adds one computed column. The result is cast to `data_type`, so pick it correctly: a Decimal
expression declared `Integer` truncates.

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

(From the Sales template: invoice items joined to their parent invoice to get `posting_date` and
`company` per item row — the columns the dashboard filters need.)

- `join_type`: `inner | left | right | full`.
- `select_columns` are the columns pulled from the right table; the join key comes along implicitly.
- The right table may be a `query` table. Joining a summarized helper query back to detail is the
  standard grain-change pattern.
- Conflicting right-side names are auto-suffixed; `rename` first rather than relying on that.
- Expression condition:
  `"join_condition": { "join_expression": { "type": "expression", "expression": "left.customer == right.name" } }`.

## union

```json
{ "type": "union", "table": { "type": "query", "workbook": "<wb>", "query_name": "<other_query>" }, "distinct": false }
```

Both sides need the same column names and types. To label each side, `mutate` a constant on both
first — `ibis.literal('1. Total')`, never a bare string (see reference/expressions.md).

## summarize — grain change only

Charts aggregate; queries stay per-row. Use `summarize` mid-pipeline, then usually `join` back to
detail. Worked example, AR ageing from the Accounting template — ledger rows rolled up to one row
per invoice, then joined back to the invoice for its customer and due date:

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
snake_case names. `dimensions: []` collapses everything to a single row (used by the funnel
template before a `union`).

## pivot_wider

Long to wide, inside a query. Rarely needed: a Table chart with non-empty `columns` pivots for you.

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

Rarely needed in a base query — charts apply their own order and limit from config. A `limit` in the
base query silently caps every chart built on it.

## sql — last resort

One operation, no others, and the query doc flips to `is_native_query: 1`, `is_builder_query: 0`
(`use_live_connection` stays `1`).

```json
{ "type": "sql", "raw_sql": "SELECT ... FROM `tabSales Invoice` ...", "data_source": "Site DB" }
```

Must start with SELECT or WITH; aliases become the column names; the dialect is the data source's
own. Dashboard filters still work (they append a `filter_group` after the `sql` op), so still expose
filterable columns per-row.

# Layering queries

A query can source from another query in the same workbook
(`{ "type": "query", "workbook": ..., "query_name": ... }`) in `source`, `join`, or `union`. Prefer
layering over one long pipeline when a helper result is reused by more than one chart — the helper
is then a single place to fix.
