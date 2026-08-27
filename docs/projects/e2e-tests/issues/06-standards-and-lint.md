# 06 — The standards doc and the lint config

Type: task
Status: open
Blocked by: 05

## Question

What rules do the parallel agents follow, and what enforces them?

The doc is `frontend/tests/AGENTS.md`. The enforcer is
`eslint-plugin-playwright`. Prose alone drifts, because each agent reads it once.

Already settled and needing only to be written down:

- `getByRole` first, then `getByLabel`, `getByText`, `getByTestId`. Raw CSS and
  XPath need a reason.
- Web-first assertions. No hard waits.
- Fixtures scoped to business actions, not Playwright wrappers. A fixture may
  create data, but the test must state what it depends on.
- Characterization baseline. A test that disagrees with the code is wrong. File
  the bug, do not fix it in the test pull request.
- Flaky tests are quarantined, excluded from the merge gate, then fixed or
  deleted inside a fixed window.

The remaining calls are made here, not grilled, to keep v1 moving:

- **Quarantine window: 7 days.** A quarantined test is fixed or deleted inside a
  week. Gameplan's nightly lane failed 6 of 15 nights while its pull-request lane
  stayed green, so a stale quarantine list is the realistic failure.
- **Naming**: one file per area, `<area>.spec.ts`. A test title is the flow
  sentence from the inventory, in product language, because ticket 08 generates
  the inventory from these titles.
- **What a flow test may assert**: what a user can see. Rendered text, row
  counts, chart labels, visible state. A test that reaches for a document field
  or a SQL string belongs in `insights/tests/`.
- **Lint**: every `eslint-plugin-playwright` rule that catches a correctness
  problem is an error — no conditionals in tests, no hard waits, no `test.only`,
  no missing awaits. Style rules stay warnings.
