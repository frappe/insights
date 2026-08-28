# Writing end-to-end tests for Insights

Read this once, then write your area's tests. Six agents write in parallel from
this file, so every rule here is a rule, not a suggestion. Where the rule leaves
you a choice, take the option this file shows first.

Scope: browser flows only. The backend has its own suite in `insights/tests/`.

Use the glossary in `CONTEXT.md` for every name you write: Workbook, Query,
Operation, Chart, Dashboard, Measure, Dimension, Data Source, Data Store.

## Layout

```
frontend/e2e/
├── .auth/            login state, gitignored, written by the setup project
├── helpers/          REST client, login, seeding functions
├── fixtures/         the test fixtures you compose from
└── tests/            one spec file per area
```

- `helpers/frappe.ts` — a REST client over `/api/resource` and `/api/method`.
- `helpers/insights.ts` — the seeding functions and the demo constants.
- `helpers/auth.ts` — login, `INSIGHTS_PATH`, the two roles.
- `fixtures/index.ts` — the `test` and `expect` you import.

Import `test` and `expect` from `../fixtures`, never from `@playwright/test`.
The fixtures file re-exports both.

## File and title rules

**One file per area**, named `<area>.spec.ts`. The areas match the inventory:
`query`, `charts`, `dashboard`, `workbook`, `shared`, `data-source`,
`permissions`.

**One top-level `test.describe` per file**, named after the area. Lint enforces
this.

**A test title is the flow sentence, in product language.** The titles are the
inventory of what this suite covers — `npx playwright test --list` prints them.
A title is read by people, so write it for them.

```ts
test.describe('query', () => {
	test('a user adds a filter and the row count falls', async ({ ... }) => {})
})
```

- Write it as a sentence about a user, in the present tense.
- Name the domain object, not the component. "a user adds a summarize operation
  and the grain changes", never "QueryEditor renders".
- No numbers, no ticket ids, no `should`.

## Verify flows and author flows

The demo setup seeds a full Workbook named **Order Analysis**. It holds the
Query "Undelivered Orders", four Charts, and a Dashboard.

| Kind | What it does | When to use it |
| --- | --- | --- |
| **verify** | Opens seeded or fixture-seeded content and checks it renders | The flow is "a thing displays correctly" |
| **author** | Clicks through creating or editing the thing | The flow is "a user builds something" |

Choose by what the flow sentence says. "A dashboard loads with all charts
rendered" is a verify flow. "A user adds a dashboard filter and linked charts
refilter" is an author flow.

A verify flow seeds over REST and asserts in the browser. It is fast and stable,
so prefer it whenever the sentence does not name a click. An author flow is slow
and carries the churn, so keep its clicking to the flow under test. Never click
to build setup data that a fixture or a seeding function can create.

## Fixtures

Every fixture is lazy. A test seeds only what it names in its destructuring.

| Fixture | What it gives |
| --- | --- |
| `adminApi` | REST as the admin |
| `viewerApi` | REST as an Insights User with no admin rights |
| `viewerPage` | A browser page signed in as the viewer |
| `demoDataSource` | The demo Data Source name, checked to exist and be synced |
| `workbook` | An empty Workbook, deleted after the test |
| `workbookWithQuery` | That Workbook plus one Query over `demo_data.orders` |
| `workbookWithChart` | Plus a saved Bar Chart counting orders by status |
| `workbookWithDashboard` | Plus a Dashboard holding that Chart |

The Workbook rungs stack. A test that names `workbookWithChart` gets one
Workbook and one teardown, because `Insights Workbook.on_trash` cascades.

**A test states what it depends on.** The destructured fixture list is that
statement. Four rules follow:

1. Name `demoDataSource` in any test that reads demo rows, even when a Workbook
   fixture already pulls it in. The name is the dependency record.
2. Never seed in `test.beforeAll` for several tests to share. Shared state makes
   the order matter and turns one failure into many.
