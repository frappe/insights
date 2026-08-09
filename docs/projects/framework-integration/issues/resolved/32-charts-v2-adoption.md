# 32 — What does Insights adopt from frappe-ui charts v2, and what stays ours?

Type: grilling
Status: resolved
Blocked by: none

## Question

The map decided that the framework contributes rendering primitives and that
the engine stays in Insights. frappe-ui charts v2 is that primitive, and it is
now real: `frappe-ui/src/charts/` on branch `charts-v2`, unit-tested and
Cypress-tested. Insights renders its own ECharts options instead, from
`frontend/src2/charts/helpers.ts` (1565 lines) through
`charts/components/BaseChart.vue`.

Two renderers now draw the same pictures. The map's ownership split says only
one of them should be ours. It does not say which parts of ours go, when they
go, or what Insights keeps drawing itself.

Grill the adoption, not the migration mechanics. The open points:

1. **The gap list is a fork in the road.** ADR-0001 records three gaps that
   Insights hits: combo charts (per-series Bar or Line), a numeric x-axis, and
   the three types v2 has no answer for — Map, Bubble, Sankey. Table and the
   region-mapping chart are not ECharts at all. Each gap has the same three
   answers: close it in frappe-ui, keep an Insights renderer beside v2, or drop
   the capability. "v2 for the common types, ours for the rest" is a hybrid, and
   a hybrid means the foundation is wrong. Decide the rule, not the ten cases.
2. **What is the seam?** v2 takes rows and column names. Insights holds
   dimensions, measures, aggregations and a query. ADR-0001 says the config
   shape stays ours and the mapper is near-identity *under the new shape*. That
   shape is not built yet — `resetConfig` is still in `charts/chart.ts`, so step
   one of the migration is still pending. Confirm the ordering still holds, or
   say what changed.
3. **Who owns the escape hatch?** ADR-0001 calls the raw ECharts hatch missing
   from v2. If Insights keeps a hatch, every gap can hide in it and the second
   renderer never dies. If it does not, an unsupported chart is a frappe-ui
   ticket and an Insights release waits on it.
4. **Release coupling.** v2 lives on an unmerged frappe-ui branch, which
   Insights reaches through framework's `link:./frappe-ui`. Ticket 28 already
   found that the crossing puts a second lockfile in the closure. Adopting v2
   makes an Insights release depend on a frappe-ui release. Name the condition
   that has to be true before the swap lands on `develop`.
5. **Does the island change the answer?** The desk island renders charts through
   the shared framework runtime. If the runtime ships v2 anyway, an Insights
   renderer is a second chart engine on the same page. Check whether that
   settles point 1 by itself.

## Why this is a ticket now

The map lists "frappe-ui charts migration — already in flight, needs no
decision" under Out of scope. That line is wrong on both halves. The migration
is not in flight — ADR-0001's first step is unbuilt — and the gap list is a
decision, not a task. This ticket amends that line.

## Evidence

- `frontend/src2/charts/helpers.ts`, `charts/components/BaseChart.vue`,
  `charts/components/Sparkline.vue` — the Insights ECharts layer.
- `charts/components/` also holds `TableChart.vue`, `MapChartConfigForm.vue`,
  `RegionMappingDialog.vue`, `SankeyChartConfigForm.vue` and
  `BubbleChartConfigForm.vue` — the four types with no v2 counterpart.
- `frappe-ui/src/charts/` on `charts-v2` — AxisChart, DonutChart, FunnelChart,
  SankeyChart, HeatmapChart, NumberCard, plus `scatterOptions.ts`,
  `referenceLines.ts`, `axisFormat.ts` and their tests. Sankey and a scatter
  path exist here, which narrows ADR-0001's gap list. Re-audit before grilling.
- [ADR-0001](../../../../adr/0001-type-independent-chart-config.md) — the config
  split, and the three gaps as recorded on 2026-08-05.
- [Ticket 28](28-runtime-version-authority.md) — the second lockfile.
- [Ticket 31](31-one-dashboard-one-chart-renderer.md) — the renderer family
  below `ChartBody` is the one card set. This ticket decides what fills it.

Work happens in the `feat/charts-v2` worktree at
`~/frappe/worktrees/insights-charts-v2`, reviewed at
`http://ai.insights.localhost:8081/insights`.

## Answer

Grilled 2026-08-09. The audit that opened the session made most of the ticket's
own premises obsolete, so read the findings before the decisions.

### What the audit changed

