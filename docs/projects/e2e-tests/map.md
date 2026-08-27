# Map: end-to-end tests

Label: `wayfinder:map`

## Destination

A Playwright suite on `develop`, running in CI on every pull request, that covers
80% of a named inventory of user flows. A regression in the core loop — data
source, query, chart, dashboard — fails the merge gate. The inventory is
generated from the test titles, so it cannot drift.

## Notes

Domain: `CONTEXT.md` is the glossary. Use its terms in test names — Workbook,
Query, Operation, Chart, Dashboard, Measure, Dimension.

**This map carries execution.** Wayfinder plans by default. Here the decisions
are few and the volume is in writing flows, so the map runs past the decisions
into the build. Tickets 01–05 decide. Ticket 06 builds the harness serially.
Tickets 07+ fan out.

Skills every session should consult: `/grilling` and `/domain-modeling` for the
decision tickets, `/tdd` for the harness, `/technical-writing` for the standards
doc.

Standing preferences for this effort, settled in the charting session:

- **Layer**: browser through Playwright. The backend already has an API-level
  suite in `insights/tests/` that CI runs on every pull request.
- **Coverage**: 80% of a named flow inventory, not a line-coverage percentage.
- **Baseline**: characterization. Today's behavior is correct by definition. A
  test that disagrees with the code means the test is wrong. File genuine bugs
  as separate tickets, never fix them inside a test pull request.
- **CI is a hard requirement.** A suite that runs only on a laptop is
  documentation, not a gate.
- **Fixtures over Page Objects**, scoped to business actions. A fixture may
  create data, but the test must state what it depends on.
- **Setup through the API, assertions through the browser.** Clicking to build
  fixture data is the main source of slow, flaky suites.
- **Enforced beats written.** Prose the agents read once will drift. Lint holds.

## Decisions so far

<!-- one line per resolved ticket -->

## Not yet specified

- **What the CI site costs.** Building a Frappe site, installing Insights and
  loading a dataset may make the pull-request gate too slow to keep. If it does,
  the fallback shape is unknown — a prebuilt Docker image, a nightly-only run, or
  a smaller fixture. Ticket 02 measures it, and the fallback is only specifiable
  once there is a number.
- **Whether the flow inventory needs a stable id per flow.** If a flow is
  renamed, the generated inventory loses its history. Whether that matters
  depends on what the inventory ends up being read for.
- **Visual regression.** Charts are the churn hotspot and the hardest thing to
  assert in text. Screenshot comparison may be the only way to cover them, but
  it brings its own flakiness. Revisit once ticket 06 shows what a chart
  assertion actually looks like.
- **Whether `factories.py` should be exposed over a test-only endpoint.** Ticket
  04 may show the browser needs the same factories the Python suite uses.
- **How the suite is sharded across CI machines** once it is large enough that
  one runner is too slow.

## Out of scope

- **The framework Island.** Embedding Insights into another app's page needs a
  second app running and a different harness. Ruled out while charting.
- **Unit tests for `src2` components.** This map is end-to-end only. A component
  test suite is a separate effort with a separate harness.
- **Backend API coverage.** `insights/tests/` already owns it.
