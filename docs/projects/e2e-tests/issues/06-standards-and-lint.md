# 06 — The standards doc and the lint config

Type: grilling
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

Open: the length of that quarantine window, the naming convention for tests and
files, what a flow test may assert (and what belongs in the Python suite
instead), and which lint rules are errors versus warnings.
