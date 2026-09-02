# A sparkline of its own

Type: task
Status: resolved

## Question

A windowed card returns two rows — the current window and the comparison. A
sparkline drawn from them is two points.

## The decision

The sparkline gets its own execution. One query answers "what is this number and
what do I hold it against", the other answers "how did it move". Two questions,
two queries.

One execution cannot serve both. Grouping at the finer grain and summing the rows
into windows in the adapter was considered and rejected: it breaks for every
non-additive measure — average, count distinct, and any percent — and a card that
is right for sums and silently wrong for averages is worse than a second query.

A month-to-date card draws **this month by day** — the card's own window at a
finer grain. The rejected reading was the last twelve months, which is a
different window and answers a line chart's question, not a card's.

## This does not break the chart contract

The map keeps `chart = one query, one operations list, one result`, and rejected
"a reading is its own execution" partly to protect it. Read why before you worry:
the three reasons were the concurrency limiter, `route_filters` resolving one
`query::column` per chart, and a drill identity that is a row.

A sparkline execution hits none of them. It reads the **same source query** under
the **same filters**, so filter routing is untouched. It is never drilled. It is
one more execution, not N. What bends is only "one operations list per chart",
and `get_query(operations=...)` already runs an alternative pipeline for
drill-down. This is that same door.

## What to build

**The derivation is ordinary.** This is the part worth getting right, because it
needs no new mechanism at all:

1. the `within` filter for the configured window **only** — not the comparison
   window,
2. a `summarize` of the card's measures grouped by the date column at a **finer
   grain**,
3. an ascending `order_by`.

No window dimension. Inside a single window, grouping at a finer grain *is* the
split, so this is the same shape an axis chart already derives.

Map the span's unit to the grain one step finer — month to day, quarter to month,
year to month, fiscal year to month, week to day. Put the map beside the window
code, not inside the adapter.

**One round trip.** `get_data` on `Insights Chart v3` already holds the chart, its
config and the adhoc filters. Extend it to run the second execution and return it
beside the first, rather than adding a second whitelisted method — the client
should not have to know when a sparkline needs its own fetch, and `adhoc_filters`
must reach both executions identically.

Run it only when `config.sparkline` **and** `config.window` are both set. A card
with a sparkline and no window keeps today's behaviour exactly: the series is
whatever rows the query returned.

**The adapter takes a second result.** `ChartAdapterInput` carries one
`result: QueryResult`. Widen it with an optional second, and read the sparkline
from that when it is there. `number.ts` builds the series from `input.result.rows`
today — that path stays for unwindowed cards.

## Done when

- A month-to-date card with a sparkline draws one point per elapsed day.
- The reading and the comparison are identical whether the sparkline is on or off.
- A card with no window is untouched, and so is every other chart type.
- No second execution runs when the sparkline is off.
- A dashboard filter reaches both executions.

## Notes

`_execute_live_query` rejects at the concurrency limiter rather than queueing, and
its comment says a dashboard already pushes the pool. Two executions per card is
bounded and opt-in, which is why it was accepted. Do not make the second one
unconditional.

`split_window` from ticket 01 is **not** needed here — grouping at a finer grain
gives the same buckets. It stays unused until something needs sub-ranges as
values. One known difference: a day with no rows is absent rather than zero, so a
sparkline can show a gap. That matches every other chart in the product, and
changing it is not this ticket's job.
