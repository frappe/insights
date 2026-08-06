# 31 — One dashboard renderer, one chart renderer

Type: grilling
Status: resolved
Blocked by: none

## Question

The foundation branch added a second dashboard implementation instead of
promoting the first. Insights now renders a dashboard three ways and a chart
card two ways. Which implementation is the one every surface uses, and what do
the others become?

## Evidence

Dashboard rendering paths in `frontend/src2`:

1. **Builder/SPA** — `dashboard/Dashboard.vue` + `DashboardItem.vue` +
   `DashboardChart.vue`, on the workbook chart store (`charts/chart.ts`). The
   client derives each chart's data query (ticket 27's finding), sort re-runs
   the query, edit affordances everywhere.
2. **Shared/public page** — `SharedDashboard.vue`, riding the builder
   components with edit turned off.
3. **Desk island viewer** — `islands/DashboardIsland.vue` + `ViewerChart.vue`
   + `viewer.ts`, on the role-free viewer endpoints. Server-owned data, per-card
   states, filter routing by `charts` on the item.

Chart-card paths: `DashboardChart.vue` → `ChartRenderer.vue` (store-coupled)
vs `ViewerChart.vue` → `ChartBody.vue` readonly (viewer endpoint). The shared
floor is already real — `ChartBody`, `FilterControl` (unified in ticket 18),
`VueGridLayout` — but the data layer above it is duplicated: `charts/chart.ts`
and `islands/viewer.ts` are two fetch-and-state stacks for the same content.

Out of this ticket's scope, already tracked elsewhere: the legacy desk widget
dashboard (fog item "Legacy desk `Dashboard` / `Dashboard Chart` content") and
frappe-ui charts v2 as the per-card rendering primitive (Out of scope).

## Shape of the answer

The leaning, from the design rules (one foundation; promote what exists): the
**viewer is the foundation**. Viewing is the common case on every surface —
desk, shared/public, and the builder's own preview are all "render this saved
dashboard". So:

- The shared/public page renders the viewer components, not the builder's.
- The builder becomes the viewer plus an editing layer, not a sibling
  implementation.
- One data layer serves reads everywhere. Whether that is `viewer.ts`'s
  endpoint stack depends on ticket 27 — if the server owns query derivation,
  the viewer endpoints are the natural read path and the workbook store keeps
  only authoring state.

The answer must name the migration order and what dies: `SharedDashboard.vue`'s
builder coupling first (lowest risk), the builder's read path last. Blocked by
nothing, but resolve ticket 27 first or together — the data-layer half of this
question is mostly that ticket.

## Answer

Ratified 2026-08-06 (grilling, together with ticket 27 — resolved first, and
its answer forces this one's data layer).

A counting correction first: there are **four** surfaces, not three. The
builder (`DashboardBuilder.vue`), the SPA read page (`dashboard/Dashboard.vue`,
grid disabled), the public page (`SharedDashboard.vue`), and the desk island.
The middle two already ride the builder stack with edit off.

**The viewer is the foundation.** The alternative — promote the builder stack
— is disqualified by ticket 27 alone: that stack's core is client derivation,
which is scheduled to die. Concretely:

- `useViewerChart` (`islands/viewer.ts`) generalizes into **the** chart-read
  store, with two feeds behind one interface: a saved chart name (viewer
  endpoints — desk, shared, SPA read page) or inline unsaved config (ticket
  27's preview endpoint — builder only). Both return rows plus derived
  operations, so the store is identical above the fetch.
- The `Chart`-aggregate adapter at the bottom of `viewer.ts` — the object
  stubbing `addOrderBy: () => {}` and friends — dies. The renderer family
  (`ChartBody` down) takes the read store natively; it survives as the one
  set of card components.
- `charts/chart.ts` shrinks to authoring state: the document, config editing,
  save. Its derivation-and-result half goes with ticket 27 step 3.
- The inversion: today the viewer fakes being a builder; after, the builder
  is a viewer that can also write.

**One surface, shims for entry points.** One `DashboardView` component, living
in `dashboard/` as that folder's core, owns everything inside the page: grid,
cards, filter bar, and the chrome actions (refresh, PNG export, Edit /
Open Workbook, Duplicate). Chrome is gated by what `get_dashboard` grants
(`can_edit`, `can_duplicate`, `workbook`, the ladder rung) — a property of
the surface, never of the host. A capability the server didn't grant doesn't
render; same rule on every surface. The entry points shrink to mount shims
(~20 lines), allowed to carry only navigation context:

- **Island shim** (`islands/`) — desk mount lifecycle, host ambient (ticket
  29's contract).
- **SPA route shim** — breadcrumbs and `document.title`; only the SPA has a
  route hierarchy.
- **Public route shim** — reference resolution from the URL, nothing else.

The test for any future line: if it renders inside the page box, it goes in
`DashboardView` behind a capability; only navigation context may live in a
shim.

**No permission work needed.** `insights.api.viewer` is already
`allow_guest=True` end to end — access is the visibility ladder, and a guest
reaches the Public rung through the same code path as everyone else. The one
loose end: the preview-image key (`X-Insights-Preview-Key`) lives in
`shared.py`'s ladder and moves into the permission controller with step 1.

**Migration order**, each step leaving the app whole:

1. **Shared/public page → viewer surface.** Dies: the public page's builder
   coupling, then `api/shared`'s dashboard read path once nothing calls it.
2. **SPA read page → the same surface**, keeping its chrome via capabilities.
   Dies: its `useDashboard` read path.
3. **Builder → the shared store**, riding ticket 27 step 3. Dies: `chart.ts`'s
   derivation half, the `Chart` adapter in `viewer.ts`, and
   `DashboardChart.vue`/`ChartRenderer.vue`'s store coupling.

Steps 1–2 do not wait on ticket 27; only step 3 does. Out of scope, tracked
elsewhere: drill-down on read surfaces (ticket 11), frappe-ui charts v2 as the
card primitive.
