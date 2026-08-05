# 17 — Dashboard island and viewer endpoints

Type: task
Status: ready-for-agent
Blocked by: 14, 15, 19
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Viewer data endpoints" and "Island presentation and the desk-page split"

## What to build

A desk user with no Insights role views a dashboard mounted on a desk page.

A small set of viewer endpoints serves island consumption: fetch a dashboard
(items, layout, capability flags), fetch a chart (config), fetch chart data
(results). Plain `frappe.whitelist()`, no role check. Each endpoint resolves
the reference through the resolver, checks read permission on the content doc
through `frappe.has_permission`, and executes under the doc's
`data_authority`. Capability flags (can edit, can duplicate) drive the
island's rights-gated affordances, so the client never guesses. The
endpoints never expose the query definition. Existing role-gated endpoints
stay as they are for the authoring app.

The `insights.dashboard` island entry renders the chart grid in the saved
layout — per-card async, skeleton per card, cards fill in as queries return,
never a blank page — plus a quiet title row. One failing card degrades in
place, the rest of the page lives. Full presentation polish is ticket 18.

The size budget is re-pinned from this first clean dashboard-island build
plus slack, replacing the preset default.

## Acceptance criteria

- [x] A user inside the audience, holding no Insights role, fetches dashboard
      and chart data through the viewer endpoints
- [x] A user outside the audience gets the denied answer, identical to a
      missing reference
- [x] A guest gets data only for `Public` content
- [x] Endpoints accept logical id, slug, and docname through the resolver
- [x] `ui_islands` declares `insights.dashboard`, and the island renders the
      grid on a desk page with per-card skeletons
- [x] The dashboard response carries capability flags
- [x] The size budget is re-pinned from the measured clean build

## Comments

2026-08-05 — the frontend half. `islands/viewer.ts` is the whole data path: it
calls the three endpoints and hands back a `Chart`-shaped object the existing
renderer accepts. The renderer expects the builder's aggregate — a store with a
document it can save and a query it can re-run — so the viewer's stand-in
answers the half it does not have inertly rather than leaving it undefined.
Anything that would re-shape the data is a no-op, because re-shaping is a query
and the server owns the query.

One card component, `islands/ViewerChart.vue`, serves both islands: it owns its
own request, its own skeleton and its own failure, so a card that cannot load
leaves the rest of the grid alone. `ChartIsland.vue` is now a wrapper around it,
which is what moved the chart island off the role-gated SPA path — both islands
work for a roleless viewer. `DashboardIsland.vue` draws the layout from one
`get_dashboard` call and lets every card fetch on its own, so the grid with its
skeletons is on screen before the first query returns.

Three cuts, because the entry graph was carrying weight no viewer uses:

- `EMPTY_RESULT` moved from `query/query` to `query/helpers`. It was the only
  value the island took from the query store, and taking it pulled the whole
  execution path — socket, queue, autosave — into the bundle. −46 kB JS.
- The alerts affordance left `QueryDataTable` for `query/components/QueryAlerts.vue`,
  which the four builder call sites now render into a `footer-actions` slot.
  Setting up an alert is authoring; its two dialogs are 42 kB of editor that
  every surface showing a result table used to carry. −42 kB JS.
- `VueGridLayout` imports `GridLayout`/`GridItem` itself instead of relying on
  the global registration in `main.ts`, which an island never runs.
  `grid-layout-plus` is in the runtime closure, so it costs nothing.

Chart config normalization is now `charts/helpers.normalizeChartConfig`, called
by both the chart store and the viewer client. An old chart drawn on a desk page
and the same chart in the builder must not disagree about what it looks like.

Measured, production build, JS + CSS raw (gzip):

| entry | before | after |
| --- | --- | --- |
| `insights_chart` | 177.2 + 25.2 kB (59.2 / 5.0) | 88.4 + 42.3 kB (31.3 / 6.8) |
| `insights_dashboard` | — | 91.1 + 43.2 kB (32.3 / 7.0) |

Budget re-pinned to **160 kB**, from the dashboard entry's 134.3 kB plus room
for ticket 18. The preset's 256 kB default is gone. `forbiddenImports` now names
the three item stores as well as the router and the workbook store; the check
runs after vite erases types, so `import type` from them still passes, which is
why the ESLint boundary rule stops at the router and the workbook store (the
base `no-restricted-imports` rule cannot tell a type import apart).

Bare imports audited against `assets.json`'s `.runtime.js` keys: every specifier
in both entries is runtime-registered. `dayjs/esm/plugin/quarterOfYear` is the
one duplicate, unchanged from ticket 14.

Verified on a desk page (`ai.insights.localhost`, dashboard `order-analysis`,
four charts): the grid renders in the saved layout, cards fill independently,
`update(props)` swaps the reference in place with no re-mount, a reference the
viewer cannot have gives the quiet page state, unmounting twice does not throw,
and the network trace shows `insights.api.viewer.*` and nothing else.

CSS grew because the island stylesheet now regenerates `prose`/`prose-v3` for
text items — 18 kB raw, 2 kB gzip — which the runtime sheet already carries.
The preset strips that safelist on purpose but has no way for an app to say
"this class is already downstairs". Worth a `blocklist` pass-through in
`@framework/ui/vite/island`.

### For ticket 18

- **Container queries do not work in an island.** The preset builds the island's
  Tailwind config from `frappe-ui/tailwind` alone and drops the app's own
  plugins, so `@tailwindcss/container-queries` never runs: `@container` computes
  to `container-type: normal` and `NumberChart`'s
  `@xl:grid-cols-3` collapses to one column, which overflows a short card. This
  is upstream in `@framework/ui/vite/island` (it needs to accept app Tailwind
  plugins) and it affects the chart island from ticket 14 too, not just this one.
- The title row is title text only. Freshness stamp, refresh and the
  rights-gated overflow menu are 18's.
- Filter items are dropped from the grid — the `filters` prop routes filter
  state to the server, but nothing draws it. The sticky filter bar is 18's, and
  it is its own surface, not a grid cell.
- Table sort is inert. `TableChart` hardcodes `enable-sort`, and the viewer has
  no way to re-order server-side, so a sort click does nothing and no indicator
  appears. Either the table takes a read-only mode or the endpoint learns to
  order.

### For ticket 22

`get_dashboard` already returns `can_edit` and `can_duplicate`, and
`get_chart` returns `can_edit`. `ViewerDashboard` and the chart response in
`islands/viewer.ts` carry them through typed; nothing renders them yet. The
duplicate affordance only appears on shipped content — `can_duplicate` is
`is_standard and check_app_permission()` — and `can_edit` is already false for
shipped content outside developer mode, so the two are mutually exclusive by
construction.
