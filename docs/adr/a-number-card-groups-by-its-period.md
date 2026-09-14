# A Number card groups by its Period

Date: 2026-09-14

## Status

Accepted. Built in `insights_chart_v3/chart_query.py` (`_add_window_operations`, `_comparison_shifts`) and `insights_data_source_v3/ibis_utils.py` (`aggregate_by_window`).

## Context

A card that shows revenue month to date against the previous month used to be a query the author built by hand: one `sum_if` per span, a pruning `select`, and a constant `ibis.literal(1)` join key to bring a target beside the single row. The author also had to know the card reads the last row.

## Decision

The author states a measure, a date column, a Period and a comparison. Derivation writes the filter, the grouping and the sort.

**The span is the group.** Each span the card needs, the configured one and one per comparison, becomes one row labeled by the date it starts on. On 2026-09-14, `month to date` against `previous` returns:

```
posting_date | grand_total
2026-08-01   | 410,000
2026-09-01   | 452,000
```

The start dates sort the rows oldest first, and the label is a real period key a target can join on. The group is the span, not the unit it names: `last 3 months` grouped by month returns three rows, and the card would show August as the three-month total.

**The engine resolves the span.** Derived operations carry `month to date`, never dates. `get_window` resolves it while the query runs, where the clock and the fiscal calendar are. A comparison is the same span recomputed from a moved anchor (`shift_anchor`), so the previous span above is Aug 1–14, not all of August. Resolving earlier would derive different operations tomorrow.

**Each span is its own aggregate.** `aggregate_by_window` filters and aggregates once per span and unions the rows. Spans that overlap both count the rows they share: `last 3 months` against the same span a month back share June and July, and neither reads short.

**An empty span is a row with null measures.** Readings are read by position, so a missing August row would give September's comparison the wrong figure.

**The sparkline is a second query.** It splits the span one grain finer and runs only when the sparkline is on.

**A `grain` Period filters nothing.** It groups by the grain, sorts newest first so the newest period is on the first page, and the rows are reversed after fetching.

## Rejected

- **One `sum_if` per span.** Every comparison adds a measure, and the single row has no period key to join on.
- **Serving the sparkline from the card's result.** Correct for sums only. One order of 100 on Sep 1 and nine of 10 on Sep 2 average 19. The mean of the two daily averages is 55.
- **One query per reading.** `_execute_live_query` rejects instead of waiting (`wait_timeout=0`), so a dashboard of multi-reading cards gets 503s. `route_filters` resolves a dashboard filter to one column per chart, and a drill opens one row. Neither works across several queries.
- **Target registration at site or workbook level.** The target stays a measure of the author's own query, so a chart remains one query, one operations list, one result.

## Consequences

A summarize grouped by spans can group by nothing else. A second dimension would split each span again, so `aggregate_by_window` throws.
