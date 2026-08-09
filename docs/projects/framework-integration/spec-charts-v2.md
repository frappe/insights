# Spec: charts v2 — Insights configures charts, frappe-ui draws them

Status: ready-for-agent
Target: `feat/charts-v2`, branched from `develop`. Two work streams — a
frappe-ui stream that lands first into branch `charts-v2`, then the Insights
render swap.

Sources: the resolved ticket
[32](issues/resolved/32-charts-v2-adoption.md) (charts v2 adoption), amended
[ADR-0001](../../adr/0001-type-independent-chart-config.md), and frappe-ui's
`spec/charts-scope.md`, which is the authority on what enters v2.
Glossary: `CONTEXT.md` — Chart, Dimension, Measure, Operation, Query, island,
viewer.

## Problem Statement

Insights draws its own charts. `helpers.ts` builds an ECharts option per chart
type, and `BaseChart.vue` mounts it. That is 1565 lines of rendering nobody
asked Insights to own.

frappe-ui now ships charts v2, the standard chart family for every Frappe app.
So the same picture has two implementations, and the Insights one is behind.
v2 has a heatmap, loading and error and empty states, theme-reactive palettes,
HTML tooltips with slots, typed events, and axis labels that measure themselves
and fit. Insights has none of these. Its dark mode stopped at charts for exactly
this reason: theming an ECharts option by hand was work no one had done.

The gap is about to become visible. An Insights chart mounted as an island sits
on a desk page beside charts the framework drew, and it does not match them —
different tooltip, different legend, different empty state, different type
scale. The framework-integration effort decided the framework contributes the
rendering primitives and Insights stays the reporting layer. Today Insights
contradicts that decision in 1565 lines.

Underneath, the config makes it worse. Each chart type names its own slots —
`x_axis.dimension`, `label_column`, `location_column`, eight names for two
ideas — so each type needs its own translation into any renderer.

And none of it is tested. The Insights frontend has no test runner. The one
Playwright suite it ever had was deleted with the v2 code.

## Solution

Insights stops drawing charts and starts configuring them.

The ownership seam cuts at the **layer**, not at the chart type. v2 owns the
**chrome** — the card, the title and subtitle, the actions, the legend, the
tooltip, and the loading, error and empty states — for every Insights chart
without exception. Only the **plot** inside the chrome varies, and it has
exactly three fillers:

1. a v2 chart component, for every type v2 admits,
2. an Insights plot built on v2's `useChart`, for Map,
3. no plot at all, for Table.

Between the stored Chart config and a v2 component sits one new module: the
**adapter**. It reads the config and the query result and returns v2 props.
Insights builds no ECharts option for a type v2 admits, and draws no chrome for
a type it owns.

A per-type seam was rejected. It reads as pragmatic and it is a hybrid: every
new chart type becomes a coin flip, and an app-owned plot that hand-rolls its
own card stops matching a v2 chart on the same Dashboard. That mismatch is the
pressure that pushes app features back into the library.

Table and Map are not staging cases waiting for v2 to catch up. frappe-ui's
scope rule excludes them on the model: a table maps no value to a visual
property, so it is not a plot; a choropleth needs a geography layer — GeoJSON,
region-name resolution, and a classification step — which is data cleaning, not
rendering. If v2 ever owns that layer, Map changes from filler 2 to filler 1 and
nothing else in Insights moves.

## User Stories

1. As a chart author, I want every chart type to render through the standard
   Frappe chart family, so that my charts look like the rest of the product.
2. As a chart author, I want a chart to show a loading state while its Query
   runs, so that I can tell a slow chart from a broken one.
3. As a chart author, I want a chart that failed to show an error state in the
   card, so that I do not have to open the console to learn it failed.
4. As a chart author, I want a chart with no rows to say so, so that I do not
   read an empty plot as a zero.
5. As a chart author, I want axis labels to stay legible without me setting a
   rotation angle, so that I stop tuning a chart to fit its own text.
6. As a chart author, I want to plot a Measure against a numeric column on the
   x-axis, so that I can read one quantity against another.
7. As a chart author, I want a combo chart where one series draws as a line over
   bars, so that I can show a rate against a volume.
8. As a chart author, I want a series in a different unit measured against a
   second axis, so that both are readable in one plot.
9. As a chart author, I want reference lines for targets and thresholds, so that
   a reader sees the number the data is judged against.
10. As a chart author, I want to split a Measure by a Dimension and get one
    series per value, so that I can compare groups over time.
