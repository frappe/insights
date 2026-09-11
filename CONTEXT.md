# Insights

Frappe's BI/analytics app. Users connect data sources, build queries as operation
pipelines, and assemble charts into dashboards — all inside a Workbook.

## Language

### Analysis

**Workbook**:
The document where analysis happens — a named collection of queries, charts, and
dashboards, saved and shared as one unit.
_Avoid_: notebook, report

**Query**:
An ordered pipeline of Operations producing tabular, per-row results. Queries return
rows; aggregation for presentation belongs to Charts.
_Avoid_: dataset

**Operation**:
One step in a query pipeline — `source`, `join`, `union`, `filter_group`, `select`,
`mutate`, `summarize`, `order_by`, `limit`, `pivot_wider`, …. Stored as JSON on the
query, compiled to SQL through ibis.
_Avoid_: transform, step

**Chart**:
An aggregated visualization over a query, configured with dimensions and measures.
Charts aggregate; a mid-pipeline `summarize` in a query is a grain change, not
presentation.
_Avoid_: visual, graph

**Dashboard**:
A grid of charts, filters, and text blocks; each item carries a Layout.

**Dashboard filter**:
A dashboard-level control that routes filter conditions into the queries behind its
linked charts.

**Measure**:
A column or expression aggregated with an aggregation type (sum, count, …).
_Avoid_: metric

**Dimension**:
A column that results are grouped or split by, optionally with a date granularity.
_Avoid_: group-by column

**Grain**:
The size of the bucket a date or ordered column is grouped into — day, week, month, quarter, year. "Grain" is the prose word. The identifier stays `granularity`: the key on a Dimension, the doctype field, and the wire field a card receives. frappe-ui's own prop type is `TimeGrain`. Both words are correct in their own layer. The one exception is a Number chart's Period, whose key is `window.grain`, because it sits beside `span` and a `granularity` there would read as the Dimension's.
_Avoid_: renaming `granularity` in code, or writing "granularity" in prose

**Period**:
The stretch of the date column one Number card reads, and the unit its comparison steps back by. Stored as `window`, holding one of a `span` or a `grain` and never both. It is the only thing that groups a card by date: left out, the card is one number over the whole result and its date column only feeds the sparkline.
_Avoid_: slice, window (in prose — `window` is the stored key), timeframe

**Span**:
A Period the engine resolves against the clock, written as the string `get_window` parses — `month to date`, `current month`, `last 3 months (include current)`. It filters to the stretch it names and groups by which stretch a row fell in, so a comparison gets a real row of its own. A `grain` Period filters nothing and groups by the grain instead.
_Avoid_: timespan (Frappe's word for the same thing, kept only in the `within` operator's value)

**Expression**:
An inline calculated column, measure, or filter written in the ibis-based expression
syntax.
_Avoid_: formula

### Drill-down

**Drill**:
Reading what a number in a chart is made of. A drill cuts the chart's pipeline before its aggregation step and reads the surface underneath. The builder's chart preview, its dashboard grid and the query builder's result table offer the same drill.
_Avoid_: drill-through, explore

**Surface**:
Three senses, one per layer.

1. The rows under a chart's aggregation — the pipeline cut just before its
   summarize or pivot step (`chart_drill.py`). This surface is the exposure
   bound. A drill may name only its columns, so a drill never reaches past what
   the chart already published.
2. A screen a user works on: the public page, an authoring surface. Read
   surfaces and authoring surfaces get different answers from the server.
3. frappe-ui's `bg-surface-*` token, a background step in the design system.

Each layer means one of them, so say which when a sentence could take two.
_Avoid_: renaming any of the three

**Segment**:
The part of a chart a reader clicked — one bar, one slice, one point. It goes to the server as its dimension values, plain triples of column, operator and value, never as operations. One level of a drill stack carries one segment, and levels accumulate, so each level narrows the rows further.
_Avoid_: slice, data point, cell