3. Never depend on a record another test created. Tests run in parallel.
4. **Never write a site-wide setting from a test.** The suite runs fully
   parallel against one site, so the write reaches every worker beside you. The
   setup project owns these. It turns `enable_permissions` on for the whole run,
   which is why the viewer reaches no Data Source and the admin reaches every
   one. The teardown project puts the old value back when the run ends.

Need something the ladder does not give? Call the seeding functions from
`helpers/insights.ts` directly with `adminApi` or `viewerApi`. Do not add a
fixture for a single test.

```ts
import { createQuery, createWorkbook, deleteWorkbook } from '../helpers/insights'

test('a user unions two queries', async ({ page, adminApi, demoDataSource }) => {
	const book = await createWorkbook(adminApi)
	await createQuery(adminApi, {
		workbook: book.name,
		table: 'orders',
		dataSource: demoDataSource,
	})
	await createQuery(adminApi, {
		workbook: book.name,
		table: 'orderitems',
		dataSource: demoDataSource,
	})
	// ... the flow, then:
	await deleteWorkbook(adminApi, book.name)
})
```

Every seeded title carries the `e2e` prefix through `uniqueTitle`, so a stray
record is findable. Keep using it.

**Publishing is not a REST write.** `is_public` and `permission_user` sit at
permlevel 1. Use `adminApi.callMethod('...update_access', ...)`, not
`updateDoc`.

## Navigation

Build every URL from `INSIGHTS_PATH` in `helpers/auth.ts`.

| Screen | Path |
| --- | --- |
| Workbook list | `${INSIGHTS_PATH}/workbook` |
| Workbook query tab | `${INSIGHTS_PATH}/workbook/<workbook>/query/<query>` |
| Workbook chart tab | `${INSIGHTS_PATH}/workbook/<workbook>/chart/<chart>` |
| Workbook dashboard tab | `${INSIGHTS_PATH}/workbook/<workbook>/dashboard/<dashboard>` |
| Dashboard list | `${INSIGHTS_PATH}/dashboards` |
| Data Source tables | `${INSIGHTS_PATH}/data-source/<name>` |
| Shared dashboard | `${INSIGHTS_PATH}/shared/dashboard/<name>` |

The tab routes accept either the document name or the tab index. Pass the
document name a fixture gave you.

After `page.goto`, assert on a visible element. Never wait for a load state, and
never call `waitForSelector`. A web-first assertion already retries.

## Picking a locator

Try in this order. Stop at the first that works.

1. `getByRole` — `getByRole('button', { name: 'New Workbook' })`
2. `getByLabel` / `getByPlaceholder` — `getByPlaceholder('Search by title')`
3. `getByText` — for rendered content, not for controls
4. `getByTestId` — see below, the app has none yet

A raw CSS locator needs a comment on the line above stating why the ladder
failed:

```ts
// locator: the results footer has no role and no stable text until a count loads
const footer = page.locator('.tnum').first()
```

XPath is banned outright.

### What this app gives you

- **frappe-ui `Button` renders `<button aria-label="{label}">`.** Any button
  written as `<Button :label="__('New Workbook')" />` is
  `getByRole('button', { name: 'New Workbook' })`.
- **A frappe-ui `Button` drops a fallthrough `:aria-label`.** Its render sets
  `'aria-label': props.label` after it spreads the other attributes. Your
  `:aria-label` is overwritten by `undefined` and never reaches the DOM. Use
  `:label` on a frappe-ui `Button`. Use `:aria-label` only on a plain `<button>`.
- **`:label` on an icon-only Button adds no visible text.** The render picks
  `slots.default?.() ?? props.label`, so a default slot wins. An icon in the
  slot keeps the button icon-only and only the accessible name changes.
- **Icon-only buttons often pass no `label`**, so they have no accessible name.
  Examples are the export and alert buttons in the results footer and the `+` in
  the tab bar. Prefer adding `:label="__('Export')"` to that Button in
  `frontend/src2/` over writing a CSS locator. It adds an accessible name and
  changes no behavior. List any such edit in your pull request.
- **`src2` ships zero `data-testid` attributes.** `getByTestId` works only after
  you add one. Add one only when the ladder and the `:label` route both fail.
