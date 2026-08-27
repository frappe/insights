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
into the build. Tickets 01–06 decide and build the
foundation. Ticket 07 builds the harness serially. Tickets 08+ fan out.

**Prototype and grilling tickets were converted to tasks** partway through, at
the user's direction, to get a v1 out. Decisions that would have been grilled are
recorded in the tickets that make them. Override any of them freely.

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

## Open

- [16 — An autosave answer drops every edit made while it was in flight](issues/16-autosave-drops-concurrent-edit.md)
  — a product bug in `frontend/src2/helpers/resource.ts`, behind three symptoms
  two agents found separately; the suite works around it and cannot record it.
- [18 — A chart page saves itself about every 1.5 seconds, forever](issues/18-chart-page-saves-itself-forever.md)
  — an `undefined` granularity makes any chart over a text column permanently
  dirty, so the autosave never stops; that turns ticket 16's one-round-trip
  window into a permanent one, and it is why chart author flows cannot be made
  deterministic. One line fixes both, and that line is already on another
  branch.

## Decisions so far

<!-- one line per resolved ticket -->

- [17 — Make the suite stable enough to gate a merge](issues/17-suite-stability.md)
  — the mass failure is the bench's background job queue crossing
  `max_queued_jobs`, which turns every write into a 503, reproduced by driving
  the queue over the cap; the residual one-a-run flake is tickets 16 and 18, and
  three workers is what holds it down until they land.

- [01 — How other Frappe apps run browser tests in CI](issues/resolved/01-how-frappe-apps-run-browser-tests.md)
  — copy `frappe/wiki`'s recipe; `e2e/helpers/frappe.ts` is reusable verbatim; a
  CI site build costs 2–3 minutes, so a pull-request gate is affordable; Insights
  already had a Playwright suite that `0abeb72f` deleted with the v2 frontend.
- [02 — The flow inventory and its ranking](issues/resolved/02-flow-inventory.md) — 69
  flows across seven areas; the cut is tier A + tier B + C13 + C15, which is 56
  of 69 or 81%; flows split into cheap **verify** flows riding on seeded content
  and slow **author** flows that carry the churn.
- [04 — The fixture dataset](issues/resolved/04-fixture-dataset.md) — the committed
  `insights_demo_data.duckdb` is broken, every join matches zero rows, so the
  seeded sample dashboard renders empty under CI; replaced by a declarative spec
  and a seeded generator, measured at 17 ms, with the binary leaving git.
- [15 — Build the fixture generator](issues/resolved/15-fixture-generator.md) —
  `insights/setup/demo_data/` holds a declarative spec and a seeded generator;
  600 ms for 2000 orders and 4881 line items, all 8 declared foreign keys join,
  and `BrokenFixture` fails the build on a dead join; the sample workbook now
  returns 459 rows instead of 2.
- [05 — Auth and API seeding](issues/resolved/05-auth-and-seeding.md) — a login
  setup project stores state for an admin and a viewer, `frappe.ts` came from
  `frappe/wiki`, and fixtures stack as a Workbook ladder; the redundant CI guard
  on `setup_demo_data` is removed, so ticket 07 needs no out-of-band CI step.
- [06 — The standards doc and the lint config](issues/resolved/06-standards-and-lint.md)
  — `frontend/e2e/AGENTS.md` carries the rules, and `eslint-plugin-playwright`
  enforces 25 of them as errors; the repo's eslint had never run, because a
  trailing comma made `.eslintrc.json` invalid JSON.

## Not yet specified

- **Whether the flow inventory needs a stable id per flow.** If a flow is
  renamed, the generated inventory loses its history. Whether that matters
  depends on what the inventory ends up being read for.
- **Visual regression.** Charts are the churn hotspot and the hardest thing to
  assert in text. Screenshot comparison may be the only way to cover them, but it
  brings its own flakiness, and ticket 01 found that **no Frappe app does it** —
  there is no recipe to copy. Revisit once ticket 07's chart exemplar shows what
  a text assertion can actually reach.
- **Sharding.** `frappe/wiki` and `frappe/frappe` both shard across 4 runners.
  Whether Insights needs that depends on how long the suite grows. The mechanism
  is known, the trigger is not.
- **Whether `factories.py` should be exposed over a test-only endpoint.** Ticket
  05 may show the browser needs the same factories the Python suite uses. Ticket
  01 found gameplan's `ui_test_helpers.py` gating pattern to copy if it does.
- **How far the fixture spec has to stretch.** Tier C holds Funnel, Sankey, Map
  and Bubble charts, and each wants a data shape the tier A and B spec will not
  have. Specifiable once ticket 15 shows what extending the spec actually costs.

## Out of scope

- **The framework Island.** Embedding Insights into another app's page needs a
  second app running and a different harness. Ruled out while charting.
- **Unit tests for `src2` components.** This map is end-to-end only. A component
  test suite is a separate effort with a separate harness.
- **Backend API coverage.** `insights/tests/` already owns it.
- [03 — Confirm the CI floor for Insights](issues/resolved/03-measure-ci-floor.md)
  — a de-risking step that ticket 01 made unnecessary. The Insights-specific
  number arrives free the first time ticket 07's CI job runs, so measuring first
  would build the same workflow twice. Priority is a working v1.
- **Replacing the demo data download.** `insights/setup/demo.py` fetches the
  production demo dataset from a hardcoded Google Drive link, so every new
  install's demo experience rests on one link staying alive. Ticket 15's
  generator could remove that dependency and make demo setup offline and
  instant. It is ruled out here on two grounds: demo data is a first-impression
  surface where synthetic distributions cost something real, and rebuilding it
  is not an end-to-end testing effort. **Ticket 15 keeps the seam open** — the
  generator must run outside a test context — so a later effort can take it up
  without a rewrite.
