# How Frappe apps run browser tests in CI

Research for ticket 01. Every claim cites a file or a workflow run read on
2026-08-27. Durations come from the GitHub Actions jobs API, not from estimates.

Apps studied: `frappe/frappe`, `frappe/gameplan`, `frappe/crm`, `frappe/wiki`,
`frappe/builder`, `frappe/lms`, `frappe/studio`, `frappe/helpdesk`,
`frappe/insights`.

## frappe/wiki

**Harness.** Playwright. `playwright.config.ts` at the repo root, specs in
`e2e/tests/`. 39 spec files. No earlier harness exists in the tree.

**CI.** `.github/workflows/ui-tests.yml`. The job runs a MariaDB and two Redis
service containers. It installs `frappe-bench` with pip, runs `bench init
--skip-redis-config-generation --skip-assets`, then `bench get-app wiki
$GITHUB_WORKSPACE`, `bench new-site`, `bench --site wiki.test install-app wiki`
and `bench build`. It caches pip, yarn and `~/.cache/ms-playwright`. It starts
the site with `bench start` after commenting out the `watch:` and `schedule:`
lines in the Procfile, then polls `curl` until the port answers.

The job runs as a four-way shard matrix. Each shard builds its own site.

**Measured duration.** Run 33054979951, a pull request on 2026-08-27, took 14
minutes 51 seconds wall clock. Shard 1 steps:

| Step | Seconds |
| --- | --- |
| Initialize containers | 15 |
| Setup Bench | 23 |
| Install Wiki | 106 |
| Start Frappe Server | 3 |
| Install Playwright | 25 |
| Run Playwright Tests | 139 |

Site build costs about 2 minutes 30 seconds per shard. Tests cost about 2
minutes 20 seconds per shard.

**Authentication.** `e2e/tests/auth.setup.ts` is a Playwright setup project. It
posts to `/api/method/login`, checks `frappe.auth.get_logged_user`, loads `/app`
to read `window.frappe.csrf_token`, writes the token to `e2e/.auth/csrf.json`,
and saves `storageState` to `e2e/.auth/user.json`. The `chromium` project
declares `dependencies: ['setup']` and `storageState: authFile`. Login therefore
happens once per run, never through the UI.

**Fixtures.** `e2e/helpers/frappe.ts` wraps the REST API with `createDoc`,
`getDoc`, `deleteDoc`, `getList` and `callMethod`, adding the saved CSRF token as
`X-Frappe-CSRF-Token`. `e2e/helpers/wiki.ts` builds domain fixtures on top, for
example `createTestWikiSpace` and `generateWikiTitle`. Cleanup resolves records
by their test-unique route rather than by the create response, so a timed-out
create is still removed.

**Gate.** Runs on `pull_request` and on push to `develop`. The `develop` branch
has no branch protection, so the check is advisory.

**Flakiness.** `retries: 2` in CI. `fullyParallel: false` and `workers: 1`, with
the comment "Sequential for Frappe state consistency". One `test.skip` in the
suite.

## frappe/crm

**Harness.** Playwright. `playwright.config.ts` at the repo root, 6 specs in
`e2e/tests/`. The config and the helpers are near-identical to Wiki, including
the same comment text, so one recipe was copied between the two repos.

**CI.** `.github/workflows/ui-tests.yml`. Same shape as Wiki, without sharding.
It adds a `Configure Site for UI Tests` step that sets `allow_tests true` and
`host_name`, and creates a dummy default outgoing Email Account through `bench
console` so the email spec can queue mail without SMTP.

**Measured duration.** Run 33055918497 on 2026-08-27 took 5 minutes 5 seconds.
Setup Bench 24 s, Install CRM 162 s, Install Playwright 20 s, Run Playwright
Tests 25 s. Site build is 97 percent of the job.

**Authentication.** Identical to Wiki. `e2e/tests/auth.setup.ts` logs in over
the API and saves `storageState`. It reads the token from `window.csrf_token`
because the CRM SPA injects boot keys onto `window`, and it fails the setup when
the token is missing rather than letting later writes return an opaque 417.

