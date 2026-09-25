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
telemetry event includes, and the word the picker uses. A query that names neither
`is_native_query` nor `is_script_query` is a builder query.
_Avoid_: visual, native, mode, editor type

**Operation**:
One step in a query pipeline — `source`, `join`, `union`, `filter_group`, `select`,
`mutate`, `summarize`, `order_by`, `limit`, `pivot_wider`, …. Stored as JSON on the
query, compiled to SQL through ibis.
_Avoid_: transform, step

**Chart**:
An aggregation over a query, configured with dimensions and measures and rendered by its chart type.
Charts aggregate; a mid-pipeline `summarize` in a query is a grain change, not
presentation.
_Avoid_: visual, graph

**Dashboard**:
A grid of charts, filters, and text blocks; each item has a Layout.

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
One measure a Number chart states, shown as a card of its own — its value, its format, its Period comparison and its target. `number_columns` names the readings and `number_column_options` keeps each one's own settings, positionally. A dashboard cell shows one reading and names it in `reading`, by its `id`, so renaming the measure keeps the cell. A Number chart on a dashboard is as many cells as it has readings.
_Avoid_: KPI, metric, data point ("card" is the thing shown, "reading" is what it states)

**Period**:
The stretch of the date column one Number card reads, and the unit its comparison steps back by. Stored as `window`, holding one of a `span` or a `grain` and never both. It is the only thing that groups a card by date: left out, the card is one number over the whole result and its date column is used only by the sparkline.
_Avoid_: slice, window (in prose — `window` is the stored key), timeframe

**Span**:
A Period the engine resolves against the clock, written as the string `get_window` parses — `month to date`, `current month`, `last 3 months (include current)`. It filters to the stretch it names and groups by which stretch a row fell in, so a comparison gets a real row of its own. A `grain` Period filters nothing and groups by the grain instead.
_Avoid_: timespan (Frappe's word for the same thing, kept only in the `within` operator's value)

**Expression**:
An inline calculated column, measure, or filter written in the ibis-based expression
syntax.
_Avoid_: formula

**Trusted code**:
Code in a query that only an Insights Admin (`is_admin`) can add or change, as for a Server Script. It is a script (a `code` operation), an expression that calls `.sql`, or a SQL query that calls a stored procedure. Each can read data the reader may not read. Trusted code that another user stored keeps running, and a non-admin can save it unchanged. A change to it by a non-admin is refused (`check_trusted_code_author`, `trusted_code_of`). See `docs/adr/code-in-a-query-follows-the-server-script-model.md`.
_Avoid_: script (for the three together), admin code, unsafe code

### Drill-down

**Drill**:
Reading what a number in a chart is made of. A drill cuts the chart's pipeline before its aggregation operation and reads the surface underneath. The builder's chart preview, its dashboard grid and the query builder's result table show the same drill.
_Avoid_: drill-through, explore

**Surface**:
Two senses.

1. The rows under a chart's aggregation — the pipeline cut just before its
   summarize or pivot operation (`chart_drill.py`). This surface is the exposure
   bound. A drill may name only its columns, so a drill never reaches past what
   the chart already published.
2. The page a View is read on. It is the `surface` argument of `insights.api.view.get_dashboard` and the `surface` of the `dashboard_viewed` telemetry event: `dashboards`, `shared` or `desk`, and `workbook` for the Builder (`VIEW_SURFACES`).

Say which sense when a sentence could take both.
_Avoid_: view, canvas, pane (for sense 2); surface for `ChartReadContext`, the object that holds a read's id and filters

**Segment**:
The part of a chart a reader clicked — one bar, one wedge, one point. It goes to the server as its dimension values, plain triples of column, operator and value, never as operations. One level of a drill stack holds one segment, and levels accumulate, so each level narrows the rows further.
_Avoid_: slice, data point, cell (a cell is the dashboard's grid unit, and a Table chart's)

**Breakdown**:
One of the two answers a drill level can ask for: group the segment by one more column of the surface. The other answer is rows — the rows behind the segment, and the word the wire, the code and the UI all use. A breakdown renders as an ad-hoc chart the answer picks for itself, and a click on it recurses.
_Avoid_: split, group-by (that is a Dimension), and records, docs, entries for the rows answer

**Additive**:
Whether a level's group values add up to the value of the segment above them. True of a sum and a count, false of an average, a distinct count and an expression. The server says it on the answer, beside the order the rows run in, because a column of decimals does not say which aggregation made it. A breakdown reads it to decide whether it may show itself as parts of one whole.
_Avoid_: summable, part-of-whole (that is what being additive licenses)

