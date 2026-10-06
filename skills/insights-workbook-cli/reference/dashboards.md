# Dashboards

A dashboard has a `title` and `items` (a JSON array). An item is a `chart`, a `filter` or a `text`.

## A text item is a section heading, nothing more

A dashboard is read, not read *through*. A note is prose nobody scrolls to, and it takes grid rows from the charts. So a text item holds only a short section heading, such as "Conversion" or "Activity", on a dashboard with more than one section. Never repeat the dashboard title in one.

The text is rich text stored as HTML. The dashboard sanitizes it and renders it as HTML, not as markdown, so `## Conversion` shows the two hashes. Write the HTML. Give the heading the full width and `h:2`, which fits one line of an `<h1>` to `<h3>`:

```json
{ "type": "text", "text": "<h3>Conversion</h3>", "layout": { "i": "heading-conversion", "x": 0, "y": 2, "w": 20, "h": 2 } }
```

Everything else you would write in a text item goes in your reply to the user: the caveat, the data gap, the retired signal, the reason a chart is cut to a date. The user reads your reply. Say it there.

## Layout

The grid is **20 columns wide**. `h` counts rows of 22px. The grid keys each item by its `layout.i` and reads its `x`, `y`, `w` and `h`. Save never refuses a layout. It fills an `i`, `x`, `y`, `w` or `h` an item lacks, or holds as something other than a number: its type's size, at `x:0` below the lowest item. A chart is `w:10 h:20`, a Number chart `w:4 h:4`, a text `w:10 h:5` and a filter `w:4 h:2`. An item whose `layout.i` an earlier item holds gets a new one. An older site does none of this, and one item without a layout breaks the whole dashboard, so there write a whole `layout` on every item.

```json
{ "type": "chart", "chart": "<chart doc name>", "layout": { "i": "item-revenue-trend", "x": 0, "y": 4, "w": 10, "h": 20 } }
```

Match the sizes the app itself uses when a person adds an item: any chart but a Number `w:10 h:20`, a filter `w:4 h:2`. Width follows what the chart plots. A chart with a few bars keeps `w:10`, because at `w:20` its intent is hard to read. Widen only a table, a long time series, or a chart with many bars to `w:20`.

Lay out top to bottom: the filters, then one section per question the reader asks, the most important first. A section is its reading and then the charts that explain it: the conversion card and the conversion charts, then the activity cards and the activity charts. Do not put every reading on top and every chart under them. Order by importance, not by chart type.

Filters own their rows. No chart may share a row with a filter, and a chart you write into one overlaps it. So put every filter in the top row, side by side at `w:4 h:2`, and start the charts under it.

`vertical_compact_layout` is on by default, so the grid pulls every item up until it rests on the one above. A `y` you write is where the item starts, not where it stays.

A Number chart is not one cell. Save places a Number chart item with no cell as one cell with no `reading`, and that cell shows only the first reading. So write the cells yourself. Each of its readings is a cell of its own at `w:4`, as tall as what that reading shows: `h:4` for a title and a value, `h:5` when the reading names a comparison, `h:7` when the chart plots a sparkline. Every one of those cells has the same `chart`, and names its reading in `reading` — the reading's `id` in `number_columns`. Saving the chart sets a missing `id` to the `measure_name`, so read the chart back after you create it and take each `id` from its `number_columns`:

```json
{ "type": "chart", "chart": "<chart doc name>", "reading": "Revenue", "layout": { "i": "kpi-revenue", "x": 0, "y": 0, "w": 4, "h": 5 } }
```

## Editing a live dashboard — merge, never rewrite

**The site owns the layout. Your script does not.**

The user moves charts, resizes them, adds a filter, and edits your titles. Every one of those changes lives in the same `items` array you write. A second run of your build script writes the `items` it computed. That destroys all the changes, silently. The user finds out by looking.

This is the failure mode, and it looks reasonable in code:

```python
# WRONG -- every user edit since the first run is now gone
items = build_the_layout_i_planned()
call("doc", "update", "Insights Dashboard v3", dashboard, stdin=json.dumps({"items": items}))
```

`doc update` does not protect you here. Its optimistic check compares `modified`. You read the document a moment before you wrote it, so the check passes. It catches an edit made *during* your write, not one made since your last run. Never reach for `--force`.

**Create the whole `items` array exactly once, when you create the dashboard.** One later write may replace it: a redesign the user asked for, when the live `items` equal the `items` your script last wrote. Keep a copy of every `items` you write, and compare it with the live array right before the redesign. If they differ, the user changed the layout since. Merge instead, or ask. `modified_by` is not that proof, because it does not say which fields changed.

Every other write after creation is a merge into the live array:

1. `doc get` the dashboard and parse `items`.
2. Match each item you want to change against a live item, by key.
3. Change only the fields you mean to change. Keep the live `layout` as it is.
4. Append a new chart below the current bottom: `y = max(item.layout.y + item.layout.h)`. Put a new filter in the top filter row, right of the last filter. When that row is full or there is none, put it at `x:0 y:0` and move every other item down 2 rows, as the app does.
5. Write the merged array back.

The key of a chart or a filter is not `layout.i`, because the UI generates its own ids:

| Item type | Match a live item by |
|---|---|
| `chart` | its `chart` — the chart document name — and its `reading`, which a Number cell names |
| `filter` | its `filter_name` |
| `text` | its `layout.i`, the one key it has |

