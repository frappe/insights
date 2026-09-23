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

**Query interface**:
The editor a query is written in — `builder`, `sql` or `script`. Those three are the
only names for them: the `interface` property a query answers with, the value the
telemetry event carries, and the word the picker uses. A query that names neither
`is_native_query` nor `is_script_query` is a builder query.
_Avoid_: visual, native, mode, editor type

**Operation**:
One step in a query pipeline — `source`, `join`, `union`, `filter_group`, `select`,
`mutate`, `summarize`, `order_by`, `limit`, `pivot_wider`, …. Stored as JSON on the
query, compiled to SQL through ibis.
_Avoid_: transform, step

**Chart**:
An aggregation over a query, drawn as one picture, configured with dimensions and measures.
Charts aggregate; a mid-pipeline `summarize` in a query is a grain change, not
presentation.
_Avoid_: visual, graph

**Dashboard**:
A grid of charts, filters, and text blocks; each item carries a Layout.

**Dashboard filter**:
A dashboard-level control that routes filter conditions into the queries behind its
linked charts.

**Filter picker**:
The one control that writes a filter, wherever a reader writes one — a dashboard filter, a card filter, a drill. It searches column, then operator, then value. The query's own filter operation is still the builder's control. The ADR names it as the host left to wire.
_Avoid_: palette (it is how the picker behaves, not what it is called. "palette" in Insights prose is a set of colors)

**Measure**:
A column or expression aggregated with an aggregation type (sum, count, …).
_Avoid_: metric

**Dimension**:
A column that results are grouped or split by, optionally at a Grain.
_Avoid_: group-by column

**Grain**:
The unit a date or ordered column is grouped by — day, week, month, quarter, year. "Grain" is the prose word. The identifier stays `granularity`: the key on a Dimension, the doctype field, and the wire field a card receives — do not rename it. frappe-ui's own prop type is `TimeGrain`. Both words are correct in their own layer. The one exception is a Number chart's Period, whose key is `window.grain`, because it sits beside `span` and a `granularity` there would read as the Dimension's.
_Avoid_: granularity (in prose — `granularity` is the stored key), bucket, resolution

**Reading**:
One measure a Number chart states, drawn as a card of its own — its value, its format, its Period comparison and its target. `number_columns` names the readings and `number_column_options` carries each one's own settings, positionally. A dashboard cell draws one reading and names it in `reading`, by its `id`, so renaming the measure keeps the cell. A Number chart on a dashboard is as many cells as it has readings.
_Avoid_: KPI, metric, data point ("card" is the thing drawn, "reading" is what it states)

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

**Trusted code**:
Code in a query that only an Insights Admin (`is_admin`) adds or changes, as a Server Script: a script (a `code` operation), an expression that calls `.sql`, and a SQL query that calls a stored procedure. Each reads past the reader's permissions. Trusted code someone else stored keeps running and saving; a change to it by anyone else is refused (`check_trusted_code_author`, `trusted_code_of`). See `docs/adr/code-in-a-query-follows-the-server-script-model.md`.
_Avoid_: script (for the three together), admin code, unsafe code

### Drill-down

**Drill**:
Reading what a number in a chart is made of. A drill cuts the chart's pipeline before its aggregation operation and reads the surface underneath. The builder's chart preview, its dashboard grid and the query builder's result table offer the same drill.
_Avoid_: drill-through, explore

**Surface**:
Three senses, one per layer.

1. The rows under a chart's aggregation — the pipeline cut just before its
   summarize or pivot operation (`chart_drill.py`). This surface is the exposure
   bound. A drill may name only its columns, so a drill never reaches past what
   the chart already published.
2. A screen a user works on: the public page, the desk island, the builder. A
   View and the Builder get different answers from the server.
3. frappe-ui's `bg-surface-*` token, a background step in the design system.

Each layer means one of them, so say which when a sentence could take two. None of the three is renamed.
_Avoid_: view, canvas, pane (for meaning 2)

**Segment**:
The part of a chart a reader clicked — one bar, one wedge, one point. It goes to the server as its dimension values, plain triples of column, operator and value, never as operations. One level of a drill stack carries one segment, and levels accumulate, so each level narrows the rows further.
_Avoid_: slice, data point, cell (a cell is the dashboard's grid unit, and a Table chart's)

**Breakdown**:
One of the two answers a drill level can ask for: group the segment by one more column of the surface. The other answer is rows — the rows behind the segment, and the word the wire, the code and the UI all use. A breakdown draws as an ad-hoc chart the answer picks for itself, and a click on it recurses.
_Avoid_: split, group-by (that is a Dimension), and records, docs, entries for the rows answer

**Additive**:
Whether a level's group values add up to the value of the segment above them. True of a sum and a count, false of an average, a distinct count and an expression. The server says it on the answer, beside the order the rows run in, because a column of decimals does not say which aggregation made it. A breakdown reads it to decide whether it may draw itself as parts of one whole.
_Avoid_: summable, part-of-whole (that is what being additive licenses)

