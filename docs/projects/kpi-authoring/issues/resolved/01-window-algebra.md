# Window algebra

Type: task
Status: resolved

## Question

A KPI needs three things the date vocabulary cannot say today: a window that
ends at today rather than at the end of the period, the same window in an
earlier period, and that window cut into a series.

`handle_timespan` already parses `Last / Current / Next` across day, week,
month, quarter, year and fiscal year
(`insights/insights/query_builders/sql_functions.py:238`). `get_current_date_range`
returns the *whole* period — `current month` is the first to the last day of the
month, so there is no month-to-date anywhere in the product. That single gap is
why `overview_board.py` hand-writes `sum_if(posting_date >= …)`.

## What to build

Three functions in `insights/insights/query_builders/sql_functions.py`, beside
the existing date helpers.

```python
def get_window(span: str, anchor: date | None = None) -> tuple[date, date]
def shift_anchor(anchor: date, unit: str, count: int) -> date
def split_window(start: date, end: date, unit: str) -> list[tuple[date, date]]
```

**`get_window`** returns the window a span names, ending at the anchor when the
span is a to-date one. `anchor` defaults to today. Spans to support, in addition
to everything `get_date_range` already handles:

| span | anchored at 2026-08-10 |
|---|---|
| `month to date` | 2026-08-01 … 2026-08-10 |
| `quarter to date` | 2026-07-01 … 2026-08-10 |
| `year to date` | 2026-01-01 … 2026-08-10 |
| `fiscal year to date` | 2026-04-01 … 2026-08-10 |

Read the fiscal year start from Insights Settings, which `get_fy_start` already
does. Read the week start from `week_starts_on`, which `get_week_start_day_index`
already does. Do not reimplement either.

**`shift_anchor`** moves the anchor, not the endpoints. This is the whole design
of the shift: "the same window last year" is `get_window(span,
shift_anchor(anchor, "year", -1))`, not an arithmetic shift of a start and an
end. Anchoring is what keeps a to-date window to-date, and it makes leap days
and short months fall out correctly instead of needing cases.

**`split_window`** cuts a window into consecutive sub-windows at a grain. A
partial sub-window at either end is returned as it is, not padded or dropped.

`handle_timespan` must keep working unchanged for every span it accepts today.
Extend it to accept the to-date spans by delegating to `get_window`.

## Done when

- Unit tests cover each to-date span, `shift_anchor` across a leap day and a
  month-length change, and `split_window` with partial ends.
- A test proves a to-date span anchored on the last day of a period equals the
  existing whole-period range. The new spans must not disagree with the old
  vocabulary where they overlap.
- Every existing `handle_timespan` test still passes.
- No caller changes. This ticket adds vocabulary and nothing consumes it yet.

## Notes

Anchor injection matters for testability: `get_window` must accept an anchor so
tests never depend on the real today. Default it to `nowdate()` inside the
function, not at the signature.
