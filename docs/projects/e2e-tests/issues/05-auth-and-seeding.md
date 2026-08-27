# 05 — Auth and API seeding

Type: task
Status: resolved
Blocked by: 04

## Question

Build the auth and seeding layer the suite sits on.

This was a prototype ticket. It is now a task: the decisions below are made, and
what remains is to build them.

**Copy `frappe/wiki`'s `e2e/helpers/frappe.ts`.** Ticket 01 found it reusable
verbatim — `createDoc`, `getDoc`, `deleteDoc`, `getList`, `callMethod` over REST
with the CSRF header. Start from it, do not write a new one.

**No test-only endpoint.** `insights/tests/factories.py` cannot be reached from
Playwright, and wrapping it in a whitelisted endpoint would ship a seeding
surface into production code. Gameplan needed a gating pattern for exactly that
risk. Plain REST against `insights/api/` avoids the surface entirely.

**Auth**: a Playwright setup project posts to `/api/method/login`, saves
`storageState` and the CSRF token, and every other project depends on it. Two
roles get a stored state — an admin and a viewer. Ticket 14 needs the viewer.

**Layout**, following wiki:

```
frontend/e2e/
├── .auth/            # gitignored
├── helpers/
├── fixtures/
└── tests/
```

Build fixtures scoped to business actions, not Playwright wrappers — a fixture
that gives a test a workbook with one query over the demo data source, and one
that gives a saved chart. A fixture may create data, but a test must state what
it depends on.

Ticket 07 rewrites `playwright.config.js` to point at this layout. This ticket
establishes it.

## Answer

Built under `frontend/e2e/`. The layout is the one this ticket named, plus a
`tsconfig.json` for the folder and a `seeding.spec.ts` that checks the layer
over REST. `.gitignore` now holds `frontend/e2e/.auth/`.

### Copied versus written

**Copied from `frappe/wiki`** — `helpers/frappe.ts`. The request bodies, the
error text and the `limit_page_length` comment are wiki's. Two changes:

- The client is bound to a CSRF token instead of reading one global file. A
  token belongs to one session, and this suite holds two.
- A missing token throws at construction. Frappe answers a write with no header
  with an opaque 417, so every seeding call would otherwise fail blank.

Wiki's `auth.setup.ts` shape is kept: log in over `/api/method/login`, confirm
the session is not Guest, load a page to mint the CSRF token, save
`storageState`. One change of substance — wiki reads the token from `/app`, and
an Insights viewer is a Website User with no desk access. The token is read from
`/insights` instead, where the app's page renderer writes it to
`window.csrf_token`.

**Written here** — `helpers/auth.ts`, `helpers/users.ts`, `helpers/insights.ts`
and `fixtures/index.ts`.

### The fixtures

`fixtures/index.ts` extends `test`. Every fixture is lazy, so a test seeds only
what it names.

| Fixture | What it gives |
| --- | --- |
| `adminApi` | REST as the admin |
| `viewerApi` | REST as an Insights User with no admin rights |
| `viewerPage` | A browser page signed in as the viewer |
| `demoDataSource` | The demo Data Source, checked to exist and to be synced |
| `workbook` | An empty Workbook, deleted after the test |
| `workbookWithQuery` | That Workbook, plus one Query over `demo_data.orders` |
| `workbookWithChart` | Plus a saved Bar Chart counting orders by status |
| `workbookWithDashboard` | Plus a Dashboard holding that Chart |

The Workbook rungs stack, so a test that asks for a Chart gets one Workbook and
one teardown. `Insights Workbook.on_trash` cascades to queries, charts,
dashboards and folders, so a single delete clears a fixture.

The seeding functions in `helpers/insights.ts` are exported on their own. A test
that needs content owned by the viewer, or two Workbooks, calls them directly
rather than reaching for a new fixture.

`demoDataSource` is what makes the data dependency visible. A test that reads
demo rows names it, and the Data Source is checked before the test body runs.

### Seeding gaps

**The demo Data Source cannot be seeded over REST.**
`insights.setup.setup_wizard.setup_demo_data` returns without doing anything
when `CI` is set or under `frappe.flags.in_test`. Its tables and table links
come from `DemoDataFactory`, which no whitelisted method reaches under CI. The
site build must create them — a `bench execute`, or ticket 15's generator.
Ticket 07 owns that CI step. `assertDemoData` fails with a named message rather
than letting a chart assertion fail on empty data.

**Publishing a Chart or a Dashboard is not a REST write.** `is_public` and
`permission_user` are permlevel 1 fields. `update_access` is the only way in, so
tickets 13 and 14 must publish through `callMethod`, not `updateDoc`.

No test-only endpoint was added.

### Not verified

There is no site build in this worktree, so nothing ran against a server.
Unverified: the login posts, `window.csrf_token` on `/insights` (read from
`_insights.py` and the built `_insights.html`, never observed), viewer creation
with the permlevel 1 `roles` and `user_type` fields over REST, whether the
Workbook, Query, Chart and Dashboard payloads are accepted, the cascade delete,
and whether the seeded Chart config is the shape the UI renders. The config
mirrors `insights/setup/sample_workbook.json`.

Verified: `tsc` passes over `frontend/e2e/`, prettier is clean, and
`playwright test --list` loads all four tests, which proves the imports and the
fixture wiring resolve at run time.

`@types/node` was missing from `frontend/package.json` and is now added. It is
not installed in this worktree — the type check borrowed the copy under
`~/frappe/frappe-ui/node_modules`. A `yarn install` is needed before CI can
type-check the suite.

**Local mirrors, not `src2/types`.** Typing the seed payloads from
`src2/types/query.types` pulls in `helpers/constants.ts`, then Vue, then the
whole frappe-ui source tree, and the type check fails on hundreds of unrelated
`.vue` imports. `helpers/insights.ts` declares the few shapes it needs instead.
The suite's contract is the REST payload, not the Vue app's types.

### Follow-up: the demo Data Source gap is closed

This answer recorded that the demo Data Source cannot be seeded over REST,
because `insights/setup/setup_wizard.py::setup_demo_data` returned early when
`frappe.flags.in_test` or `CI` was set.

That guard is removed. It duplicated a guard that already sits one layer down —
`DemoDataFactory.download_demo_data` returns early under the same condition, so
the Google Drive download the endpoint guard protected against was already
prevented. The duplicate bought nothing and blocked the browser suite.

Two consequences. Ticket 07 needs **no out-of-band CI step**: Playwright's setup
project calls the real endpoint. And the two UI callers —
`GeneralSettings.vue` and `DemoDataBanner.vue` — stop silently doing nothing
under CI, so that flow becomes testable at all.

Safe to remove: no backend test calls the endpoint. `insights/setup/test_demo_setup.py`
drives `DemoDataFactory().run()` directly.