frappe-ui carries a written scope rule for v2, `spec/charts-scope.md`, which
decides membership against six conventions and already applies them to the
Insights gap list. It is the authority for what enters v2. Most of ADR-0001's
"Blocked on" section is dead:

| ADR-0001 gap | Today on `charts-v2` |
| --- | --- |
| Combo charts | Closed. `seriesConfig[key].type: 'bar' \| 'line' \| 'area'`. |
| Bubble | Closed. `ScatterChart` with `sizeColumn`; quadrants are `referenceLines`. |
| Sankey | Closed. |
| Raw ECharts hatch | Closed. `echartOptions` at chart, axis and series level. |
| Numeric x-axis | Open, and in no v2 document at all. Decided below. |
| Map | Open, and ruled out of v2 on the model. |

Table and Map stay out of v2 for a reason, not for lack of demand. A table maps
no value to a visual property, so it is not a plot. A choropleth needs a
geography layer v2 does not own — GeoJSON, region-name resolution, and a
classification step, which is data cleaning. If v2 ever owns that layer, Map
enters.

### The decisions

1. **The ownership seam cuts at the layer, not at the chart type.** v2 chrome is
   universal: `ChartCard`, `ChartContainer`, `ChartLegend`, `ChartTooltip` and
   the loading, error and empty states dress every Insights chart, Table and Map
   included. Only the plot slot varies — a v2 chart component, an Insights plot
   on `useChart` (Map), or no plot at all (Table). Insights never builds an
   ECharts option for a type v2 admits, and never draws chrome for a type it
   owns. A per-type seam was rejected as a hybrid: it makes every new chart type
   a coin flip. This seam makes "move Map to frappe-ui later" a filler swap that
   touches nothing else.
2. **The render swap goes first, and the axis family goes first within it.**
   ADR-0001 sequenced the config split first, to avoid writing per-type mappers
   twice. That order is overturned. The config shape is domain-derived and
   already written down, while every unknown lives in the swap: real visual
   parity, the pivot question, the scrollbar, the numeric axis. Bar, Line and
   Row carry almost all of them. The throwaway mappers are the accepted price,
   capped by making the adapter one module with a function per type, so the
   config split rewrites function bodies and not structure.
3. **v2 gains a numeric x-axis**, as `xAxis.type: 'value'`. It is a membership
   decision under the scope rule, so it is argued there and lands as its own
   frappe-ui PR into `charts-v2` before the Insights swap needs it.
4. **`show_scrollbar` is dropped.** It is the scope spec's one Undecided item.
   Insights loses the feature for now rather than holding a second renderer open
   for it.
5. **`split_by` stays wide.** Keep the server-side pivot and map it to `y: [...]`,
   one series per pivoted column. The adapter reads `y` off the result columns,
   not off the config — the one place the mapper is not near-identity. Long was
   the more attractive shape and was rejected on a hard constraint: v2's `series`
   grouping takes a single `y`, and Insights allows `split_by` together with
   several measures, which only wide expresses. The cap argument turned out to
   be neutral. The cap is not a pivot feature — ranking, `Others` rewriting and
   pivoting are three independent steps in `ibis_utils.py` — and both shapes
   carry the same cells, so wide is only a more compact encoding.
6. **Insights depends on the local frappe-ui link for the duration**, because
   charts-v2 is still being polished alongside this work. The branch's
   `frontend/package.json` declares `link:../../frappe/frappe-ui` rather than
   sitting at `^1.0.0-beta.24` while building against source. Flipping that to
   the published version is a merge condition. Individual commits need not be in
   a working state.

`develop` uses the published `^1.0.0-beta.24`, not the link, so this work is
independent of the island chain and of the unmerged dependencies
[ticket 28](28-runtime-version-authority.md) found.

### Carried into the spec, not decided here

- **ADR-0001 needs amending or superseding.** Its "Blocked on" section now
  misleads. Its config decision stands.
- **The scope spec's pushbacks are Insights work items**, not open questions:
  Insights computes the `comparison` delta, reshapes funnel measures mode, lays
  out its own NumberCard grid, maps `hide_from_chart` onto
  `v-model:hiddenSeries`, and routes `overlap` through `echartOptions`.
  `label_rotation` and funnel stage widths become library behaviour and leave
  the Insights config.
- **The top-N split ranking is alphabetical, not by measure**
  (`ibis_utils.py:539-545`), so `Others` can swallow the largest series. A
  latent bug, orthogonal to this work, wants its own ticket.