**Record Link**:
Which columns of a result name a desk document, and which doctype they name. A cell holds a document when its column came from a site-DB table and holds an id there — the table's own `name`, or one of its `Link` fields. Where a column came from is traced through the pipeline, never guessed from its name, and a trace that cannot be followed (an expression, a union, raw SQL, another data source) draws no link rather than one that lands on the wrong document. The server answers it on a drill's rows level and on a Table chart's result, and the value is the control: a linked cell opens the document's form, every other cell stays a value. The word "record" is kept for the identifier — `record_links` on the wire, `record_link.py`, `recordUrl` — and never used in prose or in the UI for the rows answer: the drill menu says View rows.
_Avoid_: record (in prose or in the UI), drill-to-detail, doc link

### Data

**Data Source**:
A configured connection to one database (Frappe site, MariaDB, Postgres, DuckDB, …).
_Avoid_: connection

**Table**:
A table exposed by a data source, selectable as a query's source.

**Table Name**:
The string that names a Table — `Insights Table v3.table`. Every referrer quotes it,
and the record's key derives from it. A postgres name carries a `<schema>.` prefix
while the Data Source reads several schemas, so the name can change while the table
does not. A rename therefore has to move every referrer. See
`docs/adr/the-schema-is-a-coordinate-not-a-name.md`.
_Avoid_: table id, table key

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
An app-provided, self-contained UI unit that the framework mounts into a host page — shadow-root isolated, linked to the framework-provided shared runtime. An island is registered by being built: its name is its entry in `frontend/build-islands.mjs`, which the build writes into `assets.json` as `<name>.island.js`. Insights ships `insights.dashboard` and `insights.chart`. Island, Host, Claim and Action are the framework's words, defined in `apps/frappe/ui/island/decisions`, which is their authority.
_Avoid_: widget, block, embed (embed = the public iframe-sharing feature)

**Host**:
The page an island mounts into, and the owner of everything around it: the page header, the title, the menu. Two of them run the same mount contract — desk and a frappe-ui app — and an island never learns which one it is in.
_Avoid_: container, parent app, shell

**Claim**:
What makes a desk document ours to draw. Insights adds one Custom Field per desk doctype (`Dashboard`, `Dashboard Chart`) and an `onload` handler names the island in `__onload.island`; with the key absent, desk draws the document itself (`insights/desk.py`). A claim decides who draws, never who may read.
_Avoid_: renderer, override, takeover

**Action**:
What a page island reports for its host's header: `{ label, icon? }` plus either an `onClick` or an `href`. Reported as a plain event, beside the title. The host decides how it draws and what a link out of the app does.
_Avoid_: button, menu item, command

**Chrome**:
Everything around a plot: the card, the title, the actions, the legend, the tooltip, and the loading, error and empty states. frappe-ui charts v2 owns it for every Insights chart. See `charts-render-through-frappe-ui`.
_Avoid_: frame, shell, container

**Plot**:
The picture inside the chrome — the marks that carry the data. The only part that varies by chart type, and it has three fillers: a charts v2 component, an Insights plot built on v2's `useChart` (Map), or none at all (Table).
_Avoid_: graph, canvas, visual

**Adapter**:
The one module that turns a stored Chart config and a query result into the props of a charts v2 component (`frontend/src2/charts/adapter/`). One pure function per chart type. Insights builds no ECharts option for a type v2 admits.
_Avoid_: mapper, translator, transformer

### Reading and building

**View**:
The read half of a dashboard or a chart — what a reader gets, on the public page, in the desk island and on the app's own dashboard page alike. A view names content and the server decides what runs: operations, SQL and the query behind a chart never cross the boundary. `insights.api.view.*` on the server, every reference through `resolve_for_read`; `dashboard/view.ts`, `useChartView` in `charts/chart_view.ts`, `ViewDrillDown.vue` and `DashboardItemView.vue` on the client. The card, `ChartView.vue`, and the store under it, `ChartRead`, are drawn by both halves.
_Avoid_: viewer (neither the reader, nor the module, nor the endpoints), read surface, feed (a card is filled from a source), one door

**Builder**:
The write half — the workbook's stores, forms and grid editing. It draws content that has no name yet, so it sends the shape it is editing to `insights.api.authoring` and gets the derived operations and the SQL back, which is why those endpoints need an Insights role and a View's do not. `dashboard/builder.ts`, `charts/chart_preview.ts` and `BuilderDrillDown.vue` on the client. Editing is both questions at once, write on the document and a role, and `can_write` in `insights/permissions.py` is the one place they meet.
_Avoid_: authoring (as the name of a surface, a store or a prop — `insights.api.authoring` keeps the word), seat (the gate is a role)

