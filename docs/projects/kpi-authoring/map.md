# KPI authoring — decision map

A KPI card should be configured, not compiled. This map records how a number
card stops being a hand-built query pipeline.

Tickets live in `issues/`, one body of work each. A ticket carries a `Type:`, a
`Status:`, and any `Blocked by:` tickets.

Charted 2026-08-14. Continues the number card work in `312756c8..5a5fca04`.

## Destination

An author names a measure, a date column, a window and a comparison. Derivation
writes the filter, the grouping and the sort. Nobody writes a `sum_if` per
window, a constant join key, or a pruning `select`, and nobody has to know that
the card reads the last row.

The card's target stays a measure of the author's own query. Two small
query-layer changes make that join cheap.

## Notes

- Branch: `docs/framework-integration-map`, worktree `insights-islands`. The
  demo branch integrates this work, it never sources it.
- No schema change in this effort, so no migrate.
- The handoff that started this:
  `wayfinder/frappeverse-insights-demo/assets/number-card-redesign-handoff.md`
- The worked example of the pain:
  `wayfinder/frappeverse-insights-demo/build/overview_board.py`

## Decisions so far

Decided while charting, before tickets existed.

- **A window is a group-by, not a filter inside a measure.** One row per window,
  ordered oldest first. The measure stays plain. This is what removes the
  `sum_if` per window.
- **The group-by is the window itself, not the date grain.** Ticket 02 grouped by
  the unit the span names, which collapses a window to one row only when the span
  names one period. `last 3 months` returns three rows per window under that
  rule, and the card reads the newest month as if it were the three-month total —
  silently. Grouping by window membership makes every span return one row, and
  makes the single-period case correct by construction rather than by
  coincidence. See ticket 06.
- **Derivation stays pure, so the engine resolves the window.** `derive_operations`
  promises the same config always derives the same operations. A window depends on
  the clock and on Insights Settings, so derivation emits it unresolved — in the
  filter (ticket 02) and in the dimension (ticket 06) — and `ibis_utils` resolves
  it where the clock already lives.
- **The comparison stops being folklore.** `previous` reads the row before the
  last one today, and an author has to know that. Under window derivation the
  row before the last one *is* the previous window, because derivation wrote the
  sort. The adapter does not change.
- **Grouping restores the join key.** The constant `ibis.literal(1)` join key in
  `overview_board.py` is not a symptom of joining. It is a symptom of collapsing
  to one row. Grouping by window brings back a real period key, so the fake key
  goes without anyone solving the join.
- **The target stays the author's job.** A card reads one source query. This
  keeps `chart = one query, one operations list, one result`, which dashboard
  filter routing and drill-down both depend on.
- **The window vocabulary already half exists.** `handle_timespan` and
  `get_date_range` already parse `Last / Current / Next` across day, week,
  month, quarter, year and fiscal year. Only "to date", "shift" and "split" are
  missing.

- **A window is labelled by the date it starts on.** The dimension could have
  labelled windows `current` and `previous`. Naming them by their start date
  costs nothing and buys two things: the existing ascending `order_by` sorts them
  oldest first with no extra concept, and the label is a real period key — the
  same key whose absence forced the `ibis.literal(1)` join key in
  `overview_board.py`.
- **A row in two windows belongs to the oldest.** Spans can overlap, for example
  `last 3 months` shifted by one month. The oldest window wins, so no row is
  counted twice.
- **The window dimension is only correct beside its filter.** A row in no window
  is labelled nothing, and a NULL label sorts last, which would make it the
  card's reading. Derivation builds the filter and the dimension from one list of
  windows, so the two cannot drift, and a test pins that they are emitted
  together. Deliberately not defended further: there is no other caller, and
  `apply_windows` states the coupling in its own docstring.

- **The window sits on the chart, the comparison stays per value.** Ticket 03
  asked for both on the chart. A chart-level comparison control would be a second
  writer of `NumberColumnOptions.comparison`, which every earlier release already
  writes per value, so the picker puts its two window choices in the existing
  per-value select instead. Moving the comparison to the chart is a config change
  and deserves its own ticket, not a second writer bolted beside the first.

## Rejected alternatives

- **A reading is its own execution.** Modelling each card element as an
  independent `(measure, window, source)` execution is the cleanest model on
  paper. Rejected on three counts, all found in the code:
  `_execute_live_query` is `@concurrent_limit(wait_timeout=0)` and its own
  comment says a dashboard already starves the thread pool; `route_filters`
  resolves a dashboard filter to exactly one `query::column` per chart, so
  multi-source readings become unfilterable; and the card's drill identity is a
  row, which several readings do not have. The model survives as the way to
  *think* about a card. Execution count stays a derivation decision.
- **A new "Look up Value" operation.** A dedicated step for "bring the target
  for this period". Rejected because a granularity on the existing join key
  says the same thing with no new concept, and generalises to every cross-grain
  date join. See ticket 03.
- **Target registration at site or workbook level.** Deferred, not dropped. A
  registration is a saved lookup — build the step first, let a registration
  emit it later. Building it now would drag in the dashboard filter-link
  change.
- **Pruning meta columns in the engine.** `get_column` throws hard when a column
  is absent, and it already carries four fallback strategies from past column
  renames. A pruned column has no fallback. Pruning must be recorded in the
  query document at authoring time, so old documents are untouched. See
  ticket 04.
- **An author-declared "one row per key" field, or a profile query, to catch a
  fan-out join.** Rejected both. The first asks the author to assert something
  they often do not know, and a wrong assertion is silently wrong. The second
  costs a `GROUP BY` scan. The row count before and after the join is exact,
  already fetched, and reports what did happen rather than what might.

- **Flow or balance lives on the measure.** A flow accumulates over a window, a
  balance is the level at the window's end. Stated once on the measure, the
  window, the comparison and the sparkline all apply it and none needs a branch.
  The card does not reconstruct a balance from movements — an author whose source
  is a movement table makes it cumulative in their own query, the same way they
  own the target join. See ticket 07.
- **The sparkline gets its own execution.** Two questions — what is this number,
  and how did it move — are two queries. Serving both from one execution by
  grouping finer and summing in the adapter was rejected: it breaks for every
  non-additive measure, and a card that is right for sums and silently wrong for
  averages is worse than a second query. Two executions per chart, only when the
  sparkline is on, both cached. See ticket 08.

- **A sparkline is the card's own window, split one grain finer.** A
  month-to-date card draws this month by day. The rejected reading was the last
  twelve months, which is a different window and a line chart's question. The
  sub-windows come from `split_window`, which ticket 01 already landed, so the
  sparkline needs no new date vocabulary.

## Not yet specified

Nothing. Every question this effort opened is answered. New ones go here.

## Out of scope

- The chart contract (`one query, one operations list, one result`). Changing it
  is real work with real payoff, but it should be decided on its own, not
  arrived at by way of a KPI card.
- Dashboard filter links and the drill-down contract, which only move if the
  chart contract does.
