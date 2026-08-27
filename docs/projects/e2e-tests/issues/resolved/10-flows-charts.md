# 10 — Flows: Chart configuration and rendering

Type: task
Status: resolved
Blocked by: 02, 07

## Question

Cover this area's flows from the ticket 02 inventory, to the 80% bar.

Follow `frontend/tests/AGENTS.md` and pattern-match the two exemplar tests from
ticket 07. Do not invent a helper style. If a flow needs something the fixtures
do not offer, add it to the shared fixture module rather than working around it
locally.

Baseline is characterization: record what the UI does today. A test that
disagrees with the code means the test is wrong. If you find a genuine bug, file
it as a new ticket on this map and move on — never fix it here.

The answer lists the flows covered, the flows skipped and why, and any fixture
added.

## Answer

`frontend/e2e/tests/charts.spec.ts` holds 13 flows, C1 to C13. C1 is the
exemplar and is unchanged.

### Flows covered

| # | Kind | What it asserts |
| --- | --- | --- |
| C1 | author | Bar chart draws `delivered`, `canceled` and a `1.8K` tick |
| C2 | author | Number card reads `count_of_order_id` and `2,000` |
| C3 | author | Table chart pivots to one column per order status |
| C4 | author | Donut legend reads `delivered (89%)` and `canceled (3%)` |
| C5 | author | see "What survives a type change" below |
| C6 | author | year grain to month grain, `September, 2016` replaces `2016` |
| C7 | author | split by order status adds one legend entry per status |
| C8 | author | a second measure draws a legend of both measure names |
| C9 | author | a new sort is ascending, so `unavailable` leads |
| C9b | author | flipping a seeded sort to descending puts `delivered` first |
| C10 | author | a chart filter drops `delivered` from the chart, and the Query keeps it |
| C11 | author | Line chart over a date draws `2017`, `2018` and a `100` tick |
| C12 | author | a click on a bar opens Drill Down with 53 rows |
| C13 | verify | a card reads `74`, an arrow, `-12.94%`, and draws a sparkline |

### Flows skipped

- **C14** (Funnel, Bubble, Sankey, Map) and **C15** (chart sharing) are out of
  scope. Ticket 13 owns shared views. A Map chart draws to canvas, so no text
  assertion can reach it.

### What survives a chart type change

Read from `charts/chart.ts`, then recorded as C5.

- Bar, Line and Row are axis charts. A switch inside that set keeps the whole
  config, so the new chart draws the same categories and the same value scale.
- A switch that crosses the axis boundary, such as Bar to Donut, resets the
  config. The chart falls back to the "Pick a chart type" empty state.
- The reset is not undone by switching back. Bar to Donut to Bar leaves an empty
  X Axis.
- Filters, sort and limit sit outside the type-specific config. Filters and
  limit survive every switch. Sort is cleared by a boundary crossing, because
  the reset writes a fresh `order_by`. C5 asserts the filter and the limit
  only. The sort clearing is read from the code, not from the browser.

### Fixtures added

None. The tests use `workbookWithQuery` plus `createChart` from
`helpers/insights.ts`.

### Facts the tests depend on

- A Donut legend spells the share out, so the label reads `delivered (89%)`,
  never `delivered`.
- A date x-axis is an echarts time axis, so its labels are `Jul`, `2017` and
  such, not the grain the picker names. The grain shows in the result preview,
  as `September, 2016` or `2016`.
- A Number chart draws plain HTML. Its root is the page's only `@container`.
- A Number chart's sparkline is its own echarts instance, and the only one on
  the page.
- A bar is the one filled `<path>` in the chart. Every other path carries
  `fill="none"`.
- The builder drops the result preview for a Table chart, so a Table chart draws
  the only table on the page.
- A config section heading carries its badge count, so the Filters heading is
  named `Filters 1` once a filter exists.

### Bugs found

1. **A chart config edit made during a refresh is dropped.** Three config picks
   in a row, with no wait between them, lost the third one about one run in
   three. The Table chart flow hit this. A toast read
   `frappe.client.set_value DoesNotExistError` on the failing run. The test now
   asserts on the redrawn table between picks, which closes the window. Worth a
   ticket of its own.
2. **`AGENTS.md` says `order_purchase_timestamp` covers 23 months.** The demo
   data covers 26, from September 2016 to October 2018. No test depends on the
   count.

### Run counts

Every test ran at least five times, in three batches, at one and at three
workers. No test is quarantined. `npx eslint e2e/tests/charts.spec.ts` reports
no errors and two `no-nth-methods` warnings, both `previewRows(page).first()` in
the sort flow, where the first row is what the flow is about.

### Amendment, ticket 17

C9 became two flows. Adding a sort through the interface and flipping its
direction are two edits either side of a result assertion, and ticket 16's
autosave bug drops the second one. C9b seeds the sort, so the flip is the
chart's first unsaved change.

C3, the Table chart flow, now makes its three picks back to back. Bug 1 above is
ticket 16, and `AGENTS.md` carries the rule that works around it.
