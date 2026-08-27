# 07 — The harness and two exemplar tests

Type: task
Status: open
Blocked by: 05, 06, 15

## Question

Build the harness, serially, before any agent fans out.

The two exemplar tests are the real specification. Prose will not hold twenty
parallel agents in line; two working tests they can pattern-match will.

Deliver:

- `frontend/playwright.config.js` rewritten for a real base URL and a real
  `webServer`. The current file is an untouched stub with `testDir: './tests'`
  pointing at a directory that does not exist.
- The fixture module from ticket 05.
- `eslint-plugin-playwright` wired into the existing eslint setup.
- The CI job from ticket 03, extended to run the suite and gate pull requests.
- **Two exemplar tests**, chosen to bracket the difficulty: one simple flow with
  a text assertion, one chart flow where the assertion is genuinely hard.

The chart exemplar matters most. Charts are the churn hotspot and the least
assertable surface. If it cannot be asserted in text, say so in the answer — it
graduates the visual-regression patch of fog into a ticket.
