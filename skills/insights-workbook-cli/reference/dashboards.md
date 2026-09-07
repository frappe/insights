# Dashboards

A dashboard has a `title` and `items` (a JSON array). Three item types: `chart`, `filter`, `text`.

## Layout

The grid is **20 columns wide**; `h` is in rows of about 30px. Every item needs a `layout` with a
unique `i` — two items sharing an `i` makes the grid drop one of them.

```json
{ "type": "chart", "chart": "<chart doc name>", "layout": { "i": "item-revenue-trend", "x": 0, "y": 4, "w": 12, "h": 9 } }
{ "type": "text", "text": "## Sales Overview", "layout": { "i": "item-heading", "x": 0, "y": 0, "w": 20, "h": 1 } }
```

Sizes that read well: filter row at the top `w:4 h:1` each, heading `w:20 h:1`, KPI row (one Number
chart with several measures) `w:20 h:3`, half-width chart `w:10 h:9`, full-width table `w:20 h:10`.
Lay out top to bottom: filters, KPIs, trends, then detail tables.

## Filters — routing is by query name

A filter item declares `links`: which charts it affects and, per chart, which **query column** it
filters. At execution the filter is appended as a `filter_group` to the end of that *query's*
pipeline, before the chart's own aggregation. Two consequences:

1. The query must expose the filter column per-row — one more reason not to pre-aggregate.
2. The link value names the **query** doc, not the chart:
   `` `query_name`.`column_name` `` — backtick, dot, backtick, exactly.

```json
{
  "type": "filter",
  "filter_name": "Date Range",
  "filter_type": "Date",
  "icon": "calendar",
  "default_operator": "within",
  "default_value": "Last 12 months",
  "links": {
    "tc-kpis": "`tq-sales-invoices`.`posting_date`",
    "tc-top-items": "`tq-sales-invoice-items`.`posting_date`"
  },
  "layout": { "i": "filter-date", "x": 0, "y": 0, "w": 4, "h": 1 }
}
```

- `filter_type`: `String` | `Number` | `Date`.
- `default_operator` / `default_value` are optional. Date filters normally use `within` with a
  timespan string; String filters normally use `in` and let the UI supply the values — it reads
  them from the linked column of the linked query, so link a column whose distinct values are the
  ones the user should pick from.
- **Link every chart that should react.** An unlinked chart silently ignores the filter, which reads
  as a bug to the user.
- One filter can point different charts at different queries and columns — a "Company" filter routes
  the invoice charts to `` `tq-sales-invoices`.`company` `` and the item charts to
  `` `tq-sales-invoice-items`.`company` ``.
- The named query is usually the chart's base query, but it can be **any query feeding it**: the
  filter is applied wherever that query is built, so filtering a shared helper query reaches every
  chart layered on top of it.
- A chart whose query chain lacks the column cannot be linked: add the column to the query first
  (usually a `join` to the parent document), then link it.
- **Dashboard filters are rule-based only.** Expression filters inside a dashboard filter group are
  dropped before execution, so a filter that must be an expression belongs in the query or the
  chart's own `filters`.

## Checklist

- Every `chart` item names an existing chart; every `links` key is a chart name and the query segment
  of its value is a query in that chart's chain.
- No two items share `layout.i`, and items do not overlap.
- A dashboard with unlinked charts and a filter bar is not finished.
