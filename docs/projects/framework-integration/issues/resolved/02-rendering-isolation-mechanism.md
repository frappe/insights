# Mount mechanism for desk

Type: prototype
Status: resolved
Blocked by: 01

## Question

How does Insights UI mount inside desk — which mechanism carries it without
style or runtime conflicts, and at which granularity?

Candidates:
- The vue-islands POC (frappe/frappe#39773, `mountVueIsland` shadow root).
  Known limits from the audit: per-island CSS duplication, light-mode only,
  portal contract needs unmerged frappe-ui patches.
- A full-page iframe (CSP `frame-ancestors` plumbing already exists in
  Insights).
- A vanilla bundle with no Vue or frappe-ui requirement, mounted by framework
  anywhere including single charts.

Decided by building: mount a real Insights dashboard in a desk page via the
candidates and compare.

## Answer

**One mechanism at every granularity.** Dashboards and single charts both mount
as Vue islands in a shadow root, via framework's `mountVueIsland`.

Rejected, with reasons:

- **iframe** — overlays cannot escape the frame. A drill-down dialog centres on
  the frame and can never cover desk chrome. Disqualifying for content whose
  interaction model is dialogs, popovers, and dropdowns; it remains viable only
  for read-only display.
- **vanilla / headless bundle** — chart *rendering* is already Vue-free
  (`src2/charts/helpers.ts` is ~1500 lines of pure `getXChartOptions(config,
  result)` functions with no Vue or frappe-ui imports, and frappe-ui's
  `ECharts.vue` already accepts custom echarts options). But drill-down is a
  dialog plus a data table plus a toolbar that groups and filters *inside* the
  drill result — `DrillDown.vue` composing `QueryDataTable`, `QueryToolbar`,
  `QueryOperations`. Reproducing that on desk primitives means a second UI
  implementation that drifts from the first. Rejected as a single foundation;
  a hybrid (vanilla charts + island dashboards) was rejected as two
  foundations.

**Prerequisite: Vue and frappe-ui must be framework-provided page singletons.**
The failure we hit while prototyping — a drill-down dialog teleporting outside
the shadow tree — came from two runtimes on one page, not from shadow DOM.
Islands from one shared runtime cost almost nothing per instance: each gets its
own Vue *app instance* (small) but shares the Vue *library*.

**Measured cost, and where it actually comes from.** A chart-only island built
with `vue`, `vue-router` and `echarts` externalised still produced **2.3 MB of
JS and 4.8 MB of CSS**. Neither is shadow DOM's doing:

1. `src2/charts/chart.ts` imports `../router`, so a single chart statically
   links the app's routing and store graph.
2. The stylesheet is the whole app's Tailwind + frappe-ui output, unscoped to
   the entry.
3. `mountVueIsland` injects a `<link>` into *each* shadow root — fetched once,
   but parsed and retained per root. At chart granularity this is the
   page-load risk, and `adoptedStyleSheets` (one constructed sheet shared
   across roots) is the fix.

All three are fixable and are prerequisites for chart granularity, not
objections to it.

### Findings for downstream tickets

- **Portal contract.** Overlays teleport to `<body>` unless a portal target is
  injected. The fix exists as two unmerged frappe-ui commits on the POC branch
  (`refactor: allow modifying portal target`, `fix: use portal target in
  popover and timepicker`); they rebase onto current frappe-ui (beta.29) with
  only mechanical conflicts, main having since standardised on a `portalTo`
  prop. Upstreaming them is small.
- **`mountVueIsland` has no app-config hook.** It creates the Vue app
  internally, so a page needing plugins or global components cannot configure
  it. Wants a `configureApp(app)` option.
- **The islands builder is frappe-only.** `build-islands.mjs` globs
  `frappe/public/js/islands/` exclusively, so another app cannot ship an island
  through it — but the runtime helper works fine when bundled by the consuming
  app's own build. Suggests framework ships the helper and a build preset, not
  the builder.
- **`frappe.assets.bundled_asset` passes absolute `/assets/...` paths through**,
  so any app's stylesheet can feed `styleBundles` without assets.json
  registration.
- **Two build bugs on the POC branch**, both fixed locally while prototyping:
  `autoprefixer` is required by `build-islands.mjs` but undeclared in frappe's
  `package.json` (it was only present transitively), and the `production`
  script's command ordering sends yarn's trailing arguments to the islands
  build instead of esbuild, so `bench build --app X` silently builds every app.

Prototype: branch `proto/desk-mount` (throwaway) — a desk page mounting a real
Insights dashboard as an island beside an iframe variant.
