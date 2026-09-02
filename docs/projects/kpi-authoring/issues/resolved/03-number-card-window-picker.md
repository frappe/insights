# Number card window picker

Type: task
Status: resolved
Blocked by: 02, 06

## Question

The card's config form has to offer the window and the comparison as four
choices, not as a pipeline.

## What to build

In the number card's config form, beside the existing per-value target and
comparison controls:

- a **window** picker — `Month to date`, `Quarter to date`, `Year to date`,
  `Fiscal year to date`, `Last N months`, and the whole-period spans the date
  vocabulary already offers,
- a **comparison** option `Same window last year` / `Previous window`, which
  writes `source: 'window'` with the shift.

Both sit on the chart, not per value: they describe the reading, and a card
whose values disagree about the window is two cards.

The window picker needs a date column. When none is set, the picker says so
rather than offering a window that cannot derive.

## Done when

- Choosing a window and a comparison renders a correct card on
  `demo.erpnext.localhost` with zero author-written operations beyond a source
  and a business filter.
- The default comparison label reads from the window, so `vs same period last
  year` needs no typing. `defaultLabel` in `number.ts` handles the wording.
  **This is the one adapter change the effort needs.** `defaultLabel` returns
  `vs target` for every source that is not `previous`, so a `window` comparison
  with no label of its own prints "vs target" under the delta. Earlier tickets
  were told to leave `number.ts` alone. This ticket owns that one branch.
- A card saved before this ticket opens with no window set and renders as it did.
- A window label reads as a period, not as a raw date. A windowed card's
  dimension carries no granularity, so `column_granularity` reports none and a
  viewer prints `2026-08-01` where it means `Aug 2026`. Format the label from the
  span the card is configured with. Do not put a granularity back on the
  dimension — it would say the rows are grouped by month, and they are grouped by
  window.

## Out of scope

The sparkline. A windowed card returns two rows, so a real series needs a second
execution. Both questions that were open here are now answered — the card gets
its own execution, and it draws the window split one grain finer. Ticket 08 owns
it. Leave the existing sparkline behaviour exactly as it is.

## Notes

Build on frappe-ui controls and semantic tokens, matching the existing value
settings the earlier commits landed (`412fa6de`).

Convention worth defaulting on, from the handoff: a flow metric (revenue,
profit) defaults to comparing against the same window last year; a balance
(cash, receivables) defaults to the previous window. Defaulting is enough — do
not build a metric-type field for it in this ticket.