11. As a chart author, I want a split with many values to collapse its tail into
    one series, so that the chart stays readable.
12. As a chart author, I want stacked and 100% stacked bars, so that I can read
    totals or shares from the same chart.
13. As a chart author, I want to hide a series from the plot without removing it
    from the Chart, so that I can focus a reader without editing the config.
14. As a chart author, I want a Number chart with several values laid out
    together, so that a KPI block reads as one card.
15. As a chart author, I want a Number chart to show its change against a
    comparison period, so that a reader sees direction, not just magnitude.
16. As a chart author, I want a funnel built either from one row per stage or
    from several Measures on one row, so that both shapes I already have keep
    working.
17. As a chart author, I want the Map chart to keep its region mapping and its
    natural-breaks buckets, so that the geography work I did is not lost.
18. As a chart author, I want the Table chart to keep its pivot, totals, and
    conditional formatting, so that nothing I built stops working.
19. As a chart author, I want Table and Map cards to look like every other card
    on the Dashboard, so that a grid reads as one thing.
20. As a chart author, I want to keep drilling into the rows behind a segment,
    so that the swap costs me no capability.
21. As a chart author, I want to expand a chart to full size, so that I can read
    a dense plot.
22. As a chart author, I want my existing Charts to render unchanged after the
    swap, so that I do not have to rebuild anything.
23. As a dashboard viewer, I want charts to follow the color scheme, so that
    dark mode is not half-applied.
24. As a dashboard viewer, I want a chart's tooltip to be readable and
    selectable text, so that I can copy a value out of it.
25. As a dashboard viewer on a desk page, I want an Insights chart to match the
    charts the framework drew beside it, so that the page reads as one product.
26. As an app developer shipping standard content, I want a shipped Chart to
    render the same in Insights and in my app, so that I ship one thing.
27. As an Insights developer, I want one place that turns a Chart config into
    chart props, so that I fix a mapping bug once.
28. As an Insights developer, I want that mapping covered by tests, so that the
    config split can rewrite it safely.
29. As an Insights developer, I want the tests written against chart props and
    not against the stored config shape, so that they survive the config split.
30. As an Insights developer, I want no ECharts option-building left for any
    type v2 admits, so that a v2 improvement reaches Insights without an
    Insights change.
31. As an Insights developer, I want an escape hatch when v2's defaults are
    wrong for one chart, so that a single case does not justify a second
    renderer.
32. As a frappe-ui maintainer, I want the numeric x-axis argued against the
    scope rule, so that v2 grows by its model and not by demand.
33. As a frappe-ui maintainer, I want Insights to consume v2 as published, so
    that a local link is not load-bearing for a release.

## Implementation Decisions

### The seam

`ChartBody` stays the one card and the one state machine, as ticket 31 settled.
Its internals invert. Today it switches on chart type, calls the matching
`get*ChartOptions` builder, and hands an option to `BaseChart`. After the swap
it renders v2 chrome and puts one of the three fillers inside it. The states it
hand-rolls today — loading, error, empty — are v2's, not its own.

`ChartRenderer` keeps its job: the affordances around the card, which are expand
and drill-down. Drill-down binds to v2's typed datapoint events instead of the
ECharts events `BaseChart` forwards today.

`BaseChart.vue` is deleted. `helpers.ts` loses every `get*ChartOptions` function
for a v2-admitted type, and keeps only the Map plot's geography work.

### The adapter

One module. One function per chart type. Each takes the Chart config and the
query result, and returns the props of one v2 component. It is pure: no Vue, no
network, no ECharts.

One function per type rather than one general mapper, because the config is
per-type today and will not be after the config split. Keeping the shape flat
means the split rewrites function bodies and not structure.

The adapter reads **two** inputs, not one. With a split, the `y` column list is
the set of pivoted result columns, which config alone cannot supply. This is the
one place the mapper is not close to an identity function, and it is the reason
the adapter takes the result and not just the config.

### Wide data, and the pivot stays

A Chart with a `split_by` Dimension keeps its server-side `pivot_wider`
Operation. The adapter maps the pivoted columns onto a list-valued `y`, one
series per column, which is the wide shape v2's axis charts read.

Long data was the more attractive shape and is rejected on a hard constraint:
v2's `series` grouping takes a single `y`, and Insights allows a split together
with several Measures. Only wide expresses that.

