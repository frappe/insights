# 06 — The standards doc and the lint config

Type: task
Status: resolved
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

## Answer

The doc is **`frontend/e2e/AGENTS.md`**, not `frontend/tests/AGENTS.md`. Ticket
05 built the layer at `frontend/e2e/`, and an agent working in
`frontend/e2e/tests/` picks up an `AGENTS.md` at that folder's root for free.

### What the doc covers

Every rule this ticket fixed, plus what six parallel agents need to converge:

- The locator ladder, and **what this app actually gives you**. `src2` ships
  zero `data-testid` and one `aria-labelledby`, so `getByTestId` is unavailable
  until someone adds an attribute. frappe-ui `Button` renders
  `<button aria-label="{label}">`, so `getByRole('button', { name })` is the
  workhorse. Icon-only buttons that pass no `label` have no accessible name, and
  the doc prefers adding `:label` in `src2` over a CSS locator.
- **Charts render as SVG.** `BaseChart.vue` picks the SVG renderer for every
  chart type except Map, so axis labels and legend entries are real `<text>`
  nodes that `getByText` reaches. This shrinks the visual-regression fog the map
  still lists as open.
- **Three traps in the results table**, measured from `DataTable.vue`. `<thead>`
  uses `<td>`, so a header is role `cell` and not `columnheader`. `<tbody>` ends
  with a cell-less spacer `<tr>`, so `getByRole('row')` over-counts. The footer
  count needs a separate fetch. The doc gives one sanctioned CSS locator with
  its reason.
- The fixture ladder from ticket 05, and three rules that make a dependency
  visible: name `demoDataSource` even when a Workbook fixture pulls it in, never
  seed in `beforeAll`, never depend on another test's record.
- **The generated demo dataset** from `insights/setup/demo_data/spec.py` — all 8
  tables, their row counts, their columns, and the category values that are safe
  to assert on. Plus the one thing it does not support: `payment_value` is drawn
  independently of the line items, so no test may reconcile the two.
- The seeded **Order Analysis** Workbook, by title and shape, for verify flows.
- Verify versus author, chosen by what the flow sentence says.
- Characterization baseline, quarantine at 7 days by `@quarantine` tag, and the
  assertion ban on document fields, SQL strings, operations JSON and response
  bodies.
- Three worked examples. All three lint clean and type-check.

**Quarantine is a tag, not a skip.** `no-skipped-test` is an error, so
`test.skip` cannot be the quarantine route. Ticket 07 must exclude
`@quarantine` from the merge gate with `--grep-invert`.

### Lint

`eslint-plugin-playwright@2.11.0` added to `frontend/package.json`, wired as two
`overrides` blocks inside the existing `frontend/.eslintrc.json`. No parallel
config. `yarn lint:e2e` is the command.

**Errors** (correctness) on `e2e/**/*.ts`: `missing-playwright-await`,
`no-element-handle`, `no-eval`, `no-networkidle`, `no-page-pause`,
`no-standalone-expect`, `no-unnecessary-assertions`, `no-unsafe-references`,
`no-unused-locators`, `no-useless-await`, `no-wait-for-navigation`,
`no-wait-for-selector`, `no-wait-for-timeout`, `prefer-web-first-assertions`,
`valid-describe-callback`, `valid-expect`, `valid-expect-in-promise`,
`valid-test-tags`, `valid-title`.

**Errors** on `e2e/**/*.spec.ts` only: `expect-expect`, `no-conditional-expect`,
`no-conditional-in-test`, `no-focused-test`, `no-skipped-test`,
`require-top-level-describe` with `maxTopLevelDescribes: 1`. These are scoped to
spec files because `auth.setup.ts` legitimately has no assertion and no
describe.

**Warnings** (style): `consistent-spacing-between-blocks`, `max-nested-describe`,
`no-duplicate-hooks`, `no-force-option`, `no-get-by-title`, `no-nested-step`,
`no-nth-methods`, `no-useless-not`, `prefer-hooks-in-order`,
`prefer-hooks-on-top`, `prefer-locator`, `prefer-native-locators`,
`prefer-to-have-count`, `prefer-to-have-length`.

`require-top-level-describe` is an error and not a warning because ticket 08
reads the file structure to generate the inventory.

### Proof the rules fire

A deliberately bad spec was written, linted, and deleted. Every correctness rule
reported an error:

```
4:7   error  Unexpected focused test                     playwright/no-focused-test
6:9   error  Unexpected use of page.waitForTimeout()     playwright/no-wait-for-timeout
7:9   error  Unexpected use of page.waitForSelector()    playwright/no-wait-for-selector
8:31  error  Unexpected use of networkidle               playwright/no-networkidle
9:3   error  Avoid having conditionals in tests          playwright/no-conditional-in-test
10:4  error  Avoid calling `expect` conditionally        playwright/no-conditional-expect
12:3  error  'toBeVisible' must be awaited or returned   playwright/missing-playwright-await
16:2  error  Test has no assertions                      playwright/expect-expect
16:7  error  Unexpected use of the `.skip()` annotation  playwright/no-skipped-test
```

A second probe proved the error/warning split holds:

```
5:3   error    Replace isVisible() with toBeVisible()    playwright/prefer-web-first-assertions
6:47  warning  Use toHaveCount() instead                 playwright/prefer-to-have-count
8:41  warning  Unexpected use of nth()                   playwright/no-nth-methods
9:60  warning  Unexpected use of { force: true } option  playwright/no-force-option
```

A third proved `require-top-level-describe` rejects a bare `test` at file level.

The three worked examples from the doc were pasted into a spec file. `eslint`
and `tsc --noEmit -p e2e/tsconfig.json` both passed, which proves the examples
compile against the real fixtures. `yarn lint:e2e` is clean on the committed
suite.

### The eslint setup was dead, and is now repaired

`frontend/.eslintrc.json` had never run. Three faults:

1. A trailing comma after `"no-unused-vars": "off",`. ESLint parses the file
   with `JSON.parse`, so it failed to read the config at all.
2. `plugin:prettier/recommended` was in `extends`, but neither
   `eslint-plugin-prettier` nor `eslint-config-prettier` was installed.
3. `@typescript-eslint/parser` was named in `parserOptions`, and was not
   installed either.

All three are fixed. `parserOptions` also gained `sourceType: "module"`, without
which every `import` was a parse error. Four devDependencies added:
`eslint-plugin-playwright`, `eslint-plugin-prettier`, `eslint-config-prettier`,
`@typescript-eslint/parser`.

This repair widens the blast radius past `e2e/`. `eslint` now loads for
`src2/**` too, and nothing has ever linted there. `yarn lint:e2e` is scoped to
`e2e` on purpose, so the suite gate stays clean. Whether `src2` gets a lint gate
is a separate call.

### One lint exemption

`helpers/auth.ts` waits for `networkidle` after loading the Insights page,
because nothing on the page reports that `window.csrf_token` is set. The line
now carries an `eslint-disable-next-line playwright/no-networkidle` with the
reason. It runs once per run in the setup project. The rule stays an error
everywhere else, helpers included.

### For ticket 07

- Exclude `@quarantine` from the merge gate.
- Add `yarn lint:e2e` to the CI job. It is a second gate on the same pull
  request and costs seconds.
- `@playwright/test` resolves to 1.57.0 while `package.json` declares `^1.32.1`.
  The `{ tag }` option needs 1.42, so the declared floor is below what the
  quarantine mechanism requires. Raise it.
