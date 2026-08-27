# 01 — How other Frappe apps run browser tests in CI

Type: research
Status: resolved

## Question

Insights is not the first Frappe app to want browser tests. Several sibling apps
already run them in GitHub Actions against a real site.

Find out, for `frappe/helpdesk`, `frappe/crm`, `frappe/gameplan`,
`frappe/builder`, and `frappe/frappe` itself:

- Which harness each uses, and whether any moved between harnesses.
- How the CI workflow builds the site, and how long that takes.
- How tests authenticate, and whether they seed data through the API.
- What the fixture data is, and where it comes from.
- Whether the suite gates pull requests or only runs nightly.
- Any recorded flakiness or maintenance complaint.

The point is to copy a working recipe rather than derive one. Report what is
directly reusable, what is Insights-specific, and any recipe that was tried and
abandoned.

## Answer

Findings: [research/frappe-app-browser-tests.md](../../research/frappe-app-browser-tests.md).
Nine apps read, with durations pulled from the Actions jobs API on 2026-08-27.

**Copy `frappe/wiki`.** It is the only sharded, current Playwright suite in the
org — 39 specs, `.github/workflows/ui-tests.yml`, `playwright.config.ts`, and
`e2e/{tests,helpers,pages}/`. `frappe/crm` is the same recipe, unsharded.

**Auth is settled org-wide, and it matches what this map already decided.** A
Playwright setup project posts to `/api/method/login`, saves `storageState` and
the CSRF token under `e2e/.auth/`, and every other project depends on it. No app
logs in through the UI.

**`e2e/helpers/frappe.ts` is copyable verbatim** — `createDoc`, `getDoc`,
`deleteDoc`, `getList`, `callMethod` over REST with the CSRF header. It is
app-agnostic. Ticket 05 should start from it rather than from a blank file.

**The CI-cost worry was wrong.** A site build runs 2–3 minutes. No app uses a
prebuilt image. Measured totals: crm 5m05s, builder 3m49s, lms 5m55s, frappe
11m49s across 4 shards, gameplan 13m34s, wiki 14m51s across 4 shards. A
pull-request gate is affordable.

**Almost nobody gates merges.** Only `frappe/frappe` requires its `UI Success`
check on `develop`. CRM keeps its 5-minute suite advisory on purpose. This map
still chooses to gate, but it is choosing against the org norm, not with it.

**Flakiness is real and measured.** Gameplan runs a nightly lane five times over
and failed 6 of 15 nights while its pull-request lane stayed green. `frappe` has
79 flaky-titled issues and 3 permanently excluded specs. Ticket 06's quarantine
policy is not theoretical.

**Insights already tried this and the attempt is still in the repo.**
`.github/workflows/playwright.yml` is a nightly job, `disabled_manually`, zero
runs. `frontend/playwright.config.js` is the untouched generator scaffold. A real
suite once existed — `login.spec.js`, `setup-wizard.spec.js`,
`dashboard_page.spec.js`, `query_builder.spec.js` — and `0abeb72f refactor!:
remove v2 code` deleted it with the v2 frontend. It died with its subject, not
from neglect. Ticket 07 replaces these files rather than extending them.

**Copy gameplan's `ui_test_helpers.py` gating** if ticket 05 exposes
`factories.py`: `whitelist_for_tests`, a `cint` config key, a System Manager
check, and a site-identity probe before anything destructive runs.

**Three gaps no sibling app answers**: the data source and table fixture, running
the DuckDB store inside one CI job, and chart assertions. No app in the org does
screenshot comparison, so the visual-regression fog has no external precedent to
lean on.
