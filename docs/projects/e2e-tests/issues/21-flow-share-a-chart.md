# 21 — Nobody covers sharing a chart from the builder

Type: task
Status: open
Blocked by: 08

## Question

Cover C15, "a user shares a chart and opens the public link". It fell between
two tickets and neither picked it up.

Ticket 02 pulled C15 out of tier C and into the 80% cut, because a break there
is visible to people outside the org. Ticket 10 then skipped it and pointed at
ticket 13. Ticket 13 covered the guest half only: its shared chart flow publishes
over REST with `publishChart`, so no test ever clicks Share on a chart.

The gap is the authoring half. A user opens a Chart, presses Share, turns the
public link on, and the link works.

`dashboard.spec.ts` already holds the same flow for a Dashboard, in "a user
shares a dashboard and opens the public link". Copy its shape. Both routes end
in `update_access`, so the chart flow should differ only in the page it opens
and the control it presses.

Write it in `e2e/tests/charts.spec.ts`, beside the other chart flows. Run
`yarn flows` and commit `e2e/FLOWS.md` with it.