**Fixtures.** `e2e/helpers/crm.ts` has `buildLead`, `seedLead` and
`cleanupE2ERecords`. Records carry a `Date.now()` suffix and an
`e2e-*@example.com` email, and cleanup deletes by that email pattern. Specs seed
through the API and assert through the browser. `e2e/tests/lead.spec.ts` creates
a lead in the UI and then polls `getList` to confirm the record persisted.

**Gate.** The trigger is `push` and `pull_request` on `main-hotfix` only, plus
`workflow_dispatch`. The workflow comment calls it a "Heavy gate" on the staging
lane and says "Develop stays on the fast lane". Pull requests to `develop` do
not run it.

**Flakiness.** `retries: 2` in CI, `workers: 1`, `fullyParallel: false`. No
issues in the repo mention flakiness.

## frappe/gameplan

**Harness.** Cypress. 39 specs under `frontend/cypress/e2e/`, grouped by feature
folder. `TEST_SUITE_PLAN.md` records 33 specs and 78 tests at the last
measurement. This is the largest and most deliberately built suite in the set.

**CI.** `.github/workflows/ui-test.yml`. It runs `.github/helper/install.sh`,
which builds the bench and the site, with `GAMEPLAN_COVERAGE=1` so the frontend
bundle is instrumented. It then runs `cypress-io/github-action@v6`.

**Measured duration.** Run 33012756991 on 2026-08-26 took 13 minutes 34 seconds.
Install Dependencies 136 s, UI Tests 617 s. Tests dominate, unlike every other
app here.

**Authentication.** `frontend/cypress/support/commands.ts` defines `cy.login` as
a `cy.request` POST to `/api/method/login`.
`frontend/cypress/support/personas.ts` defines five seeded personas and
`cy.loginAs(persona)`. `cy.switchUser` handles mid-test persona changes: it
unloads the page to abort in-flight requests, clears cookies, logs in, then
waits for `frappe.auth.get_logged_user` to name the new user. The comment
explains the cause — Frappe re-sets the `sid` cookie on every response, so a
late reply from the old page hands the previous session back.

**Fixtures.** A dedicated backend seed API, `gameplan/ui_test_helpers.py`.
`resetData(scenario)` in `frontend/cypress/support/seed.ts` calls
`gameplan.ui_test_helpers.reset`, which deletes every Gameplan row, resets the
persona users, and builds one of six named scenarios. It returns the ids of the
records it made. The endpoint sits behind three gates: Frappe's own
`whitelist_for_tests`, an `enable_ui_tests` site config key read through `cint`,
and a System Manager role check. A Node task proves the responding site names
itself before the wipe runs, because the reset is destructive and host aliasing
can point a URL at the wrong site.

**Gate.** Runs on `pull_request` and on push to `main` and `develop`. `develop`
has no branch protection, so it is advisory. Results post as a sticky pull
request comment; `ui-test-report.yml` handles fork pull requests through
`workflow_run`, because a fork's token is read-only.

**Flakiness.** This repo measures it. `retries.runMode: 0` on purpose —
`TESTING.md` says a journey that passes only on a later attempt cannot report
green. `nightly-repeat.yml` runs the whole suite five times serially every night
and attributes failures to iteration and spec. Of the 15 nightly runs from
2026-08-12 to 2026-08-26, 6 failed. So roughly 40 percent of nights contain at
least one failing iteration out of five, while the pull request lane stays
green. Nightly wall clock is about 43 minutes.

`TESTING.md` also records the conventions that keep flakiness down: no bare
`cy.wait(ms)`, wait on an intercept alias instead; query by role and aria first,
`data-testid` only as an escape hatch; one happy path per feature, with
permission matrices and edge cases pushed down to the backend suite. Sharding
was considered and deferred, because six minutes of test time did not justify
the coordination cost.

## frappe/frappe

**Harness.** Cypress. 79 spec files in `cypress/integration/`. `cypress.config.js`
is at the repo root.

