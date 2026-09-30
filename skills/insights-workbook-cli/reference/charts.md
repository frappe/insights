# Charts

A chart has a `title`, a base `query` (one query doc), a `chart_type`, and a `config` (JSON).

**The chart does the aggregation.** At render time the chart builds a new data query that sources FROM its base query. It appends its own `summarize` from the config (or `pivot_wider` when a split or columns dimension is set), then `order_by` and `limit`. Insights applies dashboard filters to the base query *before* that aggregation. So base queries stay per-row.

Chart types: `Number`, `Bar`, `Line`, `Row`, `Donut`, `Funnel`, `Table`, `Map`, `Bubble`, `Sankey`, `Heatmap`.

## Titles and labels

The title names its chart on its own. A section heading is a text item (see `dashboards.md`), so the title does not repeat the section.

Write 1 to 4 words: what the chart cuts by or reads. "Install Method", "Site Plan", "Country", "Funnel", "Weekly Retention", "Top Customers". Leave out the grain when the axis shows it: "Revenue", not "Revenue, per Month". Leave out the unit when the dashboard counts one thing: on a dashboard of sites, "Site Plan", not "Sites by Site Plan".

Every name the reader sees is a label: the title, a `measure_name`, a dimension name, a funnel stage. Name a measure in 1 to 3 words. Each label is one self-explanatory word where one will do, in the host platform's vocabulary, never your query's. Take the word from the doctype or field the data comes from: "Site Plan" (the `Site Plan` doctype), not "plan price". "Sites", not "scanned sites". "Dedicated", not "own server". "Retention", not "kept". A reading such as "Came Back After Day 0" or a bare "Day 1" needs a real name, such as "D1 Retention". When no plain word fits your definition, change the definition to fit the word: "Weekly" is a site active in each of the last 4 weeks.

**Never put a date, a date range or an era in a title.** Not "Revenue Since 2026-07-08", not "Signups, Last 6 Weeks", not "Q3". Three reasons, and each one alone is enough:

- The dashboard filter owns the period, and the user changes it. The title then lies.
- A relative period ("Last 6 Weeks") is true on the day you write it and wrong every day after.
- A date you hardcode into a query filter is a fact about the data, not about the chart. It belongs in your reply to the user, where you can explain it.

The same goes for a count you measured today. "Top 34 Template Groups" becomes wrong when the 35th appears. Write "Top Template Groups".

Say the era in your reply instead: "the age charts start at 2026-07-08, the first blank-start event, because a blank start leaves no trace before it."

## Description and info

Two optional text fields on the chart document, beside `title`. Both show beside the chart title on a dashboard, a shared link and the workbook's chart view. A desk island prints its own header and shows neither.

- `info` is the text behind an info mark beside the title. The reader sees it on hover or focus. Put definitions and caveats here: what a measure counts, what a status means, what the data leaves out. "Paid = a site running this product moved to a paid plan within 30 days of the trial." Line breaks are kept.
- `description` is one line printed under the title. Leave it empty. Write one only when the title cannot carry what every reader must see at a glance. It takes height from the plot on every dashboard that shows the chart.
- A Number chart shows neither: each card shows the reading's name, not the chart title, and has no line under it. Put a reading's info in its `number_column_options` entry instead (see Number below).
- The no-dates rule for titles applies to both.

Measures and dimensions in a config use the same shapes as in the operations section. They reference columns of the **base query's result**, not of the source table. Expression measures work anywhere a measure does.

Keys on every chart config:

- `number_format`: how the chart prints a number — `{ "shorten": true, "decimals": 2, "prefix": "", "suffix": "" }`. Every value of the chart inherits it.
- `number_formats`: one Measure's own format, keyed by `measure_name`, overriding `number_format` key by key. A chart plotting one measure writes the Measure's entry and leaves the default empty.
- The unit belongs to the measure, not to a prefix. Set `format: "currency"` or `format: "percent"` on the measure (see `operations.md`). A `prefix` or `suffix` you write overrides the unit's symbol, so do not hard-code a currency symbol.
- `order_by`: list of `{ "column": { "type": "column", "column_name": "..." }, "direction": "asc"|"desc" }`. The names here are **post-aggregation** names, so sorting by a measure uses its `measure_name` (`"Revenue"`), not the underlying column.
- `limit`: integer (use it for top-N). A `Table` pages through every row, `limit` at a time, so a top-N table puts a `limit` operation in its query instead.
- `filters`: a chart-local filter group. Use `{"logical_operator": "And", "filters": []}` when unused.

## Number (reading cards)