- **Labels pass through `__()`.** The test site runs in English, so the source
  string is the rendered string. This app defines its own `__` in
  `frontend/src2/translation.ts`. It takes positional arguments, not an array,
  so `__('Add {0}', section.title)` is correct.
- **A workbook sidebar item is a router link carrying the title.** A Query tab
  is `getByRole('link', { name: query.title })`, not a button.
- **The sidebar `+` that adds a Query or a Chart is named after its section.**
  Use `getByRole('button', { name: 'Add Charts' })`, and the same shape for
  `Add Queries` and `Add Dashboards`. The row `X` is `Remove <title>`. The
  second header button is `New folder in <section>`.
- **Two components draw the workbook sidebar, and they look almost the same.**
  `WorkbookSidebarFolders.vue` draws Queries and Charts.
  `WorkbookSidebarListSection.vue` draws Dashboards only. Edit the right one.
  Check the rendered DOM before you trust a source read.
- **Charts render as SVG**, so axis labels, legend entries and data labels are
  real `<text>` nodes. `getByText('delivered')` reaches them. Map charts are the
  one exception and render to canvas. See "Asserting on a chart" below.
- **The results table is a real `<table>`.** Body rows are role `row` and cells
  are role `cell`.

### The results table, exactly

Three traps. Read this before you assert on rows.

1. Header cells are `<td>` inside `<thead>`, so their role is **`cell`**, not
   `columnheader`. Each header cell carries `data-column-name="<column>"`.
2. `<tbody>` ends with a spacer `<tr>` that holds no cells. A bare
   `getByRole('row')` count is therefore header rows plus data rows plus one.
3. Every data row starts with a row-number cell holding `1`, `2`, `3` and so on.

Count data rows through a CSS locator, with the reason on the line above:

```ts
// locator: <thead> uses <td>, and <tbody> ends with a cell-less spacer row, so
// role=row over-counts. `:has(td)` keeps only real data rows.
const dataRows = page.locator('tbody tr:has(td)')
await expect(dataRows).toHaveCount(100)
```

The query editor shows one page of 100 rows, so 100 is the count an unlimited
query over `orders` gives.

The footer reads `Showing 1–100 of 2,000 rows`, but only when the result needs
more than one page, and the total appears only after a count fetch. Do not
assert on it unless your flow is about paging.

### Asserting on a chart

A chart is assertable in text. Insights renders echarts in SVG mode, so every
axis label, legend entry and data label is a real `<text>` node in the DOM, and
no chart except Map draws to a canvas.

Scope to the chart. The result preview under the chart builder repeats every
category label, so an unscoped `getByText('delivered')` matches twice.

```ts
// locator: echarts writes `_echarts_instance_` on the element it renders into,
// so this names the chart and nothing else on the page.
const chart = page.locator('[_echarts_instance_]')
await expect(chart.getByText('delivered')).toBeVisible()
```

Three things the chart will not give you.

1. **Category order is not stable between runs.** Assert that a label is there,
   never where it is.
2. **Values are abbreviated.** A bar of 1,778 renders its axis tick and its data
   label as `1.8K`. Assert the abbreviation, or read the exact number from the
   result preview table below the chart.
3. **Data labels are off by default.** Only axis ticks and category labels are
   in the DOM until a flow turns `Show Data Labels` on.

## What a flow test may assert

**Only what a user can see.** Rendered text, row counts, chart labels, chart
values, visible state, an enabled or disabled control, a URL.

Banned in this suite:

- A document field read back over REST to prove the UI worked.
- A compiled SQL string.
- An operations JSON array.
- A network response body.

Those belong in `insights/tests/`. If your flow can only be checked that way,
say so in your report and leave the flow out.

Seeding over REST is fine and expected. The ban is on **asserting** over REST.
`seeding.spec.ts` is the one exception, because it tests the seeding layer.

### Web-first assertions

Always assert on a locator, never on an awaited value.

```ts
await expect(page.getByText('Order Analysis')).toBeVisible() // yes
expect(await page.getByText('Order Analysis').isVisible()).toBe(true) // no
```

