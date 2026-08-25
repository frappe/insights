# Type-independent chart config

Date: 2026-08-05

## Status

Accepted. The implementation is sequenced as the first step of the frappe-ui
charts v2 migration.

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

Because the slots are named per type, a type switch leaves the old type's slots
behind as garbage. `resetConfig` cleans up by emptying the config, but it runs
only when the switch crosses the axis to non-axis boundary. That boundary means
nothing to the user. It also destroys work: the selected x-axis is gone after a
switch to Number, and it does not come back on a switch to Line.

The reset also produced a crash. See the guard shipped alongside this ADR.

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

## Consequences

`resetConfig` goes away, and with it the axis to non-axis boundary. Each chart
type declares how many dimensions and measures it reads. The validator checks
that count. No option builder can reach a slot that does not exist.

A type switch becomes lossless and reversible. This makes a live preview of each
type possible, because the switch no longer costs the user any work.

Every chart type needs a mapper from the config to the v2 props. That mapper is
close to an identity function under this shape. Under the current shape it is
nine separate translations, and each one carries the old slot names into the new
render layer. This is why the change comes first in the v2 migration and not
after it.

The config is persisted, so the change needs a normalizer. `transformChartDoc`
already normalizes older config shapes on load. The new shape follows the same
route.

The `split_by` dimension currently forces a `pivot_wider` operation to make the
result wide. v2 reads long data through its `series` prop. That pivot may become
unnecessary. Confirm this during the migration.

## Blocked on, for the render layer only

The config change is not blocked. The v2 render swap is. The parity audit in
frappe-ui lists three gaps that Insights hits:

1. Combo charts. `YAxisConfig` offers a per-series `Line` or `Bar` type. The v2
   components are homogeneous.
2. A numeric x-axis. v2 supports `category` and `time` only.
3. Map, Bubble and Sankey. v2 ships seven chart types and Insights has ten. The
   audit already lists the raw ECharts escape hatch as missing.