```json
{
  "number_columns": [
    { "measure_name": "Revenue", "column_name": "base_net_total", "data_type": "Decimal", "aggregation": "sum", "format": "currency" },
    { "measure_name": "Avg Invoice", "column_name": "base_net_total", "data_type": "Decimal", "aggregation": "avg", "format": "currency" },
    { "measure_name": "Customers", "column_name": "customer", "data_type": "Integer", "aggregation": "count_distinct" }
  ],
  "number_formats": {
    "Revenue": { "decimals": 2, "shorten": true },
    "Avg Invoice": { "decimals": 2, "shorten": true }
  },
  "number_column_options": [
    { "comparison": { "source": "previous" } },
    {},
    {}
  ],
  "sparkline": true,
  "date_column": { "dimension_name": "posting_date", "column_name": "posting_date", "data_type": "Date" },
  "window": { "grain": "month" },
  "limit": 100,
  "filters": { "logical_operator": "And", "filters": [] }
}
```

- **Number cards do not show the chart title.** `measure_name` is the visible label, so it follows the label rules above. The no-dates rule applies to a `measure_name` too.
- The card shows the **last row's** value. Without a `window` the query gives one aggregated row, the grand total. A snapshot card wants that. `window` is what groups the card by date: `grain` ("month") gives one row per period in the data, `span` ("month to date") one row per stretch of the calendar. A `span` uses the grammar of the `within` filter (see `operations.md`). Either needs `date_column`.
- **Read a closed period, or compare like with like.** A `grain` card reads the newest period in the data, which is the running one: two days of a week against a whole week prints -99%. Use a span that ends at a closed period (`"Last 1 week"`, `"Last 1 month"`), or a to-date span (`"Week to date"`), whose `previous` comparison is the same stretch of the period before. Give every card in one row the same `window`. Cards side by side that read different periods look comparable and are not.
- `number_column_options` is positional: one entry per measure, same order. It holds what belongs to the reading: `comparison`, `target`, `negative_is_better`, `color`, `info`.
- `info` on a reading's options entry is the text behind an info mark beside that reading's name, for its definitions and caveats, as on any chart. A Number chart has no chart-level `description` or `info`: leave both empty.
- A comparison belongs to one reading, in that reading's options entry. `source` is `previous`, `last year`, `constant` (with `value`) or `measure` (with `measure`). `show` prints the gap as a percent (`change`, the default) or a signed number (`delta`), and `label` renames it. `previous` and `last year` both need a Period. Beside a `grain` the comparison is the period one grain before the reading's, matched by date, and a period with no data prints no figure. Beside a `span` Insights fetches the earlier period itself and matches it by date. `last year` needs a `span`, and prints nothing beside a `grain`. A second comparison is a second card.
- `target` sits beside it, also per reading: `{ "value": 750000 }` or `{ "measure": { ... } }`.
- The card sorts its own periods. An `order_by` on the date column is replaced, so do not write one.
- `sparkline` is chart-level and plots only beside a `window`. A `grain` card plots its own periods. A `span` card runs a second query one grain finer: days for a week or month span, months for a quarter, year or fiscal year span. A span counted in days (`"Last 7 days"`, `"Day to date"`) plots no sparkline, so size its cell as a card without one. Without a `window` there is no series.
- Each reading gets an `id` when the chart is saved: its `measure_name`, unless you set one. A dashboard cell names the reading by this `id`. Two readings with the same `measure_name` get the same `id`, and a cell can reach only the first, so give every reading its own name.
- Readings the reader compares side by side are ONE Number chart with several measures, not several charts. Readings that are nested counts of one population (Installed, then Active, then Weekly, each a subset of the one before) are not cards at all. They are a `Funnel`, which shows the drop between them.

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
- `split_by: { "dimension": {...}, "max_split_values": 10 }` pivots the series by that dimension (one line or bar per value). Cap it. One series per customer is unreadable.
- Bar `y_axis` extras: `stack`, `normalize`, `overlap`. Line: `smooth`, `show_area`, `show_data_points`. Per-series `type: "line" | "bar"` gives a mixed chart. `align: "Right"` puts a series on the secondary axis. A chart with bars on both axes neither stacks, overlaps nor normalizes. Bars beside a line on the other axis still stack.
- `show_data_labels` on `y_axis` labels every series. The same key on one series overrides it for that series, so a count bar can stay unlabelled beside a labelled rate line.
- `y_axis.reference_lines`: a list of rules across the plot. Each is `{ "axis": "y", "measure_name": "Revenue", "aggregate": "average", "label": "Average" }` — an aggregate of one of the chart's own measures, named and not copied — or a constant with `value`. `axis: "x"` plots a vertical rule at a category or date value. `align` picks the axis a `y` rule is read against, and `label_placement`, `color` and `dashed` are the rest of its look.
- `"show_trend_line": true` on a series draws its trend line: the straight least-squares fit through the series' plotted points, each at its date or number on the x axis. It draws only when the x axis is a date or a number: a category axis may be sorted by a measure, and a line through a ranking says nothing. A `Row` chart plots a number x axis as categories, so there it draws only on a date. A series stacked with another draws none, because it is plotted at its stack height or share and the fit reads its own values. Under `stack` without `overlap`, or under `normalize`, bars stack with bars and areas with areas, a split's values stack with each other (so a stacked split gets none, even when the result holds one value), and a line never stacks. So a lone bar, a line beside stacked bars, or overlapped bars (`overlap` cancels `stack`) still get one. A `Row` chart draws every series as a bar, so there a line-typed series stacks like the bars. It is dashed, in the series' color, on the series' axis, and labelled "<series> trend". A split gets one line per split value. Nulls are skipped, and a series with fewer than two points gets none. Hiding the series in the legend hides its trend line too. Use it on a timeline, when the question is which way a measure is heading.
- `tooltip: { "measures": [ ... ] }`: measures that reach the tooltip and nothing else — no series, no legend entry, no place on the value axis. For the count behind a rate, or a target beside an actual. A dimension cannot go here: every tooltip value is one per plotted row.
- `Row` is a horizontal bar. Use it for a top-N ranking: dimension on `x_axis`, `order_by` the measure name desc, `limit: 10`.
- Put a time series on `Line`, with the date dimension on the x-axis. A chart nobody sorted runs forwards on its own. An `order_by` you write wins over that, so sort only when the reading is a ranking rather than a timeline.