**CI.** `.github/workflows/ui-tests.yml`. A `checkrun` job runs
`.github/helper/roulette.py`, which decides whether the suite runs at all for
this pull request. The test job uses a shared composite action,
`./.github/actions/setup`, then runs `bench --site test_site run-ui-tests
frappe --headless --browser <chrome>`. The command lives in
`frappe/commands/testing.py`. The run is split four ways using `cypress-split`,
driven by `SPLIT` and `SPLIT_INDEX`.

**Measured duration.** Run 33061601343 on 2026-08-27 took 11 minutes 49 seconds
wall clock. One shard: Environment Setup 94 s, Site Setup 5 s, Run Tests 430 s.
Shards took 9.5 to 10.6 minutes each.

**Authentication.** `cypress/support/commands.js` defines `cy.login`, which
posts to `/api/method/login`. It also ships a full domain command set:
`cy.call`, `cy.insert_doc`, `cy.update_doc`, `cy.get_list`, `cy.remove_doc`,
`cy.fill_field`, `cy.switch_to_user`, `cy.add_role`. `testIsolation: false`, so
the session survives across tests in a spec.

**Fixtures.** Two sources. `bench --site test_site execute
frappe.tests.ui_test_helpers.create_test_user` seeds the user in CI, and
`frappe/tests/ui_test_helpers.py` exposes seed endpoints such as
`create_if_not_exists` and `create_todo_records`, each decorated with
`whitelist_for_tests`. That decorator, in `frappe/tests/utils/__init__.py`,
allows the call only when `frappe.in_test`, or a dev server has `allow_tests`
set, or `CI` is in the environment. Static doctype fixtures live in
`cypress/fixtures/`.

**Gate.** This is the only repo in the set where the browser suite is a required
check. Branch protection on `develop` requires `Pre-Commit`, `Server Success`
and `UI Success`. `UI Success` is an aggregator job that fails when any shard
fails.

**Flakiness.** The worst record in the set. `retries.runMode: 1`.
`defaultCommandTimeout` is 20000 ms. Three specs are permanently in
`excludeSpecPattern`: `workspace.js`, `workspace_blocks.js` and
`customize_form.js`. Issue #22843, "most flaky ui test", is still open and lists
named offenders. A repo search for "flaky" in issue titles returns 79 results.

## frappe/builder

**Harness.** Cypress, in `frontend/cypress/`. The whole suite is one spec,
`landing.cy.js`, which logs in and visits `builder/home`. It is a smoke check,
not a suite.

**CI.** `.github/workflows/ui-tests.yml`. Three Redis services and MariaDB,
`bench init`, `bench get-app`, `bench new-site`, `bench install-app`, then
`bench --site builder.test execute frappe.utils.install.complete_setup_wizard`
and `frappe.tests.ui_test_helpers.create_test_user`. Tests run with `yarn test`
from `frontend/`.

**Measured duration.** Run 33053090751 on 2026-08-27 took 3 minutes 49 seconds.
Setup 56 s, Install 87 s, Site Setup 5 s, UI Tests 22 s.

**Authentication.** `frontend/cypress/support/commands.js` defines `cy.login` as
a POST to `/api/method/login`, with the password taken from
`Cypress.config("adminPassword")`.

**Fixtures.** None beyond the framework's `create_test_user`.

**Gate.** Runs on every `pull_request` and on push to `master`. Branch
protection on `develop` lists no required contexts.

**Flakiness.** `retries.runMode: 2`. Nothing recorded, which is expected for a
one-test suite.

## frappe/lms

**Harness.** Cypress. Two specs, `cypress/e2e/batch_creation.cy.js` and
`course_creation.cy.js`.

**CI.** `.github/workflows/ui-tests.yml`. It reuses the framework runner: `bench
--site lms.test run-ui-tests lms --headless`, split across a two-container
matrix through `SPLIT` and `SPLIT_INDEX`. Site setup runs
`complete_setup_wizard`, `frappe.tests.ui_test_helpers.create_test_user`, `bench
set-password`, and one app-specific call, `lms.lms.utils.persona_captured`.

**Measured duration.** Run 32901737558 on 2026-08-25 took 5 minutes 55 seconds
for the slower container.