`page.waitForTimeout` is banned. So are `waitForSelector`, `waitForNavigation`
and `networkidle`. If a step needs a wait, assert on the element that appears
when the step finishes. Raise the assertion timeout rather than sleeping:

```ts
await expect(page.getByText('delivered')).not.toHaveCount(0, { timeout: 15_000 })
```

### Testing a race

A race needs a request held open, not a sleep. `page.route` gives you the
window: intercept the call, hold it, act while it is in flight, then let it go.
`holdFirstWrite` in `charts.spec.ts` does this for a `set_value` — copy it
rather than reaching for a timeout, which lint refuses anyway.

### No conditionals

An `if` in a test means the test does not know what it asserts. Lint rejects it.
Split the branches into two tests, or seed the state you need.

### Autosave

Every editor in this app autosaves. `useDocumentResource` sends the save 1.5
seconds after the document's first unsaved change. An edit made while that save
is in flight survives it: `updateDocState` merges the answer instead of
replacing the document, and writes the kept edit straight after. So a flow may
assert between two edits of one interaction.

**An assertion still does not mean the save has landed.** The save and the query
execution are two requests, and the results usually arrive first. A flow that
reloads the page must assert on something the save wrote before it reloads.

**Seed what the flow is not about.** A filter the flow only applies is a
fixture, not a click. `createDashboard` seeds filter items for exactly this.
Seed the config a user would leave behind, not the defaults the app fills in —
`transformChartDoc` and the dashboard transform set those on load.

## The demo dataset

`insights/setup/demo_data/spec.py` generates it. The Data Source is `demo_data`.
It is deterministic from one seed, so these numbers hold on every run.

| Table | Rows | Columns you will use |
| --- | --- | --- |
| `geolocation` | 150 | `geolocation_zip_code_prefix`, `geolocation_city`, `geolocation_state`, `geolocation_lat`, `geolocation_lng` |
| `customers` | 400 | `customer_id`, `customer_unique_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state` |
| `sellers` | 60 | `seller_id`, `seller_zip_code_prefix`, `seller_city`, `seller_state` |
| `products` | 120 | `product_id`, `product_category_name`, `product_weight_g`, `product_length_cm`, `product_height_cm`, `product_width_cm` |
| `orders` | 2000 | `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date` |
| `orderitems` | 4881 | `order_id`, `order_item_id`, `product_id`, `seller_id`, `shipping_limit_date`, `price`, `freight_value` |
| `orderpayments` | 2974 | `order_id`, `payment_sequential`, `payment_type`, `payment_installments`, `payment_value` |
| `orderreviews` | 2000 | `review_id`, `order_id`, `review_score`, `review_comment_title`, `review_comment_message`, `review_creation_date`, `review_answer_timestamp` |

Category values, safe to assert on:

- `order_status`: `delivered`, `shipped`, `canceled`, `invoiced`, `processing`,
  `unavailable`. About 88% are `delivered`.
- `payment_type`: `credit_card`, `boleto`, `voucher`, `debit_card`.
- `review_score`: 1 to 5.
- `product_category_name`: 12 Portuguese category names, `cama_mesa_banho` the
  most common.
- Cities and states are Brazilian, for example `sao paulo` and `SP`.
- `order_purchase_timestamp` runs from 2016-09-01 to 2018-10-31, which is 26
  distinct months.

All 8 declared foreign keys join with zero orphans, so any join in the spec
returns rows.

**One thing the data does not support.** `orderpayments.payment_value` is drawn
independently of the line items it pays for. A test that reconciles a payment
total against a price total will fail.

Prefer a shape assertion over an exact number where the flow allows it. Assert
that a filter removes a value, rather than that the count lands on 1,437. Exact
counts from the table above are fine, because the generator is seeded.

The seeded **Order Analysis** Workbook holds:

| Kind | Title | Shape |
| --- | --- | --- |
| Query | Undelivered Orders | 459 rows |
| Chart | Order per Month | Bar, 23 points |
| Chart | Order per Status | Donut, 5 slices |
| Chart | Top Level Metrics | Number |
| Chart | Order Value per Month per Status | Table |
| Dashboard | Order Analysis | holds all four |

