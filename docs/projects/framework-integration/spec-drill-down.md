# Spec: drill-down — one inspection layer for every surface

Status: ready-for-agent

Sources: the resolved ticket
[11](issues/resolved/11-drill-down-interaction.md) (drill-down interaction),
standing on [09](issues/resolved/09-desk-data-access.md) (data access) and
[27](issues/resolved/27-chart-query-derivation-owner.md) (query derivation
owner). The larger direction is
[33](issues/33-query-building-server-side.md) (query building moves
server-side) — this spec is its second shipped slice.
Glossary: `CONTEXT.md` — viewer, island, visibility ladder, data authority.

## Problem Statement

A viewer looks at a chart and wants to know what is behind a number. Today
they cannot. On the desk island and the Insights dashboard viewer, a segment
click does nothing — drill-down exists only in the chart builder's preview.
The builder's drill dialog is also the wrong tool to extend: it shows the
query pipeline, which read surfaces must never expose, and it stacks dialogs
recursively, so three levels deep the viewer no longer knows where they are.

The viewer's real questions are: which records make up this number, which
slice of another dimension explains it, and how do I get to the record that
needs my attention.

## Solution

Clicking a chart segment opens a small menu with two choices: **View
records** and **Break down by** a dimension. Either choice opens one dialog.
Inside it, the viewer can keep going — click a bar in a breakdown, get the
menu again — and a breadcrumb trail shows the path ("Overdue › by Region ›
West › Records"). Back pops one level. From a records view, a row that maps
to a desk record carries an open control that lands on the record in a new
tab.

The same experience runs on every surface: the desk island, the Insights
dashboard viewer, and the chart builder preview. Authors additionally get
"open as query", which lifts the current drill level into an ad-hoc query
editor. The server computes everything; the client sends only plain values.

## User Stories

1. As a desk viewer, I want to click a chart segment and see a menu of what
   I can do, so that I choose my path before anything loads.
2. As a desk viewer, I want "View records" to show me the rows behind the
   segment I clicked, so that I can see what makes up the number.
3. As a desk viewer, I want "Break down by" to list the dimensions I can
   split the segment by, so that I can find which slice explains it.
4. As a desk viewer, I want the breakdown list to be searchable, so that a
   long dimension list does not slow me down.
5. As a desk viewer, I want the breakdown to render as a sorted Row chart
   with value labels, so that I can read the ranking at a glance.
6. As a desk viewer, I want to click a bar inside the breakdown and get the
   same menu again, so that I can keep narrowing.
7. As a desk viewer, I want a breadcrumb trail of my drill path, so that I
   always know where I am.
8. As a desk viewer, I want to click an earlier crumb or press back to pop
   levels, so that I can retrace without starting over.
9. As a desk viewer, I want back and crumb pops to be instant, so that
   retracing costs nothing.
10. As a desk viewer, I want a records row that maps to a desk record to
    carry an open control, so that I can jump to the document that needs
    attention.
11. As a desk viewer, I want the record to open in a new tab, so that my
    drill path survives the jump.
12. As a desk viewer, I want the records view to state its bound ("100 of
    1,240"), so that I know when I am not seeing everything.
13. As a desk viewer, I want the drill to respect the dashboard filters the
    card was showing, so that the rows agree with the number I clicked.
14. As a number-card viewer, I want the card click to offer the same menu,
    so that a KPI decomposes like any other chart.
15. As a viewer without any Insights role, I want the drill to work wherever
    I can see the chart, so that viewing and inspecting are one grant.
16. As a viewer, I want the drill bounded to what the chart's author chose
    to publish, so that a chart never leaks more than its query selects.
17. As a chart author, I want the drill to run under the data authority I
    declared, so that publishing a whole-number KPI stays a deliberate act.
18. As a chart author, I want row exposure controlled by my query's column
    selection, so that I have one lever, not a second curation surface.
19. As an author with edit rights, I want "open as query" on the drill
    dialog, so that I can continue an investigation in the full builder.
20. As an author, I want "open as query" to leave no residue unless I save,
    so that inspection never litters my workbook.
21. As a query builder user, I want clicking a summarized cell in the result
    table to open the same drill dialog, so that I learn one interaction.
22. As a site admin, I want guests on public charts to get no drill, so that
    anonymous users cannot explore rows interactively.
23. As a site admin, I want the drill endpoint to reject columns outside the
    chart's result surface, so that the wire cannot widen exposure.
24. As a pivot-table viewer, I want a cell click to pin both the row
    dimensions and the column value, so that the drill matches the cell.
25. As a viewer of a split-by chart, I want a segment click to pin both the
    axis value and the series value, so that the drill matches the segment.
26. As the product team, I want the menu's two items instrumented by their
    own click-through, so that usage tells us the common path.

## Implementation Decisions

All decisions below were ratified in ticket 11; this section restates them
as build instructions.

**The uniform model.** Every segment click reduces to a set of segment
filters — clicked dimension values as (column, operator, literal) triples. A
number card is the empty set. No per-chart special case anywhere in the
contract.

**Wire contract.** One new stateless endpoint in the viewer API module:
`get_drill_data(chart, dashboard?, filters?, drill_stack)`. The
`drill_stack` is a list of levels; each level carries its segment filters
and one action — a breakdown (dimension) or records. The server re-derives
the chart's operations from `config` (the ticket 27 deriver), slices the
pipeline before its last summarize or pivot, validates every referenced
column against that pre-summarize surface (an unknown column is a hard
error, never a guess), applies the accumulated filters, and answers with
columns and rows. Operations JSON crosses the wire in neither direction.
`chart` and `dashboard` are referenced and resolved exactly as
`get_chart_data` does today, which also fixes the permission gate and the
data authority. Dashboard filter state routes into the drill the same way
it routes into the card.

**Breakdown candidates.** The `get_chart_data` response grows a
`drill.dimensions` field: the dimension-typed columns (text, date) of the
pre-summarize result surface, names and types. The client subtracts the
columns the clicked segment pins and sorts the chart's other declared
dimensions first, the rest alphabetically. No separate context call — the
menu must open without a round trip. Date columns are plain candidates;
per-grain entries are a later refinement.

**Record link.** On records levels the response may carry
`record_link: {doctype, column}`, derived by convention: the base source
table of the effective pipeline is a site-DB doctype table and its `name`
column survives unrenamed into the drill result. Any miss (renamed or
dropped `name`, external source, union) means the field is absent and the
client shows no control. The client never guesses a doctype from a column
name. Author-declared mapping is the recorded escape hatch if real content
misses the convention; it is not built now.

**Guests.** No drill. The endpoint refuses Guest; the client draws no menu
for anonymous sessions. Public charts stay pictures.

**The dialog.** One dialog with an internal back-stack. The menu's choice
pushes the first level; drilling inside pushes further; back and breadcrumb
crumbs pop. The client caches each level's response for the dialog's
lifetime, so pops make no server calls. The stack is ephemeral — no URL, no
persistence. Breakdown levels render the existing Row chart (ad-hoc config:
clicked measure by chosen dimension, sorted descending, value labels);
segment clicks inside it ride the existing axis-chart click path. Records
levels render the existing viewer data table with all result columns — no
operations sidebar, no group-by chrome, no column picking, no "break down
by" (rows are the ladder's floor; the crumbs offer the way back up).

**Authoring.** The builder preview and the query builder's result table feed
the same dialog through an authoring endpoint variant that accepts inline
config or operations instead of a saved chart reference — the same split the
preview endpoint made in ticket 27. That variant may return derived
operations; "open as query" loads them into an ephemeral ad-hoc query with
the full builder, gated on edit rights, rendered on Insights surfaces only —
not on the desk island. The existing recursive drill dialog and the
client-side drill derivation (`makeDrillDownQuery` and its helpers) retire
completely; no client code slices operations after this lands.

**Order of work.**

1. Server drill layer behind the viewer endpoint: stack application, slice,
   validation, `record_link`, plus `drill.dimensions` on `get_chart_data`.
2. The dialog on the read surfaces (Insights viewer, desk island): menu,
   back-stack, Row-chart breakdown, records table, record open.
3. The authoring variant and "open as query"; the builder's surfaces move
   onto the new dialog.
4. Retire the old dialog and the client-side drill derivation.

## Testing Decisions

A good test at these seams calls the API as a persona and asserts on the
response — rows, columns, metadata, or the refusal — never on how the server
sliced or what intermediate operations it built. The drill logic has no test
surface of its own, the same way the ticket 27 deriver is tested only
through the endpoints that use it.

**Seam 1 — the viewer API surface** (carries nearly everything):

- records level: segment filters narrow the rows; all result columns return
- breakdown level: grouped rows for the chosen dimension, clicked measure
- multi-level stacks: filters accumulate across levels
- number card: empty segment filters drill the whole card
- pivot and split-by segments: row dims plus column value pin together
- unknown column in the stack: hard error
- `drill.dimensions` on `get_chart_data`: pre-summarize dimensions only
- `record_link`: present on the convention, absent on every miss, and only
  on records levels
- dashboard filters route into the drill as they route into the card
- personas: the role-free desk viewer drills what they can see; the outsider
  and Guest are refused; data authority governs the rows

**Seam 2 — the authoring API surface** (only what differs):

- inline config/operations in place of a saved reference
- edit-rights gating
- derived operations present in the response for "open as query"

Prior art: the existing viewer API and authoring API test modules — same
integration base, ToDo fixtures, and persona set (author, role-free desk
user, outsider, Guest). New tests join those modules.

No frontend seam: the repo has no frontend test runner. The dialog, menu,
back-stack, and Row-chart reuse ship on manual verification.

## Out of Scope

- Per-grain breakdown entries for date columns ("by week / by month")
- Real pagination on the records level (deferred until the bound hurts)
- Author-declared record mapping and link-column provenance through the
  pipeline (the eventual direction, not built)
- Guest drill on public charts
- "Open as query" on the desk island
- An aggregate-only drill mode (ticket 09 left it out to keep one rule)
- Densifying the Row chart (if the dialog read demands it, that work lands
  on the chart itself, for every surface)

## Further Notes

- The menu is deliberately an instrument: its click distribution tells us
  whether records or breakdown is the common path. If records dominate,
  collapsing the menu later is a cheap, additive change.
- Every ratified decision was checked against "does this paint the
  server-side move into a corner" (ticket 33); the descriptor contract
  advances that move — after step 4 no client code manipulates operations
  for drilling.
- A prototype was judged unnecessary: every level composes parts that
  already exist. If the back-stack feel is in question at build time, mock
  the engine behind the descriptor and try it.