The cap argument is neutral and should not be re-litigated. Ranking the split
values, rewriting the tail to `Others`, and pivoting are three independent steps
on the server; the cap is not a feature of the pivot. Both shapes carry the same
cells, so wide is only a more compact encoding of them. Bounding the series
count in SQL keeps the result small before it crosses the wire, which is a
reason to keep the server-side cap in either shape.

No engine change. `chart_query.py` is untouched by this spec.

### What Insights reshapes

frappe-ui's scope rule pushes five things back to the caller under its
convention that v2 draws data and does not model a domain. These are Insights
work items in this spec, not open questions:

- **Comparison delta.** Insights derives the delta from the date column and
  passes a number. v2 takes a computed delta.
- **Funnel Measures mode.** Insights reads one row with several Measures and
  reshapes it to one row per stage. v2 takes a label column and a value column.
- **Number chart with several values.** Insights lays out its own grid and puts
  one v2 `NumberCard` behind each value, with the card surface turned off so a
  bordered box does not nest inside a bordered box.
- **`hide_from_chart`.** Maps onto v2's `hiddenSeries` model. Insights does not
  keep a second spelling.
- **`overlap`.** A renderer instruction, so it goes through the per-series
  `echartOptions` merge.

Two config options disappear because v2 solves them as library behaviour:
`label_rotation` and the funnel's square-root stage scaling. Both leave the
Insights config and the config forms.

### What is dropped

`show_scrollbar` is dropped. It is the scope spec's one undecided item, and
holding a second renderer open for it costs more than the feature is worth.
Charts that set it lose the slider. Revisit it in frappe-ui on its own merits.

### The frappe-ui stream

One change, landing into branch `charts-v2` before the Insights swap depends on
it: the axis charts gain a numeric x-axis, as `xAxis.type: 'value'` beside
`'category'` and `'time'`.

Argue it in `spec/charts-scope.md` under the existing rule, not as an exception
to it. It follows from convention 1 — reading a Measure against a quantity is a
statement about the data, not an instruction to the renderer — and it is the one
item on the Insights gap list the scope document never ruled on.

### The escape hatch has one owner

v2's `echartOptions`, deep-merged at chart, axis and series level, is the only
escape hatch. Insights does not keep a parallel option builder for a case v2
draws badly. This is what makes total adoption reachable rather than
aspirational: "v2 cannot do X" is almost always false, so it stops being a
reason to keep a second renderer alive.

Reach for the hatch sparingly. A default that is wrong for every app is a
frappe-ui change, and `charts-v2` is open.

### Theming closes for free

v2 exposes `currentColorScheme`, `useChartTheme` and theme-reactive palettes
that read `--chart-*` from CSS. Insights charts follow the color scheme with no
Insights theming code. This finishes the charts half of dark mode, which was
parked precisely because hand-theming an ECharts option was unclaimed work.

### The dependency

For the duration of this work, Insights consumes frappe-ui through the local
link, so that charts-v2 can keep being polished alongside the swap. The branch's
`frontend/package.json` declares the link rather than sitting on a published
version while building against source.

Flipping the link to the published version is a **merge condition**, not a task
inside the swap. `develop` consumes the published package, and this branch must
match it before it merges.

Individual commits on this branch need not be in a working state.

### Order of work

1. **frappe-ui:** numeric x-axis into `charts-v2`, argued in the scope spec,
   with its own unit and component tests.
2. **Insights:** stand up vitest, and the adapter with the axis family — Bar,
   Line, Row. This carries almost every unknown: combo, dual axis, stacked,
   reference lines, split, the numeric axis, and real visual parity.
3. **Insights:** the remaining v2-admitted types — Number, Donut, Funnel,
   Bubble, Sankey — including the three reshapes.
4. **Insights:** Table and Map into v2 chrome. Map's plot moves onto `useChart`,
   keeping its geography work; Table gets the chrome and no plot.
5. **Insights:** delete `BaseChart.vue` and every dead `get*ChartOptions`.
   Remove `label_rotation`, funnel scaling and `show_scrollbar` from the config
   forms.

The config split from ADR-0001 follows this spec and is not in it. That reverses
the ADR's own sequencing, deliberately: the config shape is settled and
domain-derived, while every unknown sits in the swap.

## Testing Decisions

A good test here asserts what a caller can observe and nothing else. For the
adapter that means the props it returns, never how it computed them. No test
should name an internal helper, and no test should assert on an ECharts option —
that is v2's business, and v2 tests it.

