# Charts

A chart has a `title`, a base `query` (one query doc), a `chart_type`, and a `config` (JSON).

**The chart does the aggregation.** At render time it builds a fresh data query that sources FROM its
base query, appends its own `summarize` (or `pivot_wider` when a split/columns dimension is set) from
the config, then `order_by` and `limit`. Dashboard filters are applied to the base query *before*
that aggregation. That is why base queries stay per-row.

Chart types: `Number`, `Bar`, `Line`, `Row`, `Donut`, `Funnel`, `Table`, `Map`, `Bubble`, `Sankey`.

## Titles

The title is the only label the reader gets, and it is the dashboard's own structure — there are no
headings. So the title has to name the chart on its own.

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

Measures and dimensions in a config use the same shapes as in the operations section, and reference
columns of the **base query's result**, not of the source table. Expression measures work anywhere a
measure does.

Keys on every chart config:

- `order_by`: list of `{ "column": { "type": "column", "column_name": "..." }, "direction": "asc"|"desc" }`.
  The names here are **post-aggregation** names, so sorting by a measure uses its `measure_name`
  (`"Revenue"`), not the underlying column.
- `limit`: integer (use it for top-N).
- `filters`: a chart-local filter group; `{"logical_operator": "And", "filters": []}` when unused.

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

- **The chart title is not rendered on Number cards** — `measure_name` IS the visible label, so make
  it human-readable ("Avg Invoice Value", not `avg_invoice_value`). The no-dates rule applies to a
  `measure_name` too.
- The card shows the **last row's** value. No `date_column` gives one aggregated row, i.e. the grand
  total (what a snapshot card wants). With a `date_column` it shows the latest period plus the delta
  against the previous one.
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
  line or bar per value). Cap it — one series per customer is unreadable.
- Bar `y_axis` extras: `stack`, `normalize`, `overlap`. Line: `smooth`, `show_area`,
  `show_data_points`. Per-series `type: "line" | "bar"` gives a mixed chart; `align: "Right"` puts a
  series on the secondary axis.
- `Row` is a horizontal bar — the right choice for a top-N ranking: dimension on `x_axis`,
  `order_by` the measure name desc, `limit: 10`.
- Time series belong on `Line` with the date dimension on the x-axis and an ascending `order_by`;
  without the sort the line zigzags.

## Donut / Funnel

```json
{ "label_column": { "dimension_name": "item_group", "column_name": "item_group", "data_type": "String" },
  "value_column": { "measure_name": "Revenue", "column_name": "base_net_total", "data_type": "Decimal", "aggregation": "sum" },
  "max_slices": 8 }
```

Donut is for part-of-whole with few categories. Funnel takes the same `label_column` /
`value_column` (plus `show_percentage`) and orders stages by `order_by`, or takes `measures: [...]`
where each measure is one stage. Sortable stage labels (`"1. Total"`, `"2. Ordered"`) keep the funnel
in order.

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

To show a detail listing (one row per document), put the identifying columns in `rows` — grouping by
a unique column such as `name` yields one row each — and use `max` for pass-through numbers that must
not be summed.

## The rest (rarely needed)

- `Map`: `location_column` (dimension), `value_column` (measure), `map_type: "world" | "india"`.
- `Bubble`: `xAxis`, `yAxis`, `size_column` (measures), `dimension` (one point per value).
- `Sankey`: `source_column`, `target_column` (dimensions), `value_column` (measure).

## Choosing

Single number → `Number`. Over time → `Line`. Compare categories → `Bar`; ranked top-N → `Row`.
Part of a whole, few slices → `Donut`. Stages → `Funnel`. Row-level detail or a cross-tab → `Table`.
Keep the existing chart type unless the request implies a change.
