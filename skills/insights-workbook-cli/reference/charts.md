# Charts

A chart has a `title`, a base `query` (one query doc), a `chart_type`, and a `config` (JSON).

**The chart does the aggregation.** At render time the chart builds a new data query that sources
FROM its base query. It appends its own `summarize` from the config (or `pivot_wider` when a split
or columns dimension is set), then `order_by` and `limit`. Insights applies dashboard filters to the
base query *before* that aggregation. So base queries stay per-row.

Chart types: `Number`, `Bar`, `Line`, `Row`, `Donut`, `Funnel`, `Table`, `Map`, `Bubble`, `Sankey`.

## Titles

The title is the only label the reader gets. A dashboard has no headings, so the titles carry its
structure. Each title must name its chart on its own.

State the measure, then the grain: "Revenue, per Month". "Sites That Published, Template Against the
Rest". "Top 10 Customers by Order Value".

**Never put a date, a date range or an era in a title.** Not "Revenue Since 2026-07-08", not "Signups,
Last 6 Weeks", not "Q3". Three reasons, and each one alone is enough:

- The dashboard filter owns the window, and the user changes it. The title then lies.
- A relative window ("Last 6 Weeks") is true on the day you write it and wrong every day after.
- A date you hardcode into a query filter is a fact about the data, not about the chart. It belongs
  in your reply to the user, where you can explain it.

The same goes for a count you measured today. "Top 34 Template Groups" becomes wrong when the 35th
appears. Write "Top Template Groups".

Say the era in your reply instead: "the age charts start at 2026-07-08, the first blank-start event,
because a blank start leaves no trace before it."

Measures and dimensions in a config use the same shapes as in the operations section. They reference
columns of the **base query's result**, not of the source table. Expression measures work anywhere a
measure does.

Keys on every chart config:

- `order_by`: list of `{ "column": { "type": "column", "column_name": "..." }, "direction": "asc"|"desc" }`.
  The names here are **post-aggregation** names, so sorting by a measure uses its `measure_name`
  (`"Revenue"`), not the underlying column.
- `limit`: integer (use it for top-N).
- `filters`: a chart-local filter group. Use `{"logical_operator": "And", "filters": []}` when unused.

## Number (KPI cards)

```json
{
  "number_columns": [
    { "measure_name": "Revenue", "column_name": "base_net_total", "data_type": "Decimal", "aggregation": "sum" },
    { "measure_name": "Avg Invoice Value", "column_name": "base_net_total", "data_type": "Decimal", "aggregation": "avg" },
    { "measure_name": "Active Customers", "column_name": "customer", "data_type": "Integer", "aggregation": "count_distinct" }
  ],
  "number_column_options": [
    { "prefix": "₹ ", "decimal": 2, "shorten_numbers": true },
    { "prefix": "₹ ", "decimal": 2, "shorten_numbers": true },
    { "shorten_numbers": false }
  ],
  "comparison": true,
  "sparkline": true,
  "date_column": { "dimension_name": "posting_date", "column_name": "posting_date", "data_type": "Date", "granularity": "month" },
  "order_by": [ { "column": { "type": "column", "column_name": "posting_date" }, "direction": "asc" } ],
  "limit": 100,
  "filters": { "logical_operator": "And", "filters": [] }
}
```

- **Number cards do not show the chart title.** `measure_name` is the visible label. Make it readable
  ("Avg Invoice Value", not `avg_invoice_value`). The no-dates rule applies to a `measure_name` too.
- The card shows the **last row's** value. Without a `date_column` the query gives one aggregated
  row, the grand total. A snapshot card wants that. With a `date_column` the card shows the latest
  period and the delta against the previous one.
- `comparison` and `sparkline` need a `date_column` and an ascending `order_by` on it, otherwise the
  delta compares arbitrary rows.
- `number_column_options` is positional: one entry per measure, same order.
- A KPI row is normally ONE Number chart with several measures, not several charts.

## Bar / Line / Row (axis charts)

```json
{
  "x_axis": { "dimension": { "dimension_name": "posting_date", "column_name": "posting_date", "data_type": "Date", "granularity": "month" } },
  "y_axis": {
    "series": [ { "measure": { "measure_name": "Revenue", "column_name": "base_net_total", "data_type": "Decimal", "aggregation": "sum" } } ],
    "show_data_labels": false
  },
  "order_by": [ { "column": { "type": "column", "column_name": "posting_date" }, "direction": "asc" } ],
  "limit": 100,
  "filters": { "logical_operator": "And", "filters": [] }
}
```

- Renders as: summarize by the x-axis dimension, one series per measure.
- `split_by: { "dimension": {...}, "max_split_values": 10 }` pivots the series by that dimension (one
  line or bar per value). Cap it. One series per customer is unreadable.
- Bar `y_axis` extras: `stack`, `normalize`, `overlap`. Line: `smooth`, `show_area`,
  `show_data_points`. Per-series `type: "line" | "bar"` gives a mixed chart. `align: "Right"` puts a
  series on the secondary axis.
