# 2. Insights configures charts, frappe-ui draws them

Date: 2026-08-09

## Status

Accepted, and implemented. Extends [ADR-0001](0001-type-independent-chart-config.md),
whose amendment agreed this seam and reversed the ordering it depended on.

## Context

Insights drew its own charts. `helpers.ts` built an ECharts option per chart
type and `BaseChart.vue` mounted it — 1565 lines of rendering nobody asked
Insights to own.

frappe-ui ships charts v2, the standard chart family for every Frappe app. So
the same picture had two implementations, and the Insights one was behind: no
heatmap, no loading or error or empty states, no theme-reactive palettes, no
HTML tooltips, and axis labels that could not measure themselves. Dark mode
stopped at charts for exactly this reason, because theming an ECharts option by
hand was work nobody had claimed.

The gap was about to become visible. An Insights chart mounted as an Island sits
on a desk page beside charts the framework drew, and it did not match them. The
framework-integration effort had already decided the framework contributes the
rendering primitives and Insights stays the reporting layer. The renderer
contradicted that decision in 1565 lines.

## Decision

**The ownership seam cuts at the layer, not at the chart type.**

frappe-ui owns the **chrome** — the card, the title, the actions, the legend,
the tooltip, and the loading, error and empty states — for every Insights chart
without exception. Only the **plot** inside the chrome varies by type, and it
has exactly three fillers:

1. a charts v2 component, for every type v2 admits,
2. an Insights plot built on v2's `useChart`, for Map,
3. no plot at all, for Table.

A per-type seam was rejected. It reads as pragmatic and it is a hybrid: every
new chart type becomes a coin flip, and an app-owned plot that draws its own
card stops matching a v2 chart on the same Dashboard. That mismatch is the
pressure that pushes app features back into the library.

**Table and Map are excluded on the model, not as staging.** A table maps no
value to a visual property, so it is not a plot. A choropleth needs a geography
layer — GeoJSON, region-name resolution, a classification step — which is data
cleaning, not rendering. If v2 ever owns that layer, Map changes from filler 2
to filler 1 and nothing else moves.

**One module turns config into props: the adapter** (`frontend/src2/charts/adapter/`).
One pure function per chart type — no Vue, no network, no ECharts. It reads
**two** inputs, the Chart config and the query result, because with a `split_by`
the value columns are named after the split's values, which config alone cannot
supply.

One function per type rather than one general mapper, because the config is
per-type today and will not be after ADR-0001's split. Keeping the shape flat
means that split rewrites function bodies and not structure.

**Adding a chart type must not edit the card.** `ChartBody` stays the one card
and the one state machine. It asks the adapter what to draw and draws it; it
does not switch on chart type. A type is added by writing one adapter function
and naming it in one map.

**`echartOptions` is the only escape hatch**, deep-merged at chart, axis and
series level. Insights keeps no parallel option builder for a case v2 draws
badly. This is what makes total adoption reachable rather than aspirational:
"v2 cannot do X" is almost always false, so it stops being a reason to keep a
second renderer alive. A default that is wrong for every app is a frappe-ui
change.

## Consequences

`BaseChart.vue` is deleted and `helpers.ts` drops from 1565 lines to 153. No
`get*ChartOptions` survives. A v2 improvement now reaches Insights without an
Insights change, and theming closes for free — charts follow the colour scheme
with no Insights theming code, which finishes the charts half of dark mode.

**The adapter's tests assert on props and never write a config literal.** Every
config goes in through a fixture builder that expresses intent. This is not a
style preference: ADR-0001's split will change the adapter's input shape, and if
the split is lossless the suite passes with only that builder rewritten. A test
that cannot be expressed in the new shape means the split lost something, and CI
says so before a Dashboard does. This is the repo's first frontend test suite.

**Insights reshapes what v2 refuses to model.** v2 draws data and does not model
a domain, so Insights derives the comparison delta, reshapes a funnel's measures
into one row per stage, and lays out its own grid of number cards. Each is
Insights work by the library's rule, not a gap in it.

Three options disappear. `label_rotation` and the funnel's square-root stage
scaling are library behaviour now. `show_scrollbar` is dropped outright: holding
a second renderer open for it cost more than the feature was worth.

Drill-down survives without the index mapping it used to need. v2 owns plot
order and its typed events carry the row itself, so nothing maps a datapoint
index back onto the result.

**Standing in this seam found five defects in it**, all fixed in frappe-ui: the
chart components did not forward the container's state slots, the loading slot
could not replace the spinner, per-series axis assignment reordered series and
shifted the palette, the scatter printed no point labels, and the number card
could not colour its value. The seam was advertised before it was exercised.
Insights was the first caller to stand in it.

The engine is untouched. No Operation, no derivation, no query change —
`test_chart_derivation.py` passes unchanged, which is the tripwire that says so.
