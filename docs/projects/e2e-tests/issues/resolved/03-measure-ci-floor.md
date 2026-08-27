# 03 — Confirm the CI floor for Insights

Type: task
Status: resolved
Blocked by: 01

## Question

Ticket 01 measured sibling apps: a Frappe site build costs 2–3 minutes, and full
browser-test jobs run 4–15 minutes. A pull-request gate is affordable. That
settles the viability question this ticket originally carried.

What remains is the Insights-specific delta. Insights carries two costs no
sibling has: a DuckDB data store inside the CI job, and a heavier frontend build.

Stand up `frappe/wiki`'s workflow shape against Insights and measure:

- Site build and Insights install.
- Frontend build (`yarn build`), which no sibling's number covers.
- Demo data setup with `CI=1`, which copies the tracked DuckDB file and syncs
  tables.
- One smoke test that loads the app and asserts the login page renders.

Report each stage separately. Replace `.github/workflows/playwright.yml` — it is
a `disabled_manually` nightly job with zero runs, left from the deleted v2 suite.

The answer records the numbers and the workflow file, not a recommendation.

## Out of scope

Dropped. This ticket was a de-risking step: find out whether a CI browser-test
job is affordable before building on the assumption that it is.

Ticket 01 removed the risk with measured numbers from nine sibling apps. A
Frappe site build costs 2–3 minutes, full jobs run 4–15 minutes, and no app
needs a prebuilt image. There is nothing left to de-risk.

The Insights-specific number — the DuckDB store and the frontend build — still
matters, but it arrives free the first time ticket 07's CI job runs. Measuring it
first would build the same workflow twice to learn it twice.

Priority is a working v1.