## Donut / Funnel

```json
{ "label_column": { "dimension_name": "item_group", "column_name": "item_group", "data_type": "String" },
  "value_column": { "measure_name": "Revenue", "column_name": "base_net_total", "data_type": "Decimal", "aggregation": "sum" },
  "max_slices": 8 }
```

Use `Donut` for part-of-whole with few categories.

`Funnel` takes the same `label_column` and `value_column`, one stage per value, biggest first. Or it takes `measures: [...]`: one stage per measure, in that order, each aggregated over the whole result, and the `measure_name` is the stage label. Every stage must be a subset of the stage before it, counted in one unit from one source query: for example `distinct_count_if(...)` measures over one per-site query. Stages summed independently from different sources are not a funnel. A later stage can come out larger than an earlier one, and the percents between them mean nothing.

## Table

```json
{
  "rows": [ { "dimension_name": "Customer", "column_name": "customer", "data_type": "String" } ],
  "columns": [],
  "values": [ { "measure_name": "Order Value", "column_name": "base_grand_total", "data_type": "Decimal", "aggregation": "sum" } ],
  "order_by": [ { "column": { "type": "column", "column_name": "Order Value" }, "direction": "desc" } ],
  "limit": 20,
  "show_row_totals": true,
  "conditional_formatting": {
    "formats": [
      { "mode": "color_scale", "column": { "type": "column", "column_name": "Order Value" }, "colorScale": "ascending", "scaleScope": "local" }
    ],
    "columns": []
  },
  "filters": { "logical_operator": "And", "filters": [] }
}
```

Empty `columns` gives a grouped table (summarize by `rows`). Non-empty `columns` pivots, capped by `max_column_values`. Other options: `show_column_totals`, `enable_color_scale` (one scale on every numeric column).

Give a table a color scale on the column that carries the point, so the reader's eye goes there first. That is a `color_scale` entry in `conditional_formatting.formats`, as above. Its `column_name` is a column the table renders: a `measure_name` (on a pivot, every column of that measure) or a pivot's dimension value (every column for that value). A name that matches no rendered column paints nothing. `colorScale` `ascending` makes the higher values deep, `descending` the lower ones. `scaleScope` `local` scales the column against itself. `global`, the default, shares one range across every column with a scale, so they read side by side. A `cell_rules` entry instead highlights a cell that passes `operator` (`<`, `<=`, `=`, `>=`, `>`, `!=`) and `value`, in `color` `red`, `amber` or `green`. Leave `columns` empty.

To show a detail listing with one row per document, put the identifying columns in `rows`. A group by a unique column such as `name` yields one row each. Use `max` for pass-through numbers that must not be summed.

## The rest (rarely needed)

