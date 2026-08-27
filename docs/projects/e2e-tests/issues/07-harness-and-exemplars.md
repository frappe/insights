# 07 — The harness and two exemplar tests

Type: task
Status: resolved
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

## Answer

The harness runs. Both exemplars pass, and a chart flow asserts in plain text
with no screenshot comparison.

### The chart verdict

**A chart flow can be asserted in text. The visual-regression patch of fog
closes.**

Insights renders echarts in SVG mode. Measured on a rendered Bar chart, the
page holds zero `<canvas>` elements and one echarts root, and every label is a
real `<text>` node:

```
["0","300","600","900","1.2K","1.5K","1.8K",
 "canceled","delivered","shipped","unavailable","invoiced","processing"]
```

So `getByText('delivered')` reaches an axis category, and `getByText('1.8K')`
reaches a value tick. Both are web-first assertions on a locator.

Scope every chart assertion to the chart. echarts writes an
`_echarts_instance_` attribute on the element it renders into, which names the
chart and nothing else:

```ts
const chart = page.locator('[_echarts_instance_]')
await expect(chart.getByText('delivered')).toBeVisible()
```

Unscoped, `getByText('delivered')` matches twice, because the chart builder
prints the same aggregated rows in a preview table under the chart.

Three limits, all measured, all now in `AGENTS.md`:

1. **Category order is not stable between runs.** Two runs of the same flow
   gave `shipped, canceled, unavailable, delivered, …` and
   `canceled, delivered, shipped, unavailable, …`. Assert that a label is
   present, never where it is.
2. **Values are abbreviated.** Turning `Show Data Labels` on adds
   `["53","1.8K","85","16","35","33"]`. The 1,778 delivered orders render as
   `1.8K` in both the tick and the data label. An exact number has to come from
   the preview table below the chart.
3. **Data labels are off by default.** Until a flow toggles them, only ticks
   and category labels are in the DOM.

What was tried and rejected: nothing weaker was needed. `toBeVisible()` on the
chart container was never written, because the axis-label route worked on the
first attempt.

Map charts remain the exception and draw to canvas. C14 in the inventory is the
only flow this verdict does not cover.

### `frontend/playwright.config.ts`

Renamed from `.js` to match `e2e/`, and it imports `storageStatePath` from the
helpers rather than repeating the path.

| Decision | Value | Why |
| --- | --- | --- |
| `testDir` | `./e2e/tests` | The generator stub pointed at `./tests`, which does not exist |
| Projects | `setup` then `chromium` | `chromium` declares `dependencies: ['setup']`, so both roles log in once per run |
| Browsers | chromium only | Firefox and WebKit buy nothing here and triple the CI cost |
| `storageState` | admin, on the `chromium` project | The `page` fixture is the admin. `viewerPage` opens its own context |
| Quarantine | `grepInvert: /@quarantine/` | `E2E_QUARANTINE=1` includes them. Verified: a tagged probe is excluded by default, included with the variable, and reachable with `--grep @quarantine` |
| `retries` | 0 local, 2 in CI | As the ticket asked |
| `fullyParallel` | `true` | Wiki and CRM run `workers: 1` for "Frappe state consistency". Every fixture here seeds its own Workbook and deletes it, so nothing is shared. Five local workers passed 3 full runs and 10 repeats |
| `workers` | 4 in CI | The runner has 4 vCPUs |
| `timeout` | 90 s test, 15 s expect | A first query execution outruns both generator defaults |
| `trace` | `on-first-retry` | Plus `video: retain-on-failure` and `screenshot: only-on-failure` |
| `webServer` | none | Documented assumption instead |

**The documented assumption.** Nothing in the config starts a server. The
command that starts a Frappe site lives in the bench root, which this package
cannot name, and the site build is the slow part that CI has to cache across
steps. CI starts the site in its own step and polls the port, the same shape
`frappe/wiki` and `frappe/crm` use. `E2E_BASE_URL` names the target and
defaults to `http://test.insights.localhost:8000`.

**A vite dev server cannot host this suite.** Under `yarn dev`, `/insights` is
vite's own `index.html`, so `window.csrf_token` is never set and the setup
project fails by design. The suite needs the built entry
(`insights/www/_insights.html`, written by `yarn build`) served by the bench.

### `.github/workflows/playwright.yml`

Replaced. The old file was a nightly cron with zero runs, left from the v2
suite. The new one is named `UI`, runs on `pull_request` and
`workflow_dispatch`, and is the check to require on `develop`.

Shape, following `frappe/wiki`'s `ui-tests.yml` but keeping this repo's own
`server-tests.yml` conventions — Python 3.14, Node 24, `actions/checkout@v6`,
redis from apt rather than service containers:

1. Add `insights.test` to `/etc/hosts`.
2. Cache pip, yarn and `~/.cache/ms-playwright`.
3. `bench init --skip-assets`, `bench get-app`, `bench new-site`,
   `bench install-app insights`, `bench build`.
