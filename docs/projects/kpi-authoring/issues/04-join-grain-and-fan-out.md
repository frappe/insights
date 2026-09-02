# Join on a date grain, and warn on fan-out

Type: task
Status: ready-for-agent

## Question

Bringing a monthly target beside daily invoices needs two things the join dialog
cannot say: match the dates at a common grain, and tell the author when the join
multiplies their rows.

Both are already possible or already measured. Neither needs a new operation.

## What to build

**Grain on the join key.** When both join columns are dates, offer one
granularity control for the pair, and apply it to both sides.
`apply_granularity(column, granularity, data_type)` already exists on the query
builder (`ibis_utils.py:852`) — it is what a summarize uses to group a date
dimension. Call it in `left_eq_right_condition` (`ibis_utils.py:285`).

One control for the pair, not one per side. Truncating a column that is already
period-start is a no-op, and truncating one that is not fixes a bug the author
would never have found. Week grain picks up `week_starts_on` for free.

This is an affordance, not a capability: `t1.creation.truncate('month') ==
t2.month_start_date` is already writable in the custom join expression today.
The point is that the common case should not need the expression editor.

**Fan-out warning.** After a join is applied, compare the result row count with
the count before the join and say what happened:

```
Sales Target Monthly has 3 rows per month.
Joining repeated each row 3 times.
```

`get_count` already accepts an `active_operation_idx`
(`frontend/src2/query/query.ts:296`), so the count at either side of the join
is available from an endpoint the builder already calls. Do **not** add a
profile query, and do **not** add a field asking the author to declare the
table unique — see *Rejected alternatives* in `map.md`.

The warning belongs on every join, not only date ones. Any join to a non-unique
right table multiplies.

## Done when

- A daily date column joins to a monthly one by choosing `Month`, with no
  expression written.
- A join that multiplies rows says so, with the actual factor.
- A join that does not multiply says nothing.
- The grain is recorded in the join condition, so a saved query re-derives it.

## Notes

Hold this line, and write it into the code review: when the join dialog meets a
case it cannot express, the answer is the custom join expression, never another
field. The `Braces` toggle at `JoinSelectorDialog.vue:313` is the relief valve.

The interval shape (`Item Price.valid_from` / `valid_upto`) and the as-of shape
(exchange rates) are real but out of scope. Both are different jobs, and both
are another small increment on this same dialog when they come. ibis 11 has
`asof_join` when the third one is wanted.