**Route**:
A dashboard's cosmetic, human-readable key. Derived from the title only while it is empty, so renaming a dashboard leaves a published link working. One of the three references `insights.resolver` accepts, after the docname and before the v2 `old_name`. Charts have none.
_Avoid_: slug, permalink

**Not Found**:
The one answer a View gives for content that does not exist and for content the reader may not read. `resolve_for_read` throws `frappe.DoesNotExistError` with `Not Found` for both, and nothing above it re-checks the read or catches the error — either would give the answer away.
_Avoid_: not available, unavailable, forbidden, a separate denied state

**Not Permitted**:
A chart the reader may view but whose data they may not read: it reads a site-DB table or permlevel column that neither their desk permissions nor a team grant covers. It does not run, and its card stays in place naming the doctypes it needs. Frappe's word, from the `PermissionError` a query raises on one unreadable table. The reader was admitted, so saying so reveals nothing — unlike **Not Found**, which covers the content itself. A dashboard every chart of which is Not Permitted reads as Not Found, except to a caller who may write it.
_Avoid_: denied, no access, hidden, no data (no data is a true zero)

**Held back**:
A permlevel column the reader may not read, taken out of the table's projection by a build. The chart keeps running while nothing names it; an operation, an expression or SQL that names it makes the chart **Not Permitted**. A held-back column still counts for the shape of a result, so a join names its output as it would for the author (`not_permitted.hold_back`, `held_back_columns`, `held_back_key`). A column the author removed or renamed is dropped (`dropped_by_author`), not held back.
_Avoid_: lost, dropped (for permlevel)

### Sharing & governance

**Grant**:
A source that admits a user to a document, one row of the table in `insights/permissions.py`: a DocShare, a workbook, a team or a Visibility level, among others. A grant not in that table does not exist.

**Visibility**:
A chart's or dashboard's declared reach — who may view it, on any surface. Four levels on the content itself, narrowest first. `Private` adds nobody: the document is read through its other grants — its workbook, a named DocShare, a team and, for a chart, a dashboard it is placed on. Owning it grants nothing. `Roles` is the roles named in `visible_to_roles`. `Everyone` is every signed-in user, and takes its word from Frappe's DocShare `everyone`. `Public` is a guest, so the open internet. Read only: no level grants write or share, and widening one is checked as a share (`validate_visibility`).
_Avoid_: rung, ladder, audience, `Specific Roles`, `is_public` (nothing reads it for a grant since `visibility` absorbed it)

**Run as owner**:
The Check on a chart that says whose permissions the rows are filtered by. Off, the default, the execution filters by whoever is asking. On, it names the chart's owner, so every reader sees the rows the owner sees. A reader who may not write the chart gets only what the owner saved: the chart and its dashboard filters, never a breakdown, the rows or a file (`can_read_rows`). Only the owner or an admin may tick it, and any writer may clear it (`may_move_run_as_owner`). An owner who is disabled or may no longer write the chart names nobody, and the chart runs as its reader. `Public` forces it on — a guest has no permissions of their own, so a public chart that ran as its reader would draw an empty page. A Public dashboard never moves it: its save refuses a chart that runs as its reader, naming it (`check_dashboard_publishes`). Field `run_as_owner`, settled in `validate_run_as_owner`.
_Avoid_: Apply User Permissions (the field it replaced, with the opposite reading), data authority, authority, author (the answer is the `owner`), cascade, carry (a chart is linked to a dashboard)

**Permission User**:
Whose permissions filter the rows an execution returns, when the caller's own cannot. A public link arrives as Guest, a preview as Guest with a key that names the user it was minted for, and an alert as the scheduler's Administrator, so it runs as the user who enabled it, recorded on the alert. For content nothing is recorded: `permission_user_for` reads the stored **Run as owner** and `owner` and returns a user. Unticked, the execution keeps whoever it already runs as.
_Avoid_: data authority, permission mode, impersonation, viewer

**Team**:
A named group of users that grants access to resources (data sources, tables). On site data a grant adds to what desk permissions allow and never narrows them; elsewhere it is the only access there is.

**Resource Permission**:
A grant tying a team to one specific resource.

**Is Standard**:
A workbook a site got from an app rather than from a person, with its queries, charts and dashboards. It ships as one file under the app's module. Identified by its `name`, the shape Frappe's Report and Print Format use, so a sync updates the document a site already holds instead of re-keying it. Read-only on a site outside developer mode: `can_write` says no even to the owner, and `can_copy` is the affordance that replaces it.
_Avoid_: standard id, or any second identifier beside the name

**Alert**:
A scheduled check on a query's results that notifies recipients over a channel when its
condition is met.

**Channel**:
How an alert reaches its recipients: email, Telegram or a webhook. A webhook posts to a
URL the user supplies, which is why outbound requests carry an address policy — see
`docs/adr/outbound-http-to-user-chosen-urls.md`.