## Characterization baseline

**Today's behavior is correct by definition.** This suite records what Insights
does now, so a future change that breaks it is visible.

A test that disagrees with the code is a wrong test. Fix the test.

If you find genuine broken behavior, **file it as a new ticket on the map** at
`docs/projects/e2e-tests/issues/NN-<slug>.md`, and write a test that records the
current behavior. Never fix product code inside a test change. A change that
mixes the two hides the fix and breaks the baseline.

The one edit to `frontend/src2/` this suite allows is an accessible name — a
`:label` on an icon-only Button, or a `data-testid`. Both are inert.

## Running the suite

Nothing in `playwright.config.ts` starts a server. The suite needs a running
site with the frontend built and the demo Data Source seeded.

```sh
cd frontend && yarn build                     # /insights needs the built entry
E2E_BASE_URL=http://<site>:<port> npx playwright test
```

`npx playwright test --list` prints every flow and ends with the count. Read the
suite's size there rather than from a number written down somewhere. The total
counts the setup and the teardown project on top of the flows in
`e2e/tests/*.spec.ts`.

`yarn dev` cannot host the suite. Vite serves its own `index.html` for
`/insights`, so the page carries no `window.csrf_token` and the setup project
fails. Point the suite at the bench port.

If the setup project reports a missing Data Source, seed it once:

```sh
CI=1 bench --site <site> execute insights.setup.setup_wizard.setup_demo_data
```

`CI` is what makes the generated, deterministic dataset the one that lands.
Without it the setup downloads the production dataset, whose row counts are not
the ones this file lists.

### Raise the background job ceiling, once per site

```sh
bench --site <site> set-config max_queued_jobs 100000 --parse
```

A full run enqueues about 300 background jobs. Most are the link cleanup behind
the Workbook deletes the fixtures make, and the rest are query reference syncs.
One `bench worker` drains about two a second, so the queue grows by about 190
jobs a run and never empties between runs.

Frappe caps the queue at `max_queued_jobs`, which is 500 plus 50 per site on the
bench. Past the cap it answers **every write that enqueues a job** with a 503
`QueueOverloaded`. Seeding, teardown and the app's own autosave all take that
route, so the failure lands on whichever tests happen to be running. One
measured run lost 17 of 54 tests across four spec files this way, and the next
run was clean because the queue had drained.

The suite's REST client retries a 503 and a 508 with backoff, because Frappe
uses both to mean "retry later". That covers a burst. It does not cover a queue
that never drains, so raise the ceiling.

**A mass failure that spans unrelated spec files is this, until proved
otherwise.** Read the queue before you read the tests:

```sh
redis-cli -p <redis_queue_port> llen "rq:queue:<bench>:default"
```

### Two workers, in CI and locally

`playwright.config.ts` pins `workers: 2`, in CI and locally.

Two ran green over a full run in 2.0 minutes. Three ran green over twelve full
runs, then lost a flow. That is the whole measurement.

**The cause is not established.** The server does cap live queries at 2, through
`_default_limit()` in `frappe/concurrency_limiter.py`. The client absorbs that
cap on its own. `src2/query/execution_queue.ts` keeps 6 queries in flight and
retries a rejection 8 times with backoff, so one tab already sits well above the
ceiling and still renders. Do not treat the cap as the reason.

**A cheaper lever exists.** Lower `MAX_IN_FLIGHT` under test before you change
the worker count. Nobody has tried it.

Serving CI under gunicorn was tried and reverted. Every test timed out and the
run took 16 minutes.

**Raising this is untested.** Measure over at least five full runs at the new
count before you believe a result.

## Quarantine

Tag a flaky test `@quarantine` and it leaves every run, which keeps the merge
gate green while you fix it. Fix or delete it inside a week, because a
quarantine list nobody clears is worse than a red test.

Quarantine by tag, never by skip:

