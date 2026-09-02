# Type-independent chart config

Date: 2026-08-05

## Status

Accepted, not yet implemented. `chart.ts` still defines `resetConfig` and
`types/chart.types.ts` still carries a config type per chart type. Amended
2026-08-09: the decision stands, the sequencing does not. This config change now
follows the render swap instead of leading it, and the swap has shipped
([ADR-0002](0002-charts-render-through-frappe-ui.md)). See *Amendment* at the
end.

## Context

A chart stores its configuration as JSON on `Insights Chart v3.config`. Each
chart type reads its own slot names out of that config:

| Type         | Dimensions                        | Measures                          |
| ------------ | --------------------------------- | --------------------------------- |
| Bar/Line/Row | `x_axis.dimension`, `split_by`    | `y_axis.series[].measure`         |
| Number       | `date_column`                     | `number_columns[]`                |
| Donut        | `label_column`                    | `value_column`                    |
| Funnel       | `label_column`                    | `value_column`, `measures[]`      |
| Table        | `rows[]`, `columns[]`             | `values[]`                        |
| Map          | `location_column`                 | `value_column`                    |
| Bubble       | `dimension`, `quadrant_column`    | `xAxis`, `yAxis`, `size_column`   |

These are eight names for two slots. Every chart is a set of dimensions and a
set of measures, plus options that say how to draw them.

frappe-ui charts v2 does not settle this question. Its props name the columns of
already-shaped data (`x`, `y`, `series`, `category`, `value`). It takes rows and
draws them. It holds no concept of a dimension, a measure, an aggregation or a
query. The config shape stays a concern of Insights.

## Decision

Split the chart config into the data selection and the presentation:

```
config = {
  dimensions: [...],   // shared across every chart type
  measures: [...],     // shared across every chart type
  filters, order_by, limit,
  display: { Bar: {...}, Line: {...}, Number: {...} },
}
```

A chart type change swaps the `display` entry only. The dimensions and the
measures survive every switch.

Slot mapping is positional. The first dimension fills the primary dimension slot
of the type, which is the x-axis, the label or the location. The first measure
fills the primary measure slot.

If the new type reads fewer slots than the user filled, keep the extra entries
and mark them as unused for this type. Never delete a selection on a type change.

## Rejected

**Per-type slots, cleaned up on a type switch** — the shape in place today.
Because the slots are named per type, a switch leaves the old type's slots
behind as garbage. `resetConfig` empties the config to clear them, and it runs
only when the switch crosses the axis to non-axis boundary. That boundary means
nothing to the user, and the reset destroys work: the selected x-axis is gone
after a switch to Number, and it does not come back on a switch to Line. The
reset also produced a crash, guarded alongside this ADR.

## Consequences

`resetConfig` goes away, and with it the axis to non-axis boundary. Each chart
type declares how many dimensions and measures it reads. The validator checks
that count. No option builder can reach a slot that does not exist.

A type switch becomes lossless and reversible. This makes a live preview of each
type possible, because the switch no longer costs the user any work.

Every chart type needs a mapper from the config to the v2 props. That mapper is
close to an identity function under this shape. Under the current shape it is
nine separate translations, and each one carries the old slot names into the new
render layer. That argued for making this change first. The amendment below
overturns the ordering and states what it costs.

The config is persisted, so the change needs a normalizer. `transformChartDoc`
already normalizes older config shapes on load. The new shape follows the same
route.

The `split_by` dimension currently forces a `pivot_wider` operation to make the
result wide. v2 reads long data through its `series` prop, so this ADR expected
the pivot to become unnecessary. It does not. See the amendment.

## Amendment, 2026-08-09

This section replaces *Blocked on, for the render layer only*, which said the v2
render swap was blocked by three gaps: combo charts, a numeric x-axis, and Map,
Bubble and Sankey, with the raw ECharts escape hatch missing.

That list described frappe-ui as it stood on 2026-08-05 and is now wrong. On
branch `charts-v2`, combo charts are a per-series `type` of `bar`, `line` or
`area`; `ScatterChart` covers Bubble, with `sizeColumn` and quadrant dividers as
reference lines; `SankeyChart` ships; and the escape hatch exists as
`echartOptions`, deep-merged at chart, axis and series level. The render swap is
not blocked.

Two of the three gaps survive, and their status changed:

- **A numeric x-axis** stays missing. It was never ruled on. v2 will gain it as
  `xAxis.type: 'value'`.
- **Map** is out of v2 permanently, on the model rather than on demand. A
  choropleth needs a geography layer the library does not own — external
  GeoJSON, region-name resolution and a classification step — which is data
  cleaning, not rendering. **Table** is out for the same kind of reason: nothing
  in it maps a value to a visual property, so it is not a plot. frappe-ui's
  `spec/charts.md` holds the rule and `spec/adr/0015-what-enters-charts.md`
  holds both rulings.

Three consequences for this ADR:

1. **The ordering is reversed.** The render swap goes first, starting with the
   axis charts, and this config change follows it. The reason is where the
   uncertainty sits: the config shape is derived from the Insights domain and is
   already settled, while real visual parity, the pivot question and the axis
   gaps can only be answered by swapping. The cost is the one this ADR named —
   per-type mappers written against the old slot names and then rewritten. It is
   capped by building the adapter as one module with a function per type, so the
   rewrite changes function bodies and not structure.
2. **The pivot stays.** v2's axis charts read wide data through a list-valued
   `y`, one series per column, which is exactly what `pivot_wider` produces. The
   long shape is available but narrower: its `series` grouping takes a single
   `y`, and Insights allows `split_by` together with several measures. Wide is
   also where the row cap belongs, because bounding the series count in SQL
   bounds the result before it crosses the wire.
3. **Insights renders no chart chrome.** The ownership seam agreed alongside this
   amendment cuts at the layer, not at the chart type: v2 owns the card, title,
   legend, tooltip and states for every Insights chart, Map and Table included,
   and only the plot inside them varies. So "Map and Table stay ours" means
   Insights owns two plots, not two chart implementations.

The seam and the ordering are recorded in
[ADR-0002](0002-charts-render-through-frappe-ui.md).