- `Map`: `location_column` (dimension), `value_column` (measure), `map_type: "world" | "india"`. A region plots only when its value, in title case, is a region name of the map. `region_mappings: { "world": { "USA": "United States of America" } }` maps a value to a map name, keyed by `map_type`. `insights.api.maps.find_unresolved_regions` takes `map_type`, `user_regions` (the column's distinct values) and `chart_name` (for the mappings it already has), and returns the `unresolved` values with up to five `suggestions` each. `get_available_regions(map_type)` lists every name. `save_region_mappings(chart_name, map_type, mappings)` writes them into the chart's config, or you write `region_mappings` yourself.
- `Bubble`: `xAxis`, `yAxis`, `size_column` (measures), `dimension` (one point per value).
- `Sankey`: `source_column`, `target_column` (dimensions), `value_column` (measure).
- `Heatmap`: `x_column`, `y_column` (dimensions) and `value_column` (measure) — one cell per pair of their values. `show_values` prints the number in the cell. `palette` is `sequential` (a magnitude) or `diverging` (signed data): blue below zero, pale at zero, red above. So when a fall is the alarm, plot the fall (previous minus current) to paint it red. `min`/`max` pin the ends of the color scale that the data's own ends set otherwise. On `diverging` an end you leave out mirrors the other, so zero stays in the middle.

## Choosing

Single number → `Number`. Over time → `Line`. Compare categories → `Bar`. Ranked top-N → `Row`. Part of a whole, few slices → `Donut`. Nested stages of one population → `Funnel`. Row-level detail or a cross-tab → `Table`. Two dimensions against one measure → `Heatmap`. Keep the existing chart type unless the request implies a change.

## Making it readable

The chart type is the easy half. These decide whether anyone can read the result.

**Count the dimension before you pick the chart.** A dimension you have not counted is a chart you cannot size. Count it with `profile_column`, which answers `distinct_count` and the share of each top value. Without it, `summarize` with a measure whose `aggregation` is `count_distinct` (in an expression, `distinct_count(col)`). Then:

| Distinct values | Use |
|---|---|
| 1 | Nothing. One value is not a split. Find the column that holds the split, or drop the chart. |
| 2 to 8 | `Donut`, or a stacked `Bar` |
| up to ~15 | `Bar`, or `Line` for a series |
| more | `Row` with `order_by` desc and `limit: 10`, and say it is a top 10 |
| hundreds | `Table`. A bar per customer is a smear, not a chart. |

The same cap applies to `split_by` and to a `Table`'s pivot `columns`. One line per value of a high-cardinality column is unreadable at any size. The chart's width follows its bar count too (see Layout in `dashboards.md`).

**Drop a split with no signal.** The count is not the only test. Also count the top value's share: when one value holds most rows (ERPNext on 722 of 838 sites), the chart shows that one value. Drop the split, or let a dashboard filter take the dominant value out. Drop a dimension that is not filled for every value of a dashboard filter, because the chart reads empty for the rest. Drop a concept the users do not use.

**Compare segments by rate, not count.** Segments differ in size, so their counts compare their sizes. Plot the outcome rate per segment, such as conversion by signup method, or `normalize` a stacked bar. Put the n in `tooltip.measures`, so a bucket of 14 does not read as strongly as a bucket of 545. One chart plots one rate. Three unrelated rates on one line are three charts, or none.

**Leave out cohorts that have not settled.** A D7 rate for a cohort that signed up 3 days ago is not a rate yet, and it reads as a drop. Filter the base query to cohorts older than the rate's window, for example `date_diff(today(), signup_date, 'day') >= 7`.

**A monitoring ask wants deviation, not a leaderboard.** A user who asks for health, monitoring or anomalies wants to know what changed, not which entities are biggest. "Most active sites" is noise to them. Plot each value against a baseline: the same weekday last week, a share rather than a count, the change against the week before as a `diverging` `Heatmap`, new names against an `average` reference line.

**Lead with the answer.** The first chart answers the user's question. Order the sections by importance, each its reading and then the charts that explain it (see Layout in `dashboards.md`). Detail tables go last. A dashboard that opens on a breakdown makes the reader hunt.

**Prefer fewer charts.** Every chart must earn its grid rows. Two charts that show the same cut in different shapes are one chart and a decision you did not make.

## Drill down

Every chart drills down, and costs nothing to author. This works only if the base query stays per-row.

The reader clicks a series element on an axis, donut, funnel or map chart. On a `Number` card or a `Table` the reader double-clicks a numeric cell. Insights then finds the **last** `summarize` or `pivot_wider` in the chart's data query. It cuts the pipeline off just before that step, refilters by that row's dimension values, and opens the result in a dialog.

The chart's own aggregation is that `summarize`. So with a per-row base query, **one click lands on the source rows behind the number**: the invoices, the events, the documents. That is the payoff of rule 1 in `rules.md`, and the strongest reason not to pre-aggregate.

Three things to know:

- **A pre-aggregated base query costs a click.** The first drill-down lands on the base query's aggregated rows, not the source rows. The dialog's own table drills again to reach them. It works. It is one click of confusion you authored.
- **A pipeline that aggregates nowhere cannot drill down at all.** Insights cuts at the last `summarize` or `pivot_wider` in the chart's own pipeline. With none it answers "Nothing here aggregates any rows, so there is nothing behind it".
- **The clicked column must be numeric** on a `Number` card and a `Table`. A count measure typed as `String` renders and cannot be drilled. Type every measure.
