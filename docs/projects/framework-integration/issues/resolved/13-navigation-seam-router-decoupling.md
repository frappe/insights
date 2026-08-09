# 13 — Navigation seam: decouple the viewer graph from the SPA router

Type: task
Status: resolved
Blocked by: none — can start immediately
Spec: [spec-insights-foundation.md](../../spec-insights-foundation.md), "Island entries and router decoupling"

## What to build

The chart and dashboard viewer graph stops importing the SPA router. A chart
or dashboard module pulled into an island entry must not drag the SPA route
graph with it — that coupling once produced a 2.3 MB chart island.

Navigation becomes one injected seam: a small navigation module with a
provider interface. The SPA provides its router. An island entry will later
provide an adapter that raises host callbacks or opens a new tab. Components
and stores in the viewer graph resolve navigation through injection, never
through a router import.

An app-local import-boundary lint enforces the seam: modules under the chart
and dashboard areas must not import the router module or SPA page modules.
The lint runs with the normal lint setup so CI and agents catch regressions.

This is a prefactor. SPA behavior does not change.

## Acceptance criteria

- [x] No module in the chart or dashboard viewer graph imports the SPA router
- [x] Navigation resolves through the injected seam, with the SPA router as
      the default provider
- [x] The lint fails when a viewer-graph module imports the router, and passes
      on the decoupled graph
- [x] Existing navigation still works in the SPA: open chart in workbook,
      navigate after duplicating a chart, dashboard navigation

## Comments

2026-08-05 — done. `frontend/src2/helpers/navigation.ts` holds the seam
(`setNavigationProvider`, `resolveHref`, `navigate`); the SPA registers its
router on it from `main.ts`. `frontend/.eslintrc.boundaries.json` bans
`**/router` imports and `vue-router`'s `useRouter`/`useRoute` under
`src2/charts/**`, `src2/dashboard/**` and `src2/query/**` (the SPA's
`DashboardList.vue` is the one excluded file), and `yarn lint` runs it.
Two follow-on refactors finished the decoupling: `9bf881b3` moved the item
stores' workbook-duplicate/title-mirror calls out of `chart.ts`/`query.ts`/
`dashboard.ts` into `workbook/workbook_items.ts`, and `0ce16c88` moved the
workbook injection key out of the workbook store so `DashboardChart.vue`
no longer pulls in the router transitively through it.
