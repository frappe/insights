# 2. Insights configures charts, frappe-ui draws them

Date: 2026-08-09

## Status

Accepted, and implemented. Extends [ADR-0001](0001-type-independent-chart-config.md),
whose amendment agreed this seam and reversed the ordering it depended on.

## Context

Insights drew its own charts. `helpers.ts` built an ECharts option per chart
type and `BaseChart.vue` mounted it — 1565 lines of rendering nobody asked
Insights to own.

frappe-ui ships charts v2, the standard chart family for every Frappe app. The
same picture had two implementations, and the Insights one was behind: no
heatmap, no loading or error states, no theme-reactive palettes. Dark mode
stopped at charts, because hand-theming an ECharts option was unclaimed work.

An Insights chart mounted as an Island sits on a desk page beside charts the
framework drew, and it did not match them. The framework-integration effort had
already given the framework the rendering primitives and left Insights the
reporting layer.

## Decision

**The ownership seam cuts at the layer, not at the chart type.**

frappe-ui owns the **chrome** — the card, the title, the actions, the legend,
the tooltip, and the loading, error and empty states — for every Insights chart
without exception. Only the **plot** inside the chrome varies by type, and it
has exactly three fillers:

1. a charts v2 component, for every type v2 admits,
2. an Insights plot built on v2's `useChart`, for Map,
3. no plot at all, for Table.

**One module turns config into props: the adapter** (`frontend/src2/charts/adapter/`).
One pure function per chart type — no Vue, no network, no ECharts. It reads two
inputs, the Chart config and the query result, because a `split_by` names the
value columns after the split's values.

One function per type rather than one general mapper. The config is per-type
today and will not be after ADR-0001's split, so a flat shape means that split
rewrites function bodies and not structure.

**Adding a chart type must not edit the card.** `ChartBody` stays the one card
and the one state machine. It asks the adapter what to draw and draws it. It
never switches on chart type.

**`echartOptions` is the only escape hatch**, deep-merged at chart, axis and
series level. A default that is wrong for every app is a frappe-ui change, not
an Insights one.

**Insights reshapes what v2 does not model.** v2 draws data and models no
domain, so Insights derives the comparison delta, reshapes a funnel's measures
into one row per stage, and lays out its own grid of number cards.

## Rejected

**A per-type seam** — v2 draws the types it admits, and Insights keeps its own
card for the rest. It is a hybrid. Every new chart type becomes a coin flip, and
an app-owned card stops matching a v2 chart on the same Dashboard. That mismatch
pushes app features back into the library.

**Table and Map as staging cases**, waiting for v2 to admit them. They are
excluded on the model instead. A table maps no value to a visual property, so it
is not a plot. A choropleth needs a geography layer — GeoJSON, region-name
resolution, a classification step — which is data cleaning, not rendering. If v2
ever owns that layer, Map moves from filler 2 to filler 1 and nothing else
moves.

**A parallel option builder for the cases v2 draws badly.** It keeps a second
renderer alive for a handful of charts, and "v2 cannot do X" is almost always
false. The escape hatch covers the same ground at a fraction of the cost.

## Consequences

`BaseChart.vue` is deleted and no `get*ChartOptions` survives. A v2 improvement
now reaches Insights without an Insights change, and charts follow the colour
scheme with no Insights theming code.

**The adapter's tests assert on props and never write a config literal.** Every
config goes in through a fixture builder that expresses intent. ADR-0001's split
will change the adapter's input shape. If the split is lossless, the suite
passes with only that builder rewritten.

`label_rotation` and the funnel's square-root stage scaling are library
behaviour now. `show_scrollbar` is dropped outright. Drill-down needs no index
mapping, because v2 owns plot order and its typed events carry the row.

The engine is untouched. `test_chart_derivation.py` passes unchanged.
