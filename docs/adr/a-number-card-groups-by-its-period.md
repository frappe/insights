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

**The engine resolves the span.** Derived operations hold `month to date`, never dates. `get_window` resolves it while the query runs, where the clock and the fiscal calendar are. A comparison is the same span recomputed from a moved anchor (`shift_anchor`), so the previous span above is Aug 1–14, not all of August. Resolving earlier would derive different operations tomorrow.

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

## A card with no Period reads the dashboard's span

Date: 2026-10-06

### Decision

A card that states no Period, on a dashboard whose `within` filter is the only filter routed to its date column on its own query, reads that filter's span as its Period. `take_dashboard_period` writes the span into the chart's config where routed filters meet the chart: `view.routed_chart` for a View, `authoring.drilled_shape` for the Builder. Derivation, the comparison rows, the sparkline, the drill and the card's labels all read that one config. The filter then no longer applies to that card as a row filter, because it would drop the comparison spans.

A card that states its own Period keeps it, and the filter still narrows its rows. A `between` range, any other operator, a link to a query the chart's query reads, and a span beside any other filter on the same column all stay row filters, because that filter would cut the comparison spans again. A span is the only Period a dashboard lends.

### Consequences

A card's operations now depend on the dashboard it is read on, not on its config alone. The View sends the effective config as the card's `chart`. The Builder renders the config it edits, so it gets the lent span beside the rows as `period`, and the store overlays it without writing it into the edited config.