**Gate.** Runs on `pull_request` and on push to `main`, `develop` and
`main-hotfix`. Not a required check.

## frappe/studio

**Harness.** Cypress, but component tests only. `.github/workflows/ui-tests.yml`
runs `yarn test:cypress` in `frontend/`. It calls `bench init` and `bench
get-app` for the Python dependencies, but it never creates a site and never
starts a server.

**Measured duration.** Run 33057588543 on 2026-08-27 took 3 minutes 21 seconds.

**Relevance.** Studio is the counter-example: it gets a browser-based check on
every pull request for under four minutes by not needing a site. That is the
cheapest lane available, and it buys component coverage rather than flow
coverage.

## frappe/helpdesk

**No browser tests.** A code search for "cypress" and for "playwright" in
`frappe/helpdesk` returns zero results. The workflow list is `build.yml`,
`generate-pot-file.yml`, `lint.yml`, `on_release.yml`, `release.yml` and
`server-tests.yml`. No abandoned harness is visible in the tree, and the only
matching issue is #1522, "Add tests for basic operations", closed.

## frappe/insights — the abandoned local recipe

Insights already tried this once.

- `.github/workflows/playwright.yml` exists on `develop`. Its state in the
  Actions API is `disabled_manually`, and it has no recorded runs. Its only
  trigger is a nightly cron. Its last two commits are `1f021da1 ci: run test
  once a day` and `7bd11d12 build: require Node >=20.19`.
- `frontend/playwright.config.js` is the unmodified `create-playwright`
  scaffold. It still targets `./tests`, still lists chromium, firefox and
  webkit, and still has the commented-out `webServer` block.
- `frontend/tests/` no longer exists. The specs were added in `f2b46bec`
  (2023-04-02) and `3d6fcc91` (2023-04-04), and were deleted by `0abeb72f`
  (2026-03-14, "refactor!: remove v2 code").

So the tests were tied to the v2 frontend and died with it. The workflow was
switched from per-pull-request to nightly before it was disabled, which is the
usual sign that it was slow or red rather than useful.

## What Insights should copy

### (a) Directly reusable recipe

Take Wiki's workflow and Wiki's Playwright layout. It is the only Playwright
recipe in the org that is sharded, current, and backed by a real suite.

1. **Workflow.** Copy `frappe/wiki/.github/workflows/ui-tests.yml`. Keep the
   MariaDB and Redis services, the pip, yarn and `~/.cache/ms-playwright`
   caches, `bench init --skip-redis-config-generation --skip-assets`, the
   Procfile edit that drops `watch:` and `schedule:`, and the `curl` poll before
   the tests start.
2. **Authentication.** Copy the setup-project pattern from
   `e2e/tests/auth.setup.ts`. One API login per run, `storageState` saved to a
   gitignored file, the CSRF token saved beside it, and a hard failure when the
   token is missing. Never log in through the UI.
3. **API helpers.** Copy `e2e/helpers/frappe.ts` as is. It is app-agnostic:
   `createDoc`, `getDoc`, `deleteDoc`, `getList`, `callMethod`, with the CSRF
   header attached. Then write the Insights equivalent of `e2e/helpers/wiki.ts`
   over it.
4. **Config.** `fullyParallel: false`, `workers: 1`, `retries: 2` in CI,
   `trace: 'on-first-retry'`, `video: 'retain-on-failure'`. Both Wiki and CRM
   settled on the same values and both say the reason is Frappe session and
   state consistency.
5. **Sharding.** Take Wiki's blob-report shards plus a `merge-reports` job. Do
   not take it on day one. Gameplan measured that sharding a six-minute suite
   was not worth the coordination cost.
6. **Unique fixture names and pattern cleanup.** Copy CRM's `uniqueSuffix` plus
   `cleanupE2ERecords` filtered on an `e2e-*` marker, and Wiki's habit of
   resolving cleanup by a test-unique field rather than by the create response.