**Record Link**:
Which columns of a result name a desk document, and which doctype they name. A cell holds a document when its column came from a site-DB table and holds an id there — the table's own `name`, or one of its `Link` fields. Where a column came from is traced through the pipeline, never guessed from its name, and a trace that cannot be followed (an expression, a union, raw SQL, another data source) gets no link rather than one that lands on the wrong document. The server answers it on a drill's rows level and on a Table chart's result, and the value is the control: a linked cell opens the document's form, every other cell stays a value. The word "record" is kept for the identifier — `record_links` on the wire, `record_link.py`, `recordUrl` — and never used in prose or in the UI for the rows answer: the drill menu says View rows.
_Avoid_: record (in prose or in the UI), drill-to-detail, doc link

### Data

**Data Source**:
A configured connection to one database (Frappe site, MariaDB, Postgres, DuckDB, …).
_Avoid_: connection

**Table**:
A table exposed by a data source, selectable as a query's source.

**Table Name**:
The string that names a Table — `Insights Table v3.table`. Every referrer quotes it,
and the record's key derives from it. A postgres name includes a `<schema>.` prefix
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
A self-contained UI unit, provided by an app, that the framework mounts into a host page. It is isolated in a shadow root and uses the shared runtime the framework provides. Building an island registers it: its name is its entry in `frontend/build-islands.mjs`, and the build writes it into `assets.json` as `<name>.island.js`. Insights ships `insights.dashboard` and `insights.chart`. Island, Host, Claim and Action are the framework's words. `apps/frappe/ui/island/decisions` defines them and is their authority.
_Avoid_: widget, block, embed (embed = the public iframe-sharing feature)

**Host**:
The page an island mounts into. The host owns everything around the island: the page header, the title and the menu. Desk and a frappe-ui app are both hosts, and they use the same mount contract. An island never knows which host it is in.
_Avoid_: container, parent app, shell

**Claim**:
The link that makes Insights render a desk document. Insights adds one Custom Field to each desk doctype it renders (`Dashboard`, `Dashboard Chart`). When the field is set, an `onload` handler puts the island's name in `__onload.island`. Without that key, desk renders the document itself (`insights/desk.py`). A claim decides who renders the document, never who may read it.
_Avoid_: renderer, override, takeover

**Action**:
An entry that a page island asks its host to show in the page header. It is `{ label, icon? }` with either an `onClick` or an `href`. The island reports it in a plain event, together with the title. The host decides how to render it, and what a link that leaves the app does.
_Avoid_: button, menu item, command

**Chrome**:
Everything around a plot: the card, the title, the actions, the legend, the tooltip, and the loading, error and empty states. frappe-ui charts v2 owns it for every Insights chart. See `charts-render-through-frappe-ui`.
_Avoid_: frame, shell, container

**Plot**:
What renders inside the chrome — the marks that show the data. The only part that varies by chart type, and it has three fillers: a charts v2 component, an Insights plot built on v2's `useChart` (Map), or none at all (Table).
_Avoid_: graph, canvas, visual

**Adapter**:
The one module that turns a stored Chart config and a query result into the props of a charts v2 component (`frontend/src2/charts/adapter/`). One pure function per chart type. Insights builds no ECharts option for a type v2 supports.
_Avoid_: mapper, translator, transformer

### Reading and building

**View**:
The read side of a dashboard or a chart: what a reader gets. It is the same on the public page, in the desk island and on the app's own dashboard page. A View sends only the name of the content, and the server decides what runs. The operations, the SQL and the query behind a chart never reach the client. On the server, a View is `insights.api.view.*`, and every reference goes through `resolve_for_read`. On the client, it is `dashboard/view.ts`, `useChartView` in `charts/chart_view.ts`, `ViewDrillDown.vue` and `DashboardItemView.vue`. The View and the Builder both use the card, `ChartView.vue`, and its store, `ChartRead`.
_Avoid_: viewer (neither the reader, nor the module, nor the endpoints), read surface, feed (a card is filled from a source), one door

**Builder**:
The write side: the workbook's stores, forms and grid editing. It renders content that has no name yet. So it sends the content it is editing to `insights.api.authoring`, and gets back the derived operations and the SQL. That is why those endpoints need an Insights role and the View endpoints do not. On the client, it is `dashboard/builder.ts`, `charts/chart_preview.ts` and `BuilderDrillDown.vue`. To edit, a user needs write permission on the document and an Insights role. `can_write` in `insights/permissions.py` is the one place that checks both.
_Avoid_: authoring (as the name of a page, a store or a prop — `insights.api.authoring` keeps the word), seat (the gate is a role)

**Route**:
A dashboard's human-readable key, for its URL. It is made from the title only while it is empty, so a published link keeps working after the dashboard is renamed. `insights.resolver` accepts three references, in this order: the docname, the route and the v2 `old_name`. Charts have no route.
_Avoid_: slug, permalink

**Not Found**:
The one answer a View gives both for content that does not exist and for content the reader may not read. `resolve_for_read` raises `frappe.DoesNotExistError` with `Not Found` in both cases. No code above it checks read again or catches the error, because either would reveal which case it is.
_Avoid_: not available, unavailable, forbidden, a separate denied state

