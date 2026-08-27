# 13 — Flows: Shared views and templates

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

`frontend/e2e/tests/shared.spec.ts` covers S1, S2 and S3. All three pass. No
flow is skipped, and nothing is quarantined.

| Flow | Title | Kind |
| --- | --- | --- |
| S1 | a logged-out visitor opens a shared dashboard link and sees charts | verify |
| S2 | a logged-out visitor opens a shared chart link | verify |
| S3 | a revoked public link stops working | verify |

S1 and S2 assert the chart content. Each seeded Chart counts orders by status,
so the test reads `delivered`, `shipped` and `canceled` as text nodes inside the
echarts element. S3 publishes, checks the link works, withdraws it, and reopens
the same link.

**What a revoked link does.** The withdrawn Dashboard answers a Guest with a
403. The app's fetch wrapper sees the 403, resets the session, and the router
sends the visitor to the site login page at `/login`. There is no 403 screen and
no error message. The test asserts the URL and the login prompt.

**Fixtures added.**

- `guestPage` in `frontend/e2e/fixtures/index.ts` — a context with an empty
  storage state. `browser.newContext` takes no options from the config, so it
  passes `baseURL` on.
- `publishDashboard`, `unpublishDashboard` and `publishChart` in
  `frontend/e2e/helpers/insights.ts` — `update_access` through
  `insights.api.run_doc_method`, as ticket 05 found.
- `buildChartDataQuery` in the same file. See below.

**The seeding gap `buildChartDataQuery` closes.** A Chart executes a derived
Query held on its `data_query` link. The chart builder compiles the chart config
into that Query's operations and autosaves them. A Chart seeded over REST never
passes through the builder, so its `data_query` holds no operations. A signed-in
viewer never notices, because the browser sends the operations it just compiled.
`insights.api.run_doc_method` reloads the stored document on the public path and
drops the caller's copy, so a published Chart with an empty `data_query` renders
"Pick a chart type and configure options to see the chart here" for a Guest. The
helper writes the operations the builder would have saved. This is a fixture
gap, not a product bug: a real author always opens the builder before
publishing.

**Bugs found.** None. One rough edge is worth a note but is not a defect: a
guest whose link was revoked lands on the login page with no word about what
happened, and the failed execution returns HTTP 500 with `TypeError` rather than
a permission error.

**Runs.** The three tests ran 5 times. All 5 runs passed. One further run failed
in `auth.setup.ts`, which is shared and was in use by other agents at the time.
No shared test failed in that run.