```ts
// quarantined 2026-08-27, ticket 21
test('a user drills down from a chart into rows', { tag: '@quarantine' }, async ({ page }) => {
```

The merge gate excludes `@quarantine`. `test.skip` and `test.only` are lint
errors, so the tag is the only route. Open a ticket on the map when you
quarantine, and put its number in the comment above the test.

## Lint

`yarn lint:e2e` runs `eslint-plugin-playwright` over this folder. Run it before
you report done. It must report no errors.

Errors, all of them correctness:

| Rule | What it stops |
| --- | --- |
| `no-conditional-in-test`, `no-conditional-expect` | branching tests |
| `no-wait-for-timeout`, `no-wait-for-selector`, `no-wait-for-navigation`, `no-networkidle` | hard waits |
| `no-focused-test`, `no-skipped-test` | `test.only`, `test.skip` |
| `missing-playwright-await`, `valid-expect`, `valid-expect-in-promise`, `no-useless-await` | missing and stray awaits |
| `prefer-web-first-assertions` | `expect(await ...isVisible())` |
| `expect-expect` | a test that asserts nothing |
| `require-top-level-describe` | a file without its area describe |
| `no-element-handle`, `no-eval`, `no-page-pause`, `no-unsafe-references` | reaching past the locator API |
| `valid-title`, `valid-test-tags` | malformed titles and tags |

Style rules stay warnings: `no-nth-methods`, `no-force-option`,
`prefer-locator`, `prefer-to-have-count`, `no-get-by-title` and the rest. A
warning says your locator is fragile. Read it before you ignore it.

## Worked examples

### An author flow

```ts
import { expect, test } from '../fixtures'
import { INSIGHTS_PATH } from '../helpers/auth'

test.describe('query', () => {
	test('a user adds a filter and the row count falls', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		// A header cell proves the results loaded. <thead> uses <td>, so the role
		// is cell.
		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'delivered' })).not.toHaveCount(0)

		await page.getByRole('button', { name: 'Filter' }).click()
		await page.getByPlaceholder('Column').fill('order_status')
		await page.getByRole('option', { name: 'order_status' }).click()
		await page.getByPlaceholder('Value').fill('canceled')
		await page.getByRole('button', { name: 'Apply' }).click()

		await expect(page.getByRole('cell', { name: 'canceled' })).not.toHaveCount(0)
		await expect(page.getByRole('cell', { name: 'delivered' })).toHaveCount(0)
	})
})
```

Note what it does. It seeds the Workbook and Query over REST, names
`demoDataSource` to record the data dependency, clicks only the flow under test,
and asserts on what a user sees.

### A verify flow

```ts
import { expect, test } from '../fixtures'
import { INSIGHTS_PATH } from '../helpers/auth'

test.describe('dashboard', () => {
	test('a dashboard loads with all charts rendered', async ({
		page,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { workbook, dashboard, chart } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)

		await expect(page.getByText(chart.title)).toBeVisible()
		// Charts render as SVG, so a legend entry is a real text node. Several
		// nodes can carry the label, so assert a count instead of visibility.
		await expect(page.getByText('delivered')).not.toHaveCount(0)
	})
})
```

### A permission flow

```ts
test.describe('permissions', () => {
	test('a viewer sees only the workbooks granted to them', async ({ viewerPage, workbook }) => {
		await viewerPage.goto(`${INSIGHTS_PATH}/workbook`)
		await expect(viewerPage.getByText(workbook.title)).toHaveCount(0)
	})
})
```

`viewerPage` is a second browser context. Use `page` for the admin and
`viewerPage` for the viewer in the same test when a flow needs both.

## Before you report done

- [ ] Every title is a flow sentence in product language.
- [ ] One `test.describe` per file, named after the area.
- [ ] Every test names the fixtures it depends on.
- [ ] No `if`, no sleep, no assertion on a REST field.
- [ ] Every CSS locator carries a `// locator:` reason.
- [ ] `yarn lint:e2e` reports no errors.
- [ ] Any genuine bug is a new ticket, not a code fix.
- [ ] Report which flows you could not reach, and why.
