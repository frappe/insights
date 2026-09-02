# Number card window derivation

Type: task
Status: resolved
Blocked by: 01

## Question

A number card configured with a window and a comparison should derive its own
operations. Today the author writes them: a filter covering both windows, a
`sum_if` per window inside the measures, and knowledge that the card reads the
last row.

## What to build

**Config.** `NumberChartConfig` in `frontend/src2/types/chart.types.ts` gains a
window, and `NumberComparison` gains a source that names one:

```ts
window?: {
    /** A span `get_window` understands, e.g. `month to date`. */
    span: string
    /** Fixed anchor for a card that must not move with today. Defaults to today. */
    anchor?: string
}
```

`NumberComparison.source` gains `'window'`, with the shift that produces it:

```ts
/** The same span, anchored `count` `unit`s back. `source: 'window'` only. */
shift?: { unit: string; count: number }
```

`previous`, `constant` and `measure` keep working exactly as they do. A card with
no `window` derives exactly what it derives today.

**Derivation stays pure.** This is the constraint that shapes the whole ticket.
`chart_query.py` states it at the top: *"Nothing here reads the database or a
document: it is a function of chart type, source query name and config, so the
same three inputs always give the same operations."* `get_window` reads Insights
Settings and the clock, so derivation must **not** call it. Resolving a window to
two dates during derivation would make the same config derive different
operations from one day to the next.

So derivation emits the window **unresolved**, and the engine resolves it at
execution, where the clock and the settings already live. The `within` filter
operator is exactly this mechanism — it carries a timespan string and
`handle_timespan` resolves it in `ibis_utils.py`.

**Derivation.** In
`insights/insights/doctype/insights_chart_v3/chart_query.py`,
`_add_number_operation` gains one path: when `window` and `date_column` are both
set, emit

1. a `filter_group` with `logical_operator: "Or"` holding one `within` filter per
   window — the configured window, plus the shifted window when the comparison
   names one,
2. a `summarize` of the card's measures grouped by `date_column` at the window's
   own grain,
3. an ascending `order_by` on the window column.

**The shifted window needs the filter to carry a shift.** `within` can say
`Month to Date` today. It cannot say "the same span, one year back". Extend the
`within` value so it can, and teach `handle_timespan` to read it — that is where
`get_window(span, shift_anchor(nowdate(), unit, count))` gets called, at
execution time.

Pick the encoding, but hold two rules: the shift must be structured, not a string
protocol parsed out of the span (`"Month to Date, 1 year ago"` is the wrong
answer), and a `within` value written before this ticket must keep resolving
unchanged. `FilterValue` in `frontend/src2/types/query.types.ts` will need
widening to match whatever you choose.

Order is the contract. The last row is the reading and the row before it is the
comparison, which is what `number.ts` already assumes. Derivation is what makes
that true rather than something an author has to know.

Add the new slots to `SLOT_SHAPES` so a malformed window is reported by
`_malformed_slots` rather than read.

**No adapter change.** `frontend/src2/charts/adapter/number.ts` must not be
touched by this ticket. A windowed card sets `comparison.source: 'previous'`
semantics through derivation, so the existing reader is correct as written. If
the adapter appears to need a change, stop and say so on this ticket — that is a
finding about the design, not a task.

## Done when

- Cases in `insights/tests/test_chart_derivation.py` cover: a card with a window
  and no comparison (one window in the filter, one row), a card with a
  `window` comparison (two windows, two rows, current last), and a card with no
  window (byte-identical operations to today).
- A test pins the sort direction. It is the contract the adapter reads.
- Existing derivation tests pass unchanged.

## Notes

The demo case to check against is "Revenue MTD vs same ten days last FY" in
`wayfinder/frappeverse-insights-demo/build/overview_board.py`. The derived
operations should replace queries `Revenue MTD (working set)` and
`Revenue MTD vs Target` down to a source, a business filter, and the target
join.

The sparkline is **out of scope**. Two rows make a two-point sparkline, and
whether a windowed card gets a second execution for its series is unsettled —
see *Not yet specified* in `../map.md`. Leave the existing sparkline behaviour
alone.
