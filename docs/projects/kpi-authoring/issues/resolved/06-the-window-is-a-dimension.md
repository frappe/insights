# The window is a dimension

Type: task
Status: resolved
Blocked by: 02

## Question

Ticket 02 groups a windowed card by the unit its span names. `month to date`
groups by month, which collapses the window to one row. That is right by
coincidence, not by construction: the span names one period, so its grain and
its window are the same thing.

`last 3 months` breaks it. The grain is month, so the current window comes back
as three rows and the comparison window as three more. The card reads the newest
month and calls it the three-month reading. No error is raised anywhere.

A silent wrong number is the worst failure this effort can ship. The card's whole
promise is that the author stops hand-building the pipeline, which means they
stop checking it.

## The decision

Group by the **window**, not by the date grain. A row belongs to the current
window, to the comparison window, or to neither. That is one row per window for
every span, including multi-period ones, and the single-period case stops being
a coincidence.

The window is a dimension, resolved at execution — the same shape ticket 02 chose
for the filter. Derivation emits the dimension unresolved, carrying the span, the
anchor and the shift. `ibis_utils` resolves it into a column that labels each row
with its window, because that is where the clock and Insights Settings already
live. Derivation must stay pure.

## What to build

1. **A guard first, so nothing lies while the rest is built.** `config_errors`
   rejects a window config it cannot derive correctly:
   - a `window` with no `date_column`. Today the derivation branch needs both, so
     a card missing the date column silently derives its old unwindowed
     operations.
   - a multi-period span, until step 2 lands.
   Ship this step on its own if the rest runs long.
2. **A window dimension.** Derivation emits it in the summarize's `dimensions`
   in place of the grain-carrying date column. The engine resolves it to a
   labelled column, ordered so the comparison window sorts before the current
   one. The sort is the contract `number.ts` reads — pin it in a test.
3. **Remove the guard's multi-period branch** once step 2 covers it.

`WINDOW_GRAINS` and `_window_grain` in `chart_query.py` go away with step 2. They
exist only to make the coincidence work.

## Done when

- `last 3 months` with a `same window last year` comparison returns exactly two
  rows, current last, each holding the whole window's total.
- Every single-period span returns what it returns today. The tests ticket 02
  added must pass unchanged.
- A card with a window and no date column reports a config error rather than
  drawing the wrong thing.
- An end-to-end test in `test_ibis_utils.py` executes the derived operations and
  asserts the row values, in the shape ticket 02 established.

## Notes

Do not touch `frontend/src2/charts/adapter/number.ts`. If the adapter appears to
need a change, that is a finding to report on this ticket, not a task.