**Breakdown**:
One of the two answers a drill level can ask for: group the segment by one more column of the surface. The other answer is rows — the rows behind the segment, and the word the wire, the code and the UI all use. A breakdown draws as an ad-hoc chart the answer picks for itself, and a click on it recurses.
_Avoid_: split, group-by (that is a Dimension); records, docs, entries for the rows answer

**Additive**:
Whether a level's group values add up to the value of the segment above them. True of a sum and a count, false of an average, a distinct count and an expression. The server says it on the answer, beside the order the rows run in, because a column of decimals does not say which aggregation made it. A breakdown reads it to decide whether it may draw itself as parts of one whole.
_Avoid_: summable, part-of-whole (that is what being additive licenses)

### Data

**Data Source**:
A configured connection to one database (Frappe site, MariaDB, Postgres, DuckDB, …).
_Avoid_: connection

**Table**:
A table exposed by a data source, selectable as a query's source.

**Table Link**:
A stored join relationship between two tables, used to suggest joins.

**Data Store**:
The site-local DuckDB warehouse holding imported copies of source tables so queries
run without hitting the source live.
_Avoid_: warehouse (implementation file name only)

**Table Import**:
The sync job that copies a source table into the Data Store.

**Unexplained Orphan**:
A Data Store table the weekly cleanup cannot show to be rebuildable. The cleanup
keeps it and raises an `Error Log`. See the cleanup ADR,
`docs/adr/the-cleanup-deletes-only-what-it-can-rebuild.md`.
_Avoid_: unknown table, stray table

### Framework integration

**Island**:
An app-provided, self-contained UI unit that the framework mounts into a host page
(desk or a Vue-frontend app) — shadow-root isolated, linked to the framework-provided
shared runtime. Declared via the `ui_islands` hook; Insights ships `insights.dashboard`
and `insights.chart`.
_Avoid_: widget, block, embed (embed = the public iframe-sharing feature)

**Chrome**:
Everything around a plot: the card, the title, the actions, the legend, the tooltip, and the loading, error and empty states. frappe-ui charts v2 owns it for every Insights chart. See ADR-0002.
_Avoid_: frame, shell, container

**Plot**:
The picture inside the chrome — the marks that carry the data. The only part that varies by chart type, and it has three fillers: a charts v2 component, an Insights plot built on v2's `useChart` (Map), or none at all (Table).
_Avoid_: graph, canvas, visual

**Adapter**:
The one module that turns a stored Chart config and a query result into the props of a charts v2 component (`frontend/src2/charts/adapter/`). One pure function per chart type. Insights builds no ECharts option for a type v2 admits.
_Avoid_: mapper, translator, transformer

### Sharing & governance

**Visibility**:
A chart's or dashboard's declared audience — who may view it, on any surface.
A strict ladder: `Private | Specific Roles | Everyone | Public`, declared as
fields on the content. View-only; editing is governed separately.
_Avoid_: sharing (person-level DocShare is the `Private` rung, not a separate axis)

**Permission User**:
Whose permissions filter the rows an execution returns, when the caller's own
cannot. A public link runs as Guest, a preview as Guest with a key, an alert as
Administrator — so each names a user, recorded on the content when it was
published or enabled. Empty means the viewer decides the rows.
_Avoid_: data authority, permission mode, run-as, impersonation

**Team**:
A named group of users that grants access to resources (data sources, tables).

**Resource Permission**:
A grant tying a team to one specific resource.

**Template**:
A pre-built workbook shipped by any installed app via the `insights_workbook_templates`
hook; imported as one shared, Administrator-owned copy per site.

**Alert**:
A scheduled check on a query's results that notifies recipients over a channel when its
condition is met.

**Channel**:
How an alert reaches its recipients: email, Telegram or a webhook. A webhook posts to a
URL the user supplies, which is why outbound requests carry an address policy — see
`docs/adr/outbound-http-to-user-chosen-urls.md`.
