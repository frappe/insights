# Drill-down interaction

Type: grilling
Status: resolved

## Question

The drill ladder: chart segment → break down by another dimension (ad-hoc
chart) → underlying rows → open the desk record. Design it as one common
layer that serves both surfaces — Insights' own dashboard viewer and the
desk dashboard page — not a desk-only bolt-on.

- Interaction shape: everything-in-dialog was the v1 sketch from the
  [desk dashboard page UX](05-desk-dashboard-page-ux.md) ticket; validate or
  revise. Back-stack feel, dimension-picker scope (chart's declared
  dimensions first, searchable full list behind).
- Row → record mapping: how does a result row know which doctype/document
  it opens? Source-table queries map cleanly; joined/aggregated rows don't.
  This is a contract/engine question, not a UI one. Known constraint:
  chart → record does not work today.
- What the drill runs under: the chart's `data_authority`, rows only, never
  the query definition (per [desk data access](09-desk-data-access.md)).

Can run in parallel with foundation implementation. Use /grilling, then
/prototype the dialog with a mocked engine if feel is still in question.

## Answer

Ratified 2026-08-09 (grilling). The experience is redefined from scratch —
the existing `DrillDown.vue` dialog was never designed for viewers (it shows
the query definition, which [ticket 09](09-desk-data-access.md) forbids on
read surfaces) and it retires entirely.

**Scope: one experience on every surface.** The Insights dashboard viewer,
the desk island, and the chart builder preview all show the same drill. The
authoring surface adds exactly one extra affordance ("open as query", below)
instead of keeping a separate power-tool dialog. Two parallel drills were
rejected on the one-foundation rule.

**The uniform model.** Every segment click reduces to a set of *segment
filters* — the clicked dimension values. A bar is `month = 'Mar'`, a donut
slice is `status = 'Overdue'`, a pivot cell is row dims + the cell's column
value, a number card is the empty set. No per-chart special case.

**Entry: menu first.** A segment click opens a small menu with two items:

1. **View records** — the rows behind the segment.
2. **Break down by →** — a searchable submenu of candidate dimensions;
   picking one lands on the breakdown directly.

Rows-first (land on records, breakdown as a secondary action) was the close
runner-up. The menu won because it absorbs the dimension picker (breakdown
is two clicks from the chart), loads nothing until the user declares intent,
and its click distribution will tell us what the common path is — if rows
dominate, collapsing the menu later is cheap. Candidates are the
dimension-typed columns of the underlying query's *pre-summarize result
surface* (the exposure bound ticket 09 ratified — never the source tables),
minus the columns the clicked segment already pins. The chart's other
declared dimensions sort first, then the rest alphabetically. Date columns
are plain candidates in v1 — no per-grain submenu yet. "Open record" is
deliberately not in the menu: from a segment covering n rows, "the" record
is undefined.

**Container: one dialog, internal back-stack.** Going deeper (click a
segment inside the drill → menu again) pushes a level; back pops; the path
renders as a breadcrumb trail ("Overdue › by Region › West › Records") and
clicking a crumb pops to it. Stacked dialogs (today's recursion) and
navigation were rejected — the drill is an inspection, not a destination.
The stack is ephemeral: no URL, no persistence, close loses it.

**Breakdown level: the existing Row chart, ad-hoc.** The clicked measure by
the chosen dimension, sorted descending, value labels on, handed to the same
renderer the dashboard cards use. A hand-built bar list was rejected under
promote-what-exists: reuse costs zero components, segment-click recursion
rides the existing axis-chart click path, and if density ever hurts, the fix
is a denser Row chart — which improves every dashboard, not just the drill.

**Records level: the underlying query's result columns, all of them,** with
the accumulated segment filters applied, in the existing viewer data table —
sortable, formatted, no operations sidebar, no group-by chrome. No column
picking: the author's control over exposure is the query itself ("select
only what you would publish"). Row count honestly stated ("100 of 1,240");
real pagination deferred until someone hits the bound. No "break down by" on
this level — rows are the ladder's floor, and the breadcrumb already offers
the way back up. A per-row "open" control renders when the row can name its
desk record, and opens it in a new tab so the drill stack survives.

**Row → record mapping: server-derived by convention.** If the base source
table of the drill's effective operations is a site-DB doctype table and its
`name` column survives unrenamed into the drill result, the response carries
`record_link: {doctype, column}`. The client renders the control off that
metadata, dumbly — it never guesses a doctype from a column name. Misses
(renamed/dropped `name`, external sources, unions) degrade to no control,
never to a wrong record. Author-declared mapping is the recorded escape
hatch if real content misses the convention; full link-column provenance
through the pipeline is the eventual direction, not built.

**Who drills.** Logged-in viewers: drill follows the chart's visibility
gate — no extra grant. The record control renders regardless of the
viewer's doctype permission; desk enforces on landing. Guests on the
`Public` rung: no drill in v1 — public charts stay pictures. Extending
interactive row exploration to anonymous users is an additive decision to
make loudly later.

**Wire contract: one stateless endpoint, no operations on the wire.**

    viewer.get_drill_data(chart, dashboard?, filters?, drill_stack)

`drill_stack` is the descriptor: one entry per level — segment filters
(column, operator, literal) plus the level's action (`{breakdown: dim}` or
`{records: true}`). The server re-derives the chart's operations from
`config` (ticket 27's deriver), slices before the last summarize, validates
every referenced column against that surface (unknown column = hard error),
applies the stack, and answers with columns + rows (+ `record_link`). The
chart reference names the `data_authority` and the visibility gate, same
`frappe.has_permission` seam as ticket 09 — nothing on the wire can flip
either. Back = re-ask with a shorter stack; the client caches each level's
response for the dialog's lifetime, so back and crumb pops are instant. The
breakdown candidates piggyback on `get_chart_data` as a `drill.dimensions`
field (names + types) — a lazy context call would put a round trip between
click and menu, the exact place latency is felt most.

**Authoring extra: "open as query".** One button on the drill dialog that
loads the server-derived operations for the current level into an ephemeral
ad-hoc query (`makeAdhocQuery` path) — full builder from there, save only if
wanted, no residue on close. Renders on Insights surfaces only, gated on
edit rights on the chart (same check as "Edit in Insights"); not on the desk
island in v1. Consequence: `DrillDown.vue` retires everywhere, including the
query builder's result table — the builder's drill moves onto the same new
dialog, fed by an authoring endpoint variant that accepts inline
config/operations, the same split ticket 27 made for preview. One UI, two
feeds, one server-side derivation — the direction
[ticket 33](33-query-building-server-side.md) records.

**Prototype:** likely unnecessary — every level is a composition of parts
that already exist (menu, dialog, Row chart, data table). If the back-stack
feel is still in question at build time, mock the engine behind the
descriptor and try it.