7. **Gameplan's conventions, verbatim.** No bare `cy.wait`/`waitForTimeout`.
   Roles and aria first, `data-testid` as an escape hatch. One happy path per
   flow, with edge cases and permission matrices pushed down to the Python
   suite. These are written in `frappe/gameplan/TESTING.md`.

Expected cost, from the measurements above: about 2 minutes 30 seconds to build
the site, plus test time. CRM's whole job is 5 minutes. Wiki's is 15 minutes
across four shards. Neither is too slow for a pull request gate.

### (b) Insights-specific gaps

- **The data source.** No app studied needs one. Every other app's fixtures are
  framework documents made over REST. An Insights query needs a source and a
  table with rows behind it, so the first decision the copied recipe does not
  answer is where the CI site's data comes from. A workbook template from
  `insights/workbook_templates/` is the closest shipped candidate.
- **The DuckDB data store.** The store is a file the warehouse opens and locks.
  No sibling app has a second storage engine in its CI site, so nothing here
  says whether a browser suite can drive an import and then read it back inside
  one job.
- **Charts.** Every suite studied asserts on text and roles. None does
  screenshot comparison. There is no recipe in the org for asserting on a
  rendered chart, so the map's open question about visual regression gets no
  answer from this research.
- **A seed endpoint.** Gameplan's `ui_test_helpers.py` is the closest match to
  the map's open question about exposing `factories.py` over a test-only
  endpoint. Copy its gating exactly if that path is taken: Frappe's
  `whitelist_for_tests`, plus an app-level config key read through `cint`, plus
  a System Manager check, plus a site-identity probe before any destructive
  call. The endpoint deletes real data when it is pointed at the wrong site.
- **Existing dead scaffold.** `frontend/playwright.config.js` and
  `.github/workflows/playwright.yml` must be replaced, not extended. The config
  is the generator default and its `testDir` points at a directory that no
  longer exists.

### (c) Recipes tried and abandoned elsewhere, and why

- **Insights' own 2023 Playwright suite.** Died with the v2 frontend in
  `0abeb72f`. Before that it had already been moved to a nightly cron and then
  disabled. Lesson: a suite bound to the frontend it tests does not survive a
  rewrite, and a suite moved to nightly is on its way to being switched off.
- **CRM's develop gate.** CRM has a working Playwright suite that finishes in
  five minutes, and still restricts it to the `main-hotfix` lane. The workflow
  comment states the choice: "Develop stays on the fast lane." So a cheap suite
  is not automatically a pull-request gate; someone decided the feedback was not
  worth the minutes.
- **Cypress Cloud recording in Gameplan.** Replaced by JUnit XML plus a sticky
  pull request comment built by `.github/scripts/junit_to_markdown.py`. Frappe
  still records to Cypress Cloud with a key committed in `ui-tests.yml`.
- **Cypress run-mode retries in Gameplan.** Removed on purpose
  (`retries.runMode: 0`, decision 26 in `TEST_SUITE_PLAN.md`). The reasoning is
  that a retry hides a flake and reports green. The replacement is the nightly
  five-times-serially lane, which surfaces the flake instead of masking it. Note
  the trade: Wiki, CRM, Builder and Frappe all keep retries, and Gameplan's
  nightly numbers show what those retries are hiding — 6 failing nights out of
  15.
- **Skipping specs to stay green.** Frappe permanently excludes three specs in
  `cypress.config.js` and has an open flaky-test issue from 2023. Gameplan
  reacted to the same pressure by making `SKIP_REALTIME_E2E` throw when `CI` is
  set, so muting a spec reddens the run rather than quietly deleting coverage.
- **A two-browser realtime spec in Gameplan.** Rejected. `TESTING.md` says
  Cypress has no native multi-session support, so it would need `cy.session`
  juggling or an iframe and would be the most flake-prone spec in the suite. The
  shipped version keeps one browser watching while a server-side session makes
  the change, through a Node-side `requestAsUser` task.
- **A prebuilt Docker image.** Nobody in the set uses one for browser tests.
  Every app builds the site from scratch in the job. At roughly 2 to 3 minutes
  that is not the bottleneck, so the map's Docker-image fallback is not needed
  on the evidence here.