4. **Build the frontend.** `yarn install --frozen-lockfile && yarn build` in
   `apps/insights/frontend`. `bench build` does not reach the Vue app, and
   `/insights` has no page to serve until this runs.
5. `set-config allow_tests 1` and `set-config host_name`.
6. **Seed the demo Data Source**, explicitly:
   `bench --site insights.test execute insights.setup.setup_wizard.setup_demo_data`
   with `CI: "Yes"`.
7. `bench start`, with `watch:` and `schedule:` dropped from the Procfile, then
   poll `/api/method/ping` until it answers.
8. `npx playwright install --with-deps chromium`, then `npx playwright test`.
9. Upload the HTML report always, and `test-results/` on failure.

**How the demo seeding works, checked rather than assumed.** Ticket 05 removed
the guard in `setup_demo_data`, so the endpoint now runs under CI. One layer
down, `insights/setup/demo.py::use_generated_data()` reads
`frappe.flags.in_test or os.environ.get("CI")` and decides between generating
the deterministic dataset from `demo_data/spec.py` and downloading the
production one from Google Drive.

That environment variable is read in the process that runs the call. Calling
the endpoint from the browser suite would therefore make the answer depend on
whether `bench start` itself was launched under `CI`, and would put a dataset
build inside a test's timeout. The workflow calls it from `bench execute` with
`CI: "Yes"` on that one step instead. `assertDemoData` in `helpers/insights.ts`
stays as the check, and its stale comment about the old guard is corrected.

Verified locally: `bench --site test.insights.localhost execute
insights.setup.setup_wizard.setup_demo_data` resolves and returns `Done 99`.
The same call on a fresh site also creates the "Order Analysis" Workbook.

Not verified: the workflow has never run on GitHub. Every step was taken from
a workflow that does run, but the file itself is unproven.

### The exemplars

Both are author flows, chosen to bracket the difficulty.

**`e2e/tests/query.spec.ts` — Q1, `a user picks a table as a query source and
sees rows`.** Seeds an empty Workbook, then clicks: `Query Builder`, the
`orders demo_data` row, `Confirm`. Asserts a header cell, the deterministic
first row `ORD-00001`, at least one `delivered` cell, and exactly 100 data
rows.

**`e2e/tests/charts.spec.ts` — C1, `a user creates a Bar chart with one
dimension and one measure`.** Seeds a Workbook with a Query over `orders`,
then clicks: the sidebar `+` under Charts, `Bar`, the X Axis column picker,
`order_status`, the Y Axis column picker, `Count of...`, `order_id`. Asserts
inside the echarts root only.

Three CSS locators were needed, each with its reason on the line above:

- `div.mb-1:has(div:text-is("Charts")) button:has(svg.lucide-plus)` — the
  sidebar add buttons are icon-only frappe-ui Buttons with no accessible name,
  and a `new folder` button sits beside the `+`. The lucide icon class is the
  only thing that tells them apart.
- `div.flex.flex-col:has(> button > div > p:text-is("X Axis"))` — X Axis, Y
  Axis and Split Series are collapsible sections holding three buttons all
  named `Select a column`. The section heading is the only discriminator.
- `[_echarts_instance_]` — the chart.

`AGENTS.md` prefers a `:label` edit in `src2` over a CSS locator. That edit was
out of scope for this ticket, so the locators stand. The sidebar `+` is the
one worth changing, because nearly every author flow in tickets 09 to 14 starts
by clicking it.

### Runs

Against `test.insights.localhost` on a bench-served build, five workers.

| Run | Tests | Result | Wall clock |
| --- | --- | --- | --- |
| Full suite, 3 times | 6 each | 18 of 18 passed | 9.8 s, 9.4 s, 9.1 s |
| Exemplars, `--repeat-each=5` | 10 | 10 of 10 passed | 18.4 s |

Zero flakes across 13 executions of each exemplar. Q1 ran 2.7 to 5.0 seconds
and C1 ran 4.1 to 7.4 seconds, so neither is near the 90-second test timeout.

### Corrections to `AGENTS.md`

Four facts in it were wrong or missing, and all six flow tickets read it:

- A workbook sidebar item is a **router link**, not a button. A Query tab is
  `getByRole('link', { name: query.title })`.
- The query editor's page size is **100 rows**, not 20. The footer reads
  `Showing 1–100 of 2,000 rows`.
- Added the sidebar `+` locator, since it has no accessible name.
- Added an "Asserting on a chart" section with the verdict above.

Also added a "Running the suite" section, because the vite trap costs an agent
a full debugging cycle otherwise.

### One thing to fix before tickets 09 to 14 fan out

`feat/e2e-tests` is one commit behind `upstream/develop`, and the missing
commit is `7aa8e6fc`. Without it `insights.api.get_site_info` is declared
GET-only, frappe-ui's `call` posts, and the 403 aborts `session.initialize()`.
The whole app renders blank, so **no browser test can pass on this branch as it
stands**.

The hunk was applied to the working tree to run the verification above, and
reverted afterwards. Merge `upstream/develop` before any agent starts.
