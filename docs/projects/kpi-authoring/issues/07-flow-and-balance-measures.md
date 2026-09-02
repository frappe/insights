# Flow and balance measures

Type: task
Status: ready-for-agent

## Question

A window applies differently depending on what the measure means.

A **flow** accumulates over the window. Revenue for August is every August
invoice added up.

A **balance** is a level, read at a moment. Cash for August is the cash on the
last day of August, not the sum of every daily cash figure. Summing a balance
over a window returns a number with no meaning, and nothing stops an author
doing it today. This effort's whole premise is that the author stops checking
the pipeline, so the tool has to be the one that knows.

## The decision

The distinction lives on the **measure**, stated once. The window, the
comparison and the sparkline then all apply it, and none of them needs a branch
of its own.

## What to build

**On the measure.** `Measure` in `frontend/src2/types/query.types.ts` gains:

```ts
/** A flow accumulates over a window. A balance is the level at the window's end. */
metric_type?: 'flow' | 'balance'
```

Absent means `flow`. Every measure written before this ticket is a flow, which
is what they already behave as.

**In derivation.** A balance changes what the aggregation means over a window,
not what the window is:

- a flow aggregates its rows with the aggregation the measure names,
- a balance takes the **last value in the window**, ordered by the card's date
  column.

The window dimension needs no change. One row per window still holds, because
"the last value in this window" is one number per window exactly as a sum is.

**What the card does not do: reconstruct a balance from movements.** If the
source is a movement table — invoices, payments, stock entries — the author makes
it cumulative in their own query, the same way they own the target join. The card
reads a level that is already there. Building an as-of reconstruction into the
card would be a second mechanism for a job the query layer already does, and the
handoff's "cumulative in minus cumulative out" belongs in the query.

Say this in the picker rather than leaving it to be discovered: a balance measure
whose source carries no level per period gives a wrong-looking number, and the
author needs to know why.

**The comparison default falls out.** The handoff's convention — flows compare
against the same window last year, balances against the previous window — stops
being a rule of thumb and becomes derivable. Ticket 03 was told to default this
by hand. Once `metric_type` exists, read it.

## Done when

- A balance measure over a window returns the level at the window's end, and its
  comparison returns the level at the comparison window's end.
- A flow measure derives exactly what it derives today. Every test from tickets
  02 and 06 passes unchanged.
- A measure with no `metric_type` behaves as a flow.
- An end-to-end test in `test_ibis_utils.py` proves a balance and a flow over the
  same window return different numbers, in the shape ticket 02 established.

## Notes

Derivation must stay pure — see `../map.md`. `metric_type` is config, so this
ticket does not strain that, but the aggregation it selects is resolved wherever
the aggregation already is.

Check whether `aggregations` in `query.types.ts` needs a member for the ordered
read, or whether the balance path selects it without the author naming one. The
second is better if it works: the author says what the measure *is*, not how to
aggregate it.
