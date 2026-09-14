# Insights configures charts, frappe-ui draws them

Date: 2026-08-09

## Status

Accepted, and implemented. Extends [`type-independent-chart-config`](type-independent-chart-config.md), whose amendment agreed this seam and reversed the ordering it depended on.

## Context

Insights drew its own charts. `helpers.ts` built an ECharts option per chart type and `BaseChart.vue` mounted it — 1565 lines of rendering code.

frappe-ui ships charts v2, the standard chart family for every Frappe app. The same picture had two implementations, and the Insights one was behind: no heatmap, no loading or error states, no theme-reactive palettes. Dark mode stopped at charts, because nobody hand-themed the ECharts options.

An Insights chart mounted as an Island sits on a desk page beside charts the framework drew, and it did not match them. The framework-integration effort had already given the framework the rendering primitives and left Insights the reporting layer.

## Decision

**The ownership seam cuts at the layer, not at the chart type.**

frappe-ui owns the **chrome** — the card, the title, the actions, the legend, the tooltip, and the loading, error and empty states. Only the **plot** inside the chrome varies by type, and it has three fillers:

1. a charts v2 component, for every type v2 admits,
2. an Insights plot built on v2's `useChart`, for Map,
3. no plot at all, for Table.

A Number Chart is the one type that draws cards of its own: its readings are cards already, and a card inside a card borders a reading twice. So the chrome leaves the card surface undrawn for it and the filler draws the states inside each reading. This is one question asked of the type — `drawsOwnCards` (`adapter/index.ts`) — not a second card: the chrome still owns the title, the actions and the border, and the answer is a property of the type, settled before there is a result.

**One module turns config into props: the adapter** (`frontend/src2/charts/adapter/`). One pure function per chart type — no network, no ECharts, and no rendering: a filler names the component to mount and the props it takes, which for Table, Number and Map is an Insights SFC rather than a charts v2 one. It reads the Chart config and the query result together, because a `split_by` names the value columns after the split's values, plus what only the surface knows — the record links, the comparison rows, whether the reader may edit, whether a run is in flight.

One function per type rather than one adapter for every type. The config is per-type today and will not be after `type-independent-chart-config`'s split, so a flat shape means that split rewrites function bodies and not structure.

**Adding a chart type must not edit the card.** `ChartBody` stays the one state machine. It asks the adapter what to draw and draws it, and asks `drawsOwnCards` where the states go. It switches on nothing else.

**`echartOptions` is the only escape hatch**, deep-merged at chart, axis and series level. A default that is wrong for every app is a frappe-ui change, not an Insights one.

**Insights reshapes what v2 does not model.** v2 draws data and models no domain, so Insights derives the comparison delta, reshapes a funnel's measures into one row per stage, and lays out its own grid of number cards.

## Rejected

**A per-type seam** — v2 draws the types it admits, and Insights keeps its own card for the rest. It is a hybrid. Every new chart type needs a ruling on which side draws it, and an app-owned card stops matching a v2 chart on the same Dashboard. That mismatch pushes app features back into the library.

**Table and Map as staging cases**, waiting for v2 to admit them. They are excluded on the model instead. A table maps no value to a visual property, so it is not a plot. A choropleth needs a geography layer — GeoJSON, region-name resolution, a classification step — which is data cleaning, not rendering. If v2 ever owns that layer, Map moves from filler 2 to filler 1 and nothing else moves.

**A parallel option builder for the cases v2 draws badly.** It keeps a second renderer alive for a few charts, and "v2 cannot do X" is rarely true. `echartOptions` covers the same cases for less.

## Consequences

`BaseChart.vue` is deleted and no `get*ChartOptions` survives. A v2 improvement now reaches Insights without an Insights change, and charts follow the color scheme with no Insights theming code.

**The adapter's tests assert on props and never write a config literal.** Every config goes in through a fixture builder that expresses intent. The `type-independent-chart-config` split will change the adapter's input shape. If the split is lossless, the suite passes with only that builder rewritten.

`label_rotation` and the funnel's square-root stage scaling are library behavior now. `show_scrollbar` is dropped outright. Drill-down needs no index mapping for the types v2 plots, because v2 owns plot order and its typed events carry the row. The Table is the one exception: it draws the formatted rows, so its resolver crosses back to the raw row it was made from.

The engine is untouched. `test_chart_derivation.py` passes unchanged.
