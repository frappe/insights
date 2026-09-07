# Dashboards

A dashboard has a `title` and `items` (a JSON array). Author two item types: `chart` and `filter`.

## Never add a text item

The document model has a third type, `text`. Do not author it.

A dashboard is read, not read *through*. A heading repeats the dashboard title, and a note is prose
nobody scrolls to. Both take grid rows from the charts.

Everything you would write in a text item goes in your reply to the user instead: the caveat, the
data gap, the retired signal, the reason a chart is cut to a date. The user reads your reply. Say it
there, and leave the grid to the charts.

## Layout

The grid is **20 columns wide**; `h` is in rows of about 30px. Every item needs a `layout` with a
unique `i` — two items sharing an `i` makes the grid drop one of them.

```json
{ "type": "chart", "chart": "<chart doc name>", "layout": { "i": "item-revenue-trend", "x": 0, "y": 4, "w": 10, "h": 8 } }
```

Match the sizes the app itself uses when a person adds an item: a Number chart `w:20 h:3`, any other
chart `w:10 h:8`, a filter `w:4 h:1`. Widen a table or a long time series to `w:20`. Lay out top to
bottom: filters, KPIs, trends, then detail tables.

## Editing a live dashboard — merge, never rewrite

**The site owns the layout. Your script does not.**

The user moves charts, resizes them, adds a filter, and edits your titles. Every one of those
changes lives in the same `items` array you write. So a second run of your build script that writes
the `items` it computed destroys all of it, silently, and the user finds out by looking.

This is the failure mode, and it looks reasonable in code:

```python
# WRONG -- every user edit since the first run is now gone
items = build_the_layout_i_planned()
call("doc", "update", "Insights Dashboard v3", dashboard, stdin=json.dumps({"items": items}))
```

`doc update` does not protect you here. Its optimistic check compares `modified`, and you read the
document a moment before you wrote it, so the check passes. It catches an edit made *during* your
write, not one made since your last run. Never reach for `--force`.

**Create the whole `items` array exactly once, when you create the dashboard.** Every write after
that is a merge into the live array:

1. `doc get` the dashboard and parse `items`.
2. Match each item you want to change against a live item, by key.
3. Change only the fields you mean to change. Keep the live `layout` as it is.
4. Append anything new below the current bottom: `y = max(item.layout.y + item.layout.h)`.
5. Write the merged array back.

The key is not `layout.i`, because the UI generates its own ids:

| Item type | Match a live item by |
|---|---|
| `chart` | its `chart` — the chart document name |
| `filter` | its `filter_name` |

Four rules the merge must keep:

- **Never drop an item you did not add.** Remove one only when the user asked for that removal, by
  name.
- **Never overwrite a `layout`.** Position and size belong to whoever last dragged the item.
- **Merge a filter's `links` key by key.** Add the entry for your new chart. Leave every other entry
  alone, including one the user wired by hand.
- **Keep keys you do not recognise**, on the item and on the document. Copy the live item and
  update it. Do not rebuild it from scratch.

`examples/build_workbook.py` ships `patch_dashboard()`, which does exactly this. Use it rather than
writing the merge again.

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
- A default date range hides history. Set one only when the user asks for a window. Otherwise leave
  the filter empty, so the dashboard opens on everything the queries hold.
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
- A chart whose window is fixed by design — a cohort, a fixed observation period — must be left
  **unlinked**. A date filter on it cuts days out of the window instead of filtering the view. Say
  in your reply which charts you left unlinked, and why.

## Checklist

- No `text` item.
- Every `chart` item names an existing chart; every `links` key is a chart name and the query segment
  of its value is a query in that chart's chain.
- No two items share `layout.i`, and items do not overlap.
- Every edit after the first run went through the merge, so every live `layout` survived.
- A dashboard with unlinked charts and a filter bar is not finished, unless you named the exception.