A Number chart puts several cells on one dashboard, all naming the same chart, so the chart name alone matches all of them and keeps one. The `reading` is what tells them apart.

Four rules the merge must keep:

- **Never drop an item you did not add.** Remove one only when the user asked for that removal, by name.
- **Never overwrite a `layout` or `layouts`.** Position and size belong to whoever last dragged the item. `layouts` holds the item's place on a narrow screen.
- **Merge a filter's `links` key by key.** Add the entry for your new chart. Leave every other entry alone, including one the user wired by hand.
- **Keep keys you do not recognise**, on the item and on the document. Copy the live item and update it. Do not rebuild it from scratch.

`examples/build_workbook.py` ships `patch_dashboard()`, which does exactly this, and `Build.upsert` runs it for a dashboard's `items`. Use them instead of writing the merge again.

## Filters — routing is by query name

A filter item declares `links`: which charts it affects and, per chart, which **query column** it filters. At execution Insights appends the filter as a `filter_group` to the end of that *query's* pipeline, before the chart's own aggregation. Two consequences:

1. The query must expose the filter column per-row. That is one more reason not to pre-aggregate.
2. The link value names the **query** doc, not the chart. The form is `` `query_name`.`column_name` ``: backtick, dot, backtick, exactly.

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
  "layout": { "i": "filter-date", "x": 0, "y": 0, "w": 4, "h": 2 }
}
```

- `filter_type`: `String` | `Number` | `Date`.
- `default_operator` and `default_value` are optional. Date filters normally use `within` with a timespan string. String filters normally use `in` and let the UI supply the values. The UI reads the values from the linked column of the linked query. So link a column whose distinct values are the ones the user should pick from.
- A default date range hides history. Set one only when the user asks for a window. Otherwise leave the filter empty, so the dashboard opens on everything the queries hold.
- `last 4 weeks` covers four whole weeks and excludes the running week. When the running week matters, write `last 4 weeks (include current)`.
- `default_user_key` opens the filter on each reader's own user default. Set it to the key, such as `"Company"`, beside `default_operator: "="`. The dashboard then sends the reader's value as the default and ignores `default_value`. A reader with no value for the key sees the filter empty. For a user permission key such as `Company`, Frappe takes the reader's single User Permission on it, then the default stored under the lower-case key (`company`, which ERPNext sets), then the User Permission marked default. Write `Company`, not `company`: the lower-case key skips the User Permission lookup. A person who edits the default in the filter editor removes `default_user_key`.
- **Link every chart that should react.** An unlinked chart silently ignores the filter, which reads as a bug to the user.
- **An entity the reader switches between is a dashboard filter.** One dashboard with a Product filter, never one copy of the charts per product with the product in each chart's own filters. A comparison between entities is a dimension or a split, not a filter. A comparison dashboard still gets a filter when one member dominates, so the reader can drop it and compare the rest.
- **The Date filter owns the period.** Do not give a chart its own `within` filter. A chart with its own window disagrees with the filter bar, and the reader cannot change it.
- One filter can point different charts at different queries and columns. A "Company" filter routes the invoice charts to `` `tq-sales-invoices`.`company` `` and the item charts to `` `tq-sales-invoice-items`.`company` ``.
- The named query is usually the chart's base query. It can be **any query that is the chart's source**. Insights applies the filter wherever that query is built. So a filter on a shared helper query reaches every chart built on it.
- A chart whose query chain lacks the column cannot be linked: add the column to the query first (usually a `join` to the parent document), then link it.
- **Dashboard filters are rule-based only.** Insights drops expression filters inside a dashboard filter group before execution. A filter that must be an expression belongs in the query or in the chart's own `filters`.
- Leave a chart **unlinked** when its window is fixed by design, such as a cohort or a fixed observation period. A date filter on it cuts days out of the window instead of filtering the view. A Number card with its own `window.span` is one of these: the span names its period, so leave it off the Date filter's links. Say in your reply which charts you left unlinked, and why.
- A Number card with no `window`, linked to the Date filter on its `date_column`, reads a `within` value as its Period. Its `previous` and `last year` comparisons then step back from the filter's span. A `between` range only narrows its rows, so it prints one number and no comparison.

### Run a chart under the dashboard filters

`insights.api.view.get_chart_data` takes the filter state as `filters`, keyed by filter name, one `{"operator", "value"}` per filter. It routes that state through the dashboard's links, so it needs `dashboard`. Without `dashboard` it ignores `filters`, and the chart runs unfiltered.

```sh
frappectl -s $SITE method call insights.api.view.get_chart_data -F chart=<chart> -F dashboard=<dashboard> \
  -F 'filters:={"Company": {"operator": "=", "value": "Acme"}, "Date Range": {"operator": "within", "value": "last 3 months"}}'
```

The chart must be on that dashboard, or the call answers "not found". A filter with no operator, or with an empty value for an operator that needs one, is not applied.

## Checklist

- A `text` item is only a section heading, written as HTML.
- No chart carries its own `within` filter. The Date filter owns the period.
- Every `chart` item names an existing chart. Every `links` key is a chart name, and the query segment of its value is a query in that chart's chain.
- Items do not overlap.
- Every edit after the first run went through the merge, so every live `layout` survived. The one exception is a redesign the user asked for, over live `items` equal to what your script last wrote.
- A dashboard with unlinked charts and a filter bar is not finished, unless you named the exception.
