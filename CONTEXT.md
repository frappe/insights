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

**Template**:
A pre-built workbook shipped by any installed app via the `insights_workbook_templates`
hook; imported as one shared, Administrator-owned copy per site.

**Alert**:
A scheduled check on a query's results that notifies recipients (email or Telegram)
when its condition is met.