- `Row` is a horizontal bar. Use it for a top-N ranking: dimension on `x_axis`, `order_by` the
  measure name desc, `limit: 10`.
- Put a time series on `Line`, with the date dimension on the x-axis and an ascending `order_by`.
  Without the sort the line zigzags.

## Donut / Funnel

```json
{ "label_column": { "dimension_name": "item_group", "column_name": "item_group", "data_type": "String" },
  "value_column": { "measure_name": "Revenue", "column_name": "base_net_total", "data_type": "Decimal", "aggregation": "sum" },
  "max_slices": 8 }
```

Use `Donut` for part-of-whole with few categories. `Funnel` takes the same `label_column` and
`value_column`, plus `show_percentage`, and orders the stages by `order_by`. It also takes
`measures: [...]`, where each measure is one stage. Sortable stage labels (`"1. Total"`,
`"2. Ordered"`) keep the funnel in order.

## Table

```json
{
  "rows": [ { "dimension_name": "Customer", "column_name": "customer", "data_type": "String" } ],
  "columns": [],
  "values": [ { "measure_name": "Order Value", "column_name": "base_grand_total", "data_type": "Decimal", "aggregation": "sum" } ],
  "order_by": [ { "column": { "type": "column", "column_name": "Order Value" }, "direction": "desc" } ],
  "limit": 20,
  "show_row_totals": true,
  "filters": { "logical_operator": "And", "filters": [] }
}
```

Empty `columns` gives a grouped table (summarize by `rows`). Non-empty `columns` pivots, capped by
`max_column_values`. Other options: `show_filter_row`, `show_column_totals`, `compact_numbers`,
`enable_color_scale`.

To show a detail listing with one row per document, put the identifying columns in `rows`. A group by
a unique column such as `name` yields one row each. Use `max` for pass-through numbers that must not
be summed.

## The rest (rarely needed)

- `Map`: `location_column` (dimension), `value_column` (measure), `map_type: "world" | "india"`.
- `Bubble`: `xAxis`, `yAxis`, `size_column` (measures), `dimension` (one point per value).
- `Sankey`: `source_column`, `target_column` (dimensions), `value_column` (measure).

## Choosing

Single number → `Number`. Over time → `Line`. Compare categories → `Bar`. Ranked top-N → `Row`.
Part of a whole, few slices → `Donut`. Stages → `Funnel`. Row-level detail or a cross-tab → `Table`.
Keep the existing chart type unless the request implies a change.

## Making it readable

The chart type is the easy half. These four decide whether anyone can read the result.

**Count the dimension before you pick the chart.** A dimension you have not counted is a chart you
cannot size. Count it in the scratch query with `summarize` and `count_distinct`. Then:

| Distinct values | Use |
|---|---|
| 1 | Nothing. One value is not a split. Find the column that carries the split, or drop the chart. |
| 2 to 8 | `Donut`, or a stacked `Bar` |
| up to ~15 | `Bar`, or `Line` for a series |
| more | `Row` with `order_by` desc and `limit: 10`, and say it is a top 10 |
| hundreds | `Table`. A bar per customer is a smear, not a chart. |

The same cap applies to `split_by` and to a `Table`'s pivot `columns`. One line per value of a
high-cardinality column is unreadable at any size.

**A share needs its n beside it.** A normalized stacked bar draws a bucket of 14 rows exactly as
strongly as a bucket of 545. Pair it with a `Table` beside it. The table holds the raw counts and the
distinct entity count. The bar gives the shape. The table gives the n, so nobody misreads a thin
bucket as a strong result.

**Lead with the answer.** The first chart is the one that answers the user's question. KPIs above
trends, trends above breakdowns, detail tables last. A dashboard that opens on a breakdown makes the
reader hunt.

**Prefer fewer charts.** Every chart must earn its grid rows. Two charts that show the same cut in
different shapes are one chart and a decision you did not make.

## Drill down

Every chart drills down, and costs nothing to author. This works only if the base query stays
per-row.

The reader clicks a series element on an axis, donut, funnel or map chart. On a `Number` card or a
`Table` the reader double-clicks a numeric cell. Insights then finds the **last** `summarize` or
`pivot_wider` in the chart's data query. It cuts the pipeline off just before that step, refilters by
that row's dimension values, and opens the result in a dialog.

The chart's own aggregation is that `summarize`. So with a per-row base query, **one click lands on
the source rows behind the number**: the invoices, the events, the documents. That is the payoff of
rule 1 in `rules.md`, and the strongest reason not to pre-aggregate.

Three things to know:

- **A pre-aggregated base query costs a click.** The first drill-down lands on the base query's
  aggregated rows, not the source rows. The dialog's own table drills again. The second click inlines
  the base query's pipeline and reaches the source rows. It works. It is one click of confusion you
  authored.
- **A chain with no `summarize` anywhere cannot drill down at all.** Insights walks the query chain
  to find one. When it finds none, it toasts "Drill down is only supported on summarized data".
- **The clicked column must be numeric** on a `Number` card and a `Table`. A count measure typed as
  `String` renders and cannot be drilled. Type every measure.
