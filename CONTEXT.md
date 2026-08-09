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

**Expression**:
An inline calculated column, measure, or filter written in the ibis-based expression
syntax.
_Avoid_: formula

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

### Framework integration

**Island**:
An app-provided, self-contained UI unit that the framework mounts into a host page
(desk or a Vue-frontend app) — shadow-root isolated, linked to the framework-provided
shared runtime. Declared via the `ui_islands` hook; Insights ships `insights.dashboard`
and `insights.chart`.
_Avoid_: widget, block, embed (embed = the public iframe-sharing feature)

**Chrome**:
Everything around a plot: the card, the title, the actions, the legend, the tooltip,
and the loading, error and empty states. frappe-ui charts v2 owns it for every
Insights chart without exception, so a chart on a desk page reads as one of the
family it sits beside. See ADR-0002.
_Avoid_: frame, shell, container

**Plot**:
The picture inside the chrome — the marks that carry the data. The only part that
varies by chart type, and it has three fillers: a charts v2 component, an Insights
plot built on v2's `useChart` (Map), or none at all (Table).
_Avoid_: graph, canvas, visual

**Adapter**:
The one module that turns a stored Chart config and a query result into the props of
a charts v2 component (`frontend/src2/charts/adapter/`). One pure function per chart
type. Insights builds no ECharts option for a type v2 admits.
_Avoid_: mapper, translator, transformer

**Standard workbook**:
The unit an app ships analytics in — a workbook, shipped as an
`insights/<folder>/` folder holding one JSON file per named item in typed
subfolders (`query/`, `chart/`, `dashboard/`), plus a `workbook.json`
(title, `required_apps`, `format_version`). The folder name is the workbook's
identity: `{app}/{folder}` is its Standard ID. Item names stay flat across an
app. References inside the folder are logical names, never docnames.
_Avoid_: bundle (the retired name), template (the retired import-a-copy channel),
package

**Standard content**:
What a shipped workbook becomes on a site: real documents (the workbook and its
items), flagged `is_standard`, each identified by a Standard ID — synced on
migrate, so shipped content exists everywhere and a reference to it never
dangles. Read-only outside developer mode; a standard workbook admits only
standard items — a site that wants it different duplicates.
_Avoid_: imported workbook, shipped copy

**Standard ID**:
The `{app}/{name}` identity of a shipped document, stored in `standard_id` on
the workbook and the three content doctypes. The only reference currency across
the app boundary; docnames are site-local hashes and never cross it. Only
standard content has one.
_Avoid_: logical id (the retired name), logical name (a bare `{name}`, as used
inside a shipped folder's files)

**Slug**:
A dashboard's readable URL handle (`sales-performance`), assigned once and only
ever used from outside. The resolver accepts it beside the Standard ID and the
docname; nothing internal references it.
_Avoid_: route, permalink

### Sharing & governance

**Visibility**:
A chart's or dashboard's declared audience — who may view it, on any surface.
A strict ladder: `Private | Specific Roles | Everyone | Public`, declared as
fields on the content. View-only; editing is governed separately.
_Avoid_: sharing (person-level DocShare is the `Private` rung, not a separate axis)

**Data Authority**:
Whose permissions filter a chart's rows at execution: `Viewer` (default — the
engine applies the viewer's role and user permissions) or `Author` (whole
numbers, audience-curated). Declared on the content, enforced by the engine.
_Avoid_: permission mode, run-as

**Team**:
A named group of users that grants access to resources (data sources, tables).

**Resource Permission**:
A grant tying a team to one specific resource.

**Alert**:
A scheduled check on a query's results that notifies recipients (email or Telegram)
when its condition is met.