**Not Permitted**:
A chart the reader may open but whose data they may not read. It reads a site-DB table or permlevel column that neither their desk permissions nor a team grant allows. It does not run. Its card stays in place and names the doctypes the reader needs. The word is Frappe's, from the `PermissionError` a query raises for one unreadable table. The reader may already open the chart, so this message reveals nothing. **Not Found** is different: it hides whether the content exists. A dashboard on which every chart is Not Permitted answers Not Found, except to a user who may write it.
_Avoid_: denied, no access, hidden, no data (no data is a true zero)

**Held back**:
A permlevel column the reader may not read, which a build removes from the table's columns. The chart keeps running while nothing in it names the column. An operation, an expression or SQL that names the column makes the chart **Not Permitted**. A held-back column still counts toward the shape of the result, so a join names its output columns as it would for the author (`not_permitted.hold_back`, `held_back_columns`, `held_back_key`). A column the author removed or renamed is dropped (`dropped_by_writer`), not held back.
_Avoid_: lost, dropped (for permlevel)

### Sharing & governance

**Grant**:
Anything that gives a user access to a document. Each kind is one row of the table in `insights/permissions.py`: a DocShare, a workbook, a team or a Visibility level, among others. Nothing outside that table is a grant.

**Member**:
A workbook's query, chart, dashboard, alert or folder (`WORKBOOK_MEMBERS`). An alert belongs to its query's workbook (`workbook_of`). A member's write and share come from its workbook only: share on a member is checked as write, and owning a member grants nothing. A DocShare on a member may only give a named user read on a dashboard or chart (`is_member_share`).
_Avoid_: item (the permissions table says "items"), child (a child row is a row of a member's child table)

**Visibility**:
Who may read a chart or dashboard, on any screen. It is a field on the content itself, with four levels from narrowest to widest. `Private` adds no reader: only the document's other grants give read. They are its workbook, a DocShare to a named user, a team and, for a chart, a dashboard it is on. Owning the document grants nothing. `Roles` adds users with a role listed in `visible_to_roles`. `Everyone` adds every signed-in user; the word comes from Frappe's DocShare `everyone`. `Public` adds guests, so anyone on the internet. Visibility gives read only: no level gives write or share. Widening it is checked as a share (`validate_visibility`).
_Avoid_: rung, ladder, audience, `Specific Roles`, `is_public` (nothing reads it for a grant since `visibility` absorbed it)

**Run as owner**:
The Check on a chart that decides whose permissions filter its rows. When it is off (the default), rows are filtered by the user who reads the chart. When it is on, they are filtered by the chart's owner, so every reader sees the rows the owner sees. Then a reader who may not write the chart gets only what the owner saved: the chart and its dashboard filters. They get no breakdown, no rows and no file (`can_read_rows`). Only the owner or an admin may check it. Any user who may write the chart may clear it (`may_move_run_as_owner`). When the owner is disabled or may no longer write the chart, the chart runs as its reader. `Public` sets it on, because a guest has no permissions of their own, and a public chart that ran as its reader would show an empty page. A Public dashboard does not change it. Instead, saving a Public dashboard is refused while a chart on it runs as its reader, and the error names that chart (`check_dashboard_publishes`). The field is `run_as_owner`, set in `validate_run_as_owner`.
_Avoid_: Apply User Permissions (the field it replaced, with the opposite reading), data authority, authority, author (the answer is the `owner`), cascade, carry (a chart is linked to a dashboard)

**Permission User**:
The user whose permissions filter the rows an execution returns, when the caller's own permissions cannot be used. A public link arrives as Guest. A preview arrives as Guest, with a key that names the user it was made for. An alert runs under the scheduler as Administrator, so it runs as the user who enabled it, which the alert records. Content records no user: `permission_user_for` reads the stored **Run as owner** and `owner`, and returns a user. When Run as owner is not checked, the execution keeps the user it already runs as.
_Avoid_: data authority, permission mode, impersonation, viewer

**Team**:
A named group of users that grants access to resources (data sources, tables). On site data, a team grant adds to what desk permissions allow and never reduces it. On other data, it is the only access.

**Resource Permission**:
A grant tying a team to one specific resource.

**Is Standard**:
A workbook that a site got from an app, not from a person, together with its queries, charts and dashboards. The app ships it as one file under the app's module. Its `name` identifies it, as for Frappe's Report and Print Format. So a sync updates the document the site already has, and does not give it a new key. Outside developer mode it is read-only: `can_write` refuses even the owner. A user copies it instead (`can_copy`).
_Avoid_: standard id, or any second identifier beside the name

**Alert**:
A scheduled check on a query's results that notifies recipients over a channel when its
condition is met.

**Channel**:
How an alert reaches its recipients: email, Telegram or a webhook. A webhook posts to a
URL the user supplies, which is why outbound requests are checked against an address policy — see
`docs/adr/outbound-http-to-user-chosen-urls.md`.
