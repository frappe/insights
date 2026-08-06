# 31 — One dashboard renderer, one chart renderer

Type: grilling
Status: open
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