**One new seam in the whole effort: the adapter, under vitest.** It is a pure
function, so the test needs no DOM, no server, and no chart. Everything else
rides a seam that already exists.

The suite must survive the config split, which will change the adapter's input
shape. So:

- **Assert on props.** The output is the stable end and the half worth pinning.
  When a v2 prop changes during charts-v2 polishing, these tests name the
  Insights charts that moved.
- **Never write a config literal.** The config goes in through a fixture builder
  that expresses intent — an axis Chart over a date Dimension, measuring
  revenue, split by region — and turns it into whatever the stored shape
  currently is.

The config split then rewrites one function, the builder, and every assertion
survives. That is also a real check on ADR-0001's central claim: if the split is
lossless, the suite passes with only the builder changed. A test that cannot be
expressed in the new shape means the split lost something, and CI says so before
a user's Dashboard does.

What the adapter suite covers: one case per chart type; the split mapping onto a
list-valued `y` read from result columns; combo series; the second axis;
reference lines; the tail series; and each of the three reshapes — comparison
delta, funnel Measures mode, and the Number grid.

Prior art: frappe-ui's own chart tests are the model, one vitest file per option
builder — `barChartOptions.test.ts`, `comboChartOptions.test.ts`,
`referenceLines.test.ts`. Same runner, same grain.

The frappe-ui stream uses frappe-ui's existing seams and adds no new one: a
vitest file beside the axis option builders for the numeric axis, and one
Cypress component test that points land by value and not by index.

Server behaviour is unchanged, so `test_chart_derivation.py` should pass
untouched. If it does not, the swap has reached the engine and something in this
spec is wrong.

Nothing asserts that a chart *looks* right. That is the browser review at
`http://ai.insights.localhost:8081/insights`, comparing against the current
renderer, and it is a required step of each stage in Order of work, not an
optional one.

## Out of Scope

- **The chart config split.** ADR-0001's `dimensions` / `measures` / `display`
  shape, `resetConfig`, and the persisted-config normalizer. Its own spec, after
  this one.
- **Moving Map into frappe-ui.** It requires v2 to own a geography layer, which
  the scope rule says it does not. The seam makes this a filler swap whenever
  that changes.
- **A frappe-ui DataTable.** The scope rule says if the library ever ships
  Table, it ships as a DataTable, not a chart. Not this spec.
- **`show_scrollbar` in v2.** Dropped here; a frappe-ui decision on its own
  merits later.
- **Playwright.** Deferred with a condition attached — see Further Notes.
- **The split ranking bug.** Top-N split values are ranked alphabetically rather
  than by Measure, so `Others` can swallow the largest series. Present equally
  before and after this swap. Its own ticket.
- **The engine.** No Operation, no derivation, no query change.
- **Island and Dashboard work.** The island renders through `ChartBody`, so it
  inherits the swap and needs no change of its own.

## Further Notes

**Playwright, and when it earns its place.** Playwright is more durable than the
adapter suite — it is agnostic to the config shape and to v2's props, so it
survives both the config split and charts-v2 polishing. It loses here on cost
and timing, not on merit. It needs a seeded site, auth, a Workbook and shaped
data before its first assertion, and the repo's only Playwright suite was
deleted with the v2 code. Most of all, a human is reviewing every chart in the
browser during this swap, which catches "this looks wrong" as well as "this did
not render". That stops being true when the swap ends. Then a thin smoke spec
earns its place — one Dashboard, one card per chart type, asserting each drew a
plot and a legend. Not a matrix, and written against the finished renderer.

**ADR-0001 is amended, not superseded.** Its config decision stands. Its
"Blocked on" section was replaced on 2026-08-09 because the gap list it named is
closed. Read the amendment before the body.

**Glossary.** This spec uses three words the glossary does not define yet —
**chrome**, **plot** and **adapter**. They carry the central decision, so they
belong in `CONTEXT.md` when this effort closes out.

**The reasoning dies with the branch.** The framework-integration effort docs are
branch-scoped. The seam and the ordering are decisions that outlive them, so
they owe an ADR of their own before this branch merges.

**Dev loop.** Work happens in the `feat/charts-v2` worktree at
`~/frappe/worktrees/insights-charts-v2`. Its Vite dev server runs on 8081
against the live bench site, so the main checkout can serve the current renderer
on 8080 for side-by-side comparison. `node_modules/frappe-ui` there is a
hand-maintained absolute symlink; `yarn install` replaces it with the published
package and must be followed by restoring it.
